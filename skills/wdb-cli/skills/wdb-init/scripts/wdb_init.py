#!/usr/bin/env python3
"""Standalone WDB Pro key initializer for Agent workflows.

This CLI turns a local WeChat installation into the private
``wdb-pro-managed-keys.json`` source consumed by ``lov-wdb-cli``. It wraps the
native ``wechat-key-scanner`` sidecar from WDB Pro, including the disposable
debuggable WeChat copy used for the WeChat 4.1.10+ login capture flow.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "lov-wdb-init/v1"
SCANNER_BINARIES = {
    "arm64": "wechat-key-scanner-aarch64-apple-darwin",
    "x86_64": "wechat-key-scanner-x86_64-apple-darwin",
}
MANAGED_KEYS_RELATIVE_PATHS = [
    Path.home()
    / "Library"
    / "Application Support"
    / "ai.lovstudio.wdb-pro"
    / "database-keys"
    / "wdb-pro-managed-keys.json",
    Path.home()
    / "Library"
    / "Application Support"
    / "me.lovpen.wdb-pro"
    / "database-keys"
    / "wdb-pro-managed-keys.json",
]
DEFAULT_DB_DIR = (
    Path.home()
    / "Library"
    / "Containers"
    / "com.tencent.xinWeChat"
    / "Data"
    / "Documents"
    / "xwechat_files"
)
DEFAULT_CAPTURE_SECONDS = 180


class WdbInitError(RuntimeError):
    """Structured error with a stable stage for agent diagnostics."""

    def __init__(self, message: str, stage: str, **debug: Any) -> None:
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.debug = {key: value for key, value in debug.items() if value is not None}


@dataclass(frozen=True)
class Account:
    id: str
    account: str
    db_dir: Path
    database_count: int
    total_size: int
    last_modified: Optional[int]

    def public(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "account": self.account,
            "dbDir": str(self.db_dir),
            "databaseCount": self.database_count,
            "totalSize": self.total_size,
            "lastModified": self.last_modified,
        }


@dataclass(frozen=True)
class ScanResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: Optional[int]
    detail: str


@dataclass
class Snapshot:
    path: Path
    db_count: int

    def close(self) -> None:
        if self.path.exists():
            shutil.rmtree(self.path, ignore_errors=True)

    def __enter__(self) -> "Snapshot":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


class ManagedWechatSession:
    def __init__(self, root: Path, app_path: Path, original_app: Path, pid: int) -> None:
        self.root = root
        self.app_path = app_path
        self.original_app = original_app
        self.pid = pid

    def restore(self, allow_login_to_settle: bool = True) -> Dict[str, Any]:
        detail: Dict[str, Any] = {"cleaned": False}
        if allow_login_to_settle:
            time.sleep(3)
        managed_pid = find_wechat_process(self.app_path) or self.pid
        if managed_pid:
            run_command(["/bin/kill", "-TERM", str(managed_pid)], check=False)
            deadline = time.time() + 10
            while find_wechat_process(self.app_path) and time.time() < deadline:
                time.sleep(0.1)
        detail["managedPid"] = managed_pid
        if not find_wechat_process(self.app_path):
            shutil.rmtree(self.root, ignore_errors=True)
            detail["cleaned"] = True
            run_command(["/usr/bin/open", "-a", "WeChat"], check=False)
        return detail


def command_detail(output: subprocess.CompletedProcess[str]) -> str:
    parts = [
        value.strip()
        for value in (output.stdout, output.stderr)
        if value and value.strip()
    ]
    return "\n".join(parts)


def run_command(
    command: Sequence[str],
    *,
    check: bool = True,
    timeout: Optional[int] = None,
    input_text: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(command),
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env or os.environ,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WdbInitError(
            "命令执行失败: {}".format(exc),
            "command",
            command=" ".join(str(part) for part in command),
        ) from exc
    if check and result.returncode != 0:
        raise WdbInitError(
            command_detail(result) or "命令返回 {}".format(result.returncode),
            "command",
            command=" ".join(str(part) for part in command),
            exitCode=result.returncode,
        )
    return result


def is_macos() -> bool:
    return sys.platform == "darwin"


def find_wechat_app() -> Optional[Path]:
    candidates = [
        Path("/Applications/WeChat.app"),
        Path("/Applications/微信.app"),
        Path.home() / "Applications" / "WeChat.app",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    try:
        output = run_command(
            [
                "/usr/bin/mdfind",
                "kMDItemCFBundleIdentifier == 'com.tencent.xinWeChat'",
            ],
            check=False,
        )
    except WdbInitError:
        return None
    for line in (output.stdout or "").splitlines():
        path = Path(line.strip())
        if path.is_dir():
            return path
    return None


def read_plist_value(app_path: Path, key: str) -> Optional[str]:
    info_plist = app_path / "Contents" / "Info.plist"
    if not info_plist.is_file():
        return None
    result = run_command(
        ["/usr/bin/plutil", "-extract", key, "raw", str(info_plist)],
        check=False,
    )
    if result.returncode != 0:
        return None
    value = (result.stdout or "").strip()
    return value or None


def read_wechat_version(app_path: Path) -> Optional[str]:
    return read_plist_value(app_path, "CFBundleShortVersionString")


def read_wechat_build(app_path: Path) -> Optional[str]:
    return read_plist_value(app_path, "CFBundleVersion")


def wechat_executable_path(app_path: Path) -> Path:
    executable = read_plist_value(app_path, "CFBundleExecutable") or "WeChat"
    return app_path / "Contents" / "MacOS" / executable


def wechat_version_requires_capture(version: Optional[str]) -> bool:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version or "")
    if not match:
        return False
    return tuple(int(part) for part in match.groups()) >= (4, 1, 10)


def code_entitlements(path: Path) -> str:
    result = run_command(
        ["/usr/bin/codesign", "-d", "--entitlements", ":-", str(path)],
        check=False,
    )
    return (result.stdout or "") + (result.stderr or "")


def entitlement_present(path: Path, key: str) -> bool:
    text = code_entitlements(path)
    marker = "<key>{}</key>".format(key)
    if marker not in text:
        return False
    tail = text.split(marker, 1)[1]
    return "<true/>" in tail[:80] or "<true />" in tail[:80]


def running_wechat_pids() -> List[int]:
    pids: List[int] = []
    for name in ("WeChat", "Weixin"):
        result = run_command(["/usr/bin/pgrep", "-x", name], check=False)
        if result.returncode != 0:
            continue
        for line in (result.stdout or "").splitlines():
            try:
                pid = int(line.strip())
            except ValueError:
                continue
            if pid > 0 and pid not in pids:
                pids.append(pid)
    return sorted(pids)


def process_matches_app(pid: int, app_path: Path) -> bool:
    executable = str(wechat_executable_path(app_path))
    result = run_command(
        ["/bin/ps", "-ww", "-p", str(pid), "-o", "command="],
        check=False,
    )
    if result.returncode != 0:
        return False
    command = (result.stdout or "").strip()
    return command == executable or command.startswith(executable + " ")


def find_wechat_process(app_path: Optional[Path] = None) -> Optional[int]:
    for pid in running_wechat_pids():
        if app_path is None or process_matches_app(pid, app_path):
            return pid
    return None


def wait_for_wechat_process(app_path: Optional[Path], timeout: int) -> Optional[int]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        pid = find_wechat_process(app_path)
        if pid:
            return pid
        time.sleep(0.1)
    return None


def discover_accounts() -> List[Account]:
    root = DEFAULT_DB_DIR
    if not root.is_dir():
        return []
    accounts: List[Account] = []
    for account_dir in sorted(root.iterdir()):
        if not account_dir.is_dir():
            continue
        db_dir = account_dir / "db_storage"
        if not db_dir.is_dir():
            continue
        database_count = 0
        total_size = 0
        last_modified: Optional[int] = None
        for path in db_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() != ".db":
                continue
            database_count += 1
            try:
                stat = path.stat()
            except OSError:
                continue
            total_size += stat.st_size
            modified = int(stat.st_mtime)
            last_modified = max(last_modified or 0, modified)
        account_id = _account_id(account_dir.name)
        accounts.append(
            Account(
                id=account_id,
                account=account_dir.name,
                db_dir=db_dir,
                database_count=database_count,
                total_size=total_size,
                last_modified=last_modified,
            )
        )
    return sorted(accounts, key=lambda item: item.account)


def _account_id(directory_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", directory_name).strip("-") or "unknown"


def select_db_dir(
    explicit: Optional[str] = None,
    account: Optional[str] = None,
) -> tuple[Path, Account]:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.name != "db_storage":
            raise WdbInitError("请选择微信号目录下的 db_storage 目录", "arguments")
        if not path.is_dir():
            raise WdbInitError("数据目录不存在: {}".format(path), "arguments", dbDir=str(path))
        if "/xwechat_files/" not in str(path):
            raise WdbInitError(
                "数据目录不在 xwechat_files 下，已拒绝执行",
                "arguments",
                dbDir=str(path),
            )
        account_dir = path.parent
        return path, Account(
            id=_account_id(account_dir.name),
            account=account_dir.name,
            db_dir=path,
            database_count=0,
            total_size=0,
            last_modified=None,
        )

    accounts = discover_accounts()
    if not accounts:
        raise WdbInitError("未发现微信数据目录，请先打开并登录微信", "discover", home=str(Path.home()))
    if account:
        matches = [
            item
            for item in accounts
            if account.lower() in item.account.lower()
            or account.lower() in item.db_dir.as_posix().lower()
            or account.lower() in item.id.lower()
        ]
        if len(matches) != 1:
            raise WdbInitError(
                "账号条件必须唯一匹配一个微信账号",
                "arguments",
                account=account,
                matches=[item.account for item in matches],
            )
        return matches[0].db_dir, matches[0]
    if len(accounts) != 1:
        raise WdbInitError(
            "检测到多个微信账号，请用 --account 指定",
            "arguments",
            accounts=[item.account for item in accounts],
        )
    return accounts[0].db_dir, accounts[0]


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def asset_scanner() -> Optional[Path]:
    machine = platform.machine()
    filename = SCANNER_BINARIES.get(machine)
    if filename:
        path = skill_root() / "assets" / "bin" / filename
        if path.is_file():
            return path
    return None


def app_scanner() -> Optional[Path]:
    candidates = [
        Path("/Applications/wdb-pro.app/Contents/MacOS/wechat-key-scanner"),
        Path.home() / "Applications" / "wdb-pro.app" / "Contents" / "MacOS" / "wechat-key-scanner",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def scanner_cache_path(source: Path) -> Path:
    directory = Path.home() / ".cache" / "ai.lovstudio.wdb-init" / "bin"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "wechat-key-scanner-{}".format(platform.machine())


def ensure_scanner_binary(source: Path) -> Path:
    source = source.resolve()
    if not source.is_file():
        raise WdbInitError("本机数据读取组件缺失", "scanner", scanner=str(source))
    destination = scanner_cache_path(source)
    try:
        if not destination.exists() or destination.stat().st_size != source.stat().st_size:
            shutil.copy2(source, destination)
            destination.chmod(0o700)
    except OSError as exc:
        raise WdbInitError(
            "复制本机数据读取组件失败",
            "scanner",
            scanner=str(source),
            error=str(exc),
        ) from exc
    # A downloaded binary can carry a quarantine ticket from its source app.
    # Only the private runtime cache is touched, never the installed app.
    run_command(["/usr/bin/xattr", "-dr", "com.apple.quarantine", str(destination)], check=False)
    entitlements = skill_root() / "assets" / "scanner-entitlements.plist"
    if entitlements.is_file() and not entitlement_present(
        destination, "com.apple.security.cs.debugger"
    ):
        run_command(
            [
                "/usr/bin/codesign",
                "--force",
                "--sign",
                "-",
                "--options",
                "runtime",
                "--entitlements",
                str(entitlements),
                str(destination),
            ],
            check=False,
        )
    return destination


def resolve_scanner(explicit: Optional[str] = None) -> Path:
    candidate: Optional[Path] = None
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
    else:
        candidate = asset_scanner() or app_scanner()
    if candidate is None:
        raise WdbInitError(
            "未找到 wechat-key-scanner 组件，请重新安装 WDB Pro",
            "scanner",
            assetRoot=str(skill_root() / "assets" / "bin"),
        )
    return ensure_scanner_binary(candidate)


def run_self_test_for_scanner(source: Path) -> ScanResult:
    """Run the native self-test on an isolated get-task-allow copy.

    Production sidecars are signed with ``com.apple.security.cs.debugger`` so
    they can attach to WeChat. The scanner's own capture self-test additionally
    needs ``com.apple.security.get-task-allow``, matching WDB Pro's release
    workflow: sign a temporary copy, test it, then discard it.
    """
    entitlements = skill_root() / "assets" / "scanner-self-test-entitlements.plist"
    with tempfile.TemporaryDirectory(prefix="wdb-init-self-test-") as tmp:
        candidate = Path(tmp) / "wechat-key-scanner"
        shutil.copy2(source, candidate)
        candidate.chmod(0o700)
        run_command(
            ["/usr/bin/xattr", "-dr", "com.apple.quarantine", str(candidate)],
            check=False,
        )
        signed = run_command(
            [
                "/usr/bin/codesign",
                "--force",
                "--sign",
                "-",
                "--options",
                "runtime",
                "--entitlements",
                str(entitlements),
                str(candidate),
            ],
            check=False,
        )
        if signed.returncode != 0:
            return ScanResult(
                False,
                "",
                command_detail(signed),
                signed.returncode,
                command_detail(signed) or "自检签名失败",
            )
        return run_scanner(candidate, ["--self-test"], timeout=60)


def platform_description() -> str:
    return "{} {}".format(platform.system(), platform.machine())


def wechat_app_info() -> Dict[str, Any]:
    app = find_wechat_app()
    if app is None:
        return {
            "installed": False,
            "path": None,
            "version": None,
            "build": None,
            "running": False,
            "pid": None,
            "getTaskAllow": None,
        }
    pid = find_wechat_process(app)
    return {
        "installed": True,
        "path": str(app.resolve()),
        "version": read_wechat_version(app),
        "build": read_wechat_build(app),
        "running": pid is not None,
        "pid": pid,
        "getTaskAllow": entitlement_present(app, "com.apple.security.get-task-allow"),
    }


def scan_accounts_with_keys() -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for account in discover_accounts():
        matching: List[Path] = []
        for path in MANAGED_KEYS_RELATIVE_PATHS:
            if path.is_file() and account_db_has_keys(path, account.db_dir):
                matching.append(path)
        output.append(
            {
                **account.public(),
                "keySource": str(matching[0]) if matching else None,
                "keyCount": _key_count(matching[0]) if matching else 0,
            }
        )
    return output


def account_db_has_keys(keys_path: Path, db_dir: Path) -> bool:
    try:
        data = json.loads(keys_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, list):
        return False
    needle = str(db_dir.resolve())
    return any(str(entry.get("path", "")).startswith(needle) for entry in data)


def _key_count(keys_path: Optional[Path]) -> int:
    if keys_path is None or not keys_path.is_file():
        return 0
    try:
        data = json.loads(keys_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    return len(data) if isinstance(data, list) else 0


def status_payload(explicit_scanner: Optional[str] = None) -> Dict[str, Any]:
    app = wechat_app_info()
    try:
        scanner = resolve_scanner(explicit_scanner)
        scanner_status = {
            "path": str(scanner),
            "debuggerEntitlement": entitlement_present(
                scanner, "com.apple.security.cs.debugger"
            ),
        }
    except WdbInitError as exc:
        scanner_status = {
            "path": None,
            "debuggerEntitlement": None,
            "error": exc.message,
            "stage": exc.stage,
            **exc.debug,
        }
    existing = [
        {"path": str(path), "exists": path.is_file(), "entryCount": _key_count(path) if path.is_file() else 0}
        for path in MANAGED_KEYS_RELATIVE_PATHS
    ]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "system": platform_description(),
        "wechat": app,
        "requiresLoginCapture": wechat_version_requires_capture(app.get("version")),
        "scanner": scanner_status,
        "managedKeys": existing,
        "accounts": scan_accounts_with_keys(),
    }


def snapshot_encrypted_pages(db_dir: Path) -> Snapshot:
    root = Path(tempfile.mkdtemp(prefix="wdb-init-db-pages-"))
    count = 0
    try:
        for path in sorted(db_dir.rglob("*.db")):
            if not path.is_file():
                continue
            try:
                with path.open("rb") as handle:
                    first_page = handle.read(4096)
            except OSError:
                continue
            if len(first_page) != 4096 or first_page.startswith(b"SQLite format 3"):
                continue
            relative = path.relative_to(db_dir)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(first_page)
            count += 1
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
    if count == 0:
        shutil.rmtree(root, ignore_errors=True)
        raise WdbInitError(
            "本机微信账号中暂未发现可读取的数据文件",
            "snapshot",
            dbDir=str(db_dir),
        )
    return Snapshot(root, count)


def run_scanner(
    scanner: Path,
    args: Sequence[str],
    target_pid: Optional[int] = None,
    timeout: int = 360,
) -> ScanResult:
    env = dict(os.environ)
    if target_pid:
        env["WDB_WECHAT_PID"] = str(target_pid)
    result = run_command(
        [str(scanner), *args],
        check=False,
        timeout=timeout,
        env=env,
    )
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    return ScanResult(
        result.returncode == 0,
        stdout,
        stderr,
        result.returncode,
        "\n".join(part for part in (stdout, stderr) if part and part.strip()).strip(),
    )


def scanner_output_to_managed_entries(content: str, db_dir: Path) -> List[Dict[str, Any]]:
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as exc:
        raise WdbInitError(
            "本机密钥结果不是有效 JSON",
            "parse",
            error=str(exc),
        ) from exc
    if not isinstance(raw, dict) or not raw:
        raise WdbInitError("本机密钥结果为空，未覆盖现有数据库", "parse")
    entries: List[Dict[str, Any]] = []
    for relative_raw, key_info in raw.items():
        relative = Path(str(relative_raw))
        if relative.is_absolute() or ".." in relative.parts:
            raise WdbInitError(
                "本机密钥结果包含越界路径: {}".format(relative_raw),
                "parse",
                relativePath=str(relative_raw),
            )
        if not isinstance(key_info, dict) or not isinstance(
            key_info.get("enc_key"), str
        ):
            raise WdbInitError(
                "本机密钥结果缺少 enc_key: {}".format(relative_raw),
                "parse",
                relativePath=str(relative_raw),
            )
        key = key_info["enc_key"].strip()
        if not re.fullmatch(r"[0-9a-fA-F]{64}", key):
            raise WdbInitError(
                "本机密钥结果中的密钥必须是 64 位十六进制字符串",
                "parse",
                relativePath=str(relative_raw),
            )
        full_path = (db_dir / relative).resolve()
        if not full_path.is_absolute():
            raise WdbInitError(
                "本机密钥结果路径必须是绝对路径: {}".format(relative_raw),
                "parse",
                relativePath=str(relative_raw),
            )
        entries.append(
            {
                "path": str(full_path),
                "key": key.lower(),
                "cipherCompatibility": 4,
            }
        )
    return entries


def save_managed_keys(entries: Sequence[Dict[str, Any]]) -> List[str]:
    if not entries:
        raise WdbInitError("没有可保存的本机密钥", "save")
    content = json.dumps(list(entries), ensure_ascii=False, indent=2) + "\n"
    saved: List[str] = []
    for final_path in MANAGED_KEYS_RELATIVE_PATHS:
        final_path = final_path.resolve()
        final_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            final_path.parent.chmod(0o700)
        except OSError:
            pass
        temp_path = final_path.parent / ".wdb-pro-managed-keys-{}.tmp".format(
            uuid.uuid4().hex
        )
        temp_path.write_text(content, encoding="utf-8")
        try:
            temp_path.chmod(0o600)
        except OSError:
            pass
        os.replace(temp_path, final_path)
        saved.append(str(final_path))
    return saved


def prepare_managed_wechat_copy(source_app: Path) -> ManagedWechatSession:
    root = (
        Path.home()
        / "Library"
        / "Caches"
        / "ai.lovstudio.wdb-pro"
        / "wechat-connection"
    ).resolve()
    app_path = root / "WeChat-WDB-Connection.app"
    if app_path == source_app.resolve() or source_app.resolve().is_relative_to(root):
        raise WdbInitError(
            "拒绝在微信原应用路径内创建临时连接副本",
            "managed_copy",
            source=str(source_app),
        )
    if find_wechat_process(app_path):
        raise WdbInitError(
            "上一次临时微信仍在运行，请退出后重试",
            "managed_copy",
            appPath=str(app_path),
        )
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    copy_command = ["/bin/cp", "-R"]
    if _supports_clonefile():
        copy_command = ["/bin/cp", "-c", "-R"]
    result = run_command([*copy_command, str(source_app), str(app_path)], check=False)
    if result.returncode != 0:
        shutil.rmtree(root, ignore_errors=True)
        raise WdbInitError(
            command_detail(result) or "创建临时微信副本失败",
            "managed_copy",
            command=" ".join(copy_command),
        )
    run_command(["xattr", "-dr", "com.apple.quarantine", str(app_path)], check=False)
    entitlements = root / "wechat-connection-entitlements.plist"
    entitlements.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>com.apple.security.cs.allow-jit</key>
  <true/>
  <key>com.apple.security.cs.disable-library-validation</key>
  <true/>
  <key>com.apple.security.get-task-allow</key>
  <true/>
</dict>
</plist>
""",
        encoding="utf-8",
    )
    info_plist = app_path / "Contents" / "Info.plist"
    run_command(
        [
            "/usr/bin/plutil",
            "-replace",
            "CFBundleDisplayName",
            "-string",
            "微信（WDB 临时连接）",
            str(info_plist),
        ],
        check=False,
    )
    sign_result = run_command(
        [
            "/usr/bin/codesign",
            "--force",
            "--sign",
            "-",
            "--options",
            "runtime",
            "--entitlements",
            str(entitlements),
            str(app_path),
        ],
        check=False,
    )
    if sign_result.returncode != 0:
        shutil.rmtree(root, ignore_errors=True)
        raise WdbInitError(
            command_detail(sign_result) or "签名临时微信副本失败",
            "managed_copy",
            copy=str(app_path),
        )
    required = [
        "com.apple.security.cs.allow-jit",
        "com.apple.security.cs.disable-library-validation",
        "com.apple.security.get-task-allow",
    ]
    if not all(entitlement_present(app_path, key) for key in required):
        shutil.rmtree(root, ignore_errors=True)
        raise WdbInitError(
            "临时微信副本未通过签名校验，原应用未被修改",
            "managed_copy",
            copy=str(app_path),
        )
    return ManagedWechatSession(root, app_path, source_app, 0)


