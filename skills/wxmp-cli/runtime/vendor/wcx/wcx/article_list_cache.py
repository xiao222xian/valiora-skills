"""Short-lived cache for successful article-list responses keyed by account ID."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Callable


ARTICLE_LIST_CACHE_TTL_SECONDS = 5 * 60

SCHEMA = """
CREATE TABLE IF NOT EXISTS article_list_pages (
    fakeid TEXT NOT NULL,
    begin_offset INTEGER NOT NULL,
    page_count INTEGER NOT NULL,
    payload TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    PRIMARY KEY (fakeid, begin_offset, page_count)
);
"""


class ArticleListCache:
    """Persist only successful ID-addressed list responses for a short time."""

    def __init__(
        self,
        path: Path,
        *,
        ttl_seconds: float = ARTICLE_LIST_CACHE_TTL_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = Path(path)
        self.ttl_seconds = ttl_seconds
        self.clock = clock

    def get(self, fakeid: str, begin: int, count: int) -> dict | None:
        account_id = fakeid.strip()
        if not account_id:
            return None
        try:
            with closing(self._connect()) as conn:
                row = conn.execute(
                    """
                    SELECT payload, fetched_at
                    FROM article_list_pages
                    WHERE fakeid = ? AND begin_offset = ? AND page_count = ?
                    """,
                    (account_id, begin, count),
                ).fetchone()
                if row is None:
                    return None
                if self.clock() - float(row[1]) > self.ttl_seconds:
                    conn.execute(
                        """
                        DELETE FROM article_list_pages
                        WHERE fakeid = ? AND begin_offset = ? AND page_count = ?
                        """,
                        (account_id, begin, count),
                    )
                    conn.commit()
                    return None
                try:
                    payload = json.loads(row[0])
                except (TypeError, ValueError):
                    payload = None
                if isinstance(payload, dict):
                    return payload
                conn.execute(
                    """
                    DELETE FROM article_list_pages
                    WHERE fakeid = ? AND begin_offset = ? AND page_count = ?
                    """,
                    (account_id, begin, count),
                )
                conn.commit()
                return None
        except (OSError, sqlite3.Error):
            return None

    def put(self, fakeid: str, begin: int, count: int, payload: dict) -> None:
        account_id = fakeid.strip()
        if not account_id:
            return
        try:
            with closing(self._connect()) as conn:
                conn.execute(
                    """
                    INSERT INTO article_list_pages
                        (fakeid, begin_offset, page_count, payload, fetched_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(fakeid, begin_offset, page_count) DO UPDATE SET
                        payload = excluded.payload,
                        fetched_at = excluded.fetched_at
                    """,
                    (
                        account_id,
                        begin,
                        count,
                        json.dumps(
                            payload,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        self.clock(),
                    ),
                )
                conn.commit()
        except (OSError, sqlite3.Error, TypeError, ValueError):
            return

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=5)
        conn.executescript(SCHEMA)
        return conn
