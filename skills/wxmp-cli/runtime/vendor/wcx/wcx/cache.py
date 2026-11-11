"""SQLite cache for articles — avoids re-fetching."""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import CACHE_DB, ensure_dirs


SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    fakeid TEXT PRIMARY KEY,
    nickname TEXT NOT NULL,
    alias TEXT,
    signature TEXT,
    round_head_img TEXT,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS articles (
    aid TEXT PRIMARY KEY,
    fakeid TEXT NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    digest TEXT,
    cover TEXT,
    author TEXT,
    create_time INTEGER NOT NULL,
    update_time INTEGER,
    article_type INTEGER,
    copyright_type INTEGER,
    content_html TEXT,
    content_md TEXT,
    fetched_at INTEGER NOT NULL,
    FOREIGN KEY (fakeid) REFERENCES accounts(fakeid)
);

CREATE INDEX IF NOT EXISTS idx_articles_fakeid ON articles(fakeid);
CREATE INDEX IF NOT EXISTS idx_articles_create_time ON articles(create_time DESC);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_dirs()
    conn = sqlite3.connect(CACHE_DB)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _ensure_article_metadata_columns(conn)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_account(conn: sqlite3.Connection, account: dict) -> None:
    conn.execute(
        """
        INSERT INTO accounts (fakeid, nickname, alias, signature, round_head_img, updated_at)
        VALUES (:fakeid, :nickname, :alias, :signature, :round_head_img, :updated_at)
        ON CONFLICT(fakeid) DO UPDATE SET
            nickname = COALESCE(NULLIF(TRIM(excluded.nickname), ''), accounts.nickname),
            alias = COALESCE(NULLIF(TRIM(excluded.alias), ''), accounts.alias),
            signature = COALESCE(NULLIF(TRIM(excluded.signature), ''), accounts.signature),
            round_head_img = COALESCE(
                NULLIF(TRIM(excluded.round_head_img), ''),
                accounts.round_head_img
            ),
            updated_at = excluded.updated_at
        """,
        {**account, "updated_at": int(time.time())},
    )


def _ensure_article_metadata_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(articles)")}
    if "article_type" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN article_type INTEGER")
    if "copyright_type" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN copyright_type INTEGER")


def upsert_article(conn: sqlite3.Connection, article: dict) -> None:
    """Insert article index data while preserving richer cached metadata."""
    conn.execute(
        """
        INSERT INTO articles
            (aid, fakeid, title, link, digest, cover, author,
             create_time, update_time, article_type, copyright_type,
             content_html, content_md, fetched_at)
        VALUES
            (:aid, :fakeid, :title, :link, :digest, :cover, :author,
             :create_time, :update_time, :article_type, :copyright_type,
             :content_html, :content_md, :fetched_at)
        ON CONFLICT(aid) DO UPDATE SET
            title = excluded.title,
            link = excluded.link,
            digest = excluded.digest,
            cover = excluded.cover,
            update_time = excluded.update_time,
            article_type = COALESCE(excluded.article_type, articles.article_type),
            copyright_type = COALESCE(
                excluded.copyright_type,
                articles.copyright_type
            )
        """,
        {
            "content_html": None,
            "content_md": None,
            "article_type": None,
            "copyright_type": None,
            **article,
            "fetched_at": int(time.time()),
        },
    )


def set_article_content(
    conn: sqlite3.Connection, aid: str, html: str, md: str
) -> None:
    conn.execute(
        "UPDATE articles SET content_html = ?, content_md = ? WHERE aid = ?",
        (html, md, aid),
    )


def list_articles(
    conn: sqlite3.Connection, fakeid: str, limit: int | None = None
) -> list[sqlite3.Row]:
    sql = "SELECT * FROM articles WHERE fakeid = ? ORDER BY create_time DESC"
    params: tuple = (fakeid,)
    if limit:
        sql += " LIMIT ?"
        params = (fakeid, limit)
    return conn.execute(sql, params).fetchall()


def get_account(conn: sqlite3.Connection, fakeid: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM accounts WHERE fakeid = ?", (fakeid,)).fetchone()
