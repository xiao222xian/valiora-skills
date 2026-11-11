#!/usr/bin/env python3
"""Plan and execute guarded macOS disk-space recovery operations."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


DECIMAL_GB = 1_000_000_000
DEFAULT_DATA_VOLUME = Path("/System/Volumes/Data")


def default_preferences_path() -> Path:
    explicit = os.environ.get("SKILL_PREFERENCES_PATH")
    if explicit:
        return Path(explicit).expanduser()
    config_dir = os.environ.get("SKILLS_CONFIG_DIR")
    if config_dir:
        return Path(config_dir).expanduser() / "preferences.json"
    return Path.home() / ".config" / "agent-skills" / "preferences.json"


DEFAULT_PROFILE = default_preferences_path()
PROFILE_KEY = "macos_disk_optimizer"
PURGE_CONFIRM = "PURGE_STAGED"
JOURNAL_NAME = ".lov-disk-optimizer-journal.jsonl"
CLEANUP_SUFFIX = ".cleanup"
MIGRATED_SUFFIX = ".migrated"
STAGED_SUFFIXES = (CLEANUP_SUFFIX, MIGRATED_SUFFIX)

REBUILDABLE_NAMES = {
    ".next",
    ".turbo",
    "Caches",
    "DerivedData",
    "DeviceSupport",
    "build",
    "dist",
    "models",
    "node_modules",
    "target",
    "_npx",
}
PROTECTED_PARTS = {
    ".git",
    "Keychains",
    "Mail",
    "Messages",
    "Photos Library.photoslibrary",
    "sessions",
}
BUILTIN_PROTECTED_RELATIVE_PATHS = (
    Path("Library") / "Application Support" / "Screen Studio" / "Screen Studio Recordings",
)
SKIP_DISCOVERY = {".git", ".Trash", "Library", "Photos Library.photoslibrary"}

CANDIDATE_REASONS = {
    "protected": "命中保护路径或敏感数据类型",
    "in-use": "其它应用正从该路径加载插件、扩展或链接命令",
    "recently-accessed": "名称可重建，但近期仍被读取；需人工确认",
    "rebuildable": "可重新生成的依赖、缓存或构建产物",
    "review-for-archive": "体积较大；需结合活跃状态与用户价值判断迁移",
}

ACTIVE_ACCESS_DAYS = 30
ACCESS_SAMPLE_LIMIT = 400
UNPACKED_EXTENSION_LOCATION = 4

# Chromium 系浏览器把未打包扩展的绝对路径写进 profile，目录本身没有链接可循。
CHROMIUM_PROFILE_GLOBS = (
    "Library/Application Support/Google/Chrome*/*/Secure Preferences",
    "Library/Application Support/Chromium/*/Secure Preferences",
    "Library/Application Support/BraveSoftware/*/*/Secure Preferences",
    "Library/Application Support/Microsoft Edge*/*/Secure Preferences",
    "Library/Application Support/Vivaldi/*/Secure Preferences",
    "Library/Application Support/Arc/User Data/*/Secure Preferences",
    "Library/Application Support/Citro Labs/*/*/Secure Preferences",
)

# 以符号链接安装插件、扩展或全局命令的宿主位置。
LINK_HOST_GLOBS = (
    ".vscode/extensions/*",
    ".vscode-insiders/extensions/*",
    ".claude/skills/*",
    ".claude/plugins/*",
    ".agents/skills/*",
    ".local/bin/*",
    "bin/*",
    "Library/pnpm/global/*/node_modules/*",
    "Library/pnpm/global/*/node_modules/@*/*",
)
ABSOLUTE_LINK_HOST_GLOBS = (
    "opt/homebrew/lib/node_modules/*",
    "opt/homebrew/lib/node_modules/@*/*",
    "usr/local/lib/node_modules/*",
    "usr/local/lib/node_modules/@*/*",
)
OBSIDIAN_REGISTRY_RELATIVE = Path("Library/Application Support/obsidian/obsidian.json")
OBSIDIAN_PLUGIN_RELATIVE = Path(".obsidian") / "plugins"


class OptimizerError(RuntimeError):
    """User-facing operational error."""


def emit(payload: Dict[str, Any], output: Optional[Path] = None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if output:
        output = output.expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def decimal_gb(value: int) -> float:
    return round(value / DECIMAL_GB, 2)


def resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def lexical(path: Path) -> Path:
    """Normalize a path without resolving symlinks."""
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def builtin_protected_paths() -> Tuple[Path, ...]:
    """Return application-managed workspaces that cleanup must never mutate."""
    return tuple(lexical(Path.home() / relative) for relative in BUILTIN_PROTECTED_RELATIVE_PATHS)


def paths_overlap(left: Path, right: Path) -> bool:
    """Return whether either path contains the other."""
    return left == right or is_relative_to(left, right) or is_relative_to(right, left)


def protected(path: Path, extra: Sequence[Path]) -> bool:
    path_variants = {lexical(path), resolved(path)}
    if any(part in PROTECTED_PARTS for variant in path_variants for part in variant.parts):
        return True
    protected_roots = (*builtin_protected_paths(), *extra)
    root_variants = {
        variant
        for root in protected_roots
        for variant in (lexical(root), resolved(root))
    }
    return any(paths_overlap(path_variant, root_variant) for path_variant in path_variants for root_variant in root_variants)


def chromium_unpacked_paths() -> List[Path]:
    """Directories a Chromium-family browser currently loads as unpacked extensions."""
    found: List[Path] = []
    home = Path.home()
    for pattern in CHROMIUM_PROFILE_GLOBS:
        for profile in home.glob(pattern):
            try:
                data = json.loads(profile.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            settings = (data.get("extensions") or {}).get("settings")
            if not isinstance(settings, dict):
                continue
            for entry in settings.values():
                if not isinstance(entry, dict) or entry.get("location") != UNPACKED_EXTENSION_LOCATION:
                    continue
                raw = entry.get("path")
                if isinstance(raw, str) and os.path.isabs(raw):
                    found.append(lexical(Path(raw)))
    return found


def obsidian_vault_roots() -> List[Path]:
    """Vault roots to inspect: the registry plus the home directory.

    A vault only reaches obsidian.json once it has been opened from that copy of the
    app, so the home directory is checked unconditionally — it is the common vault
    location that the registry keeps missing.
    """
    roots: List[Path] = [Path.home()]
    registry = Path.home() / OBSIDIAN_REGISTRY_RELATIVE
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return roots
    vaults = data.get("vaults")
    if not isinstance(vaults, dict):
        return roots
    for vault in vaults.values():
        if isinstance(vault, dict) and isinstance(vault.get("path"), str):
            roots.append(Path(vault["path"]))
    return roots


def obsidian_plugin_entries() -> List[Path]:
    """Plugin entries of every Obsidian vault this machine knows about."""
    entries: List[Path] = []
    for root in obsidian_vault_roots():
        try:
            entries.extend((root / OBSIDIAN_PLUGIN_RELATIVE).iterdir())
        except OSError:
            continue
    return entries


def link_host_entries() -> List[Path]:
    """Installed-plugin and linked-command slots that may point at a project directory."""
    home = Path.home()
    entries: List[Path] = []
    for pattern in LINK_HOST_GLOBS:
        entries.extend(home.glob(pattern))
    for pattern in ABSOLUTE_LINK_HOST_GLOBS:
        entries.extend(Path("/").glob(pattern))
    entries.extend(obsidian_plugin_entries())
    return entries


@functools.lru_cache(maxsize=1)
def referenced_paths() -> Tuple[Path, ...]:
    """Directories another application loads from right now, by symlink or recorded path.

    A build directory is only rebuildable in isolation: once a plugin host, browser or
    global link points at it, deleting it uninstalls that integration instead.
    """
    targets: List[Path] = list(chromium_unpacked_paths())
    for entry in link_host_entries():
        try:
            if not entry.is_symlink():
                continue
            targets.append(lexical(Path(os.path.realpath(str(entry)))))
        except OSError:
            continue
    unique: Dict[str, Path] = {str(item): item for item in targets}
    return tuple(unique.values())


def referenced(path: Path) -> bool:
    """Whether removing this path would break an installed plugin, extension or command."""
    path_variants = {lexical(path), resolved(path)}
    root_variants = {
        variant for root in referenced_paths() for variant in (lexical(root), resolved(root))
    }
    return any(
        paths_overlap(path_variant, root_variant)
        for path_variant in path_variants
        for root_variant in root_variants
    )


def last_access(path: Path, limit: int = ACCESS_SAMPLE_LIMIT) -> Optional[float]:
    """Newest access time across a bounded sample of files under path."""
    path = path.expanduser()
    try:
        if path.is_symlink():
            return None
        if path.is_file():
            return path.stat().st_atime
    except OSError:
        return None
    newest: Optional[float] = None
    scanned = 0
    for current, dirs, files in os.walk(str(path), followlinks=False):
        dirs[:] = [name for name in dirs if name not in SKIP_DISCOVERY]
        for name in files:
            try:
                stamp = os.lstat(os.path.join(current, name)).st_atime
            except OSError:
                continue
            if newest is None or stamp > newest:
                newest = stamp
            scanned += 1
            if scanned >= limit:
                return newest
    return newest


def recently_accessed(path: Path, days: int = ACTIVE_ACCESS_DAYS) -> bool:
    """Whether anything under path was read recently enough to still look in use.

    Modification time only records when a build ran; access time records whether
    anything has read it since.
    """
    if days <= 0:
        return False
    stamp = last_access(path)
    if stamp is None:
        return False
    return (datetime.now(timezone.utc).timestamp() - stamp) <= days * 86400


def guard_mutation_target(path: Path) -> Path:
    path = resolved(path)
    forbidden = {Path("/"), Path.home(), DEFAULT_DATA_VOLUME}
    if path in forbidden or len(path.parts) < 4:
        raise OptimizerError(f"拒绝过宽的修改目标：{path}")
    return path


def tree_stats(path: Path) -> Tuple[int, int]:
    """Return logical bytes and file-like entry count without following symlinks."""
    path = path.expanduser()
    if path.is_symlink():
        return 0, 1
    if path.is_file():
        return path.stat().st_size, 1
    total = 0
    count = 0
    for root, dirs, files in os.walk(str(path), followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(root) / name).is_symlink()]
        for name in files:
            item = Path(root) / name
            try:
                total += item.lstat().st_size
                count += 1
            except (FileNotFoundError, PermissionError):
                continue
    return total, count


def du_bytes(path: Path) -> int:
    try:
        result = subprocess.run(
            ["du", "-sk", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.stdout.strip():
            return int(result.stdout.strip().splitlines()[-1].split()[0]) * 1024
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return tree_stats(path)[0]


def classify(path: Path, extra_protected: Sequence[Path]) -> str:
    if protected(path, extra_protected):
        return "protected"
    if referenced(path):
        return "in-use"
    if path.name in REBUILDABLE_NAMES:
        if recently_accessed(path):
            return "recently-accessed"
        return "rebuildable"
    return "review-for-archive"


def mounted_volume(path: Path) -> Path:
    current = resolved(path)
    while current != current.parent and not os.path.ismount(str(current)):
        current = current.parent
    return current


def existing_ancestor(path: Path) -> Path:
    current = resolved(path)
    while current != current.parent and not current.exists():
        current = current.parent
    if not current.exists():
        raise OptimizerError(f"找不到可用的目标父目录：{path}")
    return current


def run_status(args: argparse.Namespace) -> int:
    volume = resolved(args.volume)
    usage = shutil.disk_usage(str(volume))
    payload = {
        "volume": str(volume),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "total_gb": decimal_gb(usage.total),
        "used_gb": decimal_gb(usage.used),
        "free_gb": decimal_gb(usage.free),
    }
    emit(payload, args.output)
    return 0


def discover_artifacts(root: Path, minimum_bytes: int, extra_protected: Sequence[Path]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for current, dirs, _files in os.walk(str(root), followlinks=False):
        current_path = Path(current)
        kept: List[str] = []
        for name in dirs:
            child = current_path / name
            if child.is_symlink() or name in SKIP_DISCOVERY or protected(child, extra_protected):
                continue
            if name in REBUILDABLE_NAMES:
                if referenced(child):
                    continue
                size = du_bytes(child)
                if size >= minimum_bytes:
                    category = "recently-accessed" if recently_accessed(child) else "rebuildable"
                    found.append(candidate(child, size, category, CANDIDATE_REASONS[category]))
                continue
            kept.append(name)
        dirs[:] = kept
    return found


def candidate(path: Path, size: int, category: str, reason: str) -> Dict[str, Any]:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        mtime = None
    stamp = last_access(path)
    return {
        "path": str(path),
        "size_bytes": size,
        "size_gb": decimal_gb(size),
        "category": category,
        "reason": reason,
        "modified_at": mtime,
        "accessed_at": datetime.fromtimestamp(stamp, timezone.utc).isoformat() if stamp else None,
    }


def run_inventory(args: argparse.Namespace) -> int:
    roots = [resolved(item) for item in args.root]
    extra_protected = [item.expanduser() for item in args.protected]
    minimum_bytes = int(args.min_gb * DECIMAL_GB)
    items: List[Dict[str, Any]] = []
    seen = set()
    for root in roots:
        if not root.is_dir():
            raise OptimizerError(f"扫描根目录不存在：{root}")
        children = sorted(root.iterdir(), key=lambda item: item.name.lower())
        for child in children:
            if child.is_symlink() or (child.name.startswith(".") and not args.include_hidden):
                continue
            size = du_bytes(child)
            if size < minimum_bytes:
                continue
            category = classify(child, extra_protected)
            items.append(candidate(child, size, category, CANDIDATE_REASONS[category]))
            seen.add(str(resolved(child)))
        if not args.no_artifacts:
            for item in discover_artifacts(root, minimum_bytes, extra_protected):
                if str(resolved(Path(item["path"]))) not in seen:
                    items.append(item)
    data_volume = resolved(args.volume)
    usage = shutil.disk_usage(str(data_volume))
    items.sort(key=lambda item: item["size_bytes"], reverse=True)
    emit(
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "volume": str(data_volume),
            "free_bytes": usage.free,
            "free_gb": decimal_gb(usage.free),
            "roots": [str(item) for item in roots],
            "candidates": items,
            "notes": [
                "修改日期只作判断信号，不自动等同于闲置或可删除。",
                "protected 与 in-use 候选永不进入自动清理计划。",
                f"recently-accessed 表示近 {ACTIVE_ACCESS_DAYS} 天仍被读取，只进人工复核；"
                "一次全盘备份或迁移会刷新访问时间，该字段不能单独证明目录仍在使用。",
                "目录大小可能包含嵌套候选，计划值是保守估算而非可相加账单。",
            ],
        },
        args.output,
    )
    return 0


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise OptimizerError(f"JSON 根节点必须是对象：{path}")
    return data


def run_plan(args: argparse.Namespace) -> int:
    inventory = load_json(args.inventory)
    free_bytes = int(inventory.get("free_bytes", 0))
    target_bytes = int(args.target_free_gb * DECIMAL_GB)
    buffer_bytes = int(args.buffer_gb * DECIMAL_GB)
    need = max(0, target_bytes + buffer_bytes - free_bytes)
    candidates = inventory.get("candidates", [])
    if not isinstance(candidates, list):
        raise OptimizerError("inventory.candidates 必须是数组")
    ordered = sorted(
        (item for item in candidates if item.get("category") not in {"protected", "in-use"}),
        key=lambda item: (0 if item.get("category") == "rebuildable" else 1, -int(item.get("size_bytes", 0))),
    )
    selected: List[Dict[str, Any]] = []
    estimated = 0
    selected_paths: List[Path] = []
    for item in ordered:
        path = resolved(Path(str(item.get("path", ""))))
        if any(is_relative_to(path, parent) or is_relative_to(parent, path) for parent in selected_paths):
            continue
        if estimated >= need:
            break
        action = "stage-cleanup" if item.get("category") == "rebuildable" else "review-for-archive"
        selected.append({**item, "recommended_action": action})
        selected_paths.append(path)
        estimated += int(item.get("size_bytes", 0))
    emit(
        {
            "target_free_gb": args.target_free_gb,
            "buffer_gb": args.buffer_gb,
            "current_free_gb": decimal_gb(free_bytes),
            "required_reclaim_gb": decimal_gb(need),
            "estimated_selected_gb": decimal_gb(estimated),
            "target_already_met": need == 0,
            "sufficient_candidates": estimated >= need,
            "actions": selected,
            "execution_rule": "先执行 rebuildable；archive 候选需结合上下文确认，计划本身不删除或迁移。",
        },
        args.output,
    )
    return 0 if estimated >= need else 3


def run_preflight(args: argparse.Namespace) -> int:
    root = resolved(args.archive_root)
    if not root.exists() or not root.is_dir():
        raise OptimizerError(f"归档根目录不存在：{root}")
    usage = shutil.disk_usage(str(root))
    mount = mounted_volume(root)
    writable = False
    try:
        with tempfile.NamedTemporaryFile(prefix=".lov-disk-check-", dir=str(root)):
            writable = True
    except OSError:
        writable = False
    payload = {
        "archive_root": str(root),
        "mount_point": str(mount),
        "writable": writable,
        "free_bytes": usage.free,
        "free_gb": decimal_gb(usage.free),
        "required_gb": args.required_gb,
        "enough_space": writable and usage.free >= int(args.required_gb * DECIMAL_GB),
    }
    emit(payload, args.output)
    return 0 if payload["enough_space"] else 3


def nfc(value: str) -> str:
    """HFS+ stores names in NFD while APFS keeps them as written, so compare in NFC."""
    return unicodedata.normalize("NFC", value)


def metadata_manifest(path: Path) -> Tuple[Dict[str, Tuple[str, int]], Dict[str, Path]]:
    """Map NFC-normalized relative paths to (kind, size) and to the path as listed on disk."""
    manifest: Dict[str, Tuple[str, int]] = {}
    on_disk: Dict[str, Path] = {}

    def record(item: Path, relative: str, entry: Tuple[str, int]) -> None:
        key = nfc(relative)
        if key in on_disk:
            raise OptimizerError(f"Unicode 规范化后路径冲突，无法可靠比对：{on_disk[key]} 与 {item}")
        manifest[key] = entry
        on_disk[key] = item

    if path.is_file():
        record(path, path.name, ("file", path.stat().st_size))
        return manifest, on_disk
    for root, dirs, files in os.walk(str(path), followlinks=False):
        root_path = Path(root)
        for name in dirs:
            item = root_path / name
            record(item, str(item.relative_to(path)), ("symlink" if item.is_symlink() else "dir", 0))
        for name in files:
            item = root_path / name
            try:
                size = item.lstat().st_size
            except OSError:
                continue
            record(item, str(item.relative_to(path)), ("file", size))
    return manifest, on_disk


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8 * 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_copy(source: Path, destination: Path, level: str) -> Dict[str, Any]:
    source_manifest, source_paths = metadata_manifest(source)
    destination_manifest, destination_paths = metadata_manifest(destination)
    if source_manifest != destination_manifest:
        missing = sorted(set(source_manifest) - set(destination_manifest))[:20]
        extra = sorted(set(destination_manifest) - set(source_manifest))[:20]
        changed = sorted(
            key for key in set(source_manifest) & set(destination_manifest)
            if source_manifest[key] != destination_manifest[key]
        )[:20]
        raise OptimizerError(f"复制校验差异：missing={missing}, extra={extra}, changed={changed}")
    checked = 0
    if level == "checksum":
        # Pair by normalized key: `destination / rel` spelled from the source may not be
        # the name the destination file system actually stores.
        for key, (kind, _size) in source_manifest.items():
            if kind != "file":
                continue
            left, right = source_paths[key], destination_paths[key]
            if hash_file(left) != hash_file(right):
                raise OptimizerError(f"内容哈希不一致：{left}")
            checked += 1
    total_bytes, file_count = tree_stats(source)
    return {"level": level, "bytes": total_bytes, "files": file_count, "checksummed_files": checked}


def unique_child(root: Path, label: str) -> Path:
    """Return a free child path, keeping the label's trailing suffix intact.

    The rollback validators match an exact trailing suffix (".cleanup", ".migrated"),
    so a disambiguating index must be inserted before it rather than appended.
    """
    candidate_path = root / label
    if not (candidate_path.exists() or candidate_path.is_symlink()):
        return candidate_path
    stem, dot, suffix = label.rpartition(".")
    index = 2
    while True:
        variant = f"{stem}-{index}{dot}{suffix}" if dot else f"{label}-{index}"
        candidate_path = root / variant
        if not (candidate_path.exists() or candidate_path.is_symlink()):
            return candidate_path
        index += 1


def append_journal(root: Path, event: Dict[str, Any]) -> None:
    journal = root / JOURNAL_NAME
    with journal.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_migrate(args: argparse.Namespace) -> int:
    source = guard_mutation_target(args.source)
    archive_root = resolved(args.archive_root)
    if not source.exists() or source.is_symlink():
        raise OptimizerError(f"源路径不存在或已经是链接：{source}")
    extra_protected = [item.expanduser() for item in getattr(args, "protected", [])]
    if protected(source, extra_protected):
        raise OptimizerError(f"迁移源命中保护边界：{source}")
    if referenced(source):
        raise OptimizerError(f"迁移源正被其它应用加载，移动后链接会失效：{source}")
    if not archive_root.is_dir():
        raise OptimizerError(f"归档根目录不存在：{archive_root}")
    destination = resolved(args.destination) if args.destination else archive_root / args.category / source.name
    if destination.exists() or destination.is_symlink():
        raise OptimizerError(f"目标已存在，先判断正式归档或不完整副本：{destination}")
    source_bytes, source_files = tree_stats(source)
    destination_ancestor = existing_ancestor(destination.parent)
    free = shutil.disk_usage(str(destination_ancestor)).free
    if free < source_bytes + int(args.reserve_gb * DECIMAL_GB):
        raise OptimizerError("归档卷剩余空间不足")
    same_device = source.stat().st_dev == destination_ancestor.stat().st_dev
    if same_device and not args.allow_same_volume:
        raise OptimizerError("源与归档目标位于同一卷，迁移不会释放该卷空间")
    plan = {
        "operation": "migrate",
        "source": str(source),
        "destination": str(destination),
        "source_bytes": source_bytes,
        "source_gb": decimal_gb(source_bytes),
        "source_files": source_files,
        "verify": args.verify,
        "create_symlink": not args.no_link,
        "execute": args.execute,
    }
    if not args.execute:
        emit(plan, args.output)
        return 0
    if args.confirm_source != str(source):
        raise OptimizerError("执行迁移时 --confirm-source 必须等于规范化源路径")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        destination.mkdir(parents=True)
        command = ["rsync", "-a", "--partial", f"{source}/", f"{destination}/"]
        if args.preserve_xattrs:
            command.insert(2, "-E")
        result = subprocess.run(command, check=False)
        if result.returncode:
            raise OptimizerError(f"复制失败，rsync exit={result.returncode}；源目录保持原状")
    else:
        shutil.copy2(str(source), str(destination))
    verification = verify_copy(source, destination, args.verify)
    rollback_root = resolved(args.rollback_root)
    rollback_root.mkdir(parents=True, exist_ok=True)
    rollback = unique_child(rollback_root, f"{source.name}{MIGRATED_SUFFIX}")
    shutil.move(str(source), str(rollback))
    if not args.no_link:
        source.symlink_to(destination, target_is_directory=destination.is_dir())
        if not source.exists():
            raise OptimizerError(f"链接验证失败；回滚副本仍在 {rollback}")
    event = {
        **plan,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "rollback": str(rollback),
        "verification": verification,
        "status": "migrated",
    }
    append_journal(archive_root, event)
    emit(event, args.output)
    return 0


def allowed_rebuildable(path: Path) -> bool:
    if path.name in REBUILDABLE_NAMES:
        return True
    suffixes = {
        ("CoreSimulator", "Devices"),
        ("Xcode", "iOS DeviceSupport"),
    }
    return any(tuple(path.parts[-len(suffix):]) == suffix for suffix in suffixes)


def run_stage_cleanup(args: argparse.Namespace) -> int:
    paths = [guard_mutation_target(item) for item in args.path]
    extra_protected = [item.expanduser() for item in args.protected]
    actions: List[Dict[str, Any]] = []
    for path in paths:
        if not path.exists() or path.is_symlink():
            raise OptimizerError(f"清理候选不存在或是链接：{path}")
        if protected(path, extra_protected):
            raise OptimizerError(f"候选命中保护边界：{path}")
        if referenced(path):
            raise OptimizerError(f"候选正被其它应用加载，清理会直接破坏该安装：{path}")
        if not allowed_rebuildable(path):
            raise OptimizerError(f"候选名称不在可重建白名单：{path}")
        size, files = tree_stats(path)
        actions.append({"path": str(path), "bytes": size, "gb": decimal_gb(size), "files": files})
    payload: Dict[str, Any] = {
        "operation": "stage-cleanup",
        "execute": args.execute,
        "estimated_gb": decimal_gb(sum(item["bytes"] for item in actions)),
        "items": actions,
        "note": "该操作只把明确的可重建目录移入回滚区，不清空废纸篓。",
    }
    if not args.execute:
        emit(payload, args.output)
        return 0
    if args.confirm != "STAGE_REBUILDABLES":
        raise OptimizerError("执行清理时必须传入 --confirm STAGE_REBUILDABLES")
    rollback_root = resolved(args.rollback_root)
    rollback_root.mkdir(parents=True, exist_ok=True)
    moved_records: List[Tuple[Dict[str, Any], Path, Path]] = []
    try:
        for item, path in zip(actions, paths):
            rollback = unique_child(rollback_root, f"{path.parent.name}-{path.name}{CLEANUP_SUFFIX}")
            shutil.move(str(path), str(rollback))
            moved_records.append((item, path, rollback))
            if args.recreate:
                path.mkdir(parents=True, exist_ok=True)
    except (OSError, shutil.Error) as exc:
        rollback_errors: List[Dict[str, str]] = []
        for item, path, rollback in reversed(moved_records):
            try:
                if args.recreate and path.exists() and path.is_dir() and not path.is_symlink():
                    if any(path.iterdir()):
                        raise OSError("重建路径在回滚前已有新内容")
                    path.rmdir()
                shutil.move(str(rollback), str(path))
            except (OSError, shutil.Error) as rollback_exc:
                rollback_errors.append(
                    {
                        "path": str(path),
                        "rollback": str(rollback),
                        "error": str(rollback_exc),
                    }
                )
        payload["status"] = "rolled-back" if not rollback_errors else "partial-failure"
        payload["items"] = [
            {
                **item,
                "status": "rolled-back" if any(record[0] is item for record in moved_records) else "not-started",
            }
            for item in actions
        ]
        payload["error"] = str(exc)
        payload["rollback_errors"] = rollback_errors
        emit(payload, args.output)
        return 2
    moved = [{**item, "rollback": str(rollback), "status": "staged"} for item, _path, rollback in moved_records]
    payload["items"] = moved
    payload["status"] = "staged"
    emit(payload, args.output)
    return 0


def staged_path(path: Path, rollback_root: Path) -> Path:
    """Accept only an explicit top-level rollback entry under the rollback root."""
    root = lexical(rollback_root)
    candidate = lexical(path if path.is_absolute() else root / path)
    canonical_root = root.resolve(strict=False)
    canonical_candidate = candidate.resolve(strict=False)
    if canonical_candidate.parent != canonical_root:
        raise OptimizerError(f"回滚清理目标必须是回滚根目录的直接子项：{candidate}")
    if not candidate.name.endswith(STAGED_SUFFIXES):
        raise OptimizerError(f"回滚清理目标必须以 .cleanup 或 .migrated 结尾：{candidate}")
    if candidate.is_symlink():
        raise OptimizerError(f"回滚清理目标不能是符号链接：{candidate}")
    return candidate


def rollback_key(path: Path) -> str:
    return nfc(str(resolved(path.parent) / path.name))


def load_migrations(archive_roots: Sequence[Path]) -> Dict[str, Dict[str, Any]]:
    """Latest migrated journal event per rollback entry, keyed by rollback_key."""
    events: Dict[str, Dict[str, Any]] = {}
    for root in archive_roots:
        try:
            lines = (resolved(root) / JOURNAL_NAME).read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if (
                isinstance(event, dict)
                and event.get("status") == "migrated"
                and all(isinstance(event.get(key), str) for key in ("rollback", "source", "destination"))
            ):
                events[rollback_key(Path(event["rollback"]))] = event
    return events


def migration_rollback_check(path: Path, migrations: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Prove from the journal that a .migrated entry is no longer the only copy.

    The rollback entry is the original data; it is redundant only while the original
    path is still a link that reaches the archived copy recorded for it.
    """
    event = migrations.get(rollback_key(path))
    if event is None:
        raise OptimizerError(
            f"迁移日志中没有该回滚项的 migrated 记录（--archive-root 需指向迁移时的归档根目录）：{path}"
        )
    source = Path(event["source"])
    destination = Path(event["destination"])
    if not source.is_symlink():
        raise OptimizerError(f"原路径已不是指向归档的符号链接：{source}")
    if destination.is_symlink() or not destination.exists():
        raise OptimizerError(f"归档目标不存在或归档卷未挂载：{destination}")
    if nfc(os.path.realpath(str(source))) != nfc(os.path.realpath(str(destination))):
        raise OptimizerError(f"原路径链接未指向日志记录的归档目标：{source} -> {os.readlink(str(source))}")
    if destination.is_dir() != path.is_dir():
        raise OptimizerError(f"归档目标与回滚项类型不一致：{destination}")
    return {"source": str(source), "destination": str(destination), "migrated_at": event.get("executed_at")}


