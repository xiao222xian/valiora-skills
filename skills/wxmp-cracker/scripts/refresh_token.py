#!/usr/bin/env python3
"""
Auto-refresh wcx credentials (token + cookie) for mp.weixin.qq.com.

Strategy:
  1. Launch agent-browser with a persistent profile (~/.lovstudio/wxmp-cracker/profile).
  2. Open https://mp.weixin.qq.com/ — if already logged in, redirects to /cgi-bin/home
     with ?token=XXXXXX in the URL.
  3. If not logged in, surface a prompt asking the user to scan the QR code in the
     headed Chrome window, then poll the URL until the token appears.
  4. Extract token from URL, full cookie jar (including HttpOnly) via
     `agent-browser cookies get`.
  5. Run `wcx login --token ... --cookie ...` — wcx validates by firing a real search.

Exit codes:
  0 — credentials refreshed and validated
  1 — login timed out (user never scanned)
  2 — wcx login rejected the credentials
  3 — prerequisite missing (agent-browser / wcx not installed)
"""

import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

PROFILE_DIR = Path.home() / ".lovstudio" / "wxmp-cracker" / "profile"
MP_HOME = "https://mp.weixin.qq.com/"
TOKEN_URL_RE = re.compile(r"[?&]token=(\d+)")
LOGIN_TIMEOUT_DEFAULT = 180  # seconds to wait for QR scan


def run(cmd: List[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def require_tools() -> None:
    missing = [t for t in ("agent-browser", "wcx") if shutil.which(t) is None]
    if missing:
        print(f"ERROR: missing required tools: {', '.join(missing)}", file=sys.stderr)
        print("  • agent-browser: npm i -g agent-browser", file=sys.stderr)
        print("  • wcx: install from your internal distribution", file=sys.stderr)
        sys.exit(3)


def ab(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return run(["agent-browser", *args], check=check, capture=capture)


def ensure_browser_open(headed: bool) -> None:
    """Open mp.weixin.qq.com with a persistent profile. Safe to call repeatedly."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    # Close any running daemon so --profile/--headed take effect cleanly.
    run(["agent-browser", "close", "--all"], check=False)
    cmd = ["agent-browser"]
    if headed:
        cmd.append("--headed")
    cmd += ["--profile", str(PROFILE_DIR), "open", MP_HOME]
    run(cmd, check=True, capture=False)


def current_url() -> str:
    r = ab("get", "url", check=False)
    return (r.stdout or "").strip()


def extract_token(url: str) -> Optional[str]:
    m = TOKEN_URL_RE.search(url)
    return m.group(1) if m else None


def wait_for_login(timeout: int) -> str:
    """Poll until the page shows a valid token. Return the token."""
    deadline = time.time() + timeout
    notified = False
    while time.time() < deadline:
        url = current_url()
        token = extract_token(url)
        if token:
            return token
        if not notified:
            print(
                "\n⏳ 请在弹出的 Chrome 窗口扫码登录微信公众号后台\n"
                f"   (最多等待 {timeout} 秒, profile: {PROFILE_DIR})\n",
                file=sys.stderr,
            )
            notified = True
        time.sleep(3)
    print(f"ERROR: 登录超时（{timeout}s）——未检测到 token", file=sys.stderr)
    sys.exit(1)


def dump_cookie_string() -> str:
    """Return 'k1=v1; k2=v2; ...' from agent-browser cookies get."""
    r = ab("cookies", "get")
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip() and "=" in ln]
    pairs = []
    for ln in lines:
        k, _, v = ln.partition("=")
        if k and v:
            pairs.append(f"{k}={v}")
    return "; ".join(pairs)


def wcx_login(token: str, cookie: str) -> None:
    r = run(["wcx", "login", "--token", token, "--cookie", cookie], check=False)
    if r.returncode != 0 or "凭证有效" not in (r.stdout or ""):
        sys.stderr.write(r.stdout or "")
        sys.stderr.write(r.stderr or "")
        print("ERROR: wcx 拒绝了新凭证", file=sys.stderr)
        sys.exit(2)
    print(r.stdout.strip())


def close_browser() -> None:
    run(["agent-browser", "close", "--all"], check=False)


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh wcx token + cookie via agent-browser")
    ap.add_argument("--timeout", type=int, default=LOGIN_TIMEOUT_DEFAULT,
                    help=f"seconds to wait for QR scan (default: {LOGIN_TIMEOUT_DEFAULT})")
    ap.add_argument("--keep-open", action="store_true",
                    help="keep browser session open after refresh (default: close)")
    ap.add_argument("--headless", action="store_true",
                    help="try headless (only works if profile already has a live session)")
    args = ap.parse_args()

    require_tools()

    headed = not args.headless
    print(f"→ opening {MP_HOME} (profile: {PROFILE_DIR})", file=sys.stderr)
    ensure_browser_open(headed=headed)

    token = wait_for_login(args.timeout)
    print(f"✓ token: {token}", file=sys.stderr)

    cookie = dump_cookie_string()
    if not cookie:
        print("ERROR: 无法从浏览器读取 cookie", file=sys.stderr)
        sys.exit(2)
    print(f"✓ cookie: {len(cookie)} chars, {cookie.count('=')} pairs", file=sys.stderr)

    wcx_login(token, cookie)

    if not args.keep_open:
        close_browser()


if __name__ == "__main__":
    main()
