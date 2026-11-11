#!/usr/bin/env python3
"""Local-only feedback CLI. No automatic history scan or rule rewriting."""
import argparse
import fcntl
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from feedback.store import Store, stats
from feedback.report import render

DEFAULT = Path.home() / '.local' / 'share' / 'valiora-feedback'


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, default=DEFAULT)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('report')
    sub.add_parser('stats')
    sub.add_parser('list')
    sub.add_parser('verify')
    add = sub.add_parser('add')
    for name in ('project', 'session', 'evidence', 'channel', 'polarity', 'kind'):
        add.add_argument('--' + name, required=True)
    add.add_argument('--source-id', default='')
    add.add_argument('--host', default='codex')
    add.add_argument('--confidence', type=float, default=0.8)
    add.add_argument('--rating', type=int)
    add.add_argument('--scope', default='task')
    add.add_argument('--target', default='')
    update = sub.add_parser('update')
    update.add_argument('--id', required=True)
    update.add_argument('--status', required=True)
    update.add_argument('--action', default='')
    update.add_argument('--verification', default='')
    delete = sub.add_parser('delete')
    delete.add_argument('--id', required=True)
    delete.add_argument('--confirm', action='store_true')
    args = parser.parse_args()
    args.store.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Also serialize mutation+report, so concurrent CLI runs never publish a stale report.
    with (args.store / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        store = Store(args.store)
        options = vars(args).copy()
        for key in ('store', 'command'):
            options.pop(key)
        if args.command == 'add':
            result = store.add(**options)
        elif args.command == 'update':
            store.update(args.id, args.status, args.action, args.verification)
            result = {'ok': True, 'id': args.id}
        elif args.command == 'delete':
            if not args.confirm:
                raise ValueError('真实删除不可撤销；仅在用户明确要求删除时添加 --confirm')
            store.delete(args.id)
            result = {'ok': True, 'deleted': args.id}
        elif args.command == 'list':
            result = store.snapshot()
        elif args.command == 'stats':
            result = stats(store.snapshot())
        elif args.command == 'verify':
            result = store.verify()
        else:
            result = {'ok': True}
        report = render(store)
        print(json.dumps({'result': result, 'dashboard': report}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, AssertionError) as error:
        print('错误：' + str(error), file=sys.stderr)
        sys.exit(2)