def _supports_clonefile() -> bool:
    probe = Path(tempfile.mkdtemp(prefix="wdb-init-clone-probe-"))
    try:
        source = probe / "source"
        source.write_text("probe", encoding="utf-8")
        result = run_command(
            ["/bin/cp", "-c", str(source), str(probe / "target")],
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False
    finally:
        shutil.rmtree(probe, ignore_errors=True)


def launch_managed_wechat_copy(session: ManagedWechatSession) -> int:
    run_command(["/usr/bin/open", "-n", str(session.app_path)], check=False)
    pid = wait_for_wechat_process(session.app_path, 20)
    if pid:
        session.pid = pid
        return pid
    executable = wechat_executable_path(session.app_path)
    try:
        subprocess.Popen(
            [str(executable)],
            cwd=str(executable.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise WdbInitError(
            "临时微信副本启动失败: {}".format(exc),
            "managed_copy",
            copy=str(session.app_path),
        ) from exc
    pid = wait_for_wechat_process(session.app_path, 8)
    if not pid:
        raise WdbInitError(
            "临时微信副本未能在超时时间内启动",
            "managed_copy",
            copy=str(session.app_path),
        )
    session.pid = pid
    return pid


def run_capture(
    scanner: Path, db_dir: Path, timeout: int
) -> Tuple[ScanResult, str]:
    app = (
        find_wechat_app()
        or Path("/Applications/WeChat.app")
    )
    if not app.is_dir():
        raise WdbInitError("未检测到微信应用，请先安装最新版微信", "wechat")
    version = read_wechat_version(app)
    production_debuggable = entitlement_present(
        app, "com.apple.security.get-task-allow"
    )
    if not production_debuggable and find_wechat_process(app):
        raise WdbInitError(
            "请先完全退出微信。WDB Pro 将从原应用创建临时连接副本，不需要关闭 SIP。",
            "requiresQuit",
            wechatVersion=version,
        )
    session = prepare_managed_wechat_copy(app)
    try:
        pid = launch_managed_wechat_copy(session)
        probe = run_scanner(scanner, ["--probe-task-access", str(pid)], pid)
        if not probe.success:
            raise WdbInitError(
                probe.detail or "无法访问微信进程",
                "task_access",
                wechatVersion=version,
                managedCopy=str(session.app_path),
            )
        with snapshot_encrypted_pages(db_dir) as snapshot:
            output_dir = Path(tempfile.mkdtemp(prefix="wdb-init-output-"))
            output_path = output_dir / "keys.json"
            try:
                result = run_scanner(
                    scanner,
                    [
                        "--capture-passphrase",
                        str(snapshot.path),
                        str(output_path),
                        str(timeout),
                    ],
                    pid,
                    timeout=timeout + 60,
                )
                content = (
                    output_path.read_text(encoding="utf-8")
                    if result.success and output_path.is_file()
                    else ""
                )
            finally:
                shutil.rmtree(output_dir, ignore_errors=True)
        if not result.success:
            if "PASSPHRASE_VERIFY_FAILED" in result.detail:
                raise WdbInitError("捕获口令未能派生可用密钥", "capture", detail=result.detail)
            if "PASSPHRASE_CAPTURE_TIMEOUT" in result.detail:
                raise WdbInitError("登录期密钥捕获超时", "capture", detail=result.detail)
            raise WdbInitError(
                "登录期密钥捕获失败",
                "capture",
                detail=result.detail,
            )
        return result, content
    finally:
        session.restore(True)


def run_scan(
    scanner: Path, db_dir: Path, version: Optional[str]
) -> Tuple[ScanResult, Path]:
    app = find_wechat_app()
    if app is None:
        raise WdbInitError("未检测到微信应用", "wechat")
    if wechat_version_requires_capture(version):
        raise WdbInitError(
            "当前微信版本需要在下一次登录时完成连接",
            "requiresRelogin",
            wechatVersion=version,
        )
    pid = find_wechat_process(app)
    if pid is None:
        raise WdbInitError("请先打开并登录微信，再回来继续", "requiresLogin")
    probe = run_scanner(scanner, ["--probe-task-access", str(pid)], pid)
    if not probe.success:
        raise WdbInitError(
            probe.detail or "无法访问微信进程",
            "task_access",
            wechatVersion=version,
        )
    with snapshot_encrypted_pages(db_dir) as snapshot:
        output_dir = Path(tempfile.mkdtemp(prefix="wdb-init-output-"))
        output_path = output_dir / "keys.json"
        try:
            result = run_scanner(
                scanner,
                [str(snapshot.path), str(output_path)],
                pid,
                timeout=180,
            )
            return result, output_path
        except Exception:
            shutil.rmtree(output_dir, ignore_errors=True)
            raise


def emit_payload(payload: Dict[str, Any], output_format: str) -> None:
    if output_format == "text":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def add_account_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db-dir", help="微信账号下的 db_storage 目录")
    parser.add_argument("--account", help="按 wxid 或目录名限定账号")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="初始化 WDB Pro 管理的微信数据库密钥副本"
    )
    parser.add_argument("--scanner", help="wechat-key-scanner 可执行文件路径")
    parser.add_argument("--timeout", type=int, default=DEFAULT_CAPTURE_SECONDS)
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "text"],
        default="json",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="检查微信、账号和密钥文件状态")
    status.set_defaults(func=cmd_status)

    scan = subparsers.add_parser("scan", help="从运行中的微信内存扫描现有密钥")
    add_account_options(scan)
    scan.set_defaults(func=cmd_scan)

    capture = subparsers.add_parser(
        "capture", help="等待下一次登录时捕获密钥（微信 4.1.10+）"
    )
    add_account_options(capture)
    capture.set_defaults(func=cmd_capture)

    doctor = subparsers.add_parser(
        "doctor", help="检查组件、签名、账号与已保存密钥的完整诊断"
    )
    doctor.set_defaults(func=cmd_doctor)

    return parser


