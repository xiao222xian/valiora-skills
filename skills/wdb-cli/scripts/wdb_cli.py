#!/usr/bin/env python3
"""Standalone, read-only WeChat SQLCipher query CLI for Agent workflows."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import http.client
import json
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "lov-wdb-cli/v1"
MAX_BLOB_BYTES = 16 * 1024 * 1024
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
ZSTD_BATCH_BYTES = 64 * 1024 * 1024
CHAT_CONTENT_COLUMNS = ["message_content", "msgcontent", "strcontent", "content"]
CHAT_TIME_COLUMNS = [
    "create_time", "msgcreatetime", "createtime", "msg_time", "msgtime", "timestamp", "time"
]
CHAT_TYPE_COLUMNS = ["local_type", "messagetype", "message_type", "type", "msgtype", "msg_type"]
CHAT_DIRECTION_COLUMNS = ["mesdes", "direction", "is_send", "issend"]
CONTACT_USERNAME_COLUMNS = [
    "m_nsusrname", "m_nsusername", "username", "user_name", "usr_name", "usrname", "wxid",
    "contact_username",
]
CONTACT_NICKNAME_COLUMNS = ["nickname", "nick_name", "nickname", "m_nsnickname", "m_nsnick"]
CONTACT_REMARK_COLUMNS = ["m_nsremark", "remark", "conremark", "remark_name", "remarkname"]
CONTACT_ALIAS_COLUMNS = ["m_nsaliasname", "alias", "aliasname"]
CONTACT_PACKED_COLUMNS = ["_packed_wccontactdata", "packed_wccontactdata", "wccontactdata", "extra_buffer"]
WDB_PRO_MANAGED_KEYS_RELATIVE_PATHS = [
    Path("Library/Application Support/ai.lovstudio.wdb-pro/database-keys/wdb-pro-managed-keys.json"),
    Path("Library/Application Support/me.lovpen.wdb-pro/database-keys/wdb-pro-managed-keys.json"),
]
CHAT_BODY_CHUNK_ROWS = 2000
MOMENT_TIME_SNIPPET_CHARS = 64
SNS_MEDIA_TYPES = {"2": "image", "6": "video"}
SNS_MEDIA_HOSTS = ("qpic.cn", "wechat.com", "qq.com")
SNS_MEDIA_USER_AGENT = "MicroMessenger Client"
SNS_MEDIA_MAX_BYTES = 20 * 1024 * 1024
SNS_MEDIA_REQUEST_INTERVAL = 0.4
SNS_PLACEHOLDER_ERRNOS = {"-106", "-107", "-108"}
SNS_IMAGE_SIGNATURES = [
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
]
U64_MASK = (1 << 64) - 1
ISAAC64_INIT = (
    0x647C4677A2884B7C, 0xB9F8B322C73AC862, 0x8C0EA5053D4712A0, 0xB29B2E824A595524,
    0x82F053DB8355E0CE, 0x48FE4A0FA5A09315, 0xAE985BF2CBFC89ED, 0x98F5704F6C44C0AB,
)


class WdbError(RuntimeError):
    def __init__(self, message: str, stage: str, **debug: Any) -> None:
        super().__init__(message)
        self.stage = stage
        self.debug = {key: value for key, value in debug.items() if value is not None and key != "key"}


@dataclass(frozen=True)
class DatabaseSpec:
    path: Path
    key: Optional[str] = None
    cipher_compatibility: int = 3
    db_type: str = "unknown"
    source: str = "direct"

    def public(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "filename": self.path.name,
            "type": self.db_type,
            "encrypted": bool(self.key),
            "cipherCompatibility": self.cipher_compatibility if self.key else None,
            "exists": self.path.is_file(),
            "source": self.source,
        }


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sql_text(value: str) -> str:
    return "CAST(X'{}' AS TEXT)".format(value.encode("utf-8").hex())


def first_column(columns: Sequence[str], candidates: Sequence[str]) -> Optional[str]:
    by_lower = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in by_lower:
            return by_lower[candidate.lower()]
    return None


def normalize_timestamp(value: Any) -> Optional[int]:
    try:
        number = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return None
    if number <= 0:
        return None
    while number > 10_000_000_000:
        number //= 1000
    return number if 315_532_800 <= number <= 4_102_444_800 else None


def iso_local(seconds: Optional[int]) -> Optional[str]:
    if seconds is None:
        return None
    return dt.datetime.fromtimestamp(seconds).astimezone().isoformat(timespec="seconds")


def parse_day_or_range(date_value: Optional[str], start: Optional[str], end: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    if date_value:
        try:
            start_dt = dt.datetime.strptime(date_value, "%Y-%m-%d").astimezone()
        except ValueError as exc:
            raise WdbError("日期必须使用 YYYY-MM-DD", "arguments", date=date_value) from exc
        return int(start_dt.timestamp()), int((start_dt + dt.timedelta(days=1)).timestamp())
    if not start and not end:
        return None, None

    def parse_boundary(value: Optional[str], is_end: bool) -> Optional[int]:
        if not value:
            return None
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                parsed = dt.datetime.strptime(value, "%Y-%m-%d").astimezone()
                if is_end:
                    parsed += dt.timedelta(days=1)
            else:
                parsed = dt.datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    parsed = parsed.astimezone()
            return int(parsed.timestamp())
        except ValueError as exc:
            raise WdbError("时间边界必须是 YYYY-MM-DD 或 ISO 8601", "arguments", value=value) from exc

    start_ts, end_ts = parse_boundary(start, False), parse_boundary(end, True)
    if start_ts is not None and end_ts is not None and end_ts <= start_ts:
        raise WdbError("结束时间必须晚于开始时间", "arguments", start=start, end=end)
    return start_ts, end_ts


def infer_db_type(path: Path, explicit: Optional[str] = None) -> str:
    if explicit and explicit.lower() not in {"", "unknown", "data"}:
        return explicit
    text = str(path).lower()
    name = path.name.lower()
    if "contact" in text or "wccontact" in name:
        return "Contact"
    if "/message/" in text or name.startswith(("msg", "message", "biz_message")):
        return "Message"
    if "/sns/" in text or name.startswith("sns"):
        return "Sns"
    if "session" in text:
        return "Session"
    if "head_image" in text:
        return "HeadImage"
    return explicit or "unknown"


def _parse_toml_like(content: str, source: Path) -> List[DatabaseSpec]:
    specs: List[DatabaseSpec] = []
    current: Dict[str, Any] = {}
    current_type = "unknown"

    def flush() -> None:
        nonlocal current
        if current.get("path"):
            path = Path(os.path.expandvars(os.path.expanduser(str(current["path"]))))
            explicit = str(current.get("type") or current_type)
            specs.append(DatabaseSpec(
                path=path,
                key=str(current.get("key")) if current.get("key") else None,
                cipher_compatibility=int(current.get("cipher_compatibility") or 3),
                db_type=infer_db_type(path, explicit),
                source=str(source),
            ))
        current = {}

    for raw_line in content.splitlines():
        line = raw_line.strip()
        header = re.fullmatch(r"\[\[databases\.([^\]]+)\]\]", line)
        if header:
            flush()
            current_type = header.group(1)
            continue
        match = re.match(r"^(path|key|type|cipher_compatibility)\s*=\s*(.+?)\s*$", line)
        if not match:
            continue
        key, raw_value = match.groups()
        raw_value = raw_value.split(" #", 1)[0].strip()
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in "\"'":
            raw_value = raw_value[1:-1]
        current[key] = raw_value
    flush()
    return specs


def _parse_dtrace(content: str, source: Path) -> List[DatabaseSpec]:
    specs: List[DatabaseSpec] = []
    current_path: Optional[str] = None
    for line in content.splitlines():
        path_match = re.search(r"sqlcipher db path:\s*['\"](.+?)['\"]", line.strip(), re.I)
        if path_match:
            current_path = path_match.group(1)
            continue
        key_match = re.search(r"PRAGMA\s+key\s*=\s*[\"'](.+?)[\"']\s*;?", line.strip(), re.I)
        if key_match and current_path:
            path = Path(os.path.expandvars(os.path.expanduser(current_path)))
            specs.append(DatabaseSpec(path, key_match.group(1), 3, infer_db_type(path), str(source)))
            current_path = None
    return specs


def _load_keys_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WdbError("密钥 JSON 解析失败", "load_keys", keysSource=str(path), error=str(exc)) from exc


def _normalize_wdb_pro_key(value: Any, path: Path, index: int) -> str:
    key = str(value or "").strip()
    match = re.fullmatch(r"(?:[xX]'([0-9a-fA-F]{64})'|0[xX]([0-9a-fA-F]{64})|([0-9a-fA-F]{64}))", key)
    if not match:
        raise WdbError(
            "WDB Pro 管理副本中的密钥必须是 64 位十六进制字符串",
            "load_keys",
            keysSource=str(path),
            entry=index,
        )
    return "x'{}'".format(next(group for group in match.groups() if group).lower())


def _parse_wdb_pro_managed(path: Path, raw: Any) -> List[DatabaseSpec]:
    if not isinstance(raw, list):
        raise WdbError("WDB Pro 管理副本顶层必须是数组", "load_keys", keysSource=str(path))
    specs: List[DatabaseSpec] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise WdbError("WDB Pro 管理副本条目必须是对象", "load_keys", keysSource=str(path), entry=index)
        database_path = str(entry.get("path") or "").strip()
        if not database_path:
            raise WdbError("WDB Pro 管理副本中的数据库路径不能为空", "load_keys", keysSource=str(path), entry=index)
        try:
            compatibility = int(entry.get("cipherCompatibility", entry.get("cipher_compatibility", 4)))
        except (TypeError, ValueError) as exc:
            raise WdbError(
                "WDB Pro 管理副本中的 cipherCompatibility 必须是整数",
                "load_keys",
                keysSource=str(path),
                entry=index,
            ) from exc
        if compatibility <= 0:
            raise WdbError(
                "WDB Pro 管理副本中的 cipherCompatibility 必须大于 0",
                "load_keys",
                keysSource=str(path),
                entry=index,
            )
        full_path = Path(os.path.expandvars(os.path.expanduser(database_path)))
        specs.append(DatabaseSpec(
            full_path,
            _normalize_wdb_pro_key(entry.get("key"), path, index),
            compatibility,
            infer_db_type(full_path),
            str(path),
        ))
    if not specs:
        raise WdbError("WDB Pro 管理副本中没有可用数据库条目", "load_keys", keysSource=str(path))
    return specs


def _parse_wechat_cli(path: Path, raw: Any) -> List[DatabaseSpec]:
    if not isinstance(raw, dict):
        raise WdbError("wechat-cli all_keys.json 顶层必须是对象", "load_keys", keysSource=str(path))
    config_path = path.with_name("config.json")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        db_dir = Path(os.path.expandvars(os.path.expanduser(str(config["db_dir"]))))
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise WdbError("wechat-cli config.json 缺失或 db_dir 无效", "load_keys", configPath=str(config_path), error=str(exc)) from exc
    specs: List[DatabaseSpec] = []
    for relative, key_info in raw.items():
        if not isinstance(key_info, dict) or not key_info.get("enc_key"):
            continue
        candidate = Path(str(relative))
        full_path = candidate if candidate.is_absolute() else db_dir / candidate
        key = str(key_info["enc_key"]).strip()
        if re.fullmatch(r"[0-9a-fA-F]+", key):
            key = "x'{}'".format(key)
        specs.append(DatabaseSpec(full_path, key, 4, infer_db_type(full_path), str(path)))
    return specs


def parse_keys_file(path: Path) -> List[DatabaseSpec]:
    if not path.is_file():
        raise WdbError("密钥文件不存在", "load_keys", keysSource=str(path))
    if path.suffix.lower() == ".json":
        raw = _load_keys_json(path)
        if path.name == "wdb-pro-managed-keys.json" or isinstance(raw, list):
            return _parse_wdb_pro_managed(path, raw)
        return _parse_wechat_cli(path, raw)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WdbError("密钥文件读取失败", "load_keys", keysSource=str(path), error=str(exc)) from exc
    specs = _parse_dtrace(content, path)
    if not specs:
        specs = _parse_toml_like(content, path)
    if not specs:
        raise WdbError("密钥文件中没有可用数据库条目", "load_keys", keysSource=str(path))
    return specs


def resolve_keys_path(explicit: Optional[str]) -> Optional[Path]:
    candidates: List[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    elif os.environ.get("WDB_KEYS_FILE"):
        candidates.append(Path(os.environ["WDB_KEYS_FILE"]).expanduser())
    else:
        candidates.extend(Path.home() / relative for relative in WDB_PRO_MANAGED_KEYS_RELATIVE_PATHS)
        candidates.extend([
            Path.home() / ".wechat-cli" / "all_keys.json",
            Path.cwd() / "keys.toml",
            Path.cwd() / "wdb.keys",
        ])
        key_files = sorted(Path.cwd().glob("*.keys"))
        if len(key_files) == 1:
            candidates.extend(key_files)
    return next((path.resolve() for path in candidates if path.is_file()), None)


def load_specs(args: argparse.Namespace) -> Tuple[List[DatabaseSpec], Optional[Path]]:
    key_path = resolve_keys_path(args.keys)
    specs = parse_keys_file(key_path) if key_path else []
    direct_paths = [Path(item).expanduser().resolve() for item in (args.database or [])]
    if direct_paths:
        by_path = {spec.path.expanduser().resolve(): spec for spec in specs}
        specs = [by_path.get(path, DatabaseSpec(path=path, db_type=infer_db_type(path))) for path in direct_paths]
    if args.account:
        needle = args.account.lower()
        specs = [spec for spec in specs if needle in str(spec.path).lower()]
    deduped: List[DatabaseSpec] = []
    seen = set()
    for spec in specs:
        resolved = spec.path.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(DatabaseSpec(resolved, spec.key, spec.cipher_compatibility, spec.db_type, spec.source))
    if not deduped:
        raise WdbError(
            "没有定位到数据库；请提供 --keys、WDB_KEYS_FILE 或 --database",
            "resolve_source",
            keysSource=str(key_path) if key_path else None,
            account=args.account,
        )
    return deduped, key_path


class Database:
    def __init__(self, spec: DatabaseSpec, sqlcipher_path: Optional[str]) -> None:
        self.spec = spec
        self.sqlcipher_path = sqlcipher_path
        self.strategy: Optional[Tuple[List[str], List[str], str]] = None
        self._snapshot_dir: Optional[tempfile.TemporaryDirectory] = None
        self._snapshot_path: Optional[Path] = None

    def close(self) -> None:
        if self._snapshot_dir is not None:
            self._snapshot_dir.cleanup()
            self._snapshot_dir = None
            self._snapshot_path = None
            self.strategy = None

    def _read_path(self) -> Path:
        if self._snapshot_path is not None:
            return self._snapshot_path
        source = self.spec.path
        wal = Path(str(source) + "-wal")
        journal = Path(str(source) + "-journal")

        def signature(path: Path) -> Optional[Tuple[int, ...]]:
            try:
                info = path.stat()
            except FileNotFoundError:
                return None
            return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

        # Even read-only SQLite/SQLCipher can modify the live WAL index. Only
        # ordinary file reads touch the source; never copy or open its SHM.
        for _ in range(3):
            temporary = None
            try:
                before = [signature(path) for path in (source, wal, journal)]
                if before[0] is None:
                    raise WdbError("数据库文件不存在", "snapshot", databasePath=str(source))
                if before[2] is not None and before[2][2] > 0:
                    raise WdbError("存在回滚日志，无法安全复制；请使用已完成的离线副本", "snapshot")
                temporary = tempfile.TemporaryDirectory(prefix="wdb-cli-snapshot-")
                target = Path(temporary.name) / "database.db"
                shutil.copyfile(source, target)
                target.chmod(0o600)
                if before[1] is not None:
                    target_wal = Path(str(target) + "-wal")
                    shutil.copyfile(wal, target_wal)
                    target_wal.chmod(0o600)
                after = [signature(path) for path in (source, wal, journal)]
                if before != after:
                    continue
                self._snapshot_dir = temporary
                self._snapshot_path = target
                temporary = None
                return target
            except FileNotFoundError:
                # A WAL can disappear during a checkpoint. Retry a fresh pair.
                continue
            except OSError as exc:
                raise WdbError("数据库快照复制失败", "snapshot", errno=exc.errno) from exc
            finally:
                if temporary is not None:
                    temporary.cleanup()
        raise WdbError("数据库持续变化，未获得稳定副本；稍后重试或使用离线副本", "snapshot", attempts=3)

    def _plain_query(self, sql: str) -> List[Dict[str, Any]]:
        uri = self._read_path().as_uri() + "?mode=ro"
        try:
            connection = sqlite3.connect(uri, uri=True)
            connection.row_factory = sqlite3.Row
            try:
                connection.execute("PRAGMA query_only = ON")
                rows = connection.execute(sql).fetchall()
                return [dict(row) for row in rows]
            finally:
                connection.close()
        except sqlite3.Error as exc:
            raise WdbError("SQLite 查询失败", "query", databasePath=str(self.spec.path), error=str(exc)) from exc

    def _key_pragma(self) -> str:
        value = (self.spec.key or "").strip()
        if re.fullmatch(r"x'[0-9a-fA-F]+'", value):
            return 'PRAGMA key = "{}";'.format(value)
        if re.fullmatch(r"[0-9a-fA-F]{64,}", value):
            return 'PRAGMA key = "x\'{}\'";'.format(value)
        return "PRAGMA key = '{}';".format(value.replace("'", "''"))

    def _strategies(self) -> List[Tuple[List[str], List[str], str]]:
        compat = int(self.spec.cipher_compatibility or 3)
        raw = [
            ([], [], "native"),
            (["PRAGMA cipher_compatibility = {};".format(compat)], [], "declared-compatibility"),
            (["PRAGMA cipher_compatibility = 4;"], [], "sqlcipher4"),
            (["PRAGMA cipher_compatibility = 3;"], [], "sqlcipher3"),
            (["PRAGMA cipher_compatibility = 3;"], [
                "PRAGMA cipher_page_size = 1024;", "PRAGMA kdf_iter = 64000;",
                "PRAGMA cipher_hmac_algorithm = HMAC_SHA1;",
                "PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA1;",
            ], "legacy-sqlcipher3"),
        ]
        unique: List[Tuple[List[str], List[str], str]] = []
        seen = set()
        for before, after, name in raw:
            signature = (tuple(before), tuple(after))
            if signature not in seen:
                seen.add(signature)
                unique.append((before, after, name))
        return unique

    def _cipher_query(self, sql: str, strategy: Tuple[List[str], List[str], str]) -> List[Dict[str, Any]]:
        if not self.sqlcipher_path:
            raise WdbError(
                "读取加密数据库需要 sqlcipher 命令",
                "dependency",
                install="brew install sqlcipher",
                databasePath=str(self.spec.path),
            )
        before, after, strategy_name = strategy
        script = "\n".join([
            ".bail on", ".timeout 5000", ".headers on", ".mode json",
            ".output /dev/null",
            *before, self._key_pragma(), *after, "PRAGMA query_only = ON;",
            ".output stdout",
            sql.rstrip(";") + ";",
        ]) + "\n"
        try:
            process = subprocess.run(
                [self.sqlcipher_path, "-readonly", str(self._read_path())],
                input=script,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise WdbError("SQLCipher 进程执行失败", "query", databasePath=str(self.spec.path), error=str(exc)) from exc
        if process.returncode != 0:
            raise WdbError(
                "SQLCipher 查询失败", "query", databasePath=str(self.spec.path),
                backend="sqlcipher", strategy=strategy_name,
                error=process.stderr.strip()[-1500:] or "exit {}".format(process.returncode),
            )
        output = process.stdout.strip()
        if not output:
            return []
        try:
            decoder = json.JSONDecoder()
            parsed_values = []
            offset = 0
            while offset < len(output):
                while offset < len(output) and output[offset].isspace():
                    offset += 1
                if offset >= len(output):
                    break
                parsed_value, offset = decoder.raw_decode(output, offset)
                parsed_values.append(parsed_value)
            parsed = parsed_values[-1] if parsed_values else []
        except json.JSONDecodeError as exc:
            raise WdbError(
                "SQLCipher JSON 输出解析失败", "query", databasePath=str(self.spec.path),
                backend="sqlcipher", strategy=strategy_name, output=output[:500],
            ) from exc
        if not isinstance(parsed, list):
            raise WdbError("SQLCipher 返回结构异常", "query", databasePath=str(self.spec.path), backend="sqlcipher")
        return [row for row in parsed if isinstance(row, dict)]

    def _ensure_strategy(self) -> None:
        if not self.spec.key or self.strategy is not None:
            return
        errors = []
        for strategy in self._strategies():
            try:
                self._cipher_query("SELECT count(*) AS count FROM sqlite_master", strategy)
                self.strategy = strategy
                return
            except WdbError as exc:
                errors.append({"strategy": strategy[2], "error": exc.debug.get("error", str(exc))})
        raise WdbError(
            "所有 SQLCipher 兼容策略均未打开数据库",
            "open_database",
            databasePath=str(self.spec.path),
            backend="sqlcipher",
            attempts=errors,
        )

    def query(self, sql: str) -> List[Dict[str, Any]]:
        self._read_path()
        if not self.spec.key:
            return self._plain_query(sql)
        self._ensure_strategy()
        assert self.strategy is not None
        return self._cipher_query(sql, self.strategy)

    @property
    def backend_name(self) -> str:
        if not self.spec.key:
            return "sqlite3"
        return self.strategy[2] if self.strategy else "sqlcipher"


class Context:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.specs, self.keys_path = load_specs(args)
        sqlcipher_path = args.sqlcipher or os.environ.get("WDB_SQLCIPHER") or shutil.which("sqlcipher")
        self.databases = [Database(spec, sqlcipher_path) for spec in self.specs]
        self._tables: Dict[str, List[str]] = {}
        self._columns: Dict[Tuple[str, str], List[str]] = {}
        self._column_details: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

    def __enter__(self) -> "Context":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        for database in self.databases:
            database.close()

    def databases_except(self, db_types: Sequence[str]) -> List[Database]:
        # Listing tables snapshots the whole file, and one account's message
        # databases alone run to gigabytes, so a lookup skips the types that
        # cannot hold its table. --database picks, or a filter that leaves
        # nothing, read every database.
        if self.args.database:
            return self.databases
        skipped = {db_type.lower() for db_type in db_types}
        kept = [database for database in self.databases if database.spec.db_type.lower() not in skipped]
        return kept or self.databases

    def _load_schema(self, database: Database) -> None:
        database_key = str(database.spec.path)
        if database_key in self._tables:
            return
        rows = database.query(
            "SELECT m.name AS table_name, p.cid, p.name AS column_name, p.type AS column_type, "
            "p.\"notnull\" AS not_null, p.dflt_value, p.pk "
            "FROM sqlite_master m LEFT JOIN pragma_table_info(m.name) p "
            "WHERE m.type IN ('table','view') ORDER BY m.name, p.cid"
        )
        tables: List[str] = []
        details_by_table: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            table = str(row.get("table_name") or "")
            if not table:
                continue
            if table not in details_by_table:
                tables.append(table)
                details_by_table[table] = []
            if row.get("column_name") is not None:
                details_by_table[table].append({
                    "name": row.get("column_name"),
                    "type": row.get("column_type"),
                    "nullable": not bool(row.get("not_null")),
                    "primaryKey": bool(row.get("pk")),
                    "default": row.get("dflt_value"),
                })
        self._tables[database_key] = tables
        for table, details in details_by_table.items():
            cache_key = (database_key, table)
            self._column_details[cache_key] = details
            self._columns[cache_key] = [str(item["name"]) for item in details]

    def tables(self, database: Database) -> List[str]:
        key = str(database.spec.path)
        self._load_schema(database)
        return self._tables[key]

    def columns(self, database: Database, table: str) -> List[str]:
        key = (str(database.spec.path), table)
        self._load_schema(database)
        return self._columns[key]

    def column_details(self, database: Database, table: str) -> List[Dict[str, Any]]:
        key = (str(database.spec.path), table)
        self._load_schema(database)
        return self._column_details[key]


def read_varint(data: bytes, offset: int) -> Optional[Tuple[int, int]]:
    value = 0
    shift = 0
    for index in range(offset, min(len(data), offset + 10)):
        byte = data[index]
        value |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            return value, index + 1
        shift += 7
    return None


def proto_field(data: bytes, target: int) -> Optional[bytes]:
    offset = 0
    fields = 0
    while offset < len(data) and fields < 512:
        key = read_varint(data, offset)
        if not key:
            return None
        key_value, offset = key
        field_number, wire_type = key_value // 8, key_value % 8
        fields += 1
        if wire_type == 0:
            value = read_varint(data, offset)
            if not value:
                return None
            offset = value[1]
        elif wire_type == 1:
            offset += 8
        elif wire_type == 2:
            length = read_varint(data, offset)
            if not length:
                return None
            size, start = length
            end = start + size
            if end > len(data):
                return None
            if field_number == target:
                return data[start:end]
            offset = end
        elif wire_type == 5:
            offset += 4
        else:
            return None
    return None


def packed_profile(hex_value: Optional[str]) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {"signature": None, "momentsCoverUrl": None}
    if not hex_value or not re.fullmatch(r"[0-9a-fA-F]+", hex_value) or len(hex_value) % 2:
        return result
    try:
        data = bytes.fromhex(hex_value[: 128 * 1024])
    except ValueError:
        return result
    signature = proto_field(data, 4)
    if signature and len(signature) <= 1024:
        try:
            text = signature.decode("utf-8").strip()
            if text and len(text) <= 280 and not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", text):
                result["signature"] = text
        except UnicodeDecodeError:
            pass
    sns_profile = proto_field(data, 27)
    cover = proto_field(sns_profile, 2) if sns_profile else None
    if cover and len(cover) <= 4096:
        try:
            url = cover.decode("utf-8").strip()
            parsed = urllib.parse.urlparse(url)
            host = (parsed.hostname or "").lower()
            allowed = any(host == suffix or host.endswith("." + suffix) for suffix in ("qpic.cn", "wechat.com", "qq.com"))
            if parsed.scheme in {"http", "https"} and allowed:
                result["momentsCoverUrl"] = url
        except UnicodeDecodeError:
            pass
    return result


def decode_blob(hex_value: Optional[str]) -> Tuple[Optional[str], str]:
    if not hex_value or not re.fullmatch(r"[0-9a-fA-F]+", hex_value) or len(hex_value) % 2:
        return None, "invalid-blob"
    data = bytes.fromhex(hex_value)
    if len(data) > MAX_BLOB_BYTES:
        return None, "blob-too-large"
    if data.startswith(ZSTD_MAGIC):
        try:
            import zstandard  # type: ignore
            return zstandard.ZstdDecompressor().decompress(data, max_output_size=MAX_BLOB_BYTES).decode("utf-8", "replace"), "zstd"
        except Exception:
            binary = shutil.which("zstd")
            if binary:
                proc = subprocess.run([binary, "-q", "-d", "-c"], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                if proc.returncode == 0 and len(proc.stdout) <= MAX_BLOB_BYTES:
                    return proc.stdout.decode("utf-8", "replace"), "zstd"
            return None, "zstd-unavailable"
    try:
        import lz4.block  # type: ignore
        decoded = lz4.block.decompress(data, uncompressed_size=min(len(data) * 256, MAX_BLOB_BYTES))
        text = decoded.rstrip(b"\x00").decode("utf-8", "replace")
        if "<" in text and ">" in text:
            return text, "lz4"
    except Exception:
        pass
    try:
        text = data.rstrip(b"\x00").decode("utf-8")
        printable = sum(char.isprintable() or char.isspace() for char in text)
        if text and printable / len(text) > 0.9:
            return text, "utf8-blob"
    except UnicodeDecodeError:
        pass
    return None, "binary"


def zstd_content_size(data: bytes) -> Optional[int]:
    """Frame_Content_Size from a zstd frame header (RFC 8878), or None when not declared."""
    if len(data) < 5 or not data.startswith(ZSTD_MAGIC):
        return None
    descriptor = data[4]
    single_segment = bool(descriptor & 0x20)
    width = (1 if single_segment else 0, 2, 4, 8)[descriptor >> 6]
    if not width:
        return None
    # Magic, descriptor, window descriptor (absent in single-segment frames), dictionary ID.
    start = 5 + (0 if single_segment else 1) + (0, 1, 2, 4)[descriptor & 0x03]
    field = data[start: start + width]
    if len(field) < width:
        return None
    return int.from_bytes(field, "little") + (256 if width == 2 else 0)


def predecode_zstd_rows(rows: Sequence[Dict[str, Any]], prefix: str = "content") -> None:
    """Without the zstandard module, decompress the rows' zstd bodies in shared zstd processes.

    decode_blob alone starts one process per body, which takes about an hour for a
    keyword scan of one 4.x shard. Frames are concatenated and the output is split
    back by each header's declared content size; rows without a declared size, and
    every row of a batch whose process fails or whose output does not add up, are
    left to decode_blob.
    """
    binary = shutil.which("zstd")
    if not binary or module_available("zstandard"):
        return
    batches: List[List[Tuple[Dict[str, Any], bytes, int]]] = [[]]
    budget = 0
    for row in rows:
        value = row.get("__{}".format(prefix))
        if str(row.get("__{}_type".format(prefix))) != "blob" or not isinstance(value, str):
            continue
        if len(value) % 2 or len(value) // 2 > MAX_BLOB_BYTES or not re.fullmatch(r"[0-9a-fA-F]+", value):
            continue
        data = bytes.fromhex(value)
        size = zstd_content_size(data)
        if size is None or size > MAX_BLOB_BYTES:
            continue
        if batches[-1] and budget + size > ZSTD_BATCH_BYTES:
            batches.append([])
            budget = 0
        batches[-1].append((row, data, size))
        budget += size
    for batch in batches:
        if not batch:
            continue
        try:
            proc = subprocess.run(
                [binary, "-q", "-d", "-c"], input=b"".join(data for _, data, _ in batch),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0 or len(proc.stdout) != sum(size for _, _, size in batch):
            continue
        offset = 0
        for row, _, size in batch:
            row["__{}_decoded".format(prefix)] = (proc.stdout[offset: offset + size].decode("utf-8", "replace"), "zstd")
            offset += size


def content_from_row(row: Dict[str, Any], prefix: str = "content") -> Tuple[Optional[str], str]:
    kind = str(row.get("__{}_type".format(prefix)) or "null")
    value = row.get("__{}".format(prefix))
    if value is None:
        return None, kind
    if kind == "blob":
        return row.get("__{}_decoded".format(prefix)) or decode_blob(str(value))
    return str(value), "text"


def find_contact_table(ctx: Context, database: Database) -> Optional[str]:
    tables = ctx.tables(database)
    exact = next((table for table in tables if table.lower() == "wccontact"), None)
    if exact:
        return exact
    for table in tables:
        if "contact" in table.lower():
            columns = [column.lower() for column in ctx.columns(database, table)]
            if any(name in columns for name in CONTACT_USERNAME_COLUMNS):
                return table
    return None


def contact_rows(ctx: Context, match: Optional[str], limit: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    # Contact-like tables also live in session.db and general.db, so skip only
    # the types that never hold one.
    for database in ctx.databases_except(["Message", "HeadImage", "Sns"]):
        try:
            table = find_contact_table(ctx, database)
            if not table:
                continue
            columns = ctx.columns(database, table)
            username = first_column(columns, CONTACT_USERNAME_COLUMNS)
            if not username:
                continue
            nickname = first_column(columns, CONTACT_NICKNAME_COLUMNS)
            remark = first_column(columns, CONTACT_REMARK_COLUMNS)
            alias = first_column(columns, CONTACT_ALIAS_COLUMNS)
            packed = first_column(columns, CONTACT_PACKED_COLUMNS)
            added = first_column(columns, ["m_uiaddtime", "m_uicreatetime", "add_time", "addtime", "create_time", "createtime"])
            con_type = first_column(columns, ["m_uicontype", "local_type", "contacttype", "type"])
            notify = first_column(columns, ["chat_room_notify", "chatroomnotify"])
            select = [
                "rowid AS __rowid",
                "{} AS username".format(quote_identifier(username)),
                "{} AS nickname".format(quote_identifier(nickname)) if nickname else "NULL AS nickname",
                "{} AS remark".format(quote_identifier(remark)) if remark else "NULL AS remark",
                "{} AS alias".format(quote_identifier(alias)) if alias else "NULL AS alias",
                "{} AS added_time".format(quote_identifier(added)) if added else "NULL AS added_time",
                "{} AS contact_type".format(quote_identifier(con_type)) if con_type else "NULL AS contact_type",
                "{} AS chat_room_notify".format(quote_identifier(notify)) if notify else "NULL AS chat_room_notify",
                "hex({}) AS packed_hex".format(quote_identifier(packed)) if packed else "NULL AS packed_hex",
            ]
            where = ""
            if match:
                searchable = [column for column in (username, nickname, remark, alias) if column]
                conditions = ["instr(CAST({} AS TEXT), {}) > 0".format(quote_identifier(column), sql_text(match)) for column in searchable]
                where = " WHERE " + " OR ".join(conditions)
            sql = "SELECT {} FROM {}{} LIMIT {}".format(", ".join(select), quote_identifier(table), where, limit + 1)
            for row in database.query(sql):
                username_value = str(row.get("username") or "").strip()
                if not username_value:
                    continue
                nickname_value = str(row.get("nickname") or "").strip() or None
                remark_value = str(row.get("remark") or "").strip() or None
                alias_value = str(row.get("alias") or "").strip() or None
                profile = packed_profile(str(row.get("packed_hex") or ""))
                added_ts = normalize_timestamp(row.get("added_time"))
                contact_kind = "group" if "@chatroom" in username_value.lower() else "official" if username_value.lower().startswith("gh_") else "user"
                notify_value = row.get("chat_room_notify")
                results.append({
                    "displayName": remark_value or nickname_value or alias_value or username_value,
                    "username": username_value,
                    "nickname": nickname_value,
                    "remark": remark_value,
                    "alias": alias_value,
                    "contactType": contact_kind,
                    "signature": profile["signature"],
                    "momentsCoverUrl": profile["momentsCoverUrl"],
                    "addedTime": iso_local(added_ts),
                    "isMuted": None if notify_value is None else int(notify_value) == 0,
                    "source": {"databasePath": str(database.spec.path), "tableName": table, "rowid": int(row["__rowid"])},
                })
        except WdbError as exc:
            errors.append({"databasePath": str(database.spec.path), "stage": exc.stage, **exc.debug})
    if match:
        needle = match.casefold()
        results.sort(key=lambda item: (
            0 if item["username"].casefold() == needle else
            1 if str(item.get("alias") or "").casefold() == needle else
            2 if item["displayName"].casefold() == needle else 3,
            item["displayName"].casefold(), item["username"].casefold(),
        ))
    else:
        results.sort(key=lambda item: (item["displayName"].casefold(), item["username"].casefold()))
    return results[:limit], errors


def is_chat_table(name: str) -> bool:
    lower = name.lower()
    return (
        lower.startswith(("chat_", "msg_", "message_", "chatroom_")) or lower == "chat" or
        (lower.startswith("chat") and lower[4:].isdigit()) or ("chat" in lower and "room" in lower)
    )


def valid_chat_columns(columns: Sequence[str]) -> bool:
    lower = [column.lower() for column in columns]
    return bool(first_column(lower, CHAT_CONTENT_COLUMNS)) and (
        bool(first_column(lower, CHAT_TIME_COLUMNS)) or any("msg" in column for column in lower)
    )


def table_variants(identifier: str) -> List[str]:
    value = identifier.strip()
    match = re.fullmatch(r"(?:Chat|Msg)_([a-fA-F0-9]{32})(?:_dels)?", value)
    raw_hash = value if re.fullmatch(r"[a-fA-F0-9]{32}", value) else match.group(1) if match else hashlib.md5(value.encode("utf-8")).hexdigest()
    raw_hash = raw_hash.lower()
    return ["Chat_" + raw_hash, "Msg_" + raw_hash, "Chat_Chat_" + raw_hash + "_dels"]


GROUP_SENDER_PREFIX_RE = re.compile(r"^([A-Za-z0-9_@\.\-]{2,64}):[ \t]*\r?\n")
# Only map appmsg types verified against real WeChat payloads. Anything else
# keeps the generic "app" label so we never invent a wrong meaning; `appType`
# always carries the raw `<appmsg><type>` value for the caller to inspect.
APPMSG_LABELS = {
    57: "quote",
    62: "pat",
}


def split_group_sender_prefix(content: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Split WeChat's stored group prefix (`<sender username>:\\n`) from the body.

    Group messages persist the sender ahead of the payload, which hides the
    real `<msg>` XML from naive `startswith("<")` detection. Plain text bodies
    are unaffected because the prefix only matches a username-like token.
    """
    if not content:
        return None, content
    match = GROUP_SENDER_PREFIX_RE.match(content)
    if not match:
        return None, content
    body = content[match.end():]
    if not body.strip():
        return None, content
    return match.group(1), body


