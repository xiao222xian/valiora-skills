"""Local feedback storage. Inspired by Lovstudio feedback-loop 0.3.0 (MIT)."""
import hashlib
import os
import re
import sqlite3
import statistics
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

STATUSES = {'captured', 'triaged', 'change-proposed', 'change-applied', 'verified', 'declined', 'deferred'}
SCOPES = {'task', 'skill', 'reference', 'root-prompt'}
SCHEMA = '''
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, ts TEXT NOT NULL, project TEXT NOT NULL, session TEXT NOT NULL,
 host TEXT NOT NULL, source_id TEXT NOT NULL, channel TEXT NOT NULL, polarity TEXT NOT NULL,
 kind TEXT NOT NULL, confidence REAL NOT NULL, rating INTEGER, evidence TEXT NOT NULL,
 scope TEXT NOT NULL, target TEXT NOT NULL, dedup TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS event_dedup ON events(dedup, ts);
CREATE TABLE IF NOT EXISTS outcomes (
 id INTEGER PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
 ts TEXT NOT NULL, status TEXT NOT NULL, action TEXT NOT NULL, verification TEXT NOT NULL);
PRAGMA user_version=1;
'''


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('时间必须包含时区')
    return dt.astimezone(timezone.utc)


def redact(value, limit=240):
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    patterns = [
        r'(?i)\b(?:password|passwd|token|secret|api[_ -]?key)\s*[:=]\s*\S+',
        r'\b(?:sk|pk|ghp|gho|ghs|xox[baprs])[-_][\w-]{8,}',
        r'(?i)\bBearer\s+\S+',
        r'https?://\S+',
        r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
        r'(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)',
        r'(?<!\d)\d{17}[\dXx](?!\w)',
        r'(?<!\d)\d{13,19}(?!\d)',
        r'/Users/[^\s,;，；]+',
        r'\b[A-Za-z0-9+/=_-]{40,}\b',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '[已遮蔽]', text)
    return text[:limit]


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.directory.chmod(0o700)
        self.path = self.directory / 'feedback.sqlite3'
        self.path.touch(mode=0o600, exist_ok=True)
        self.path.chmod(0o600)
        with self.connect() as con:
            version = con.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('未知账本版本，停止以免覆盖')
            con.execute('PRAGMA journal_mode=WAL')
            con.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('PRAGMA secure_delete=ON')
        try:
            with con:
                yield con
        finally:
            con.close()

    def add(self, *, project, session, evidence, channel, polarity, kind,
            host='codex', source_id='', confidence=0.8, rating=None,
            scope='task', target='', ts=None):
        if channel not in {'explicit', 'passive'} or polarity not in {'positive', 'negative', 'mixed', 'neutral'}:
            raise ValueError('非法通道或极性')
        if kind not in {'praise', 'approval', 'dissatisfaction', 'error', 'preference', 'correction'}:
            raise ValueError('只记录评价或已确认问题；普通需求变更不落账')
        if not 0 <= confidence <= 1 or (channel == 'passive' and confidence >= 1):
            raise ValueError('被动推断置信度必须小于 1')
        if rating is not None and (channel != 'explicit' or rating not in range(1, 6)):
            raise ValueError('评分必须是用户明确给出的 1–5 分')
        if scope not in SCOPES or not project.strip() or not session.strip():
            raise ValueError('必须提供项目、会话和合法作用域')
        evidence = redact(evidence)
        if not evidence or evidence == '[已遮蔽]':
            raise ValueError('缺少可保留的反馈证据')
        date = timestamp(ts or now()).isoformat(timespec='microseconds')
        # Include project/host/channel to avoid conflating unrelated feedback.
        key = hashlib.sha256('\0'.join([host, project, session, source_id or evidence, kind, channel]).encode()).hexdigest()
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            previous = con.execute('SELECT id,ts FROM events WHERE dedup=? ORDER BY ts DESC', (key,)).fetchall()
            for row in previous:
                if source_id or abs((timestamp(date) - timestamp(row['ts'])).total_seconds()) <= 600:
                    return {'id': row['id'], 'duplicate': True}
            event_id = 'fb-' + uuid.uuid4().hex
            values = (event_id, date, redact(project, 80), session[:160], host[:30], source_id[:160],
                      channel, polarity, kind, confidence, rating, evidence, scope, redact(target, 160), key)
            con.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', values)
        return {'id': event_id, 'duplicate': False}

    def update(self, event_id, status, action='', verification='', ts=None):
        if status not in STATUSES:
            raise ValueError('非法处理状态')
        if status == 'verified' and not verification.strip():
            raise ValueError('标记已验证时必须提供验证证据')
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            event = con.execute('SELECT ts FROM events WHERE id=?', (event_id,)).fetchone()
            if not event:
                raise ValueError('事件不存在')
            date = timestamp(ts or now()).isoformat(timespec='microseconds')
            if timestamp(date) < timestamp(event['ts']):
                raise ValueError('处理时间早于反馈时间')
            con.execute('INSERT INTO outcomes(event_id,ts,status,action,verification) VALUES(?,?,?,?,?)',
                        (event_id, date, status, redact(action), redact(verification)))

    def snapshot(self):
        with self.connect() as con:
            con.execute('BEGIN')
            events = [dict(r) for r in con.execute('SELECT * FROM events ORDER BY ts DESC')]
            outcomes = [dict(r) for r in con.execute('SELECT * FROM outcomes ORDER BY ts,id')]
        by_id = {}
        for outcome in outcomes:
            by_id.setdefault(outcome['event_id'], []).append(outcome)
        for event in events:
            history = by_id.get(event['id'], [])
            latest = history[-1] if history else {}
            event['status'] = latest.get('status', 'captured')
            event['action'] = latest.get('action', '')
            event['verification'] = latest.get('verification', '')
            verified = next((o for o in history if o['status'] == 'verified'), None)
            event['first_verified'] = verified['ts'] if verified else None
            event['local_date'] = timestamp(event['ts']).astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d')
            event.pop('dedup')
        return events

    def delete(self, event_id):
        # No tombstone carrying the original evidence. Cascades remove outcomes.
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            if con.execute('DELETE FROM events WHERE id=?', (event_id,)).rowcount != 1:
                raise ValueError('事件不存在')
        with self.connect() as con:
            con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            con.execute('VACUUM')
            con.execute('PRAGMA wal_checkpoint(TRUNCATE)')

    def verify(self):
        with self.connect() as con:
            assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not con.execute('PRAGMA foreign_key_check').fetchall()
        return {'ok': True, 'events': len(self.snapshot())}


def stats(events):
    groups = {}
    for channel in ('explicit', 'passive'):
        subset = [e for e in events if e['channel'] == channel]
        groups[channel] = {'total': len(subset), 'positive_ratio':
                           sum(e['polarity'] == 'positive' for e in subset) / len(subset) if subset else None}
    durations = [(timestamp(e['first_verified']) - timestamp(e['ts'])).total_seconds() / 86400
                 for e in events if e['first_verified']]
    ratings = [e['rating'] for e in events if e['rating'] is not None]
    return {'total': len(events), 'channels': groups,
            'unresolved': sum(e['status'] not in {'verified', 'declined'} for e in events),
            'median_days_to_first_verification': statistics.median(durations) if durations else None,
            'rating_count': len(ratings), 'average_explicit_rating': statistics.mean(ratings) if ratings else None}
