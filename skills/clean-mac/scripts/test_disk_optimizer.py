#!/usr/bin/env python3
"""Regression tests for guarded rollback-item handling."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import time
import unicodedata
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).with_name("disk_optimizer.py")
SPEC = importlib.util.spec_from_file_location("disk_optimizer", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"无法加载测试目标：{SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def call_json(function, args):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = function(args)
    return code, json.loads(output.getvalue())


class StagedCleanupTests(unittest.TestCase):
    def test_path_guard_accepts_only_top_level_cleanup_entry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "trash"
            root.mkdir()
            valid = root / "build-target.cleanup"
            valid.mkdir()
            self.assertEqual(MODULE.staged_path(valid, root), valid)
            migrated = root / "library.migrated"
            migrated.mkdir()
            self.assertEqual(MODULE.staged_path(migrated, root), migrated)

            with self.assertRaises(MODULE.OptimizerError):
                MODULE.staged_path(root / "keep.txt", root)
            with self.assertRaises(MODULE.OptimizerError):
                MODULE.staged_path(root / "nested" / "build-target.cleanup", root)

    def test_stage_cleanup_rolls_back_when_a_later_move_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            root.mkdir()
            first = root / ".next"
            second = root / "node_modules"
            first.mkdir()
            second.mkdir()
            (first / "cache.bin").write_bytes(b"first")
            (second / "module.bin").write_bytes(b"second")
            rollback_root = Path(temp_dir) / "trash"
            real_move = MODULE.shutil.move

            def move_with_fixture_failure(source, destination):
                if Path(source).resolve() == second.resolve():
                    raise OSError("locked fixture")
                return real_move(source, destination)

            with patch.object(MODULE.shutil, "move", side_effect=move_with_fixture_failure):
                code, result = call_json(
                    MODULE.run_stage_cleanup,
                    argparse.Namespace(
                        path=[first, second],
                        protected=[],
                        rollback_root=rollback_root,
                        recreate=True,
                        execute=True,
                        confirm="STAGE_REBUILDABLES",
                        output=None,
                    ),
                )

            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "rolled-back")
            self.assertEqual([item["status"] for item in result["items"]], ["rolled-back", "not-started"])
            self.assertTrue((first / "cache.bin").exists())
            self.assertTrue((second / "module.bin").exists())
            self.assertFalse(rollback_root.exists() and any(rollback_root.iterdir()))

    def test_list_and_purge_preserve_other_trash_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "trash"
            root.mkdir()
            cleanup = root / "cache.cleanup"
            cleanup.mkdir()
            (cleanup / "payload.bin").write_bytes(b"rebuildable")
            keep = root / "camera.CR3"
            keep.write_bytes(b"keep")

            list_code, listed = call_json(
                MODULE.run_list_staged,
                argparse.Namespace(rollback_root=root, output=None),
            )
            self.assertEqual(list_code, 0)
            self.assertEqual(
                [Path(item["path"]).resolve() for item in listed["items"]],
                [cleanup.resolve()],
            )

            preview_code, preview = call_json(
                MODULE.run_purge_staged,
                argparse.Namespace(
                    path=[cleanup],
                    rollback_root=root,
                    execute=False,
                    confirm="",
                    output=None,
                ),
            )
            self.assertEqual(preview_code, 0)
            self.assertEqual(preview["method"], "direct-filesystem")
            self.assertFalse(preview["finder"])
            self.assertTrue(cleanup.exists())

            purge_code, result = call_json(
                MODULE.run_purge_staged,
                argparse.Namespace(
                    path=[cleanup],
                    rollback_root=root,
                    execute=True,
                    confirm="PURGE_STAGED",
                    output=None,
                ),
            )
            self.assertEqual(purge_code, 0)
            self.assertEqual(result["status"], "purged")
            self.assertFalse(cleanup.exists())
            self.assertTrue(keep.exists())


class MigratedRollbackTests(unittest.TestCase):
    """A .migrated entry is purgeable only while the journal proves the archive copy is live."""

    def migrate(self, base):
        source = base / "home" / "Music" / "library"
        source.mkdir(parents=True)
        (source / "Beyoncé - Halo.mp3").write_bytes(b"audio")
        archive = base / "archive"
        archive.mkdir()
        rollback_root = base / "Trash" / "lov-clean-mac-20260926-migrations"
        with patch.object(MODULE, "referenced", return_value=False):
            code, event = call_json(
                MODULE.run_migrate,
                argparse.Namespace(
                    source=source,
                    archive_root=archive,
                    category="media",
                    destination=None,
                    protected=[],
                    rollback_root=rollback_root,
                    verify="checksum",
                    reserve_gb=0.0,
                    preserve_xattrs=False,
                    no_link=False,
                    allow_same_volume=True,
                    execute=True,
                    confirm_source=str(source.resolve()),
                    output=None,
                ),
            )
        self.assertEqual(code, 0)
        return source, archive, rollback_root, Path(event["rollback"]), Path(event["destination"])

    def list_staged(self, rollback_root, archive_roots):
        return call_json(
            MODULE.run_list_staged,
            argparse.Namespace(rollback_root=rollback_root, archive_root=archive_roots, output=None),
        )

    def purge(self, rollback_root, paths, archive_roots, execute):
        return call_json(
            MODULE.run_purge_staged,
            argparse.Namespace(
                path=paths,
                rollback_root=rollback_root,
                archive_root=archive_roots,
                execute=execute,
                confirm="PURGE_STAGED" if execute else "",
                output=None,
            ),
        )

    def test_verified_migration_rollback_is_listed_and_purged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, archive, rollback_root, rollback, destination = self.migrate(Path(temp_dir))
            keep = rollback_root / "unrelated.txt"
            keep.write_bytes(b"keep")

            list_code, listed = self.list_staged(rollback_root, [archive])
            self.assertEqual(list_code, 0)
            self.assertEqual([item["status"] for item in listed["items"]], ["pending"])
            self.assertEqual(listed["items"][0]["migration"]["destination"], str(destination))
            self.assertEqual(listed["total_bytes"], len(b"audio"))

            preview_code, preview = self.purge(rollback_root, [rollback], [archive], execute=False)
            self.assertEqual(preview_code, 0)
            self.assertTrue(rollback.exists())

            purge_code, result = self.purge(rollback_root, [rollback], [archive], execute=True)
            self.assertEqual(purge_code, 0)
            self.assertEqual(result["status"], "purged")
            self.assertEqual([item["status"] for item in result["items"]], ["purged"])
            self.assertFalse(rollback.exists())
            self.assertTrue(keep.exists())
            self.assertTrue(source.is_symlink())
            self.assertEqual((source / "Beyoncé - Halo.mp3").read_bytes(), b"audio")

    def test_migration_rollback_without_journal_is_blocked_and_refused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _source, _archive, rollback_root, rollback, _destination = self.migrate(Path(temp_dir))

            _code, listed = self.list_staged(rollback_root, [])
            self.assertEqual([item["status"] for item in listed["items"]], ["blocked"])
            self.assertEqual(listed["total_bytes"], 0)
            with self.assertRaisesRegex(MODULE.OptimizerError, "迁移日志"):
                self.purge(rollback_root, [rollback], [], execute=True)
            self.assertTrue(rollback.exists())

    def test_migration_rollback_is_refused_when_archive_copy_is_unreachable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            _source, archive, rollback_root, rollback, destination = self.migrate(base)
            destination.rename(base / "ejected")

            _code, listed = self.list_staged(rollback_root, [archive])
            self.assertEqual([item["status"] for item in listed["items"]], ["blocked"])
            with self.assertRaisesRegex(MODULE.OptimizerError, "归档目标不存在"):
                self.purge(rollback_root, [rollback], [archive], execute=True)
            self.assertTrue(rollback.exists())

    def test_migration_rollback_is_refused_when_source_link_changed(self):
        def replace_with_directory(source, _base):
            source.unlink()
            source.mkdir()

        def repoint_link(source, base):
            other = base / "other"
            other.mkdir()
            source.unlink()
            source.symlink_to(other, target_is_directory=True)

        for change, message in ((replace_with_directory, "符号链接"), (repoint_link, "未指向")):
            with self.subTest(change=change.__name__), tempfile.TemporaryDirectory() as temp_dir:
                base = Path(temp_dir)
                source, archive, rollback_root, rollback, _destination = self.migrate(base)
                change(source, base)
                with self.assertRaisesRegex(MODULE.OptimizerError, message):
                    self.purge(rollback_root, [rollback], [archive], execute=True)
                self.assertTrue(rollback.exists())

    def test_purge_rechecks_migration_right_before_deleting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            _source, archive, rollback_root, rollback, destination = self.migrate(base)
            cleanup = rollback_root / "cache.cleanup"
            cleanup.mkdir()
            (cleanup / "payload.bin").write_bytes(b"rebuildable")
            real_rmtree = MODULE.shutil.rmtree

            def rmtree_then_eject(target, *args, **kwargs):
                real_rmtree(target, *args, **kwargs)
                if destination.exists():
                    destination.rename(base / "ejected")

            with patch.object(MODULE.shutil, "rmtree", side_effect=rmtree_then_eject):
                code, result = self.purge(rollback_root, [cleanup, rollback], [archive], execute=True)

            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "partial-failure")
            self.assertEqual([item["status"] for item in result["items"]], ["purged", "error"])
            self.assertFalse(cleanup.exists())
            self.assertTrue(rollback.exists())


class CopyVerificationTests(unittest.TestCase):
    """HFS+ archive volumes return NFD names for files an APFS source stores in NFC."""

    NAMES = (
        "Beyoncé - Halo.mp3",
        "Acetre - Mãe Bruxa.mp3",
        "DJ SLY - いのちの名前 ~ジブリ・メドレー~.mp3",
    )

    def make_pair(self, base):
        source = base / "source"
        destination = base / "destination"
        for root, form in ((source, "NFC"), (destination, "NFD")):
            album = root / unicodedata.normalize(form, "Mãe")
            album.mkdir(parents=True)
            for name in self.NAMES:
                (album / unicodedata.normalize(form, name)).write_bytes(name.encode("utf-8"))
        if sorted(os.listdir(source / "Mãe")) == sorted(os.listdir(next(destination.iterdir()))):
            self.skipTest("文件系统会统一 Unicode 规范化形式，无法构造 NFD 目标")
        return source, destination

    def test_nfd_destination_names_match_nfc_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, destination = self.make_pair(Path(temp_dir))
            hashed = []
            real_hash = MODULE.hash_file

            def recording_hash(path):
                hashed.append(str(path))
                return real_hash(path)

            with patch.object(MODULE, "hash_file", side_effect=recording_hash):
                result = MODULE.verify_copy(source, destination, "checksum")

            self.assertEqual(result["checksummed_files"], len(self.NAMES))
            on_disk = {
                os.path.join(root, name) for root, _dirs, files in os.walk(str(destination)) for name in files
            }
            self.assertEqual({item for item in hashed if item.startswith(str(destination))}, on_disk)

    def test_checksum_still_detects_changed_content_behind_nfd_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, destination = self.make_pair(Path(temp_dir))
            album = next(destination.iterdir())
            target = album / unicodedata.normalize("NFD", self.NAMES[0])
            target.write_bytes(b"x" * len(self.NAMES[0].encode("utf-8")))
            MODULE.verify_copy(source, destination, "metadata")
            with self.assertRaisesRegex(MODULE.OptimizerError, "内容哈希不一致"):
                MODULE.verify_copy(source, destination, "checksum")

    def test_normalization_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            names = [unicodedata.normalize(form, "Beyoncé") for form in ("NFC", "NFD")]
            with patch.object(MODULE.os, "walk", return_value=iter([(str(root), names, [])])):
                with self.assertRaisesRegex(MODULE.OptimizerError, "Unicode 规范化后路径冲突"):
                    MODULE.metadata_manifest(root)


class ProtectedWorkspaceTests(unittest.TestCase):
    def test_screen_studio_recordings_and_containing_parent_are_protected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            screen_studio = Path(temp_dir) / "Screen Studio"
            recordings = screen_studio / "Screen Studio Recordings"
            recording_cache = recordings / "Current Recording" / "Caches"
            with patch.object(MODULE, "builtin_protected_paths", return_value=(recordings.resolve(),)):
                self.assertTrue(MODULE.protected(screen_studio, []))
                self.assertTrue(MODULE.protected(recordings, []))
                self.assertTrue(MODULE.protected(recording_cache, []))

    def test_stage_cleanup_rejects_rebuildable_name_inside_protected_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            recordings = Path(temp_dir) / "Screen Studio Recordings"
            recording_cache = recordings / "Current Recording" / "Caches"
            recording_cache.mkdir(parents=True)
            with patch.object(MODULE, "builtin_protected_paths", return_value=(recordings.resolve(),)):
                with self.assertRaisesRegex(MODULE.OptimizerError, "候选命中保护边界"):
                    MODULE.run_stage_cleanup(
                        argparse.Namespace(
                            path=[recording_cache],
                            protected=[],
                            rollback_root=Path(temp_dir) / "trash",
                            recreate=False,
                            execute=False,
                            confirm="",
                            output=None,
                        )
                    )

    def test_migrate_rejects_protected_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            recordings = Path(temp_dir) / "Screen Studio Recordings"
            recordings.mkdir()
            archive = Path(temp_dir) / "archive"
            archive.mkdir()
            with patch.object(MODULE, "builtin_protected_paths", return_value=(recordings.resolve(),)):
                with self.assertRaisesRegex(MODULE.OptimizerError, "迁移源命中保护边界"):
                    MODULE.run_migrate(
                        argparse.Namespace(source=recordings, archive_root=archive, protected=[])
                    )

    def test_explicit_protected_child_also_blocks_parent_mutation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / "parent"
            protected_child = parent / "keep"
            self.assertTrue(MODULE.protected(parent, [protected_child]))

    def test_symlinked_protected_workspace_keeps_its_original_parent_protected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            screen_studio = Path(temp_dir) / "Screen Studio"
            screen_studio.mkdir()
            recordings_link = screen_studio / "Screen Studio Recordings"
            external_recordings = Path(temp_dir) / "external-recordings"
            external_recordings.mkdir()
            recordings_link.symlink_to(external_recordings, target_is_directory=True)
            with patch.object(MODULE, "builtin_protected_paths", return_value=(recordings_link,)):
                self.assertTrue(MODULE.protected(screen_studio, []))
                self.assertTrue(MODULE.protected(external_recordings, []))


class ReferencedPathTests(unittest.TestCase):
    """A build directory stops being rebuildable once something else loads from it."""

    @contextlib.contextmanager
    def references(self, link_entries=(), unpacked=()):
        with patch.object(MODULE, "link_host_entries", return_value=list(link_entries)), patch.object(
            MODULE, "chromium_unpacked_paths", return_value=list(unpacked)
        ):
            MODULE.referenced_paths.cache_clear()
            try:
                yield
            finally:
                MODULE.referenced_paths.cache_clear()

    def test_symlinked_plugin_target_is_referenced(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            build = Path(temp_dir) / "project" / "dist"
            build.mkdir(parents=True)
            host = Path(temp_dir) / "vault" / ".obsidian" / "plugins"
            host.mkdir(parents=True)
            link = host / "my-plugin"
            link.symlink_to(build, target_is_directory=True)
            with self.references(link_entries=[link]):
                self.assertTrue(MODULE.referenced(build))
                self.assertTrue(MODULE.referenced(build.parent))
                self.assertFalse(MODULE.referenced(Path(temp_dir) / "unrelated"))

    def test_unpacked_extension_path_is_referenced(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            build = Path(temp_dir) / "extension" / "dist"
            build.mkdir(parents=True)
            with self.references(unpacked=[MODULE.lexical(build)]):
                self.assertTrue(MODULE.referenced(build))
                self.assertTrue(MODULE.referenced(build / "assets"))

    def test_chromium_profile_yields_only_unpacked_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            profile = home / "Library/Application Support/Chromium/Default"
            profile.mkdir(parents=True)
            (profile / "Secure Preferences").write_text(
                json.dumps(
                    {
                        "extensions": {
                            "settings": {
                                "aaa": {"location": 4, "path": "/abs/unpacked/dist"},
                                "bbb": {"location": 1, "path": "store-extension/1.0_0"},
                                "ccc": {"location": 4, "path": "relative/path"},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(MODULE.Path, "home", return_value=home):
                found = [str(item) for item in MODULE.chromium_unpacked_paths()]
            self.assertEqual(found, ["/abs/unpacked/dist"])

    def test_stage_cleanup_rejects_referenced_build_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            build = Path(temp_dir) / "project" / "dist"
            build.mkdir(parents=True)
            (build / "main.js").write_bytes(b"bundle")
            with self.references(unpacked=[MODULE.lexical(build)]):
                with self.assertRaisesRegex(MODULE.OptimizerError, "正被其它应用加载"):
                    MODULE.run_stage_cleanup(
                        argparse.Namespace(
                            path=[build],
                            protected=[],
                            rollback_root=Path(temp_dir) / "trash",
                            recreate=False,
                            execute=False,
                            confirm="",
                            output=None,
                        )
                    )

    def test_migrate_rejects_referenced_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "project" / "dist"
            source.mkdir(parents=True)
            archive = Path(temp_dir) / "archive"
            archive.mkdir()
            with self.references(unpacked=[MODULE.lexical(source)]):
                with self.assertRaisesRegex(MODULE.OptimizerError, "正被其它应用加载"):
                    MODULE.run_migrate(
                        argparse.Namespace(source=source, archive_root=archive, protected=[])
                    )

    def test_discover_artifacts_skips_referenced_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "projects"
            kept = root / "linked-plugin" / "dist"
            removable = root / "plain-app" / "dist"
            for directory in (kept, removable):
                directory.mkdir(parents=True)
                (directory / "main.js").write_bytes(b"x" * 16)
            with self.references(unpacked=[MODULE.lexical(kept)]):
                found = {item["path"] for item in MODULE.discover_artifacts(root, 0, [])}
            self.assertIn(str(removable), found)
            self.assertNotIn(str(kept), found)

    def test_classify_marks_referenced_directory_as_in_use(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            build = Path(temp_dir) / "dist"
            build.mkdir()
            with self.references(unpacked=[MODULE.lexical(build)]):
                self.assertEqual(MODULE.classify(build, []), "in-use")
            with self.references():
                self.assertIn(MODULE.classify(build, []), {"rebuildable", "recently-accessed"})


class AccessTimeTests(unittest.TestCase):
    def test_last_access_reports_newest_sample(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir) / "dist"
            directory.mkdir()
            recent = directory / "fresh.js"
            recent.write_bytes(b"fresh")
            stale = directory / "stale.js"
            stale.write_bytes(b"stale")
            os.utime(stale, (time.time() - 400 * 86400, time.time() - 400 * 86400))
            newest = MODULE.last_access(directory)
            self.assertIsNotNone(newest)
            self.assertGreater(newest, time.time() - 3600)

    def test_recently_accessed_is_false_for_old_access(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir) / "dist"
            directory.mkdir()
            stale = directory / "stale.js"
            stale.write_bytes(b"stale")
            old = time.time() - 400 * 86400
            os.utime(stale, (old, old))
            self.assertFalse(MODULE.recently_accessed(directory))
            self.assertTrue(MODULE.recently_accessed(directory, days=0) is False)


if __name__ == "__main__":
    unittest.main()
