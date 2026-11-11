"""Read the app's native cache and reuse its maintained wcx engine."""
from __future__ import annotations

import csv
import hashlib
import importlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class BackendError(RuntimeError):
    def __init__(self, code, message, exit_code=4, hint=''):
        super().__init__(message)
        self.code, self.exit_code, self.hint = code, exit_code, hint


def load_spec():
    return json.loads(Path(__file__).with_name('cli_spec.json').read_text())


def project_root(spec, explicit=None):
    configured = explicit or os.environ.get('LOV_WXMP_PROJECT_ROOT') or os.environ.get('LOV_CLI_PROJECT_ROOT')
    return Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[3]


def engine(spec, explicit=None):
    expected = project_root(spec, explicit) / 'vendor/wcx/wcx'
    if not (expected / 'cli.py').is_file():
        raise BackendError('project_missing', '未找到微探项目。', 3, '使用 --project-root 指定项目目录。')
    try:
        from wcx import cache, config, exporters
        import wcx
        if Path(wcx.__file__).resolve().parent != expected.resolve():
            raise BackendError('backend_mismatch', '采集引擎与当前项目不一致。', 3, '重新运行 agent-harness/scripts/install.sh。')
        for name in ('httpx', 'curl_cffi', 'typer', 'rich', 'markdownify', 'bs4', 'lxml'):
            importlib.import_module(name)
    except ImportError as exc:
        raise BackendError('backend_missing', '采集引擎尚未安装完整。', 3, '运行 agent-harness/scripts/install.sh。') from exc
    return cache, config, exporters


def database(config, explicit=None):
    value = explicit or os.environ.get('LOV_WXMP_DB')
    return Path(value).expanduser().resolve() if value else config.CACHE_DB


@contextmanager
def readonly(path):
    if not path.is_file():
        raise BackendError('cache_missing', '尚无本地文章缓存。', 3, '先在微探采集文章，或用 --db 选择已有缓存。')
    conn = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        yield conn
    finally:
        conn.close()


def doctor(spec, explicit_root=None, db=None):
    _, config, _ = engine(spec, explicit_root)
    path = database(config, db)
    if path.exists():
        with readonly(path) as conn:
            conn.execute('SELECT aid, fakeid, title, content_md FROM articles LIMIT 0')
            conn.execute('SELECT fakeid, nickname FROM accounts LIMIT 0')
    return {'ready': True, 'backend': 'wcx', 'project_root': str(project_root(spec, explicit_root)),
            'database': str(path), 'cache_exists': path.is_file(), 'network_checked': False}


def accounts(conn, query=None):
    rows = conn.execute('''SELECT a.*, COUNT(r.aid) AS article_count FROM accounts a
        LEFT JOIN articles r ON r.fakeid=a.fakeid GROUP BY a.fakeid
        ORDER BY a.updated_at DESC, a.fakeid''').fetchall()
    if query:
        query = query.casefold()
        rows = [r for r in rows if any(query in (r[k] or '').casefold() for k in ('nickname', 'alias', 'fakeid'))]
    return rows


def select_account(conn, value):
    rows = conn.execute('SELECT * FROM accounts WHERE fakeid=?', (value,)).fetchall()
    if not rows:
        rows = [r for r in conn.execute('SELECT * FROM accounts')
                if value.casefold() in ((r['nickname'] or '').casefold(), (r['alias'] or '').casefold())]
    if not rows:
        raise BackendError('account_missing', '本地未找到该公众号。', 4, '先用 accounts 查看公众号。')
    if len(rows) != 1:
        raise BackendError('ambiguous_account', '有多个同名公众号，请精确选择。', 5, '使用 JSON 结果中的公众号选择值。')
    return rows[0]


def article_rows(conn, account, query=None, limit=None, offset=0):
    where, params = 'fakeid=?', [account['fakeid']]
    if query:
        where += " AND (instr(lower(title),lower(?))>0 OR instr(lower(COALESCE(content_md,'')),lower(?))>0)"
        params += [query, query]
    total = conn.execute(f'SELECT count(*) FROM articles WHERE {where}', params).fetchone()[0]
    rows = conn.execute(f'SELECT * FROM articles WHERE {where} ORDER BY create_time DESC, aid LIMIT ? OFFSET ?',
                        params + [limit if limit is not None else -1, offset]).fetchall()
    return rows, total