def cmd_status(args: argparse.Namespace) -> Tuple[Dict[str, Any], str]:
    return status_payload(args.scanner), "status"


def cmd_scan(args: argparse.Namespace) -> Tuple[Dict[str, Any], str]:
    db_dir, account = select_db_dir(args.db_dir, args.account)
    scanner = resolve_scanner(args.scanner)
    app = find_wechat_app()
    version = read_wechat_version(app) if app else None
    result, output_path = run_scan(scanner, db_dir, version)
    if not result.success:
        shutil.rmtree(output_path.parent, ignore_errors=True)
        stage = "scan"
        if "TASK_FOR_PID_DENIED" in result.detail:
            stage = "task_access"
        elif "PASSPHRASE_REQUIRED" in result.detail:
            raise WdbInitError(
                "当前微信不再保留旧式数据库密钥，需要在下一次登录时完成连接",
                "requiresRelogin",
                detail=result.detail,
            )
        raise WdbInitError(
            "本机数据读取失败",
            stage,
            detail=result.detail,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    try:
        content = output_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WdbInitError(
            "扫描结果文件不存在或不可读",
            "parse",
            outputPath=str(output_path),
            error=str(exc),
        ) from exc
    finally:
        shutil.rmtree(output_path.parent, ignore_errors=True)
    entries = scanner_output_to_managed_entries(content, db_dir)
    saved = save_managed_keys(entries)
    return {
        "status": "ready",
        "account": account.account,
        "databaseCount": len(entries),
        "managedKeys": [
            {"path": path, "exists": Path(path).is_file()}
            for path in saved
        ],
        "detail": "已连接 {} 个本机数据文件".format(len(entries)),
    }, "scan"


def cmd_capture(args: argparse.Namespace) -> Tuple[Dict[str, Any], str]:
    db_dir, account = select_db_dir(args.db_dir, args.account)
    scanner = resolve_scanner(args.scanner)
    result, content = run_capture(scanner, db_dir, args.timeout)
    if not result.success:
        raise WdbInitError(
            "登录期密钥捕获失败",
            "capture",
            detail=result.detail,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    entries = scanner_output_to_managed_entries(content, db_dir)
    saved = save_managed_keys(entries)
    return {
        "status": "ready",
        "account": account.account,
        "databaseCount": len(entries),
        "managedKeys": [
            {"path": path, "exists": Path(path).is_file()}
            for path in saved
        ],
        "detail": "已连接 {} 个本机数据文件".format(len(entries)),
    }, "capture"


def cmd_doctor(args: argparse.Namespace) -> Tuple[Dict[str, Any], str]:
    payload = status_payload(args.scanner)
    scanner = payload.get("scanner", {})
    scanner_path = scanner.get("path")
    if scanner_path:
        result = run_self_test_for_scanner(Path(scanner_path))
        payload["scanner"]["selfTest"] = {
            "ok": result.success,
            "detail": result.detail,
        }
    return payload, "doctor"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not is_macos():
        payload = {
            "schemaVersion": SCHEMA_VERSION,
            "error": "WDB Pro 密钥初始化目前仅支持 macOS",
            "debug": {"stage": "platform", "system": platform.system()},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    try:
        payload, command = args.func(args)
        payload["schemaVersion"] = SCHEMA_VERSION
        payload["command"] = command
        emit_payload(payload, args.output_format)
        return 0
    except WdbInitError as exc:
        payload = {
            "schemaVersion": SCHEMA_VERSION,
            "command": getattr(args, "command", None),
            "status": "error",
            "error": exc.message,
            "debug": {"stage": exc.stage, **exc.debug},
        }
        emit_payload(payload, args.output_format)
        return 2
    except KeyboardInterrupt:
        payload = {
            "schemaVersion": SCHEMA_VERSION,
            "command": getattr(args, "command", None),
            "error": "操作已中止",
            "debug": {"stage": "interrupt"},
        }
        emit_payload(payload, args.output_format)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
