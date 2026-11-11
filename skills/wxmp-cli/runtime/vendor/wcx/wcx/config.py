"""Configuration: token/cookie persistence in ~/.config/wcx/."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "wcx"
CONFIG_DIR = Path(user_config_dir(APP_NAME))
DATA_DIR = Path(user_data_dir(APP_NAME))
CONFIG_PATH = CONFIG_DIR / "config.json"
CACHE_DB = DATA_DIR / "cache.db"
REQUEST_GUARD_DB = DATA_DIR / "request-guard.db"
ARTICLE_LIST_CACHE_DB = DATA_DIR / "article-list-cache.db"
OWN_BIZUIN_COOKIE_NAMES = ("bizuin", "data_bizuin", "slave_bizuin")


@dataclass
class Credentials:
    token: str
    cookie: str
    last_login_at: int | None = None
    account: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def own_bizuin(credentials: Credentials) -> str:
    account = credentials.account or {}
    account_bizuin = str(account.get("bizuin") or "").strip()
    if account_bizuin.isdigit():
        return account_bizuin

    cookie_values: dict[str, str] = {}
    for part in credentials.cookie.split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name in OWN_BIZUIN_COOKIE_NAMES:
            cookie_values[name] = value.strip().strip('"')

    for name in OWN_BIZUIN_COOKIE_NAMES:
        value = cookie_values.get(name, "")
        if value.isdigit():
            return value
    return ""


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_credentials() -> Optional[Credentials]:
    if not CONFIG_PATH.exists():
        return None
    data = json.loads(CONFIG_PATH.read_text())
    if "token" not in data or "cookie" not in data:
        return None
    last_login_at = data.get("last_login_at")
    if not isinstance(last_login_at, int):
        last_login_at = None
    account = data.get("account")
    if not isinstance(account, dict):
        account = None
    return Credentials(
        token=data["token"],
        cookie=data["cookie"],
        last_login_at=last_login_at,
        account=account,
    )


def save_credentials(creds: Credentials) -> None:
    ensure_dirs()
    CONFIG_PATH.write_text(json.dumps(creds.to_dict(), ensure_ascii=False, indent=2))
    CONFIG_PATH.chmod(0o600)


def clear_credentials() -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
