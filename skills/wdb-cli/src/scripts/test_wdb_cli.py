#!/usr/bin/env python3
"""Standard-library integration tests for the standalone CLI."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import http.client
import io
import json
import os
import select
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple
from unittest import mock

import decode_wechat_v4_dat as dat
import wdb_cli as wdb


SCRIPT = Path(__file__).with_name("wdb_cli.py")


def varint(value: int) -> bytes:
    output = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        output.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(output)


def proto_bytes(field: int, value: bytes) -> bytes:
    return varint(field * 8 + 2) + varint(len(value)) + value


SNS_FIXTURE_KEY = 0x0123456789ABCDEF  # synthetic, not a real CDN media key
SNS_FIXTURE_TOKEN = "fixture-token-not-real"


def local_ts(*parts: int) -> int:
    return int(dt.datetime(*parts).astimezone().timestamp())


def moment_xml(username: str, created: int, media: str = "") -> str:
    return (
        "<TimelineObject><id>0</id><username>{}</username><createTime>{}</createTime>"
        "<contentDesc>post {}</contentDesc><ContentObject><mediaList>{}</mediaList></ContentObject>"
        "</TimelineObject>"
    ).format(username, created, created, media)


def sns_v4_database(path: Path, rows: Sequence[Tuple[int, str, str]]) -> None:
    """WeChat 4.x shape: no time column, createTime lives only inside the XML."""
    connection = sqlite3.connect(str(path))
    try:
        connection.execute("CREATE TABLE contact (username TEXT, nick_name TEXT)")
        connection.executemany("INSERT INTO contact VALUES (?, ?)", [("wxid_self", "我"), ("wxid_friend", "朋友")])
        connection.execute("CREATE TABLE SnsTimeLine (tid INTEGER, user_name TEXT, content TEXT, pack_info_buf TEXT)")
        connection.executemany("INSERT INTO SnsTimeLine VALUES (?, ?, ?, '')", rows)
        connection.commit()
    finally:
        connection.close()


def chat_database(path: Path, tables: Dict[str, Sequence[Tuple[int, object]]], contacts: Sequence[str] = ()) -> None:
    """One Msg_ table per conversation; bytes bodies are stored as BLOBs like 4.x compressed rows."""
    connection = sqlite3.connect(str(path))
    try:
        connection.execute("CREATE TABLE WCContact (m_nsUsrName TEXT, nickname TEXT)")
        connection.executemany("INSERT INTO WCContact VALUES (?, ?)", [(username, username) for username in contacts])
        for table, rows in tables.items():
            connection.execute('CREATE TABLE "{}" (message_content TEXT, create_time INTEGER, local_type INTEGER)'.format(table))
            connection.executemany('INSERT INTO "{}" VALUES (?, ?, 1)'.format(table), [(body, created) for created, body in rows])
        connection.commit()
    finally:
        connection.close()


def zstd_frame(payload: bytes, declare_size: bool = True) -> bytes:
    """One raw block in a zstd frame, so tests need no compressor."""
    # Single-segment frames carry a 1-byte content size; otherwise a 1 KiB window descriptor.
    descriptor, header = (0x20, bytes([len(payload)])) if declare_size else (0x00, b"\x00")
    block = (1 | len(payload) << 3).to_bytes(3, "little")  # last block, raw, size
    return wdb.ZSTD_MAGIC + bytes([descriptor]) + header + block + payload


class FakeResponse:
    def __init__(self, body: bytes, headers: Dict[str, str]) -> None:
        self.body = body
        self.headers = http.client.HTTPMessage()
        for name, value in headers.items():
            self.headers[name] = value

    def read(self, amount: int = -1) -> bytes:
        return self.body if amount < 0 else self.body[:amount]

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


class WdbCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="wdb-cli-test-")
        self.root = Path(self.temp.name)
        self.database = self.root / "fixture.db"
        self.username = "wxid_friend"
        self.feed_id = "feed-001"
        timestamp = int(dt.datetime(2026, 8, 1, 12, 0, 0).astimezone().timestamp())
        cover = b"https://example.qpic.cn/moments-cover.jpg"
        packed = proto_bytes(4, "签名测试".encode("utf-8")) + proto_bytes(27, proto_bytes(2, cover))
        table = "Msg_" + hashlib.md5(self.username.encode("utf-8")).hexdigest()

        connection = sqlite3.connect(str(self.database))
        try:
            connection.execute(
                "CREATE TABLE WCContact (m_nsUsrName TEXT, nickname TEXT, m_nsRemark TEXT, "
                "m_nsAliasName TEXT, _packed_WCContactData BLOB, chat_room_notify INTEGER)"
            )
            connection.execute(
                "INSERT INTO WCContact VALUES (?, ?, ?, ?, ?, ?)",
                (self.username, "朋友昵称", "朋友备注", "friend_alias", packed, 0),
            )
            connection.execute("CREATE TABLE Name2Id (user_name TEXT)")
            connection.execute("INSERT INTO Name2Id(rowid, user_name) VALUES (7, ?)", (self.username,))
            connection.execute(
                'CREATE TABLE "{}" (message_content TEXT, create_time INTEGER, local_type INTEGER, mesdes INTEGER, real_sender_id INTEGER)'.format(table)
            )
            connection.execute(
                'INSERT INTO "{}" VALUES (?, ?, ?, ?, ?)'.format(table),
                ("这是一条目标聊天", timestamp, 1, 1, 7),
            )
            connection.execute("CREATE TABLE SnsTimeLine (tid TEXT, user_name TEXT, content TEXT, create_time INTEGER)")
            moment_xml = (
                "<TimelineObject><username>{}</username><nickname>朋友昵称</nickname>"
                "<createTime>{}</createTime><contentDesc>朋友圈正文</contentDesc>"
                "<ContentObject><media><url>https://example.qpic.cn/photo.jpg</url></media></ContentObject>"
                "</TimelineObject>"
            ).format(self.username, timestamp)
            connection.execute("INSERT INTO SnsTimeLine VALUES (?, ?, ?, ?)", (self.feed_id, self.username, moment_xml, timestamp))
            connection.execute(
                "CREATE TABLE SnsMessage_tmp3 (feed_id TEXT, create_time INTEGER, from_username TEXT, from_nickname TEXT, content TEXT)"
            )
            connection.execute("INSERT INTO SnsMessage_tmp3 VALUES (?, ?, ?, ?, ?)", (self.feed_id, timestamp + 60, "wxid_liker", "点赞者", ""))
            connection.execute("INSERT INTO SnsMessage_tmp3 VALUES (?, ?, ?, ?, ?)", (self.feed_id, timestamp + 120, "wxid_commenter", "评论者", "写得好"))
            connection.commit()
        finally:
            connection.close()
        self.table = table

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *arguments: str) -> dict:
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "--database", str(self.database), *arguments],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def test_doctor_finds_available_data_capabilities(self) -> None:
        result = self.run_cli("doctor")
        capabilities = result["data"]["databases"][0]["capabilities"]
        self.assertTrue(capabilities["contacts"])
        self.assertTrue(capabilities["chats"])
        self.assertTrue(capabilities["moments"])

    def test_contact_profile_uses_stable_source_and_packed_fields(self) -> None:
        result = self.run_cli("contacts", "--match", "朋友备注")
        contact = result["data"][0]
        self.assertEqual(contact["username"], self.username)
        self.assertEqual(contact["displayName"], "朋友备注")
        self.assertEqual(contact["signature"], "签名测试")
        self.assertEqual(contact["momentsCoverUrl"], "https://example.qpic.cn/moments-cover.jpg")
        self.assertEqual(contact["source"]["tableName"], "WCContact")
        self.assertIsInstance(contact["source"]["rowid"], int)

    def test_chat_day_contact_and_query_preserve_exact_identity(self) -> None:
        result = self.run_cli(
            "chats", "--date", "2026-08-01", "--contact", self.username, "--query", "目标"
        )
        self.assertEqual(len(result["data"]), 1)
        message = result["data"][0]
        self.assertEqual(message["text"], "这是一条目标聊天")
        self.assertEqual(message["conversationId"], self.username)
        self.assertEqual(message["source"]["tableName"], self.table)
        self.assertEqual(message["source"]["rowid"], 1)

    def test_moment_observed_interactions_and_cover(self) -> None:
        result = self.run_cli("moments", "--date", "2026-08-01", "--feed-id", self.feed_id)
        self.assertEqual(len(result["data"]), 1)
        moment = result["data"][0]
        self.assertEqual(moment["text"], "朋友圈正文")
        self.assertEqual(moment["observedLikeCount"], 1)
        self.assertEqual(moment["observedCommentCount"], 1)
        self.assertEqual(moment["authorMomentsCoverUrl"], "https://example.qpic.cn/moments-cover.jpg")
        self.assertEqual(moment["source"]["tableName"], "SnsTimeLine")

    def test_quote_reply_is_labeled_and_group_prefix_leaves_text_clean(self) -> None:
        group = "12345678@chatroom"
        table = "Msg_" + hashlib.md5(group.encode("utf-8")).hexdigest()
        path = self.root / "group.db"
        timestamp = int(dt.datetime(2026, 8, 1, 12, 0, 0).astimezone().timestamp())
        quote = (
            '<?xml version="1.0"?><msg><appmsg appid="" sdkver="0">'
            "<title>➕1</title><type>57</type><appattach><aeskey></aeskey></appattach>"
            "<refermsg><type>1</type><svrid>6079353708458032497</svrid>"
            "<fromusr>{}</fromusr><chatusr>althasHang</chatusr>"
            "<displayname>Jesse</displayname><content>天啊为什么不是上海</content>"
            "<createtime>{}</createtime></refermsg></appmsg></msg>"
        ).format(group, timestamp - 25)
        connection = sqlite3.connect(str(path))
        try:
            connection.execute("CREATE TABLE WCContact (m_nsUsrName TEXT, nickname TEXT)")
            connection.execute("INSERT INTO WCContact VALUES (?, ?)", (group, "聚会群"))
            connection.execute("CREATE TABLE Name2Id (user_name TEXT)")
            connection.execute("INSERT INTO Name2Id(rowid, user_name) VALUES (1, ?)", ("wxid_lily",))
            connection.execute(
                'CREATE TABLE "{}" (message_content TEXT, create_time INTEGER, local_type INTEGER, mesdes INTEGER, real_sender_id INTEGER)'.format(table)
            )
            connection.execute(
                'INSERT INTO "{}" VALUES (?, ?, ?, ?, ?)'.format(table),
                ("wxid_lily:\n" + quote, timestamp, 244813135921, 1, 1),
            )
            connection.execute(
                'INSERT INTO "{}" VALUES (?, ?, ?, ?, ?)'.format(table),
                ("wxid_other:\n1", timestamp + 5, 1, 1, 1),
            )
            pat = (
                '<msg><appmsg><title>"小苋" 拍了拍 "曲东奇"</title><type>62</type>'
                "<patinfo><fromusername>wxid_other</fromusername></patinfo></appmsg></msg>"
            )
            connection.execute(
                'INSERT INTO "{}" VALUES (?, ?, ?, ?, ?)'.format(table),
                ("wxid_other:\n" + pat, timestamp + 10, 266287972401, 1, 1),
            )
            connection.commit()
        finally:
            connection.close()
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "--database", str(path), "chats", "--date", "2026-08-01"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        messages = json.loads(process.stdout)["data"]
        quote_message, plain_message, pat_message = messages[0], messages[1], messages[2]
        self.assertEqual(quote_message["messageType"], "quote")
        self.assertEqual(quote_message["appType"], 57)
        self.assertEqual(quote_message["text"], "➕1")
        self.assertEqual(quote_message["senderUsername"], "wxid_lily")
        self.assertEqual(quote_message["quoted"]["senderName"], "Jesse")
        self.assertEqual(quote_message["quoted"]["senderUsername"], "althasHang")
        self.assertEqual(quote_message["quoted"]["content"], "天啊为什么不是上海")
        self.assertTrue(quote_message["quoted"]["createTime"].startswith("2026-08-01"))
        self.assertIn("wxid_lily:", quote_message["rawContent"])
        self.assertEqual(plain_message["text"], "1")
        self.assertEqual(pat_message["messageType"], "pat")
        self.assertEqual(pat_message["appType"], 62)
        self.assertIsNone(pat_message["quoted"])

    def test_schema_browses_unknown_tables(self) -> None:
        result = self.run_cli("schema", "--table", "Name2Id", "--counts")
        tables = result["data"][0]["tables"]
        self.assertEqual([table["name"] for table in tables], ["Name2Id"])
        self.assertEqual(tables[0]["rowCount"], 1)
        self.assertEqual(tables[0]["columns"][0]["name"], "user_name")

    def test_sql_supports_generic_readonly_queries(self) -> None:
        result = self.run_cli(
            "sql", "--database", str(self.database),
            "--query", "SELECT rowid, user_name FROM Name2Id ORDER BY rowid", "--limit", "10"
        )
        self.assertEqual(result["data"], [{"rowid": 7, "user_name": self.username}])
        self.assertFalse(result["meta"]["truncated"])

    def test_record_reads_exact_row(self) -> None:
        result = self.run_cli(
            "record", "--database", str(self.database), "--table", self.table, "--rowid", "1"
        )
        self.assertEqual(result["data"]["record"]["message_content"], "这是一条目标聊天")
        self.assertEqual(result["data"]["source"]["rowid"], 1)

    def test_toml_key_manifest_is_parsed_without_exposing_key(self) -> None:
        key_file = self.root / "keys.toml"
        key_file.write_text(
            '[[databases.Message]]\npath = "{}"\nkey = "x\'{}\'"\ncipher_compatibility = 3\ntype = "Message"\n'.format(
                self.database, "ab" * 32
            ),
            encoding="utf-8",
        )
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "--keys", str(key_file), "--sqlcipher", "/missing/sqlcipher", "doctor"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        payload = json.loads(process.stdout)
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("ab" * 32, serialized)
        self.assertEqual(payload["data"]["databaseCount"], 1)

    def test_wdb_pro_managed_keys_are_auto_discovered_before_wechat_cli(self) -> None:
        managed_path = (
            self.root
            / "Library"
            / "Application Support"
            / "ai.lovstudio.wdb-pro"
            / "database-keys"
            / "wdb-pro-managed-keys.json"
        )
        managed_path.parent.mkdir(parents=True)
        raw_key = "cd" * 32
        managed_path.write_text(
            json.dumps([
                {
                    "path": str(self.database),
                    "key": "0x" + raw_key,
                    "cipherCompatibility": 4,
                }
            ]),
            encoding="utf-8",
        )
        legacy_path = self.root / ".wechat-cli" / "all_keys.json"
        legacy_path.parent.mkdir(parents=True)
        legacy_path.write_text("{}", encoding="utf-8")

        environment = dict(os.environ)
        environment["HOME"] = str(self.root)
        environment.pop("WDB_KEYS_FILE", None)
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "--sqlcipher", "/missing/sqlcipher", "doctor"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            cwd=self.root,
            check=False,
        )

        self.assertEqual(process.returncode, 0, process.stderr)
        payload = json.loads(process.stdout)
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(payload["data"]["keysSource"], str(managed_path.resolve()))
        self.assertEqual(payload["data"]["databaseCount"], 1)
        self.assertEqual(payload["data"]["databases"][0]["cipherCompatibility"], 4)
        self.assertNotIn(raw_key, serialized)


class WdbSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="wdb-snapshot-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "live ? 数据.db"

    def reader(self, key=None):
        reader = wdb.Database(wdb.DatabaseSpec(self.path, key, 4), shutil.which("sqlcipher"))
        self.addCleanup(reader.close)
        return reader

    def writer(self):
        writer = sqlite3.connect(self.path)
        self.addCleanup(writer.close)
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE events (value INTEGER)")
        writer.execute("INSERT INTO events VALUES (42)")
        writer.commit()
        return writer

    def fingerprints(self):
        return {p.name: (p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns,
                         hashlib.sha256(p.read_bytes()).hexdigest())
                for p in self.root.iterdir() if p.is_file()}

    def test_live_wal_read_is_isolated_and_keeps_source_unchanged(self):
        writer = self.writer()
        before = self.fingerprints()
        reader = self.reader()
        with mock.patch.object(wdb.sqlite3, "connect", wraps=sqlite3.connect) as connect:
            self.assertEqual(reader.query("SELECT * FROM events"), [{"value": 42}])
            self.assertNotIn(self.path.as_uri(), connect.call_args.args[0])
        self.assertEqual(before, self.fingerprints())
        self.assertEqual(reader.spec.path, self.path)
        snapshot = reader._snapshot_path
        self.assertEqual(snapshot.stat().st_mode & 0o777, 0o600)
        self.assertEqual(snapshot.parent.stat().st_mode & 0o777, 0o700)
        writer.execute("INSERT INTO events VALUES (43)")
        writer.commit()
        self.assertEqual(reader.query("SELECT * FROM events"), [{"value": 42}])
        reader.close()
        self.assertFalse(snapshot.parent.exists())
        self.assertEqual(reader.query("SELECT COUNT(*) AS n FROM events"), [{"n": 2}])

    def test_source_shm_is_never_copied_and_missing_shm_is_not_created(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute("CREATE TABLE events (value INTEGER)")
        connection.close()
        shm = Path(str(self.path) + "-shm")
        shm.write_bytes(b"foreign-wcdb-index")
        reader = self.reader()
        with mock.patch.object(wdb.shutil, "copyfile", wraps=shutil.copyfile) as copy:
            reader.query("SELECT * FROM events")
        self.assertEqual([call.args[0] for call in copy.call_args_list], [self.path])
        self.assertEqual(shm.read_bytes(), b"foreign-wcdb-index")
        self.assertFalse(Path(str(reader._snapshot_path) + "-shm").exists())
        shm.unlink()  # Only this disposable fixture, never a user's SHM.
        reader.close()
        reader.query("SELECT * FROM events")
        self.assertFalse(shm.exists())

    def test_continuous_changes_fail_closed_and_remove_attempts(self):
        writer = self.writer()
        reader = self.reader()
        copy = shutil.copyfile
        destinations = []

        def changing_copy(source, target):
            result = copy(source, target)
            destinations.append(Path(target).parent)
            if source == self.path:
                writer.execute("INSERT INTO events VALUES (99)")
                writer.commit()
            return result

        with mock.patch.object(wdb.shutil, "copyfile", side_effect=changing_copy), \
                mock.patch.object(wdb.sqlite3, "connect") as connect:
            with self.assertRaises(wdb.WdbError) as caught:
                reader.query("SELECT * FROM events")
        self.assertEqual(caught.exception.stage, "snapshot")
        self.assertEqual(caught.exception.debug["attempts"], 3)
        connect.assert_not_called()
        self.assertTrue(all(not path.exists() for path in destinations))

    def test_copy_failure_and_rollback_journal_never_open_source(self):
        self.writer()
        reader = self.reader()
        with mock.patch.object(wdb.shutil, "copyfile", side_effect=OSError(28, "disk full")), \
                mock.patch.object(wdb.sqlite3, "connect") as connect:
            with self.assertRaises(wdb.WdbError) as caught:
                reader.query("SELECT 1")
        self.assertEqual(caught.exception.stage, "snapshot")
        self.assertEqual(caught.exception.debug, {"errno": 28})
        connect.assert_not_called()
        Path(str(self.path) + "-journal").write_bytes(b"pending rollback")
        with self.assertRaises(wdb.WdbError) as caught:
            reader.query("SELECT 1")
        self.assertEqual(caught.exception.stage, "snapshot")

    def test_run_cleans_snapshot_after_query_exception(self):
        self.writer()
        args = wdb.build_parser().parse_args(["--database", str(self.path), "doctor"])
        snapshots = []

        def fail(ctx):
            snapshots.append(ctx.databases[0]._read_path())
            raise RuntimeError("query failed")

        with mock.patch.object(wdb, "run_context", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "query failed"):
                wdb.run(args)
        self.assertTrue(snapshots)
        self.assertTrue(all(not path.parent.exists() for path in snapshots))

    @unittest.skipUnless(shutil.which("sqlcipher"), "SQLCipher CLI unavailable")
    def test_real_sqlcipher_wal_and_empty_result_use_only_snapshot(self):
        key = "ab" * 32
        writer = subprocess.Popen([shutil.which("sqlcipher"), str(self.path)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
        try:
            writer.stdin.write(
                '.bail on\n.output /dev/null\nPRAGMA key = "x\'{}\'";\n'
                'PRAGMA journal_mode=WAL;\nPRAGMA wal_autocheckpoint=0;\n'
                'CREATE TABLE events (value INTEGER);\nINSERT INTO events VALUES (42);\n'
                '.output stdout\n.print READY\n'.format(key))
            writer.stdin.flush()
            self.assertTrue(select.select([writer.stdout], [], [], 10)[0], "writer timeout")
            self.assertEqual(writer.stdout.readline().strip(), "READY")
            before = self.fingerprints()
            reader = self.reader("x'{}'".format(key))
            with mock.patch.object(wdb.subprocess, "run", wraps=subprocess.run) as run:
                self.assertEqual(reader.query("SELECT * FROM events"), [{"value": 42}])
                self.assertEqual(reader.query("SELECT * FROM events WHERE value = 0"), [])
            for call in run.call_args_list:
                self.assertNotIn(str(self.path), call.args[0])
                self.assertNotIn(key, " ".join(call.args[0]))
            reader.close()
            self.assertEqual(before, self.fingerprints())
        finally:
            writer.communicate(".quit\n", timeout=10)


class MomentRangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="wdb-moments-test-")
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "sns.db"
        # Trip posts were cached first and own the lowest rowids; forty newer
        # posts follow; browsing back later cached one more trip post last.
        rows = [(100 + day, "wxid_self", moment_xml("wxid_self", local_ts(2021, 8, 1 + day, 12))) for day in range(6)]
        rows.append((200, "wxid_friend", moment_xml("wxid_friend", local_ts(2021, 8, 3, 9))))
        rows += [(300 + n, "wxid_self", moment_xml("wxid_self", local_ts(2026, 1, 1) + n * 3600)) for n in range(40)]
        rows.append((400, "wxid_self", moment_xml("wxid_self", local_ts(2021, 9, 30, 20))))
        sns_v4_database(self.database, rows)

    def moments(self, *arguments: str) -> dict:
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "--database", str(self.database), "moments", *arguments],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def test_range_is_not_cut_by_limit_when_time_lives_in_xml(self) -> None:
        trip = ["--from", "2021-07-25", "--to", "2021-10-10", "--contact", "wxid_self"]
        result = self.moments(*trip, "--limit", "10")
        self.assertEqual([post["feedId"] for post in result["data"]], ["400", "105", "104", "103", "102", "101", "100"])
        self.assertEqual(
            {key: result["meta"][key] for key in ("count", "matchedCount", "scannedRows", "truncated")},
            {"count": 7, "matchedCount": 7, "scannedRows": 48, "truncated": False},
        )
        self.assertEqual(result["data"][0]["source"]["rowid"], 48)

        cut = self.moments(*trip, "--limit", "3")
        self.assertEqual([post["feedId"] for post in cut["data"]], ["400", "105", "104"])
        self.assertTrue(cut["meta"]["truncated"])
        self.assertEqual(cut["meta"]["matchedCount"], 7)

        everyone = self.moments("--from", "2021-07-25", "--to", "2021-10-10")
        self.assertEqual(everyone["meta"]["count"], 8)
        picked = self.moments("--feed-id", "100", "--feed-id", "400")
        self.assertEqual(sorted(post["feedId"] for post in picked["data"]), ["100", "400"])

    def test_rows_left_unread_by_an_error_report_truncated(self) -> None:
        query = wdb.Database.query

        def fail_bodies(database: wdb.Database, sql: str):
            if " WHERE rowid IN (" in sql:
                raise wdb.WdbError("SQLCipher 查询失败", "query")
            return query(database, sql)

        args = wdb.build_parser().parse_args([
            "--database", str(self.database), "moments", "--from", "2021-07-25", "--to", "2021-10-10",
        ])
        with mock.patch.object(wdb.Database, "query", fail_bodies):
            data, meta = wdb.run(args)
        self.assertEqual(data, [])
        self.assertTrue(meta["truncated"])
        self.assertEqual(meta["matchedCount"], 8)
        self.assertEqual(meta["errors"][0]["stage"], "query")


class MomentScopeTests(unittest.TestCase):
    """A keys-file account laid out like WeChat 4.x db_storage, one table per database."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="wdb-scope-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.storage = self.root / "xwechat_files" / "wxid_fixture_ab12" / "db_storage"
        august = local_ts(2021, 8, 2, 9)
        # wxid_gone was deleted: its posts stay in SnsTimeLine, its contact row is gone.
        posts = [
            (feed, author, moment_xml(author, august + feed * 60), "")
            for feed, author in enumerate(["wxid_self", "wxid_twin_a", "wxid_twin_b", "wxid_gone"], start=1)
        ]
        layout = {
            "contact/contact.db": ("contact", "username TEXT, nick_name TEXT",
                                   [("wxid_self", "我"), ("wxid_twin_a", "同名"), ("wxid_twin_b", "同名")]),
            "session/session.db": ("SessionNoContactInfoTable", "username TEXT, session_title TEXT",
                                   [("wxid_session_only", "临时会话")]),
            "general/general.db": ("wacontact", "user_name TEXT, type INTEGER", [("gh_fixture@app", 1)]),
            "sns/sns.db": ("SnsTimeLine", "tid INTEGER, user_name TEXT, content TEXT, pack_info_buf TEXT", posts),
            "message/message_0.db": ("Msg_" + hashlib.md5(b"wxid_twin_a").hexdigest(),
                                     "message_content TEXT, create_time INTEGER, local_type INTEGER", [("你好", august, 1)]),
            "head_image/head_image.db": ("head_image", "username TEXT, image_buffer BLOB", [("wxid_self", b"\x89PNG")]),
        }
        for relative, (table, columns, rows) in layout.items():
            path = self.storage / relative
            path.parent.mkdir(parents=True)
            connection = sqlite3.connect(str(path))
            try:
                connection.execute('CREATE TABLE "{}" ({})'.format(table, columns))
                connection.executemany('INSERT INTO "{}" VALUES ({})'.format(table, ", ".join("?" * len(rows[0]))), rows)
                connection.commit()
            finally:
                connection.close()
        self.keys = self.root / "keys.toml"
        self.keys.write_text(
            "".join('[[databases.unknown]]\npath = "{}"\n'.format(self.storage / relative) for relative in layout),
            encoding="utf-8",
        )
        self.august = ["--from", "2021-08-01", "--to", "2021-08-31"]

    def cli(self, *arguments: str, source: Optional[Sequence[str]] = None) -> dict:
        source = list(source or ["--keys", str(self.keys), "--account", "wxid_fixture"])
        process = subprocess.run(
            [sys.executable, str(SCRIPT), *source, *arguments],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def opened(self, *arguments: str) -> Tuple[object, dict, set]:
        args = wdb.build_parser().parse_args(["--keys", str(self.keys), "--account", "wxid_fixture", *arguments])
        with mock.patch.object(wdb.shutil, "copyfile", wraps=shutil.copyfile) as copy:
            data, meta = wdb.run(args)
        return data, meta, {Path(call.args[0]).name for call in copy.call_args_list}

    def test_contact_missing_from_contact_table_still_matches_its_posts(self) -> None:
        gone = self.cli("moments", "--contact", "wxid_gone", *self.august)
        self.assertEqual([(post["authorId"], post["feedId"]) for post in gone["data"]], [("wxid_gone", "4")])
        media = self.cli("moments-media", "--contact", "wxid_gone", *self.august, "--output", str(self.root / "out"))
        self.assertEqual(media["meta"]["postCount"], 1)
        stats = self.cli("stats", "--contact", "wxid_gone", *self.august)
        self.assertEqual(stats["data"]["moments"]["postCount"], 1)
        twins = self.cli("moments", "--contact", "同名", *self.august)
        self.assertEqual(
            sorted((post["authorId"], post["authorName"]) for post in twins["data"]),
            [("wxid_twin_a", "同名"), ("wxid_twin_b", "同名")],
        )

    def test_contact_value_inside_other_contacts_still_matches_itself(self) -> None:
        # wxid_gone is also part of a current contact's id, so the contact match is
        # not empty; its own posts and chats must still come back.
        gone_table = "Msg_" + hashlib.md5(b"wxid_gone").hexdigest()
        contact_db = sqlite3.connect(str(self.storage / "contact" / "contact.db"))
        message_db = sqlite3.connect(str(self.storage / "message" / "message_0.db"))
        try:
            contact_db.execute("INSERT INTO contact VALUES (?, ?)", ("wxid_gone_new", "换了新号"))
            message_db.execute('CREATE TABLE "{}" (message_content TEXT, create_time INTEGER, local_type INTEGER)'.format(gone_table))
            message_db.execute('INSERT INTO "{}" VALUES (?, ?, 1)'.format(gone_table), ("还记得我吗", local_ts(2021, 8, 3, 9)))
            contact_db.commit()
            message_db.commit()
        finally:
            contact_db.close()
            message_db.close()
        moments = self.cli("moments", "--contact", "wxid_gone", *self.august)
        self.assertEqual([(post["authorId"], post["feedId"]) for post in moments["data"]], [("wxid_gone", "4")])
        chats = self.cli("chats", "--contact", "wxid_gone", *self.august)
        self.assertEqual([(hit["source"]["tableName"], hit["text"]) for hit in chats["data"]], [(gone_table, "还记得我吗")])
        stats = self.cli("stats", "--contact", "wxid_gone", *self.august)
        self.assertEqual((stats["data"]["chats"]["count"], stats["data"]["moments"]["postCount"]), (1, 1))

    def test_keys_source_opens_only_databases_that_can_hold_the_table(self) -> None:
        _, meta, opened = self.opened("moments", *self.august)
        self.assertEqual(meta["count"], 4)
        self.assertEqual(opened, {"contact.db", "session.db", "general.db", "sns.db"})
        data, _, opened = self.opened("contacts")
        self.assertEqual(
            sorted(item["username"] for item in data),
            ["gh_fixture@app", "wxid_self", "wxid_session_only", "wxid_twin_a", "wxid_twin_b"],
        )
        self.assertEqual(opened, {"contact.db", "session.db", "general.db"})

    def test_explicit_databases_and_relabelled_timelines_are_still_read(self) -> None:
        sns = self.storage / "sns" / "sns.db"
        export = self.root / "export.db"
        sns_v4_database(export, [(9, "wxid_self", moment_xml("wxid_self", local_ts(2021, 8, 20, 9)))])
        explicit = self.cli("moments", *self.august, source=["--database", str(sns), "--database", str(export)])
        self.assertEqual(sorted(post["feedId"] for post in explicit["data"]), ["1", "2", "3", "4", "9"])
        # Keys-file labels are free text: the timeline under an unfamiliar label is
        # still read while a neighbouring database carries the Sns type.
        neighbour = self.storage / "sns" / "sns_index.db"
        connection = sqlite3.connect(str(neighbour))
        try:
            connection.execute("CREATE TABLE SnsIndex (tid INTEGER)")
            connection.commit()
        finally:
            connection.close()
        relabelled = self.root / "relabelled.toml"
        relabelled.write_text(
            self.keys.read_text(encoding="utf-8").replace(
                '[[databases.unknown]]\npath = "{}"'.format(sns), '[[databases.moments]]\npath = "{}"'.format(sns)
            ) + '[[databases.unknown]]\npath = "{}"\n'.format(neighbour),
            encoding="utf-8",
        )
        self.assertEqual(self.cli("moments", *self.august, source=["--keys", str(relabelled)])["meta"]["count"], 4)


class ChatQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="wdb-chats-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def chats(self, databases: Sequence[Path], *arguments: str) -> dict:
        selectors = [part for path in databases for part in ("--database", str(path))]
        process = subprocess.run(
            [sys.executable, str(SCRIPT), *selectors, "chats", *arguments],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def test_keyword_hits_are_not_cut_by_newer_blob_rows(self) -> None:
        friend = "wxid_friend"
        table = "Msg_" + hashlib.md5(friend.encode("utf-8")).hexdigest()
        base = local_ts(2026, 9, 11, 10)
        rows = [
            (base, "周末一起去爬山吗"),
            (base + 60, "<msg><appmsg><title>爬山路线</title><type>5</type></appmsg></msg>".encode("utf-8")),
            (base + 90, "好的"),
        ]
        # Newer stickers and images: BLOB bodies pass the SQL keyword filter
        # unconditionally, so they reach the Python filter ahead of the hits.
        rows += [(base + 120 + n, '<msg><emoji md5="{:032x}"/></msg>'.format(n).encode("utf-8")) for n in range(10)]
        path = self.root / "message_0.db"
        chat_database(path, {table: rows}, [friend])

        for limit in ("5", "100"):
            result = self.chats([path], "--contact", friend, "--query", "爬山", "--limit", limit)
            self.assertEqual([message["text"] for message in result["data"]], ["周末一起去爬山吗", "爬山路线"])
            self.assertEqual([message["source"]["rowid"] for message in result["data"]], [1, 2])
            self.assertFalse(result["meta"]["truncated"])
        cut = self.chats([path], "--contact", friend, "--query", "爬山", "--limit", "1")
        self.assertEqual([message["text"] for message in cut["data"]], ["爬山路线"])
        self.assertTrue(cut["meta"]["truncated"])

    def test_keyword_matches_text_rows_in_any_case(self) -> None:
        base = local_ts(2026, 9, 11, 10)
        path = self.root / "message_0.db"
        chat_database(path, {"Msg_{:032x}".format(1): [
            (base, "AI 课程今晚开始"),
            (base + 60, "Café 见"),
            (base + 120, "明天见"),
            (base + 180, "<msg><appmsg><title>ai 工具清单</title><type>5</type></appmsg></msg>".encode("utf-8")),
        ]})
        # ASCII case folds in SQL; É has no SQL fold, so TEXT rows skip the pre-filter.
        for keyword, expected in (("ai", ["AI 课程今晚开始", "ai 工具清单"]), ("CAFÉ", ["Café 见"])):
            result = self.chats([path], "--query", keyword, "--limit", "10")
            self.assertEqual([message["text"] for message in result["data"]], expected, keyword)
            self.assertFalse(result["meta"]["truncated"], keyword)

    def test_quote_with_millisecond_createtime_is_normalized(self) -> None:
        sent = local_ts(2026, 9, 11, 10)
        quote = (
            "<msg><appmsg><title>收到</title><type>57</type>"
            "<refermsg><type>1</type><content>课程几点开始</content>"
            "<createtime>{}</createtime></refermsg></appmsg></msg>"
        ).format((sent - 60) * 1000)
        path = self.root / "message_0.db"
        chat_database(path, {"Msg_{:032x}".format(1): [(sent, quote)]})
        quoted = self.chats([path], "--query", "课程", "--limit", "10")["data"][0]["quoted"]
        self.assertEqual(quoted["timestampUnix"], sent - 60)
        self.assertEqual(quoted["createTime"], wdb.iso_local(sent - 60))

    def test_limit_keeps_newest_messages_across_batches_and_databases(self) -> None:
        base = local_ts(2026, 9, 1, 8)
        # 401 chat tables force a second 400-table batch, which holds the
        # newest message of message_0.db.
        first = self.root / "message_0.db"
        chat_database(first, {"Msg_{:032x}".format(n): [(base + n * 60, "m0-{}".format(n))] for n in range(401)})
        second = self.root / "message_1.db"
        chat_database(second, {"Msg_{:032x}".format(999): [(base + 86400, "m1-newest")]})

        result = self.chats([first], "--limit", "2")
        self.assertEqual([message["text"] for message in result["data"]], ["m0-399", "m0-400"])
        self.assertTrue(result["meta"]["truncated"])
        both = self.chats([first, second], "--limit", "2")
        self.assertEqual([message["text"] for message in both["data"]], ["m0-400", "m1-newest"])
        self.assertEqual(both["meta"]["scannedTables"], 402)
        exact = self.chats([first, second], "--limit", "402")
        self.assertEqual(exact["meta"]["count"], 402)
        self.assertFalse(exact["meta"]["truncated"])

    def test_rows_left_unread_by_an_error_report_truncated(self) -> None:
        path = self.root / "message_0.db"
        chat_database(path, {"Msg_{:032x}".format(1): [(local_ts(2026, 9, 1, 8), "你好")]})
        query = wdb.Database.query

        def failing(marker: str):
            def run(database: wdb.Database, sql: str):
                if marker in sql:
                    raise wdb.WdbError("SQLCipher 查询失败", "query")
                return query(database, sql)
            return run

        for marker in ("ORDER BY COALESCE(create_time, 0) DESC", " WHERE m.rowid IN ("):
            args = wdb.build_parser().parse_args(["--database", str(path), "chats", "--limit", "5"])
            with mock.patch.object(wdb.Database, "query", failing(marker)):
                data, meta = wdb.run(args)
            self.assertEqual(data, [], marker)
            self.assertTrue(meta["truncated"], marker)
            self.assertEqual(meta["errors"][0]["stage"], "query")

    def test_zstd_content_size_reads_every_header_layout(self) -> None:
        magic = wdb.ZSTD_MAGIC
        self.assertEqual(wdb.zstd_content_size(magic + b"\x20\xc8"), 200)
        self.assertEqual(wdb.zstd_content_size(magic + b"\x40\x00" + (256).to_bytes(2, "little")), 512)
        self.assertEqual(wdb.zstd_content_size(magic + b"\x81\x00\x07" + (70000).to_bytes(4, "little")), 70000)
        self.assertEqual(wdb.zstd_content_size(magic + b"\xe3\x01\x02\x03\x04" + (1 << 33).to_bytes(8, "little")), 1 << 33)
        self.assertIsNone(wdb.zstd_content_size(magic + b"\x00\x00"))
        self.assertIsNone(wdb.zstd_content_size(magic + b"\x81\x00\x07\x01"))
        self.assertIsNone(wdb.zstd_content_size(b"<msg/>"))
        zstd = shutil.which("zstd")
        if not zstd:
            self.skipTest("zstd command not installed")
        # The reference compressor picks the field width by size.
        for size in (10, 300, 70000):
            source = self.root / "body-{}".format(size)
            source.write_bytes((b"wdb-cli " * 10000)[:size])
            frame = subprocess.run([zstd, "-q", "-c", str(source)], stdout=subprocess.PIPE, check=True).stdout
            self.assertEqual(wdb.zstd_content_size(frame), size)

    def test_zstd_bodies_share_one_process_per_chunk_without_the_module(self) -> None:
        zstd = shutil.which("zstd")
        if not zstd:
            self.skipTest("zstd command not installed")
        base = local_ts(2026, 9, 11, 10)
        texts = ["第{}条：周末爬山".format(n) if n % 3 == 0 else "第{}条".format(n) for n in range(12)]
        rows = [(base + n * 60, zstd_frame(text.encode("utf-8"))) for n, text in enumerate(texts)]
        # No declared size: decode_blob takes this frame in a process of its own.
        rows.append((base + 900, zstd_frame("没声明长度也去爬山".encode("utf-8"), declare_size=False)))
        expected = [text for text in texts if "爬山" in text] + ["没声明长度也去爬山"]
        run = subprocess.run
        calls = []

        def counting(command, *args, **kwargs):
            if command[0] == zstd:
                calls.append(command)
            return run(command, *args, **kwargs)

        def search(path: Path) -> list:
            del calls[:]
            args = wdb.build_parser().parse_args(["--database", str(path), "chats", "--query", "爬山", "--limit", "100"])
            with mock.patch.dict(sys.modules, {"zstandard": None}), mock.patch.object(subprocess, "run", counting):
                data, meta = wdb.run(args)
            self.assertFalse(meta["truncated"])
            self.assertEqual({message["contentEncoding"] for message in data}, {"zstd"})
            return [message["text"] for message in data]

        path = self.root / "message_0.db"
        chat_database(path, {"Msg_{:032x}".format(1): rows})
        self.assertEqual(search(path), expected)
        self.assertEqual(len(calls), 2)

        # A wrong declared size fails the shared process; every row then gets a
        # process of its own and the intact frames still match.
        corrupt = bytearray(zstd_frame("坏帧也提到爬山".encode("utf-8")))
        corrupt[5] += 1
        path = self.root / "message_1.db"
        chat_database(path, {"Msg_{:032x}".format(1): rows + [(base + 960, bytes(corrupt))]})
        self.assertEqual(search(path), expected)
        self.assertEqual(len(calls), 1 + len(rows) + 1)


class Isaac64Tests(unittest.TestCase):
    def test_from_seed_matches_rand_isaac_reference_vectors(self) -> None:
        # rand_isaac 0.5.0 `test_isaac64_true_values_64`, seeds given as u64 words.
        self.assertEqual(next(wdb.isaac64_blocks([1, 23, 456, 7890]))[:10], [
            15071495833797886820, 7720185633435529318, 10836773366498097981, 5414053799617603544,
            12890513357046278984, 17001051845652595546, 9240803642279356310, 12558996012687158051,
            14673053937227185542, 1677046725350116783,
        ])
        blocks, words = wdb.isaac64_blocks([12345, 67890, 54321, 9876]), []
        while len(words) < 10010:
            words.extend(next(blocks))
        self.assertEqual(words[10000:10010], [
            18143823860592706164, 8491801882678285927, 2699425367717515619, 17196852593171130876,
            2606123525235546165, 15790932315217671084, 596345674630742204, 9947027391921273664,
            11788097613744130851, 10391409374914919106,
        ])


class MomentMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="wdb-media-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / "sns.db"
        self.output = self.root / "out"
        self.jpeg = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 12 + b"\xff\xd9"
        self.png = b"\x89PNG\r\n\x1a\n" + bytes(64)
        media = (
            '<media><id>11</id><type>2</type>'
            '<thumb type="1" key="{key}" enc_idx="1" token="{token}">http://szmmsns.qpic.cn/mmsns/fixture/150</thumb>'
            '<url type="1" md5="0" key="{key}" enc_idx="1" token="{token}">http://szmmsns.qpic.cn/mmsns/fixture/0</url>'
            '<size width="640" height="480" totalSize="{size}"/></media>'
            '<media><id>12</id><type>2</type><url type="1">https://shmmsns.qpic.cn/mmsns/plain/0?idx=1</url></media>'
            '<media><id>13</id><type>6</type><url type="1">http://shzjwxsns.video.qq.com/102/20250/snsvideodownload</url></media>'
        ).format(key=SNS_FIXTURE_KEY, token=SNS_FIXTURE_TOKEN, size=len(self.jpeg))
        finder = "<finderFeed><mediaList><media><mediaType>4</mediaType><url>https://finder.video.qq.com/x</url></media></mediaList></finderFeed>"
        xml = moment_xml("wxid_self", local_ts(2021, 8, 1, 12), media).replace("</mediaList>", "</mediaList>" + finder)
        sns_v4_database(self.database, [(500, "wxid_self", xml)])
        self.requests: list = []

    def urlopen(self, request, timeout):
        self.requests.append(request)
        if "/fixture/0" in request.full_url:
            encrypted = wdb.xor_bytes(self.jpeg, wdb.isaac64_keystream(SNS_FIXTURE_KEY, len(self.jpeg)))
            return FakeResponse(encrypted, {"x-Enc": "1"})
        if "/plain/0" in request.full_url:
            return FakeResponse(self.png, {})
        raise AssertionError("unexpected request")

    def run_media(self, *arguments: str, database: Optional[Path] = None) -> Tuple[int, dict, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(wdb.urllib.request, "urlopen", self.urlopen), \
                mock.patch.object(wdb, "SNS_MEDIA_REQUEST_INTERVAL", 0), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = wdb.main(["--database", str(database or self.database), "moments-media", *arguments])
        return code, json.loads(stdout.getvalue() or "{}"), stdout.getvalue() + stderr.getvalue()

    def test_downloads_originals_and_decrypts_x_enc_without_leaking_secrets(self) -> None:
        code, result, printed = self.run_media("--feed-id", "500", "--output", str(self.output))
        self.assertEqual(code, 0, printed)
        items = result["data"]
        self.assertEqual(
            [(item["mediaIndex"], item["mediaType"], item["status"]) for item in items],
            [(1, "image", "downloaded"), (2, "image", "downloaded"), (3, "video", "skipped")],
        )
        self.assertEqual(Path(items[0]["path"]).read_bytes(), self.jpeg)
        self.assertEqual((items[0]["kind"], items[0]["encrypted"], items[0]["width"], items[0]["height"]), ("jpg", True, 640, 480))
        self.assertEqual(Path(items[0]["path"]).name, "20210801-120000_500_01.jpg")
        self.assertEqual(Path(items[1]["path"]).read_bytes(), self.png)
        self.assertEqual((items[1]["kind"], items[1]["encrypted"]), ("png", False))
        encrypted_request, plain_request = self.requests
        parts = urllib.parse.urlsplit(encrypted_request.full_url)
        self.assertEqual((parts.scheme, parts.netloc, parts.path), ("https", "szmmsns.qpic.cn", "/mmsns/fixture/0"))
        self.assertEqual(urllib.parse.parse_qs(parts.query), {"token": [SNS_FIXTURE_TOKEN], "idx": ["1"]})
        self.assertEqual(encrypted_request.get_header("User-agent"), "MicroMessenger Client")
        self.assertEqual(plain_request.full_url, "https://shmmsns.qpic.cn/mmsns/plain/0?idx=1")
        self.assertNotIn(SNS_FIXTURE_TOKEN, printed)
        self.assertNotIn(str(SNS_FIXTURE_KEY), printed)
        self.assertEqual(result["meta"]["statusCounts"], {"downloaded": 2, "exists": 0, "skipped": 1, "failed": 0})

        self.requests.clear()
        code, again, _ = self.run_media("--feed-id", "500", "--output", str(self.output))
        self.assertEqual(code, 0)
        self.assertEqual([item["status"] for item in again["data"]], ["exists", "exists", "skipped"])
        self.assertEqual(self.requests, [])

    def test_placeholder_answer_fails_without_writing(self) -> None:
        def placeholder(request, timeout):
            self.requests.append(request)
            return FakeResponse(b"\x89PNG\r\n\x1a\n" + bytes(32), {"X-Errno": "-106"})

        self.urlopen = placeholder
        code, result, printed = self.run_media("--feed-id", "500", "--output", str(self.output))
        self.assertEqual(code, 1)
        self.assertEqual([item["status"] for item in result["data"]], ["failed", "failed", "skipped"])
        self.assertEqual({error["stage"] for error in result["meta"]["errors"]}, {"placeholder"})
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertNotIn(SNS_FIXTURE_TOKEN, printed)

    def test_refuses_wechat_data_dir_and_unscoped_runs(self) -> None:
        account = self.root / "xwechat_files" / "wxid_fixture_ab12"
        (account / "db_storage" / "sns").mkdir(parents=True)
        inside = account / "db_storage" / "sns" / "sns.db"
        shutil.copyfile(self.database, inside)
        code, _, printed = self.run_media("--feed-id", "500", "--output", str(account / "exports"), database=inside)
        self.assertEqual(code, 2)
        self.assertIn('"stage": "arguments"', printed)
        self.assertFalse((account / "exports").exists())
        code, _, _ = self.run_media("--output", str(self.output))
        self.assertEqual(code, 2)
        self.assertEqual(self.requests, [])


def hevc_frame(workdir: Path, name: str, pix_fmt: str, lavfi: str) -> bytes:
    target = workdir / f"{name}.hevc"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", lavfi, "-frames:v", "1",
         "-pix_fmt", pix_fmt, "-c:v", "libx265", "-x265-params", "log-level=none", str(target)],
        check=True,
    )
    return target.read_bytes()


def v2_container(payload: bytes, aes_key: bytes, xor_key: int, aes_size: int = 64, xor_size: int = 32) -> bytes:
    pad = 16 - aes_size % 16
    proc = subprocess.run(
        ["openssl", "enc", "-e", "-aes-128-ecb", "-nopad", "-K", aes_key.hex()],
        input=payload[:aes_size] + bytes([pad]) * pad,
        stdout=subprocess.PIPE,
        check=True,
    )
    tail = bytes(byte ^ xor_key for byte in payload[len(payload) - xor_size :])
    header = b"\x07\x08V2\x08\x07" + struct.pack("<II", aes_size, xor_size) + b"\x01"
    return header + proc.stdout + payload[aes_size : len(payload) - xor_size] + tail


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe") and shutil.which("openssl"), "needs ffmpeg + openssl")
class WxgfDecodeTests(unittest.TestCase):
    CODE = 1223854821
    WXID = "wxid_fixture"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        kvcomm = root / "app_data/net/kvcomm"
        kvcomm.mkdir(parents=True)
        (kvcomm / f"key_{self.CODE}_fixture").write_bytes(b"")
        self.img_dir = root / f"xwechat_files/{self.WXID}_a1b2/msg/attach/hash/2026-09/Img"
        self.img_dir.mkdir(parents=True)
        self.aes_key = hashlib.md5(f"{self.CODE}{self.WXID}".encode()).hexdigest()[:16].encode()
        self.colour = hevc_frame(root, "colour", "yuv420p", "color=c=red:s=64x48")
        self.alpha = hevc_frame(root, "alpha", "gray", "color=c=black:s=64x48,drawbox=x=0:y=0:w=32:h=48:c=white:t=fill")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def decode(self, streams: bytes):
        payload = b"wxgf\x13" + bytes(14) + streams
        path = self.img_dir / "media.dat"
        path.write_bytes(v2_container(payload, self.aes_key, self.CODE & 0xFF))
        return dat.decode_file(path)

    def test_single_stream_renders_jpeg(self) -> None:
        image, meta = self.decode(self.colour)
        self.assertTrue(image.startswith(b"\xff\xd8\xff"))
        self.assertEqual((meta["kind"], meta["container"], meta["streams"], meta["alpha"]), ("jpg", "wxgf", 1, False))

    def test_alpha_stream_first_is_merged_not_rendered_as_image(self) -> None:
        image, meta = self.decode(self.alpha + self.colour)
        self.assertTrue(image.startswith(b"\x89PNG"))
        self.assertEqual((meta["kind"], meta["streams"], meta["alpha"]), ("png", 2, True))
        self.assertTrue(dat.png_chunk_crc_ok(image))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-q", "--quiet", action="store_true", help="仅输出失败信息")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1 if args.quiet else 2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
