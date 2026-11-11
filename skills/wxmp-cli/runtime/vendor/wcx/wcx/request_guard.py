"""Persistent request pacing for authenticated WeChat endpoints.

The desktop app starts a fresh wcx process for searches and fetches, so an
in-memory delay is not enough. This guard stores reservations and cooldowns in
SQLite, making the pacing rule shared by every sidecar process.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


DEFAULT_MIN_INTERVAL_SECONDS = 15.0
DEFAULT_COOLDOWN_SECONDS = 60.0 * 60.0


@dataclass(frozen=True)
class RequestCooldown:
    retry_at: float


class RequestCooldownError(RuntimeError):
    def __init__(self, retry_at: float):
        super().__init__("authenticated WeChat requests are cooling down")
        self.retry_at = retry_at


class RequestGuard:
    def __init__(
        self,
        db_path: Path,
        key: str,
        *,
        min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        clock: Callable[[], float] = time.time,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.db_path = db_path
        self.key = key
        self.min_interval_seconds = max(
            float(min_interval_seconds), DEFAULT_MIN_INTERVAL_SECONDS
        )
        self.cooldown_seconds = max(
            float(cooldown_seconds), DEFAULT_COOLDOWN_SECONDS
        )
        self._clock = clock
        self._sleeper = sleeper

    def acquire(self) -> None:
        """Reserve the next request slot, waiting when another process used it."""
        now = self._clock()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            next_allowed_at, cooldown_until = self._read_state(conn)
            if cooldown_until > now:
                conn.commit()
                raise RequestCooldownError(cooldown_until)

            reserved_at = max(now, next_allowed_at)
            conn.execute(
                """
                INSERT INTO request_guard (guard_key, next_allowed_at, cooldown_until)
                VALUES (?, ?, 0)
                ON CONFLICT(guard_key) DO UPDATE SET
                    next_allowed_at = excluded.next_allowed_at
                """,
                (self.key, reserved_at + self.min_interval_seconds),
            )
            conn.commit()

        wait_seconds = reserved_at - now
        if wait_seconds > 0:
            self._sleeper(wait_seconds)

    def check_cooldown(self) -> None:
        """Reject an operation that is cooling down without reserving a slot."""
        now = self._clock()
        with self._connect() as conn:
            _, cooldown_until = self._read_state(conn)
        if cooldown_until > now:
            raise RequestCooldownError(cooldown_until)

    def activate_cooldown(self) -> RequestCooldown:
        """Stop further requests after WeChat reports frequency control."""
        now = self._clock()
        retry_at = now + self.cooldown_seconds
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            next_allowed_at, current_cooldown = self._read_state(conn)
            retry_at = max(retry_at, current_cooldown)
            conn.execute(
                """
                INSERT INTO request_guard (guard_key, next_allowed_at, cooldown_until)
                VALUES (?, ?, ?)
                ON CONFLICT(guard_key) DO UPDATE SET
                    next_allowed_at = excluded.next_allowed_at,
                    cooldown_until = excluded.cooldown_until
                """,
                (self.key, max(next_allowed_at, retry_at), retry_at),
            )
            conn.commit()
        return RequestCooldown(retry_at=retry_at)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS request_guard (
                guard_key TEXT PRIMARY KEY,
                next_allowed_at REAL NOT NULL DEFAULT 0,
                cooldown_until REAL NOT NULL DEFAULT 0
            )
            """
        )
        return conn

    def _read_state(self, conn: sqlite3.Connection) -> tuple[float, float]:
        row = conn.execute(
            "SELECT next_allowed_at, cooldown_until FROM request_guard WHERE guard_key = ?",
            (self.key,),
        ).fetchone()
        if row is None:
            return 0.0, 0.0
        return float(row[0]), float(row[1])