def appmsg_type(content: Optional[str]) -> Optional[int]:
    """Return `<appmsg><type>` for an appmsg payload, else None."""
    if not content or "<appmsg" not in content[:2000].casefold():
        return None
    raw = xml_value(content, "type")
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def appmsg_quote(content: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return the quoted (`refermsg`) block of an appmsg payload, else None."""
    if not content or "<refermsg" not in content.casefold():
        return None
    block = re.search(r"<refermsg(?:\s[^>]*)?>([\s\S]*?)</refermsg>", content, re.I)
    if not block:
        return None
    body = block.group(1)
    # Some clients write the quoted time in milliseconds.
    created_ts = normalize_timestamp(xml_value(body, "createtime"))
    return {
        "senderUsername": xml_value(body, "chatusr") or xml_value(body, "fromusr"),
        "senderName": xml_value(body, "displayname"),
        "content": xml_value(body, "content"),
        "rawType": xml_value(body, "type"),
        "createTime": iso_local(created_ts),
        "timestampUnix": created_ts,
        "serverId": xml_value(body, "svrid"),
    }


def message_type_label(raw: Any, content: Optional[str]) -> str:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = -1
    labels = {1: "text", 3: "image", 34: "voice", 43: "video", 47: "emoji", 49: "app", 10000: "system"}
    app_type = appmsg_type(content)
    if app_type is not None:
        return APPMSG_LABELS.get(app_type, "app")
    if value in labels:
        return labels[value]
    if content and content.lstrip().startswith("<"):
        return "xml"
    return "unknown"


def xml_value(content: str, tag: str) -> Optional[str]:
    match = re.search(r"<{}(?:\s[^>]*)?>([\s\S]*?)</{}>".format(re.escape(tag), re.escape(tag)), content, re.I)
    if not match:
        return None
    value = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", match.group(1))
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(re.sub(r"\s+", " ", value)).strip()
    return value or None


def message_text(content: Optional[str], label: str) -> Optional[str]:
    if not content:
        return None
    if not content.lstrip().startswith("<"):
        return content
    for tag in ("title", "content", "des", "displayname"):
        value = xml_value(content, tag)
        if value:
            return value
    return "[{}]".format(label)


def _chat_hit(
    row: Dict[str, Any],
    database: Database,
    table: str,
    conversation_id: Optional[str],
    query_text: Optional[str],
) -> Optional[Dict[str, Any]]:
    content, encoding = content_from_row(row)
    prefix, body = split_group_sender_prefix(content)
    label = message_type_label(row.get("local_type"), body)
    text = message_text(body, label)
    if query_text:
        haystack = "\n".join(part for part in (text, body, content) if part).casefold()
        if query_text.casefold() not in haystack:
            return None
    timestamp = normalize_timestamp(row.get("create_time"))
    direction = row.get("direction")
    try:
        is_own = int(direction) == 0 if direction is not None else None
    except (TypeError, ValueError):
        is_own = None
    return {
        "timestamp": iso_local(timestamp),
        "timestampUnix": timestamp,
        "conversationId": conversation_id,
        "senderUsername": row.get("sender_username") or prefix,
        "isOwn": is_own,
        "messageType": label,
        "rawType": row.get("local_type"),
        "appType": appmsg_type(body),
        "quoted": appmsg_quote(body),
        "text": text,
        "contentEncoding": encoding,
        "rawContent": content,
        "source": {
            "databasePath": str(database.spec.path),
            "tableName": table,
            "rowid": int(row["__rowid"]),
        },
    }


def message_rows(
    ctx: Context,
    contact: Optional[str],
    query_text: Optional[str],
    start_ts: Optional[int],
    end_ts: Optional[int],
    limit: int,
    include_deleted: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    contacts, contact_errors = contact_rows(ctx, contact, 1000) if contact else ([], [])
    errors.extend(contact_errors)
    identifiers = [item["username"] for item in contacts]
    # Contacts match by substring, so the value can hit other people while its own
    # account (a deleted friend, an old id) is missing; the value always counts too.
    if contact and contact not in identifiers:
        identifiers.append(contact)
    allowed_tables = {variant.lower() for identity in identifiers for variant in table_variants(identity)} if contact else None
    table_to_identity = {
        variant.lower(): item["username"] for item in contacts for variant in table_variants(item["username"])
    }
    hits: List[Dict[str, Any]] = []
    scan: Dict[str, Any] = {"scannedTables": 0, "truncated": False}
    # SQLite's lower() folds ASCII only. A keyword with other cased letters (É, Ж)
    # would lose case variants in SQL, so TEXT rows then go to the Python match.
    prefilter_text_rows = bool(query_text) and not any(
        not char.isascii() and (char.lower() != char or char.upper() != char or char.casefold() != char)
        for char in query_text or ""
    )
    for database in ctx.databases:
        try:
            tables = ctx.tables(database)
        except WdbError as exc:
            errors.append({"databasePath": str(database.spec.path), "stage": exc.stage, **exc.debug})
            scan["truncated"] = True
            continue
        name2id = next((table for table in tables if table.lower() == "name2id"), None)
        name2id_columns = ctx.columns(database, name2id) if name2id else []
        name2id_username = first_column(name2id_columns, ["user_name", "username", "name"])
        # (table, candidate SQL, body SQL); a plan's index tags its candidate rows.
        query_plans: List[Tuple[str, str, str]] = []
        for table in tables:
            if not is_chat_table(table) or (not include_deleted and table.lower().endswith("_dels")):
                continue
            if allowed_tables is not None and table.lower() not in allowed_tables:
                continue
            columns = ctx.columns(database, table)
            if not valid_chat_columns(columns):
                continue
            content_col = first_column(columns, CHAT_CONTENT_COLUMNS)
            assert content_col is not None
            time_col = first_column(columns, CHAT_TIME_COLUMNS)
            type_col = first_column(columns, CHAT_TYPE_COLUMNS)
            direction_col = first_column(columns, CHAT_DIRECTION_COLUMNS)
            sender_id_col = first_column(columns, ["real_sender_id"])
            join = ""
            sender_expr = "NULL AS sender_username"
            if name2id and name2id_username and sender_id_col:
                join = " LEFT JOIN {} n ON n.rowid = m.{}".format(
                    quote_identifier(name2id), quote_identifier(sender_id_col)
                )
                sender_expr = "n.{} AS sender_username".format(quote_identifier(name2id_username))
            where_parts = []
            if time_col and start_ts is not None:
                time_expr = "m." + quote_identifier(time_col)
                where_parts.append(
                    "({t} >= {v} OR {t} >= {ms})".format(t=time_expr, v=start_ts, ms=start_ts * 1000)
                )
            if time_col and end_ts is not None:
                time_expr = "m." + quote_identifier(time_col)
                where_parts.append(
                    "({t} < {v} OR ({t} >= 1000000000000 AND {t} < {ms}))".format(
                        t=time_expr, v=end_ts, ms=end_ts * 1000
                    )
                )
            if prefilter_text_rows:
                content_expr = "m." + quote_identifier(content_col)
                where_parts.append(
                    "(typeof({c})='blob' OR instr(lower(CAST({c} AS TEXT)), lower({q})) > 0)".format(
                        c=content_expr, q=sql_text(query_text)
                    )
                )
            where = " WHERE " + " AND ".join(where_parts) if where_parts else ""
            content_q = quote_identifier(content_col)
            index = len(query_plans)
            time_select = "m.{} AS create_time".format(quote_identifier(time_col)) if time_col else "NULL AS create_time"
            select = [
                "m.rowid AS __rowid",
                "{} AS __table".format(index),
                "typeof(m.{c}) AS __content_type, CASE WHEN typeof(m.{c})='blob' "
                "THEN hex(m.{c}) ELSE CAST(m.{c} AS TEXT) END AS __content".format(c=content_q),
                time_select,
                "m.{} AS local_type".format(quote_identifier(type_col)) if type_col else "NULL AS local_type",
                "m.{} AS direction".format(quote_identifier(direction_col)) if direction_col else "NULL AS direction",
                sender_expr,
            ]
            query_plans.append((
                table,
                "SELECT m.rowid AS __rowid, {} AS __table, {} FROM {} m{}".format(
                    index, time_select, quote_identifier(table), where
                ),
                "SELECT {} FROM {} m{}".format(", ".join(select), quote_identifier(table), join),
            ))

        # 4.x keeps most bodies as compressed BLOBs that SQL cannot search, so a
        # keyword query must not LIMIT in SQL: list every candidate newest first,
        # then decode bodies chunk by chunk until limit + 1 hits are found.
        for batch_start in range(0, len(query_plans), 400):
            batch = query_plans[batch_start: batch_start + 400]
            sql = "SELECT * FROM ({}) ORDER BY COALESCE(create_time, 0) DESC, __table DESC, __rowid DESC".format(
                " UNION ALL ".join(plan for _, plan, _ in batch)
            )
            if not query_text:
                sql += " LIMIT {}".format(limit + 1)
            try:
                candidates = database.query(sql)
            except WdbError as exc:
                errors.append({
                    "databasePath": str(database.spec.path),
                    "tableNames": [table for table, _, _ in batch],
                    "stage": exc.stage,
                    **exc.debug,
                })
                scan["truncated"] = True
                continue
            scan["scannedTables"] += len(batch)
            found: List[Dict[str, Any]] = []
            for offset in range(0, len(candidates), CHAT_BODY_CHUNK_ROWS):
                chunk = candidates[offset: offset + CHAT_BODY_CHUNK_ROWS]
                rowids: Dict[int, List[int]] = {}
                for candidate in chunk:
                    rowids.setdefault(int(candidate["__table"]), []).append(int(candidate["__rowid"]))
                try:
                    rows = database.query(" UNION ALL ".join(
                        "{} WHERE m.rowid IN ({})".format(query_plans[index][2], ",".join(str(rowid) for rowid in ids))
                        for index, ids in rowids.items()
                    ))
                except WdbError as exc:
                    errors.append({
                        "databasePath": str(database.spec.path),
                        "tableNames": [query_plans[index][0] for index in rowids],
                        "stage": exc.stage,
                        **exc.debug,
                    })
                    scan["truncated"] = True
                    break
                predecode_zstd_rows(rows)
                bodies = {(int(row["__table"]), int(row["__rowid"])): row for row in rows}
                for candidate in chunk:
                    index = int(candidate["__table"])
                    table = query_plans[index][0]
                    hit = _chat_hit(
                        bodies[(index, int(candidate["__rowid"]))], database, table,
                        table_to_identity.get(table.lower()), query_text,
                    )
                    if hit:
                        found.append(hit)
                        if len(found) > limit:
                            break
                if len(found) > limit:
                    scan["truncated"] = True
                    break
            hits.extend(found)
    hits.sort(key=lambda item: (
        item.get("timestampUnix") or 0,
        item["source"]["databasePath"], item["source"]["tableName"], item["source"]["rowid"],
    ), reverse=True)
    scan["truncated"] = scan["truncated"] or len(hits) > limit
    return hits[:limit][::-1], errors, scan


def moment_urls(content: str) -> List[str]:
    tags = ["cdnthumburl", "thumburl", "thumb", "cdnmidimgurl", "cdnbigimgurl", "cover", "coverurl", "url"]
    urls: List[str] = []
    for tag in tags:
        for match in re.finditer(r"<{}(?:\s[^>]*)?>([\s\S]*?)</{}>".format(tag, tag), content, re.I):
            value = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", match.group(1)).strip()
            value = html.unescape(value)
            if re.match(r"^https?://", value, re.I) and value not in urls:
                urls.append(value)
    return urls[:9]


def parse_moment(content: Optional[str]) -> Dict[str, Any]:
    content = content or ""
    timestamp = normalize_timestamp(xml_value(content, "createTime"))
    return {
        "authorId": xml_value(content, "username"),
        "authorName": xml_value(content, "nickname"),
        "timestampUnix": timestamp,
        "timestamp": iso_local(timestamp),
        "text": xml_value(content, "contentDesc"),
        "mediaUrls": moment_urls(content),
        "article": {
            "title": xml_value(content, "title"),
            "description": xml_value(content, "description") or xml_value(content, "des"),
            "url": xml_value(content, "url"),
            "coverUrl": xml_value(content, "cover") or xml_value(content, "thumburl") or xml_value(content, "cdnthumburl"),
        },
    }


def _moment_interactions(ctx: Context, database: Database, tables: Sequence[str], feed_ids: Sequence[str]) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    errors: List[Dict[str, Any]] = []
    table = next((item for item in tables if item.lower() == "snsmessage_tmp3"), None)
    if not table:
        table = next((item for item in tables if "snsmessage" in item.lower()), None)
    if not table or not feed_ids:
        return grouped, errors
    columns = ctx.columns(database, table)
    feed_col = first_column(columns, ["feed_id", "feedid", "object_id", "objectid"])
    time_col = first_column(columns, ["create_time", "createtime", "timestamp", "time"])
    from_col = first_column(columns, ["from_username", "fromusername", "username", "from_user"])
    nick_col = first_column(columns, ["from_nickname", "fromnickname", "nickname"])
    content_col = first_column(columns, ["content", "comment", "text"])
    if not feed_col or not from_col:
        return grouped, errors
    for offset in range(0, len(feed_ids), 400):
        chunk = feed_ids[offset: offset + 400]
        select = [
            "rowid AS __rowid",
            "{} AS feed_id".format(quote_identifier(feed_col)),
            "{} AS create_time".format(quote_identifier(time_col)) if time_col else "NULL AS create_time",
            "{} AS from_username".format(quote_identifier(from_col)),
            "{} AS from_nickname".format(quote_identifier(nick_col)) if nick_col else "NULL AS from_nickname",
            "{} AS content".format(quote_identifier(content_col)) if content_col else "NULL AS content",
        ]
        sql = "SELECT {} FROM {} WHERE {} IN ({}) ORDER BY rowid".format(
            ", ".join(select), quote_identifier(table), quote_identifier(feed_col),
            ",".join(sql_text(str(feed_id)) for feed_id in chunk),
        )
        try:
            for row in database.query(sql):
                feed_id = str(row.get("feed_id") or "")
                raw_content = str(row.get("content") or "").strip()
                actor = str(row.get("from_username") or "")
                item = {
                    "type": "comment" if raw_content else "like",
                    "actorId": actor,
                    "actorName": str(row.get("from_nickname") or "").strip() or actor,
                    "content": raw_content or None,
                    "timestampUnix": normalize_timestamp(row.get("create_time")),
                    "timestamp": iso_local(normalize_timestamp(row.get("create_time"))),
                    "source": {"databasePath": str(database.spec.path), "tableName": table, "rowid": int(row["__rowid"])},
                }
                grouped.setdefault(feed_id, []).append(item)
        except WdbError as exc:
            errors.append({"databasePath": str(database.spec.path), "tableName": table, "stage": exc.stage, **exc.debug})
    return grouped, errors


def _moment_posts(
    database: Database,
    table: str,
    body_sql: str,
    rowids: Sequence[int],
    contact_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    posts: List[Dict[str, Any]] = []
    for offset in range(0, len(rowids), 400):
        chunk = rowids[offset: offset + 400]
        sql = "{} WHERE rowid IN ({})".format(body_sql, ",".join(str(int(rowid)) for rowid in chunk))
        for row in database.query(sql):
            content, encoding = content_from_row(row)
            parsed = parse_moment(content)
            author_id = str(row.get("user_name") or parsed.get("authorId") or "").strip()
            timestamp = normalize_timestamp(row.get("create_time")) or parsed.get("timestampUnix")
            contact_item = contact_by_id.get(author_id) or {}
            posts.append({
                "feedId": str(row.get("feed_id") or row["__rowid"]),
                "timestamp": iso_local(timestamp),
                "timestampUnix": timestamp,
                "authorId": author_id or None,
                "authorName": contact_item.get("displayName") or parsed.get("authorName") or author_id or None,
                "authorMomentsCoverUrl": contact_item.get("momentsCoverUrl"),
                "text": parsed.get("text"),
                "mediaUrls": parsed.get("mediaUrls"),
                "article": parsed.get("article"),
                "contentEncoding": encoding,
                "rawContent": content,
                "source": {"databasePath": str(database.spec.path), "tableName": table, "rowid": int(row["__rowid"])},
            })
    return posts


def moment_rows(
    ctx: Context,
    contact: Optional[str],
    feed_ids: Optional[Sequence[str]],
    start_ts: Optional[int],
    end_ts: Optional[int],
    limit: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    contacts, contact_errors = contact_rows(ctx, contact, 1000) if contact else contact_rows(ctx, None, 100000)
    errors = list(contact_errors)
    contact_by_id = {item["username"]: item for item in contacts}
    # As in chats, the value itself always counts as an author id, so a deleted
    # friend or an old account matches its own posts even when the value is also
    # part of other contacts.
    allowed = (set(contact_by_id) | {contact}) if contact else None
    scan: Dict[str, Any] = {"scannedTables": 0, "scannedRows": 0, "matchedCount": 0, "truncated": False}

    def wanted(author_id: Optional[str], timestamp: Optional[int]) -> bool:
        if allowed is not None and author_id not in allowed:
            return False
        if start_ts is not None and (timestamp is None or timestamp < start_ts):
            return False
        return end_ts is None or (timestamp is not None and timestamp < end_ts)

    # WeChat 4.x SnsTimeLine keeps createTime only inside the XML and its rowid
    # order is not time order, so a SQL LIMIT before filtering silently drops
    # posts. Scan every row's author and <createTime> first, cut by time, then
    # read only the bodies that survive the cut.
    bodies: Dict[int, Tuple[str, str]] = {}
    matches: List[Tuple[Optional[int], int, int, Optional[Dict[str, Any]]]] = []
    # A keys file may give sns.db any label, so skip only the message and head
    # image databases; the rest are already open for author names.
    timeline_databases = ctx.databases_except(["Message", "HeadImage"])
    for index, database in enumerate(ctx.databases):
        if database not in timeline_databases:
            continue
        try:
            tables = ctx.tables(database)
            table = next((item for item in tables if item.lower() == "snstimeline"), None)
            if not table:
                continue
            columns = ctx.columns(database, table)
            tid_col = first_column(columns, ["tid", "feed_id", "feedid", "id"])
            user_col = first_column(columns, ["user_name", "username", "author"])
            content_col = first_column(columns, ["content", "xml"])
            time_col = first_column(columns, ["create_time", "createtime", "timestamp", "time"])
            if not tid_col or not content_col:
                continue
            content_q = quote_identifier(content_col)
            user_expr = "{} AS user_name".format(quote_identifier(user_col)) if user_col else "NULL AS user_name"
            time_expr = "{} AS create_time".format(quote_identifier(time_col)) if time_col else "NULL AS create_time"
            body_sql = (
                "SELECT rowid AS __rowid, {} AS feed_id, {}, {}, typeof({c}) AS __content_type, "
                "CASE WHEN typeof({c})='blob' THEN hex({c}) ELSE CAST({c} AS TEXT) END AS __content FROM {}"
            ).format(quote_identifier(tid_col), user_expr, time_expr, quote_identifier(table), c=content_q)
            bodies[index] = (table, body_sql)
            where = ""
            if feed_ids:
                where = " WHERE {} IN ({})".format(
                    quote_identifier(tid_col), ",".join(sql_text(str(item)) for item in feed_ids)
                )
            rows = database.query(
                "SELECT rowid AS __rowid, {}, {}, CASE WHEN typeof({c})='text' AND instr({c}, '<createTime>') > 0 "
                "THEN substr({c}, instr({c}, '<createTime>'), {n}) END AS __time_snippet FROM {}{}".format(
                    user_expr, time_expr, quote_identifier(table), where, c=content_q, n=MOMENT_TIME_SNIPPET_CHARS,
                )
            )
            scan["scannedTables"] += 1
            scan["scannedRows"] += len(rows)
            unresolved: List[int] = []
            for row in rows:
                author_id = str(row.get("user_name") or "").strip()
                timestamp = normalize_timestamp(row.get("create_time")) or normalize_timestamp(
                    xml_value(str(row.get("__time_snippet") or ""), "createTime")
                )
                if timestamp is None or (allowed is not None and not author_id):
                    unresolved.append(int(row["__rowid"]))
                elif wanted(author_id, timestamp):
                    matches.append((timestamp, index, int(row["__rowid"]), None))
            for post in _moment_posts(database, table, body_sql, unresolved, contact_by_id):
                if wanted(post["authorId"], post["timestampUnix"]):
                    matches.append((post["timestampUnix"], index, post["source"]["rowid"], post))
        except WdbError as exc:
            errors.append({"databasePath": str(database.spec.path), "stage": exc.stage, **exc.debug})
            scan["truncated"] = True
    matches.sort(key=lambda item: (item[0] or 0, str(ctx.databases[item[1]].spec.path), item[2]), reverse=True)
    scan["matchedCount"] = len(matches)
    scan["truncated"] = scan["truncated"] or len(matches) > limit
    kept = matches[:limit]

    loaded: Dict[Tuple[int, int], Dict[str, Any]] = {}
    pending_rowids: Dict[int, List[int]] = {}
    for _, index, rowid, post in kept:
        if post is None:
            pending_rowids.setdefault(index, []).append(rowid)
    for index, rowids in pending_rowids.items():
        database = ctx.databases[index]
        table, body_sql = bodies[index]
        try:
            for post in _moment_posts(database, table, body_sql, rowids, contact_by_id):
                loaded[(index, post["source"]["rowid"])] = post
        except WdbError as exc:
            errors.append({"databasePath": str(database.spec.path), "tableName": table, "stage": exc.stage, **exc.debug})
            scan["truncated"] = True
    selected: List[Tuple[int, Dict[str, Any]]] = []
    for _, index, rowid, post in kept:
        post = post or loaded.get((index, rowid))
        if post is not None and wanted(post["authorId"], post["timestampUnix"]):
            selected.append((index, post))
    for index in sorted({index for index, _ in selected}):
        database = ctx.databases[index]
        own = [post for owner, post in selected if owner == index]
        interactions, interaction_errors = _moment_interactions(
            ctx, database, ctx.tables(database), [post["feedId"] for post in own]
        )
        errors.extend(interaction_errors)
        for post in own:
            observed = interactions.get(post["feedId"], [])
            post["observedLikeCount"] = sum(entry["type"] == "like" for entry in observed)
            post["observedCommentCount"] = sum(entry["type"] == "comment" for entry in observed)
            post["observedInteractions"] = observed
    return [post for _, post in selected], errors, scan


def isaac64_blocks(seed_words: Sequence[int]) -> Iterator[List[int]]:
    """Yield 256-word blocks of rand_isaac `Isaac64Rng::from_seed`, in `next_u64` order."""
    mem = [0] * 256
    for index, word in enumerate(seed_words):
        mem[index] = word & U64_MASK
    a, b, c, d, e, f, g, h = ISAAC64_INIT
    # from_seed runs two init passes, seed_from_u64 only one. A self-made round
    # trip passes with either; only two passes decode real x-Enc CDN bodies.
    for _ in range(2):
        for i in range(0, 256, 8):
            a = (a + mem[i]) & U64_MASK
            b = (b + mem[i + 1]) & U64_MASK
            c = (c + mem[i + 2]) & U64_MASK
            d = (d + mem[i + 3]) & U64_MASK
            e = (e + mem[i + 4]) & U64_MASK
            f = (f + mem[i + 5]) & U64_MASK
            g = (g + mem[i + 6]) & U64_MASK
            h = (h + mem[i + 7]) & U64_MASK
            a = (a - e) & U64_MASK; f ^= h >> 9; h = (h + a) & U64_MASK
            b = (b - f) & U64_MASK; g ^= (a << 9) & U64_MASK; a = (a + b) & U64_MASK
            c = (c - g) & U64_MASK; h ^= b >> 23; b = (b + c) & U64_MASK
            d = (d - h) & U64_MASK; a ^= (c << 15) & U64_MASK; c = (c + d) & U64_MASK
            e = (e - a) & U64_MASK; b ^= d >> 14; d = (d + e) & U64_MASK
            f = (f - b) & U64_MASK; c ^= (e << 20) & U64_MASK; e = (e + f) & U64_MASK
            g = (g - c) & U64_MASK; d ^= f >> 17; f = (f + g) & U64_MASK
            h = (h - d) & U64_MASK; e ^= (g << 14) & U64_MASK; g = (g + h) & U64_MASK
            mem[i:i + 8] = [a, b, c, d, e, f, g, h]
    ra = rb = rc = 0
    while True:
        rc = (rc + 1) & U64_MASK
        rb = (rb + rc) & U64_MASK
        block = [0] * 256
        for half, other in ((0, 128), (128, 0)):
            for i in range(128):
                step = i & 3
                if step == 0:
                    mix = ~(ra ^ ((ra << 21) & U64_MASK)) & U64_MASK
                elif step == 1:
                    mix = ra ^ (ra >> 5)
                elif step == 2:
                    mix = ra ^ ((ra << 12) & U64_MASK)
                else:
                    mix = ra ^ (ra >> 33)
                x = mem[half + i]
                ra = (mix + mem[other + i]) & U64_MASK
                y = (ra + rb + mem[(x >> 3) & 255]) & U64_MASK
                mem[half + i] = y
                rb = (x + mem[(y >> 11) & 255]) & U64_MASK
                block[255 - half - i] = rb
        yield block


def isaac64_keystream(seed: int, length: int, big_endian: bool = True) -> bytes:
    blocks = isaac64_blocks([seed])
    word_format = (">" if big_endian else "<") + "256Q"
    chunks = [struct.pack(word_format, *next(blocks)) for _ in range((length + 2047) // 2048)]
    return b"".join(chunks)[:length]


def xor_bytes(data: bytes, stream: bytes) -> bytes:
    return (int.from_bytes(data, "big") ^ int.from_bytes(stream[:len(data)], "big")).to_bytes(len(data), "big")


def sns_image_kind(data: bytes) -> Optional[str]:
    for signature, kind in SNS_IMAGE_SIGNATURES:
        if data.startswith(signature):
            return kind
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def decrypt_sns_media(data: bytes, key: int) -> Optional[Tuple[bytes, str]]:
    """Undo CDN `x-Enc: 1` the way wdb-pro `decode_sns_remote_encrypted_image` does."""
    swapped = int.from_bytes(key.to_bytes(8, "little"), "big")
    for seed in dict.fromkeys((key, swapped)):
        for big_endian in (True, False):
            stream = isaac64_keystream(seed, len(data), big_endian)
            for candidate in (stream, stream[::-1]):
                plain = xor_bytes(data, candidate)
                kind = sns_image_kind(plain)
                if kind:
                    return plain, kind
    return None


def parse_sns_media_key(value: Optional[str]) -> Optional[int]:
    text = (value or "").strip()
    if re.fullmatch(r"-?\d+", text):
        return int(text) & U64_MASK
    if re.fullmatch(r"0[xX][0-9a-fA-F]{1,16}", text):
        return int(text, 16)
    return None


def xml_attributes(text: Optional[str]) -> Dict[str, str]:
    return {
        name.lower(): html.unescape(value)
        for name, value in re.findall(r'([\w:.-]+)\s*=\s*"([^"]*)"', text or "")
    }


def sns_media_entries(content: Optional[str]) -> List[Dict[str, Any]]:
    region = re.search(r"<ContentObject(?:\s[^>]*)?>([\s\S]*?)</ContentObject>", content or "", re.I)
    body = region.group(1) if region else (content or "")
    entries: List[Dict[str, Any]] = []
    for media in re.finditer(r"<media(?:\s([^>]*))?>([\s\S]*?)</media>", body, re.I):
        inner = media.group(2)
        raw_type = xml_value(inner, "type")
        if raw_type is None:
            continue  # nested 视频号 cards use <mediaType>; they are not this post's media
        url_tag = re.search(r"<url(?:\s([^>]*))?>([\s\S]*?)</url>", inner, re.I)
        attributes = {**xml_attributes(media.group(1)), **xml_attributes(url_tag.group(1) if url_tag else None)}
        url = None
        if url_tag:
            url = html.unescape(re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", url_tag.group(2))).strip() or None
        size_tag = re.search(r"<size\b([^>]*)>", inner, re.I)
        size = xml_attributes(size_tag.group(1) if size_tag else None)
        entries.append({
            "index": len(entries) + 1,
            "mediaId": xml_value(inner, "id"),
            "type": SNS_MEDIA_TYPES.get(raw_type, "other"),
            "url": url,
            "token": attributes.get("token") or None,
            "key": attributes.get("key") or None,
            "width": int(size["width"]) if size.get("width", "").isdigit() else None,
            "height": int(size["height"]) if size.get("height", "").isdigit() else None,
        })
    return entries


def sns_media_request_url(url: str, token: Optional[str]) -> str:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme.lower() == "http":
        parts = parts._replace(scheme="https")
    present = {name.lower() for name, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True) if value}
    extra = []
    if token:
        if "token" not in present:
            extra.append(("token", token))
        if "idx" not in present:
            extra.append(("idx", "1"))
    query = "&".join(item for item in (parts.query, urllib.parse.urlencode(extra)) if item)
    return urllib.parse.urlunsplit(parts._replace(query=query))


def is_cdn_placeholder(data: bytes) -> bool:
    # An expired token is answered with HTTP 200 and a fixed 120x120 PNG, not an error.
    return (
        4900 <= len(data) <= 5200 and data.startswith(b"\x89PNG\r\n\x1a\n")
        and struct.unpack(">II", data[16:24]) == (120, 120)
    )


def fetch_sns_media(entry: Dict[str, Any]) -> Tuple[bytes, str, bool]:
    if not entry.get("url"):
        raise WdbError("朋友圈媒体缺少原图地址", "media_url")
    url = sns_media_request_url(entry["url"], entry.get("token"))
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not any(host == suffix or host.endswith("." + suffix) for suffix in SNS_MEDIA_HOSTS):
        raise WdbError("原图地址不是微信 CDN", "media_url", host=host or None)
    request = urllib.request.Request(url, headers={"User-Agent": SNS_MEDIA_USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            headers = response.headers
            body = response.read(SNS_MEDIA_MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise WdbError("CDN 返回 HTTP 错误", "http", host=host, status=exc.code) from exc
    except OSError as exc:
        # Socket/TLS reasons never carry the request URL, so the token stays out.
        reason = getattr(exc, "reason", exc)
        raise WdbError("CDN 请求失败", "http", host=host, error="{}: {}".format(type(exc).__name__, reason)) from exc
    except http.client.HTTPException as exc:
        raise WdbError("CDN 响应异常", "http", host=host, error=type(exc).__name__) from exc
    x_errno = (headers.get("x-errno") or "").strip()
    x_info = (headers.get("x-info") or "").strip()
    if x_errno in SNS_PLACEHOLDER_ERRNOS or x_info.lower() == "illref" or is_cdn_placeholder(body):
        raise WdbError("CDN 返回防盗链占位图，token 可能已失效", "placeholder", host=host, xErrno=x_errno or None, xInfo=x_info or None)
    if len(body) > SNS_MEDIA_MAX_BYTES:
        raise WdbError("原图超过 20 MiB", "too_large", host=host)
    kind = sns_image_kind(body)
    if kind:
        return body, kind, False
    x_enc = (headers.get("x-enc") or "").strip()
    if x_enc != "1":
        raise WdbError("CDN 返回的内容不是图片", "payload", host=host, xEnc=x_enc or None, bytes=len(body))
    key = parse_sns_media_key(entry.get("key"))
    if key is None:
        raise WdbError("x-Enc 原图缺少 media key", "missing_key", host=host)
    decoded = decrypt_sns_media(body, key)
    if decoded is None:
        raise WdbError("x-Enc 解密后不是图片", "decrypt", host=host, bytes=len(body))
    return decoded[0], decoded[1], True


def media_output_dir(ctx: Context, output: str) -> Path:
    target = Path(output).expanduser().resolve()
    roots = [Path.home() / "Library" / "Containers" / "com.tencent.xinWeChat"]
    for database in ctx.databases:
        parts = database.spec.path.parts
        for marker in ("xwechat_files", "com.tencent.xinWeChat"):
            if marker in parts:
                roots.append(Path(*parts[: parts.index(marker) + 1]))
    for root in roots:
        root = root.resolve()
        if target == root or root in target.parents:
            raise WdbError("输出目录不能位于微信数据目录内", "arguments", output=str(target))
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WdbError("输出目录创建失败", "arguments", output=str(target), errno=exc.errno) from exc
    return target


def moment_media_rows(posts: List[Dict[str, Any]], target: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    items: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    requested = False
    for post in posts:
        stamp = dt.datetime.fromtimestamp(post["timestampUnix"]).strftime("%Y%m%d-%H%M%S") if post.get("timestampUnix") else "unknown"
        prefix = "{}_{}".format(stamp, re.sub(r"[^0-9A-Za-z._-]+", "_", post["feedId"]))
        for entry in sns_media_entries(post.get("rawContent")):
            item: Dict[str, Any] = {
                "feedId": post["feedId"],
                "mediaIndex": entry["index"],
                "mediaId": entry["mediaId"],
                "mediaType": entry["type"],
                "timestamp": post["timestamp"],
                "timestampUnix": post["timestampUnix"],
                "authorId": post["authorId"],
                "width": entry["width"],
                "height": entry["height"],
                "status": "skipped",
                "path": None,
                "kind": None,
                "bytes": None,
                "encrypted": None,
                "error": None,
                "source": post["source"],
            }
            stem = "{}_{:02d}".format(prefix, entry["index"])
            candidates = [target / "{}.{}".format(stem, kind) for kind in ("jpg", "png", "gif", "webp")]
            existing = next((path for path in candidates if path.is_file()), None)
            if entry["type"] == "image" and existing is not None:
                item.update(status="exists", path=str(existing), kind=existing.suffix[1:], bytes=existing.stat().st_size)
            elif entry["type"] == "image":
                if requested:
                    time.sleep(SNS_MEDIA_REQUEST_INTERVAL)
                requested = True
                try:
                    data, kind, encrypted = fetch_sns_media(entry)
                    destination = target / "{}.{}".format(stem, kind)
                    partial = destination.with_name(destination.name + ".part")
                    try:
                        partial.write_bytes(data)
                        partial.replace(destination)
                    except OSError as exc:
                        raise WdbError("原图写入失败", "write", errno=exc.errno) from exc
                    item.update(status="downloaded", path=str(destination), kind=kind, bytes=len(data), encrypted=encrypted)
                except WdbError as exc:
                    item.update(status="failed", error={"stage": exc.stage, "message": str(exc), **exc.debug})
                    errors.append({"feedId": post["feedId"], "mediaIndex": entry["index"], **item["error"]})
            items.append(item)
            detail = Path(item["path"]).name if item["path"] else (item["error"] or {}).get("stage") or item["mediaType"]
            eprint("moments-media\t{}\t{}#{:02d}\t{}".format(item["status"], post["feedId"], entry["index"], detail))
    return items, errors


def record_row(ctx: Context, database_path: str, table: str, rowid: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    target = Path(database_path).expanduser().resolve()
    database = next((db for db in ctx.databases if db.spec.path == target), None)
    if database is None:
        raise WdbError("指定数据库不在当前数据源中", "record", databasePath=str(target))
    tables = ctx.tables(database)
    actual_table = next((item for item in tables if item.lower() == table.lower()), None)
    if not actual_table:
        raise WdbError("指定表不存在", "record", databasePath=str(target), tableName=table)
    columns = ctx.columns(database, actual_table)
    select = ["rowid AS __rowid"]
    for index, column in enumerate(columns):
        quoted = quote_identifier(column)
        alias_type = quote_identifier("__kind_{}".format(index))
        alias_value = quote_identifier("__value_{}".format(index))
        select.append("typeof({0}) AS {1}".format(quoted, alias_type))
        select.append("CASE WHEN typeof({0})='blob' THEN hex({0}) ELSE CAST({0} AS TEXT) END AS {1}".format(quoted, alias_value))
    sql = "SELECT {} FROM {} WHERE rowid = {} LIMIT 1".format(", ".join(select), quote_identifier(actual_table), int(rowid))
    rows = database.query(sql)
    if not rows:
        raise WdbError("指定 rowid 不存在", "record", databasePath=str(target), tableName=actual_table, rowid=rowid)
    raw = rows[0]
    values: Dict[str, Any] = {}
    for index, column in enumerate(columns):
        kind = raw.get("__kind_{}".format(index))
        value = raw.get("__value_{}".format(index))
        if kind == "null":
            values[column] = None
        elif kind in {"integer", "real"}:
            values[column] = float(value) if kind == "real" else int(value)
        elif kind == "blob":
            decoded, encoding = decode_blob(str(value or ""))
            values[column] = {"encoding": encoding, "decoded": decoded, "hex": None if decoded else value}
        else:
            values[column] = value
    return {
        "record": values,
        "source": {"databasePath": str(target), "tableName": actual_table, "rowid": rowid},
    }, []


def select_database(ctx: Context, selector: str) -> Database:
    target = Path(selector).expanduser()
    exact_path = target.resolve() if target.is_absolute() or target.exists() else None
    matches = [
        database for database in ctx.databases
        if (exact_path is not None and database.spec.path == exact_path)
        or database.spec.path.name == selector
        or str(database.spec.path) == selector
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise WdbError(
            "没有找到指定数据库",
            "select_database",
            database=selector,
            candidates=[str(database.spec.path) for database in ctx.databases],
        )
    raise WdbError(
        "数据库名称命中多个文件，请改用完整路径",
        "select_database",
        database=selector,
        candidates=[str(database.spec.path) for database in matches],
    )


def schema_data(
    ctx: Context,
    database_selector: Optional[str],
    table_match: Optional[str],
    include_counts: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    selected = [select_database(ctx, database_selector)] if database_selector else ctx.databases
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for database in selected:
        try:
            table_items = []
            for table in ctx.tables(database):
                if table_match and table_match.casefold() not in table.casefold():
                    continue
                table_item: Dict[str, Any] = {
                    "name": table,
                    "columns": ctx.column_details(database, table),
                }
                if include_counts:
                    try:
                        count_rows = database.query("SELECT count(*) AS count FROM {}".format(quote_identifier(table)))
                        table_item["rowCount"] = int(count_rows[0]["count"]) if count_rows else 0
                    except WdbError as exc:
                        table_item["rowCountError"] = exc.debug.get("error", str(exc))
                table_items.append(table_item)
            results.append({
                "databasePath": str(database.spec.path),
                "databaseType": database.spec.db_type,
                "backend": database.backend_name,
                "tables": table_items,
            })
        except WdbError as exc:
            errors.append({"databasePath": str(database.spec.path), "stage": exc.stage, **exc.debug})
    return results, errors


def _single_read_query(query: str) -> str:
    value = query.strip()
    if not re.match(r"(?is)^(select|with)\b", value):
        raise WdbError("sql 仅接受 SELECT 或 WITH 只读查询", "arguments")
    quote: Optional[str] = None
    semicolons: List[int] = []
    index = 0
    while index < len(value):
        char = value[index]
        if quote:
            if char == quote:
                if index + 1 < len(value) and value[index + 1] == quote:
                    index += 2
                    continue
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == ";":
            semicolons.append(index)
        index += 1
    if quote:
        raise WdbError("SQL 引号未闭合", "arguments")
    if semicolons and (len(semicolons) > 1 or value[semicolons[0] + 1:].strip()):
        raise WdbError("sql 每次只接受一条查询", "arguments")
    return value[:-1].rstrip() if value.endswith(";") else value


def normalize_sql_value(value: Any) -> Any:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        return value
    raw = bytes(value)
    decoded, encoding = decode_blob(raw.hex())
    return {"encoding": encoding, "decoded": decoded, "hex": None if decoded else raw.hex()}


def sql_rows(
    ctx: Context,
    database_selector: str,
    query: str,
    limit: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Database, bool]:
    database = select_database(ctx, database_selector)
    readonly_query = _single_read_query(query)
    wrapped = "SELECT * FROM ({}) AS __lov_wdb_query LIMIT {}".format(readonly_query, limit + 1)
    rows = database.query(wrapped)
    normalized = [
        {key: normalize_sql_value(value) for key, value in row.items()}
        for row in rows[:limit]
    ]
    return normalized, [], database, len(rows) > limit


def doctor_data(ctx: Context) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    databases = []
    errors = []
    for database in ctx.databases:
        item = database.spec.public()
        try:
            tables = ctx.tables(database)
            has_contacts = find_contact_table(ctx, database) is not None
            has_chats = any(
                is_chat_table(table) and valid_chat_columns(ctx.columns(database, table))
                for table in tables
            )
            item.update({
                "open": True,
                "backend": database.backend_name,
                "tableCount": len(tables),
                "capabilities": {
                    "contacts": has_contacts,
                    "chats": has_chats,
                    "moments": any(table.lower() == "snstimeline" for table in tables),
                    "momentInteractions": any("snsmessage" in table.lower() for table in tables),
                },
            })
        except WdbError as exc:
            item.update({"open": False, "backend": database.backend_name})
            errors.append({"databasePath": str(database.spec.path), "stage": exc.stage, **exc.debug})
        databases.append(item)
    return {
        "keysSource": str(ctx.keys_path) if ctx.keys_path else None,
        "databaseCount": len(databases),
        "openCount": sum(bool(item.get("open")) for item in databases),
        "dependencies": {
            "python": sys.version.split()[0],
            "sqlcipher": ctx.args.sqlcipher or os.environ.get("WDB_SQLCIPHER") or shutil.which("sqlcipher"),
            "zstandard": module_available("zstandard") or bool(shutil.which("zstd")),
            "lz4": module_available("lz4.block"),
        },
        "databases": databases,
    }, errors


def module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def download_cover(items: List[Dict[str, Any]], output: str) -> None:
    target = Path(output).expanduser()
    multiple = len(items) > 1
    if multiple or target.is_dir() or str(output).endswith(os.sep):
        target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(items):
        url = item.get("momentsCoverUrl")
        if not url:
            continue
        parsed = urllib.parse.urlparse(url)
        suffix = Path(parsed.path).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            suffix = ".jpg"
        if multiple or target.is_dir():
            safe_name = re.sub(r"[^0-9A-Za-z._-]+", "_", item.get("username") or str(index))
            destination = target / (safe_name + suffix)
        else:
            destination = target
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 lov-wdb-cli/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise WdbError("封面图超过 20 MiB", "download_cover", url=url)
            destination.write_bytes(data)
            item["downloadedPath"] = str(destination.resolve())
        except (OSError, urllib.error.URLError) as exc:
            item["downloadError"] = str(exc)


def build_meta(command: str, data: Any, errors: List[Dict[str, Any]], **extra: Any) -> Dict[str, Any]:
    count = len(data) if isinstance(data, list) else 1
    return {"count": count, "errors": errors, **extra}


def output_envelope(command: str, data: Any, meta: Dict[str, Any], output_format: str) -> None:
    envelope = {"schemaVersion": SCHEMA_VERSION, "command": command, "data": data, "meta": meta}
    if output_format == "json":
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
    elif output_format == "jsonl":
        print(json.dumps({"schemaVersion": SCHEMA_VERSION, "command": command, "meta": meta}, ensure_ascii=False))
        items = data if isinstance(data, list) else [data]
        for item in items:
            print(json.dumps(item, ensure_ascii=False))
    else:
        if isinstance(data, list):
            for item in data:
                source = item.get("source", {}) if isinstance(item, dict) else {}
                summary = item.get("displayName") or item.get("text") or item.get("feedId") or str(item)
                print("{}\t{}:{}:{}".format(summary, source.get("databasePath", ""), source.get("tableName", ""), source.get("rowid", "")))
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        if meta.get("errors"):
            eprint(json.dumps({"errors": meta["errors"]}, ensure_ascii=False, indent=2))


def add_range_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--date", help="本地自然日，YYYY-MM-DD")
    group.add_argument("--from", dest="start", help="开始日期或 ISO 8601")
    parser.add_argument("--to", dest="end", help="结束日期或 ISO 8601；纯日期按含当天处理")


def add_format_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", dest="output_format", choices=["json", "jsonl", "text"], default=argparse.SUPPRESS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="自由查看并只读查询微信 SQLCipher 数据库")
    parser.add_argument("--keys", help="WDB Pro 管理副本、keys.toml、DTrace .keys 或 wechat-cli all_keys.json")
    parser.add_argument("--database", action="append", help="直接指定数据库；可重复，密钥清单中同路径的 key 会自动复用")
    parser.add_argument("--account", help="按数据库路径片段限定账号")
    parser.add_argument("--sqlcipher", help="sqlcipher 可执行文件路径；默认读取 WDB_SQLCIPHER 或 PATH")
    parser.add_argument("--format", dest="output_format", choices=["json", "jsonl", "text"], default="json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="检查数据源、依赖、数据库可读性和能力")
    add_format_arg(doctor)

    contacts = subparsers.add_parser("contacts", help="查询联系人基本信息")
    contacts.add_argument("--match", help="昵称、备注、微信号或 wxid 片段")
    contacts.add_argument("--limit", type=int, default=200)
    add_format_arg(contacts)

    chats = subparsers.add_parser("chats", help="查询某天或区间聊天记录")
    add_range_args(chats)
    chats.add_argument("--contact", help="昵称、备注、wxid、32 位 hash 或完整聊天表名")
    chats.add_argument("--query", help="正文包含文本")
    chats.add_argument("--limit", type=int, default=1000)
    chats.add_argument("--include-deleted", action="store_true")
    add_format_arg(chats)

    moments = subparsers.add_parser("moments", help="查询朋友圈帖子、媒体和可观测互动")
    add_range_args(moments)
    moments.add_argument("--contact", help="昵称、备注、微信号或 wxid")
    moments.add_argument("--feed-id", action="append", help="朋友圈 feed id；可重复")
    moments.add_argument("--limit", type=int, default=500)
    add_format_arg(moments)

    moments_media = subparsers.add_parser("moments-media", help="下载朋友圈原图，x-Enc 加密图自动解密")
    add_range_args(moments_media)
    moments_media.add_argument("--contact", help="昵称、备注、微信号或 wxid")
    moments_media.add_argument("--feed-id", action="append", help="朋友圈 feed id；可重复")
    moments_media.add_argument("--output", required=True, help="保存目录；不能位于微信数据目录内")
    moments_media.add_argument("--limit", type=int, default=50, help="最多处理的帖子数")
    add_format_arg(moments_media)

    cover = subparsers.add_parser("cover", help="获取联系人朋友圈封面 URL，可选下载")
    cover.add_argument("--contact", required=True, help="昵称、备注、微信号或 wxid")
    cover.add_argument("--output", help="下载到文件或目录")
    cover.add_argument("--limit", type=int, default=20)
    add_format_arg(cover)

    stats = subparsers.add_parser("stats", help="汇总聊天、联系人和朋友圈统计")
    add_range_args(stats)
    stats.add_argument("--contact", help="限定联系人")
    stats.add_argument("--limit", type=int, default=20000, help="各数据集最大读取量")
    add_format_arg(stats)

    record = subparsers.add_parser("record", help="按 databasePath + tableName + rowid 精确读取")
    record.add_argument("--database", dest="record_database", required=True)
    record.add_argument("--table", required=True)
    record.add_argument("--rowid", type=int, required=True)
    add_format_arg(record)

    schema = subparsers.add_parser("schema", help="浏览任意数据库的表、字段与可选行数")
    schema.add_argument("--database", dest="schema_database", help="完整路径或唯一文件名")
    schema.add_argument("--table", help="按表名片段筛选")
    schema.add_argument("--counts", action="store_true", help="同时读取各表行数，可能较慢")
    add_format_arg(schema)

    sql = subparsers.add_parser("sql", help="对指定数据库执行单条 SELECT/WITH 只读查询")
    sql.add_argument("--database", dest="sql_database", required=True, help="完整路径或唯一文件名")
    sql.add_argument("--query", required=True, help="单条 SELECT 或 WITH 查询")
    sql.add_argument("--limit", type=int, default=1000, help="最大返回行数")
    add_format_arg(sql)
    return parser


def run(args: argparse.Namespace) -> Tuple[Any, Dict[str, Any]]:
    if getattr(args, "limit", 1) <= 0:
        raise WdbError("limit 必须大于 0", "arguments", limit=args.limit)
    direct_selector = None
    if args.command == "record":
        direct_selector = args.record_database
    elif args.command == "schema" and args.schema_database:
        direct_selector = args.schema_database
    elif args.command == "sql":
        direct_selector = args.sql_database
    if direct_selector:
        direct = Path(direct_selector).expanduser().resolve()
        existing = list(args.database or [])
        if direct.is_file() and str(direct) not in [str(Path(item).expanduser().resolve()) for item in existing]:
            args.database = existing + [str(direct)]
    with Context(args) as ctx:
        return run_context(ctx)


def run_context(ctx: Context) -> Tuple[Any, Dict[str, Any]]:
    args = ctx.args
    if args.command == "doctor":
        data, errors = doctor_data(ctx)
        return data, build_meta(args.command, data, errors)
    if args.command == "contacts":
        data, errors = contact_rows(ctx, args.match, args.limit)
        return data, build_meta(args.command, data, errors, truncated=len(data) >= args.limit)
    if args.command == "chats":
        start_ts, end_ts = parse_day_or_range(args.date, args.start, args.end)
        data, errors, scan = message_rows(ctx, args.contact, args.query, start_ts, end_ts, args.limit, args.include_deleted)
        return data, build_meta(args.command, data, errors, **scan, startTime=iso_local(start_ts), endTime=iso_local(end_ts))
    if args.command == "moments":
        start_ts, end_ts = parse_day_or_range(args.date, args.start, args.end)
        data, errors, scan = moment_rows(ctx, args.contact, args.feed_id, start_ts, end_ts, args.limit)
        return data, build_meta(args.command, data, errors, **scan, startTime=iso_local(start_ts), endTime=iso_local(end_ts))
    if args.command == "moments-media":
        if not (args.feed_id or args.contact or args.date or args.start or args.end):
            raise WdbError("moments-media 至少需要 --feed-id、--contact 或日期范围", "arguments")
        start_ts, end_ts = parse_day_or_range(args.date, args.start, args.end)
        target = media_output_dir(ctx, args.output)
        posts, errors, scan = moment_rows(ctx, args.contact, args.feed_id, start_ts, end_ts, args.limit)
        data, media_errors = moment_media_rows(posts, target)
        status_counts = {
            status: sum(item["status"] == status for item in data)
            for status in ("downloaded", "exists", "skipped", "failed")
        }
        return data, build_meta(
            args.command, data, errors + media_errors, outputDir=str(target), postCount=len(posts),
            statusCounts=status_counts, **scan, startTime=iso_local(start_ts), endTime=iso_local(end_ts),
        )
    if args.command == "cover":
        data, errors = contact_rows(ctx, args.contact, args.limit)
        data = [item for item in data if item.get("momentsCoverUrl")]
        if args.output and data:
            download_cover(data, args.output)
        return data, build_meta(args.command, data, errors, truncated=len(data) >= args.limit)
    if args.command == "record":
        data, errors = record_row(ctx, args.record_database, args.table, args.rowid)
        return data, build_meta(args.command, data, errors)
    if args.command == "schema":
        data, errors = schema_data(ctx, args.schema_database, args.table, args.counts)
        table_count = sum(len(item.get("tables", [])) for item in data)
        return data, build_meta(args.command, data, errors, tableCount=table_count)
    if args.command == "sql":
        data, errors, database, truncated = sql_rows(ctx, args.sql_database, args.query, args.limit)
        return data, build_meta(
            args.command,
            data,
            errors,
            databasePath=str(database.spec.path),
            query=_single_read_query(args.query),
            truncated=truncated,
        )
    if args.command == "stats":
        start_ts, end_ts = parse_day_or_range(args.date, args.start, args.end)
        chats, chat_errors, chat_scan = message_rows(ctx, args.contact, None, start_ts, end_ts, args.limit, False)
        moments, moment_errors, moment_scan = moment_rows(ctx, args.contact, None, start_ts, end_ts, args.limit)
        contacts, contact_errors = contact_rows(ctx, args.contact, args.limit)
        by_day: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for item in chats:
            day = (item.get("timestamp") or "unknown")[:10]
            by_day[day] = by_day.get(day, 0) + 1
            kind = item.get("messageType") or "unknown"
            by_type[kind] = by_type.get(kind, 0) + 1
        data = {
            "range": {"startTime": iso_local(start_ts), "endTime": iso_local(end_ts)},
            "contacts": {"count": len(contacts)},
            "chats": {"count": len(chats), "byDay": dict(sorted(by_day.items())), "byType": dict(sorted(by_type.items()))},
            "moments": {
                "postCount": len(moments),
                "observedLikeCount": sum(item.get("observedLikeCount", 0) for item in moments),
                "observedCommentCount": sum(item.get("observedCommentCount", 0) for item in moments),
            },
        }
        errors = contact_errors + chat_errors + moment_errors
        return data, build_meta(args.command, data, errors, chatTables=chat_scan["scannedTables"], momentTables=moment_scan["scannedTables"], truncated=chat_scan["truncated"] or moment_scan["truncated"])
    raise WdbError("未知命令", "arguments", command=args.command)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        data, meta = run(args)
        output_envelope(args.command, data, meta, args.output_format)
        return 0 if not meta.get("errors") or args.command == "doctor" else 1
    except WdbError as exc:
        payload = {
            "schemaVersion": SCHEMA_VERSION,
            "command": getattr(args, "command", None),
            "error": str(exc),
            "debug": {"stage": exc.stage, **exc.debug},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        eprint(json.dumps({"schemaVersion": SCHEMA_VERSION, "error": "操作已中止", "debug": {"stage": "interrupt"}}, ensure_ascii=False))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