def staged_entry(path: Path) -> Dict[str, Any]:
    exists = path.exists() and not path.is_symlink()
    size, files = tree_stats(path) if exists else (0, 0)
    return {
        "path": str(path),
        "bytes": size,
        "gb": decimal_gb(size),
        "files": files,
        "status": "pending" if exists else "already-absent",
    }


def run_list_staged(args: argparse.Namespace) -> int:
    rollback_root = resolved(args.rollback_root)
    if not rollback_root.is_dir():
        raise OptimizerError(f"回滚根目录不存在：{rollback_root}")
    archive_roots = getattr(args, "archive_root", [])
    migrations = load_migrations(archive_roots)
    items: List[Dict[str, Any]] = []
    for child in sorted(rollback_root.iterdir(), key=lambda item: item.name.lower()):
        if child.is_symlink() or not child.name.endswith(STAGED_SUFFIXES):
            continue
        item = staged_entry(child)
        if child.name.endswith(MIGRATED_SUFFIX) and item["status"] == "pending":
            try:
                item["migration"] = migration_rollback_check(child, migrations)
            except OptimizerError as exc:
                item["status"] = "blocked"
                item["reason"] = str(exc)
        items.append(item)
    purgeable_bytes = sum(int(item["bytes"]) for item in items if item["status"] == "pending")
    emit(
        {
            "operation": "list-staged",
            "rollback_root": str(rollback_root),
            "archive_roots": [str(resolved(root)) for root in archive_roots],
            "items": items,
            "total_bytes": purgeable_bytes,
            "total_gb": decimal_gb(purgeable_bytes),
        },
        args.output,
    )
    return 0


