#!/usr/bin/env python3
"""Unit tests for the WDB Pro managed-key initializer."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import wdb_init as wdb  # noqa: E402


class WdbInitParserTests(unittest.TestCase):
    def test_version_gate(self) -> None:
        self.assertFalse(wdb.wechat_version_requires_capture("4.1.9"))
        self.assertTrue(wdb.wechat_version_requires_capture("4.1.10"))
        self.assertTrue(wdb.wechat_version_requires_capture("5.0.0"))
        self.assertFalse(wdb.wechat_version_requires_capture(None))

    def test_scanner_output_becomes_managed_entries(self) -> None:
        key = "0123456789abcdef" * 4
        content = '{"message/message_0.db":{"enc_key":"%s"}}' % key
        entries = wdb.scanner_output_to_managed_entries(
            content, Path("/tmp/db_storage")
        )
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["path"].endswith("/db_storage/message/message_0.db"))
        self.assertEqual(entries[0]["key"], key)
        self.assertEqual(entries[0]["cipherCompatibility"], 4)

    def test_rejects_parent_traversal(self) -> None:
        key = "0123456789abcdef" * 4
        content = '{"../other.db":{"enc_key":"%s"}}' % key
        with self.assertRaises(wdb.WdbInitError) as caught:
            wdb.scanner_output_to_managed_entries(content, Path("/tmp/db_storage"))
        self.assertEqual(caught.exception.stage, "parse")

    def test_rejects_invalid_key(self) -> None:
        content = '{"message/message_0.db":{"enc_key":"short"}}'
        with self.assertRaises(wdb.WdbInitError):
            wdb.scanner_output_to_managed_entries(content, Path("/tmp/db_storage"))


class WdbInitWriteTests(unittest.TestCase):
    def test_managed_keys_write_atomically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wdb-init-test-keys-") as tmp:
            # Point the module constants at the isolated directory, then restore.
            original = wdb.MANAGED_KEYS_RELATIVE_PATHS
            root = Path(tmp)
            wdb.MANAGED_KEYS_RELATIVE_PATHS = [
                root / "current" / "wdb-pro-managed-keys.json",
                root / "legacy" / "wdb-pro-managed-keys.json",
            ]
            try:
                key = "0123456789abcdef" * 4
                entries = [
                    {
                        "path": "/tmp/db_storage/message/message_0.db",
                        "key": key,
                        "cipherCompatibility": 4,
                    }
                ]
                paths = wdb.save_managed_keys(entries)
                self.assertEqual(len(paths), 2)
                for path in paths:
                    self.assertTrue(Path(path).is_file())
                    self.assertIn("0123456789abcdef", Path(path).read_text())
            finally:
                wdb.MANAGED_KEYS_RELATIVE_PATHS = original


if __name__ == "__main__":
    unittest.main()
