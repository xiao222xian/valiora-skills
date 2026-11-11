#!/usr/bin/env python3
"""
Run any wcx subcommand with automatic token refresh on credential expiry.

Usage:
    wcx_run.py [--no-retry] -- <wcx subcommand and args>

Examples:
    wcx_run.py -- search "宝玉"
    wcx_run.py -- fetch gh_abc123 --limit 20
    wcx_run.py -- export gh_abc123 --format md --out ./posts

Detection: wcx prints strings like "登录失效" / "凭证无效" / "token失效" to stdout/stderr
or exits non-zero. On first such failure we auto-invoke refresh_token.py and retry
exactly once. A successful run exits 0 with wcx's stdout intact.

Also preflights the wcx version: anything older than MIN_WCX_VERSION is upgraded
via `pip install -U git+…` before the command runs, since pre-0.2.0 wcx had a
fatal 501 bug when fetching article bodies.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REFRESH = SCRIPT_DIR / "refresh_token.py"

# Default export root. Lives next to the persistent profile so a single
# `~/.lovstudio/wxmp-cracker/` is the canonical home for both credentials and
# exported articles — no scatter across whatever cwd the user happened to be in.
# Override via WXMP_EXPORT_ROOT.
DEFAULT_EXPORT_ROOT = Path(
    os.environ.get("WXMP_EXPORT_ROOT")
    or (Path.home() / ".lovstudio" / "wxmp-cracker" / "exports")
)

# Minimum wcx version this skill expects. Bump in lockstep with wcx releases
# that fix user-visible issues (e.g. 0.2.0 fixed the http→https 301 → 501 bug).
MIN_WCX_VERSION = (0, 2, 0)
WCX_INSTALL_SPEC = "git+https://github.com/lovstudio/wcx.git"

# Patterns wcx emits when credentials are bad. Keep this list conservative — we
# only retry on clear auth failures, not generic errors.
EXPIRY_MARKERS = (
    "登录失效",
    "凭证无效",
    "凭证失效",
    "token 失效",
    "token失效",
    "未登录",
    "cookie 失效",
    "cookie失效",
    "请先登录",
    "请先执行 wcx login",
    # wcx ≥ 0.2.x 风控失效信号
    "认证失败",
    "Auth failed",
    "invalid session",
    "Re-login needed",
    "ret=200003",
    "运行 wcx login",
)


def _parse_version(s: str) -> Tuple[int, ...]:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", s)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def ensure_wcx_version() -> None:
    """Preflight: wcx present and ≥ MIN_WCX_VERSION, else auto-upgrade."""
    try:
        out = subprocess.run(
            ["wcx", "--version"], capture_output=True, text=True, timeout=10,
        )
        installed = _parse_version(out.stdout + out.stderr)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        installed = (0, 0, 0)

    if installed >= MIN_WCX_VERSION:
        return

    reason = ("未安装 wcx" if installed == (0, 0, 0)
              else f"wcx {'.'.join(map(str, installed))} 过旧")
    need = ".".join(map(str, MIN_WCX_VERSION))
    print(f"\n↻ {reason}，自动升级到 ≥ {need} …\n", file=sys.stderr)
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", f"wcx @ {WCX_INSTALL_SPEC}"],
    )
    if r.returncode != 0:
        print(
            f"\nERROR: wcx 自动升级失败。请手动运行：\n"
            f"  pip install -U {WCX_INSTALL_SPEC}\n",
            file=sys.stderr,
        )
        sys.exit(r.returncode)


def inject_default_out(wcx_args: List[str]) -> List[str]:
    """For `export <target>`, default `--out` to DEFAULT_EXPORT_ROOT. Skipped
    if the user passed --out / -o themselves.

    Note: wcx itself creates a `<target>/` subdir under whatever `--out`
    points at, so we pass the *parent* root, not `<root>/<target>`. Otherwise
    we'd get `exports/品牌方/品牌方/articles/...`. End result with the parent:
    `exports/品牌方/articles/...` — exactly what we want.
    """
    if not wcx_args or wcx_args[0] != "export":
        return wcx_args
    if any(a == "--out" or a == "-o" or a.startswith("--out=") for a in wcx_args):
        return wcx_args
    if len(wcx_args) < 2 or wcx_args[1].startswith("-"):
        return wcx_args  # malformed; let wcx complain

    target = wcx_args[1]
    DEFAULT_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    final_dir = DEFAULT_EXPORT_ROOT / target  # informational only
    print(f"\n[SKILL] 未指定 --out，默认导出到 {final_dir}\n", file=sys.stderr)
    return wcx_args + ["--out", str(DEFAULT_EXPORT_ROOT)]


def looks_expired(output: str, returncode: int) -> bool:
    blob = output or ""
    if any(m in blob for m in EXPIRY_MARKERS):
        return True
    # wcx status on logged-out state prints "未登录" and exits 0; but most commands
    # exit non-zero + print a hint. Require BOTH a marker AND non-zero to reduce
    # false positives, except when wcx explicitly blocks on missing creds.
    return False


# Fingerprints of the pre-0.2.0 501 bug. When the body fetch hits the http→https
# redirect bug, wcx prints `HTTP Error 501: Not Implemented` for *every* article
# while list fetch itself succeeds. Different from a real upstream 501.
BROKEN_WCX_MARKERS = (
    "HTTP Error 501",
    "501: Not Implemented",
    "501 Not Implemented",
)


def looks_like_broken_wcx(output: str) -> bool:
    blob = output or ""
    return any(m in blob for m in BROKEN_WCX_MARKERS)


def force_upgrade_wcx() -> int:
    print(
        "\n[SKILL] 检测到 wcx 正文抓取命中已知的 501 bug。"
        "\n[SKILL] 正在强制升级 wcx（pip install -U …）…\n",
        file=sys.stderr, flush=True,
    )
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "--force-reinstall",
         "--no-deps", f"wcx @ {WCX_INSTALL_SPEC}"],
    )
    return r.returncode


def run_wcx(argv: List[str]) -> subprocess.CompletedProcess:
    # Stream stdout/stderr to the user AND capture for inspection.
    proc = subprocess.Popen(
        ["wcx", *argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    captured: List[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        captured.append(line)
    rc = proc.wait()
    return subprocess.CompletedProcess(proc.args, rc, "".join(captured), "")


def refresh(timeout: int) -> int:
    print("\n↻ wcx 凭证失效，自动重新获取 token …\n", file=sys.stderr)
    r = subprocess.run(
        [sys.executable, str(REFRESH), "--timeout", str(timeout)],
        check=False,
    )
    return r.returncode


def main() -> None:
    ap = argparse.ArgumentParser(description="Run wcx with auto-refresh on expiry")
    ap.add_argument("--no-retry", action="store_true", help="disable auto-refresh on expiry")
    ap.add_argument("--refresh-timeout", type=int, default=180,
                    help="seconds for QR scan during refresh (default: 180)")
    ap.add_argument("rest", nargs=argparse.REMAINDER,
                    help="wcx subcommand and args (prefix with --)")
    args = ap.parse_args()

    wcx_args = args.rest
    if wcx_args and wcx_args[0] == "--":
        wcx_args = wcx_args[1:]
    if not wcx_args:
        print("ERROR: 需要 wcx 子命令, e.g. -- search 宝玉", file=sys.stderr)
        sys.exit(64)

    ensure_wcx_version()

    wcx_args = inject_default_out(wcx_args)

    result = run_wcx(wcx_args)

    # Fast path: clean success.
    if result.returncode == 0 and not looks_expired(result.stdout, 0) \
       and not looks_like_broken_wcx(result.stdout):
        sys.exit(0)

    # Broken-wcx path: 501 bug slipped past version check (e.g. --version lies,
    # or pypi has a wheel that is stale vs git HEAD). Force-reinstall and retry.
    if not args.no_retry and looks_like_broken_wcx(result.stdout):
        rc = force_upgrade_wcx()
        if rc != 0:
            print(
                "\nERROR: wcx 强制升级失败。请手动运行：\n"
                f"  pip install -U --force-reinstall {WCX_INSTALL_SPEC}\n",
                file=sys.stderr,
            )
            sys.exit(rc)
        print("\n↻ wcx 已升级，重新执行原命令 …\n", file=sys.stderr)
        result2 = run_wcx(wcx_args)
        sys.exit(result2.returncode)

    if args.no_retry or not looks_expired(result.stdout, result.returncode):
        sys.exit(result.returncode or 1)

    rc = refresh(args.refresh_timeout)
    if rc != 0:
        print(f"ERROR: 刷新 token 失败 (exit {rc})", file=sys.stderr)
        sys.exit(rc)

    print("\n↻ 重新执行原命令 …\n", file=sys.stderr)
    result2 = run_wcx(wcx_args)
    sys.exit(result2.returncode)


if __name__ == "__main__":
    main()