def run_purge_staged(args: argparse.Namespace) -> int:
    rollback_root = resolved(args.rollback_root)
    if not rollback_root.is_dir():
        raise OptimizerError(f"回滚根目录不存在：{rollback_root}")
    paths: List[Path] = []
    seen = set()
    for raw_path in args.path:
        candidate_path = staged_path(raw_path, rollback_root)
        if str(candidate_path) in seen:
            raise OptimizerError(f"回滚清理目标重复：{candidate_path}")
        seen.add(str(candidate_path))
        paths.append(candidate_path)

    archive_roots = getattr(args, "archive_root", [])
    migrations = load_migrations(archive_roots)
    items: List[Dict[str, Any]] = []
    for path in paths:
        item = staged_entry(path)
        if path.name.endswith(MIGRATED_SUFFIX) and item["status"] == "pending":
            item["migration"] = migration_rollback_check(path, migrations)
        items.append(item)
    payload: Dict[str, Any] = {
        "operation": "purge-staged",
        "execute": args.execute,
        "method": "direct-filesystem",
        "finder": False,
        "retry": False,
        "rollback_root": str(rollback_root),
        "archive_roots": [str(resolved(root)) for root in archive_roots],
        "items": items,
        "estimated_gb": decimal_gb(sum(int(item["bytes"]) for item in items)),
        "note": "只处理显式 .cleanup 路径与经迁移日志验证的 .migrated 路径；不会清空其他废纸篓项目。",
    }
    if not args.execute:
        emit(payload, args.output)
        return 0
    if args.confirm != PURGE_CONFIRM:
        raise OptimizerError(f"执行回滚区清理时必须传入 --confirm {PURGE_CONFIRM}")

    errors: List[Dict[str, str]] = []
    for item, path in zip(items, paths):
        if not path.exists():
            item["status"] = "already-absent"
            continue
        try:
            # Earlier deletions can take long enough for the archive volume to be ejected.
            if path.name.endswith(MIGRATED_SUFFIX):
                migration_rollback_check(path, migrations)
            if path.is_dir():
                shutil.rmtree(str(path))
            else:
                path.unlink()
            if path.exists() or path.is_symlink():
                raise OSError("删除后路径仍存在")
            item["status"] = "purged"
        except (OSError, OptimizerError) as exc:
            item["status"] = "error"
            errors.append({"path": str(path), "error": str(exc)})
            break

    payload["status"] = "purged" if not errors else "partial-failure"
    payload["errors"] = errors
    emit(payload, args.output)
    return 0 if not errors else 2