def summary(row):
    result = dict(row)
    md, html = result.pop('content_md', ''), result.pop('content_html', '')
    result['has_content'] = bool((md or '').strip() or (html or '').strip())
    return result


def validate_values(values):
    limit = values.get('limit')
    if limit is not None and not 1 <= limit <= 100000:
        raise BackendError('invalid_limit', '篇数应为 1 到 100000。', 2)
    if values.get('offset', 0) < 0:
        raise BackendError('invalid_offset', '起始位置不能为负数。', 2)
    for key in ('account', 'article', 'query', 'nickname'):
        if values.get(key) is not None and not values[key].strip():
            raise BackendError('empty_input', '请输入有效的名称或选择值。', 2)


def export_rows(exporters, account, rows, values):
    out = Path(values['out']).expanduser().absolute()
    if out.exists() or out.is_symlink():
        raise BackendError('output_exists', '导出目录已存在，请使用新目录。', 5)
    formats = ['md', 'json', 'csv'] if values['format'] == 'all' else [values['format']]
    if values.get('dry_run'):
        return {'dry_run': True, 'out': str(out), 'article_count': len(rows), 'formats': formats, 'body': values['body']}
    # Reserve the final directory exclusively; never overwrite a concurrent export.
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        out.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise BackendError('output_exists', '导出目录已存在，请使用新目录。', 5) from exc
    try:
        with tempfile.TemporaryDirectory(prefix='.wxmp-export-', dir=out.parent) as tmp:
            staging = Path(tmp)
            exporters.export_index(rows, account, staging, fmt=values['format'])
            if values['body'] != 'none':
                writer = exporters.export_article_markdown if values['body'] == 'md' else exporters.export_article_html
                for row in rows:
                    # wcx names files by date/title; separate article folders prevent collisions.
                    key = hashlib.sha256(row['aid'].encode()).hexdigest()
                    path = writer(row, staging / 'articles' / key)
                    text = path.read_text(encoding='utf-8')
                    content = row['content_md' if values['body'] == 'md' else 'content_html']
                    if not text.strip() or (content and content not in text):
                        raise BackendError('export_invalid', '正文导出验证失败。')
            if 'json' in formats:
                payload = json.loads((staging/'index.json').read_text())
                if payload['articles'] != [dict(r) for r in rows] or payload['account'] != dict(account):
                    raise BackendError('export_invalid', '文章索引验证失败。')
            if 'csv' in formats:
                with (staging/'index.csv').open(encoding='utf-8-sig', newline='') as stream:
                    if len(list(csv.reader(stream))) != len(rows)+1:
                        raise BackendError('export_invalid', '表格导出验证失败。')
            if 'md' in formats and not (staging/'index.md').read_text(encoding='utf-8').strip():
                raise BackendError('export_invalid', '文章索引为空。')
            files = []
            for path in sorted(staging.rglob('*')):
                if path.is_file():
                    raw = path.read_bytes()
                    files.append({'path': str(path.relative_to(staging)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
            manifest = {'schema': 'lov-wxmp-export/v1', 'article_count': len(rows), 'files': files}
            (staging/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            for item in staging.iterdir():
                item.rename(out/item.name)
            for item in files:
                if hashlib.sha256((out/item['path']).read_bytes()).hexdigest() != item['sha256']:
                    raise BackendError('export_invalid', '导出文件回读验证失败。')
        return {'out': str(out), 'article_count': len(rows), 'files': files, 'manifest': str(out/'manifest.json')}
    except BaseException:
        shutil.rmtree(out)
        raise


def network_run(spec, argv):
    # Upstream exceptions can contain private request URLs; never echo raw stderr.
    try:
        result = subprocess.run([sys.executable, '-m', 'wcx.cli', *argv], capture_output=True,
                                text=True, shell=False, timeout=spec['backend']['timeout_seconds'])
    except subprocess.TimeoutExpired as exc:
        raise BackendError('backend_timeout', '采集等待超时，已保存的文章会保留。', 4, '用 articles 检查进度后再继续。') from exc
    if result.returncode:
        raw = result.stderr + result.stdout
        if any(word in raw for word in ('尚未登录', '认证失败', '登录已', '登录失效')):
            raise BackendError('auth_required', '请先在微探扫码登录。', 4)
        if any(word in raw for word in ('200013', '风控', '冷却', '本地保护')):
            raise BackendError('cooldown', '当前需要暂停采集，已保存的文章会保留。', 4, '稍后重试。')
        raise BackendError('backend_failed', '采集未完成，已保存的文章会保留。', 4, '用 status 检查登录配置，用 articles 查看已保存内容。')
    payloads = []
    for line in result.stdout.splitlines():
        if line.startswith('__WXMP_') or not line.strip():
            continue
        try:
            payloads.append(json.loads(line))
        except ValueError:
            continue
    if not payloads:
        raise BackendError('backend_invalid', '未收到可读取的采集结果。')
    return payloads[-1]


def validate_fetch_result(payload, account):
    if (not isinstance(payload, dict) or payload.get('fakeid') != account['fakeid']
            or not isinstance(payload.get('scanned'), int)):
        raise BackendError('backend_invalid', '采集结果与所选公众号不一致。')
    if payload.get('article_index_status') != 'ready':
        raise BackendError('index_unavailable', '暂时无法取得文章列表，已有缓存会保留。', 4, '稍后再试，或在微探导入文章链接。')


def run_command(spec, command, values, explicit_root=None):
    validate_values(values)
    _, config, exporters = engine(spec, explicit_root)
    path = database(config, values.get('db'))
    name = command['name']
    if name == 'status':
        try:
            creds = config.load_credentials()
            configured = bool(creds and creds.token and creds.cookie)
        except (ValueError, TypeError, AttributeError):
            configured = False
        result = {'credentials_configured': configured, 'session_validity': 'unchecked', 'database': str(path),
                  'cache_exists': path.is_file(), 'accounts': 0, 'articles': 0}
        if path.is_file():
            with readonly(path) as conn:
                for table in ('accounts', 'articles'):
                    result[table] = conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
        return result
    if name == 'search':
        payload = network_run(spec, ['search-accounts-json', values['query']])
        if not isinstance(payload, list):
            raise BackendError('backend_invalid', '公众号搜索结果无法读取。')
        return {'accounts': payload}
    if name == 'fetch':
        if path.resolve() != config.CACHE_DB.resolve():
            raise BackendError('alternate_cache', '采集只写入微探默认缓存。', 2, '移除 --db 和 LOV_WXMP_DB 后重试。')
        if values['limit'] > 500:
            raise BackendError('invalid_limit', '单次采集篇数应为 1 到 500。', 2)
        if values.get('date'):
            try:
                datetime.strptime(values['date'], '%Y-%m-%d')
                if values['mode'] != 'audit' or len(values['date']) != 10:
                    raise ValueError()
            except ValueError as exc:
                raise BackendError('invalid_date', '日期应为 YYYY-MM-DD，且仅用于回查。', 2) from exc
        if values.get('nickname'):
            account = {'fakeid': values['account'], 'nickname': values['nickname'], 'alias': '', 'signature': '', 'round_head_img': ''}
        else:
            with readonly(path) as conn:
                account = dict(select_account(conn, values['account']))
        if values.get('dry_run'):
            return {'dry_run': True, 'account': account, 'limit': values['limit'], 'mode': values['mode'], 'with_content': values['content']}
        argv = ['fetch-selected-account-json', json.dumps(account, ensure_ascii=False), str(values['limit']),
                '1' if values['content'] else '0', '--mode', values['mode']]
        if values.get('date'):
            argv += ['--audit-date', values['date']]
        payload = network_run(spec, argv)
        validate_fetch_result(payload, account)
        with readonly(path) as conn:
            saved = select_account(conn, account['fakeid'])
            _, total = article_rows(conn, saved)
        return {'result': payload, 'cached_articles': total, 'account': dict(saved)}
    if name == 'accounts' and not path.exists():
        return {'accounts': [], 'cache_exists': False}
    with readonly(path) as conn:
        if name == 'accounts':
            return {'accounts': [dict(r) for r in accounts(conn, values.get('query'))], 'cache_exists': True}
        if name == 'article':
            row = conn.execute('SELECT * FROM articles WHERE aid=?', (values['article'],)).fetchone()
            if row is None:
                raise BackendError('article_missing', '本地未找到该文章。', 4)
            return dict(row)
        account = select_account(conn, values['account'])
        rows, total = article_rows(conn, account, values.get('query'), values.get('limit'), values.get('offset', 0))
        if name == 'articles':
            return {'account': dict(account), 'articles': [summary(r) for r in rows], 'total': total, 'offset': values['offset']}
        if name == 'export':
            return export_rows(exporters, account, rows, values)
    raise BackendError('unknown_command', '不支持此命令。', 2)