def run_verify(args: argparse.Namespace) -> int:
    volume = resolved(args.volume)
    usage = shutil.disk_usage(str(volume))
    required = int((args.target_free_gb + args.buffer_gb) * DECIMAL_GB)
    link_results = []
    for path in args.link:
        item = path.expanduser()
        link_results.append({
            "path": str(item),
            "is_symlink": item.is_symlink(),
            "resolves": item.exists(),
            "target": os.readlink(str(item)) if item.is_symlink() else None,
        })
    passed = usage.free >= required and all(item["is_symlink"] and item["resolves"] for item in link_results)
    emit(
        {
            "passed": passed,
            "volume": str(volume),
            "free_bytes": usage.free,
            "free_gb": decimal_gb(usage.free),
            "target_free_gb": args.target_free_gb,
            "buffer_gb": args.buffer_gb,
            "required_gb": args.target_free_gb + args.buffer_gb,
            "links": link_results,
        },
        args.output,
    )
    return 0 if passed else 3


def read_profile(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise OptimizerError("共享 profile 根节点必须是对象")
    return data


def run_profile(args: argparse.Namespace) -> int:
    path = resolved(args.profile)
    data = read_profile(path)
    skills = data.get("skills", {})
    if not isinstance(skills, dict):
        raise OptimizerError("profile.skills 必须是对象")
    current = skills.get(PROFILE_KEY, {})
    if not isinstance(current, dict):
        current = {}
    if args.profile_action == "show":
        emit({"profile": str(path), "settings": current}, args.output)
        return 0
    settings = {
        "target_free_gb": args.target_free_gb,
        "buffer_gb": args.buffer_gb,
        "archive_volume": str(args.archive_volume.expanduser()) if args.archive_volume else None,
        "protected_paths": [str(item.expanduser()) for item in args.protected],
        "cleanup_policy": args.cleanup_policy,
    }
    emit({"profile": str(path), "settings_to_persist": settings}, None)
    if not args.write:
        return 0
    skills[PROFILE_KEY] = settings
    data["skills"] = skills
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    emit({"profile": str(path), "status": "saved", "settings": settings}, args.output)
    return 0


def add_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", type=Path, help="可选 JSON 输出文件；默认输出到 stdout")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="读取数据卷真实可用空间")
    status.add_argument("--volume", type=Path, default=DEFAULT_DATA_VOLUME)
    add_output(status)
    status.set_defaults(func=run_status)

    inventory = commands.add_parser("inventory", help="只读扫描大目录和可重建产物")
    inventory.add_argument("--root", type=Path, action="append", required=True)
    inventory.add_argument("--volume", type=Path, default=DEFAULT_DATA_VOLUME)
    inventory.add_argument("--protected", type=Path, action="append", default=[])
    inventory.add_argument("--min-gb", type=float, default=0.5)
    inventory.add_argument("--include-hidden", action="store_true")
    inventory.add_argument("--no-artifacts", action="store_true")
    add_output(inventory)
    inventory.set_defaults(func=run_inventory)

    plan = commands.add_parser("plan", help="按容量缺口生成最小清理与归档建议")
    plan.add_argument("--inventory", type=Path, required=True)
    plan.add_argument("--target-free-gb", type=float, required=True)
    plan.add_argument("--buffer-gb", type=float, default=15.0)
    add_output(plan)
    plan.set_defaults(func=run_plan)

    preflight = commands.add_parser("preflight-volume", help="检查归档卷容量与可写性")
    preflight.add_argument("--archive-root", type=Path, required=True)
    preflight.add_argument("--required-gb", type=float, required=True)
    add_output(preflight)
    preflight.set_defaults(func=run_preflight)

    migrate = commands.add_parser("migrate", help="事务式复制、校验、回滚与原路径链接")
    migrate.add_argument("--source", type=Path, required=True)
    migrate.add_argument("--archive-root", type=Path, required=True)
    migrate.add_argument("--category", default="projects")
    migrate.add_argument("--destination", type=Path)
    migrate.add_argument("--protected", type=Path, action="append", default=[])
    migrate.add_argument("--rollback-root", type=Path, default=Path.home() / ".Trash")
    migrate.add_argument("--verify", choices=("metadata", "checksum"), default="metadata")
    migrate.add_argument("--reserve-gb", type=float, default=10.0)
    migrate.add_argument("--preserve-xattrs", action="store_true")
    migrate.add_argument("--no-link", action="store_true")
    migrate.add_argument("--allow-same-volume", action="store_true", help=argparse.SUPPRESS)
    migrate.add_argument("--execute", action="store_true")
    migrate.add_argument("--confirm-source", default="")
    add_output(migrate)
    migrate.set_defaults(func=run_migrate)

    cleanup = commands.add_parser("stage-cleanup", help="把白名单内可重建目录移入回滚区")
    cleanup.add_argument("--path", type=Path, action="append", required=True)
    cleanup.add_argument("--protected", type=Path, action="append", default=[])
    cleanup.add_argument("--rollback-root", type=Path, default=Path.home() / ".Trash")
    cleanup.add_argument("--recreate", action="store_true")
    cleanup.add_argument("--execute", action="store_true")
    cleanup.add_argument("--confirm", default="")
    add_output(cleanup)
    cleanup.set_defaults(func=run_stage_cleanup)

    archive_root_help = "迁移时使用的归档根目录；读取其迁移日志以验证 .migrated 回滚项"

    staged = commands.add_parser("list-staged", help="列出回滚区内的 .cleanup 与 .migrated 回滚项")
    staged.add_argument("--rollback-root", type=Path, default=Path.home() / ".Trash")
    staged.add_argument("--archive-root", type=Path, action="append", default=[], help=archive_root_help)
    add_output(staged)
    staged.set_defaults(func=run_list_staged)

    purge = commands.add_parser(
        "purge-staged", help="直接回收显式 .cleanup 项与经日志验证的 .migrated 项，不调用 Finder"
    )
    purge.add_argument("--path", type=Path, action="append", required=True)
    purge.add_argument("--rollback-root", type=Path, default=Path.home() / ".Trash")
    purge.add_argument("--archive-root", type=Path, action="append", default=[], help=archive_root_help)
    purge.add_argument("--execute", action="store_true")
    purge.add_argument("--confirm", default="")
    add_output(purge)
    purge.set_defaults(func=run_purge_staged)

    verify = commands.add_parser("verify", help="按十进制 GB 与链接状态完成真实验收")
    verify.add_argument("--volume", type=Path, default=DEFAULT_DATA_VOLUME)
    verify.add_argument("--target-free-gb", type=float, required=True)
    verify.add_argument("--buffer-gb", type=float, default=15.0)
    verify.add_argument("--link", type=Path, action="append", default=[])
    add_output(verify)
    verify.set_defaults(func=run_verify)

    profile = commands.add_parser("profile", help="查看或初始化可移植默认配置")
    profile.add_argument("profile_action", choices=("show", "init"))
    profile.add_argument(
        "--profile",
        "--preferences",
        dest="profile",
        type=Path,
        default=DEFAULT_PROFILE,
    )
    profile.add_argument("--target-free-gb", type=float, default=200.0)
    profile.add_argument("--buffer-gb", type=float, default=15.0)
    profile.add_argument("--archive-volume", type=Path)
    profile.add_argument("--protected", type=Path, action="append", default=[])
    profile.add_argument("--cleanup-policy", choices=("conservative", "balanced", "aggressive"), default="balanced")
    profile.add_argument("--write", action="store_true")
    add_output(profile)
    profile.set_defaults(func=run_profile)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (OptimizerError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
