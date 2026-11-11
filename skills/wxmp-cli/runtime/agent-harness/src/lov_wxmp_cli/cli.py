"""Task-oriented commands over the wxmp app backend."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from datetime import datetime

from . import __version__
from .backend import BackendError, doctor, load_spec, project_root, run_command


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise BackendError('invalid_arguments', '命令参数不完整或格式不正确。', 2, '使用 --help 查看参数说明。')


def parser_for(spec):
    parser = Parser(prog=spec['command'], description=spec['description'])
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--json', dest='json_output', action='store_true', help='输出供脚本使用的 JSON')
    parser.add_argument('--project-root', help='微探项目目录')
    parser.add_argument('--db', help='只读查询或导出的缓存路径')
    children = parser.add_subparsers(dest='command')
    for name, desc in [('doctor', '检查运行依赖'), ('info', '查看版本与项目'), ('capabilities', '查看支持的操作')]:
        children.add_parser(name, help=desc)
    for command in spec['commands']:
        child = children.add_parser(command['name'], help=command['description'], description=command['description'])
        for p in command['parameters']:
            kwargs = {'help': p.get('description', '')}
            dest = p['name'].replace('-', '_')
            if p['kind'] == 'flag':
                child.add_argument(*p['flags'], dest=dest, action='store_true', **kwargs)
                continue
            kwargs['type'] = {'int': int, 'float': float}.get(p.get('type'), str)
            for key in ('default', 'choices'):
                if key in p:
                    kwargs[key] = p[key]
            if p['kind'] == 'positional':
                if not p.get('required'):
                    kwargs['nargs'] = '?'
                child.add_argument(dest, **kwargs)
            else:
                child.add_argument(*p['flags'], dest=dest, required=p.get('required', False), **kwargs)
    return parser


def human(command, data):
    if command == 'doctor':
        print('运行依赖已就绪。' + (' 已找到本地文章缓存。' if data['cache_exists'] else ' 尚无本地文章缓存。'))
    elif command == 'info':
        print(f"微探命令行 {data['version']}\n项目：{data['project_root']}")
    elif command == 'capabilities':
        for item in data['builtins'] + data['commands']:
            print(f"{item['name']:15} {item.get('description', '')}")
    elif command == 'status':
        print('已保存登录配置（未在线验证）。' if data['credentials_configured'] else '尚无有效登录配置，请在微探扫码登录。')
        print(f"缓存：{data['accounts']} 个公众号，{data['articles']} 篇文章。")
    elif command in ('accounts', 'search'):
        for row in data['accounts']:
            print(row['nickname'] + (f" · {row['article_count']} 篇" if 'article_count' in row else ''))
        if not data['accounts']:
            print('暂无公众号。')
    elif command == 'articles':
        print(f"{data['account']['nickname']} · 共 {data['total']} 篇匹配文章")
        for row in data['articles']:
            day = datetime.fromtimestamp(row['create_time']).strftime('%Y-%m-%d') if row['create_time'] else '日期未知'
            print(f"{day}  {row['title']}" + ('  [正文已保存]' if row['has_content'] else ''))
    elif command == 'article':
        print(f"{data['title']}\n\n{data.get('content_md') or data.get('content_html') or '正文尚未保存。'}")
    elif data.get('dry_run'):
        print('预览完成，未执行采集或写入文件。')
        if 'out' in data:
            print(f"拟导出 {data['article_count']} 篇文章至 {data['out']}")
        else:
            print(f"拟采集 {data['account']['nickname']}，最多 {data['limit']} 篇。")
    elif command == 'export':
        print(f"已导出并验证 {data['article_count']} 篇文章：{data['out']}")
    elif command == 'fetch':
        print(f"采集结束，{data['account']['nickname']} 当前缓存 {data['cached_articles']} 篇文章。")


def failure(command, error, json_output):
    context = hashlib.sha256((error.code + str(error)).encode()).hexdigest()[:8]
    payload = {'ok': False, 'command': command, 'error': {'code': error.code, 'message': str(error),
               'context_id': 'cli-' + context, 'hint': error.hint}}
    if json_output:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(str(error) + (' ' + error.hint if error.hint else ''), file=sys.stderr)
    return error.exit_code


def main(argv=None):
    raw = list(sys.argv[1:] if argv is None else argv)
    json_output, command = '--json' in raw, 'help'
    started = time.monotonic()
    try:
        spec = load_spec()
        parser = parser_for(spec)
        if not raw:
            parser.print_help()
            return 0
        args = parser.parse_args(raw)
        command = args.command
        if command is None:
            raise BackendError('missing_command', '请选择要执行的命令。', 2, '使用 --help 查看支持的操作。')
        if command == 'doctor':
            data = doctor(spec, args.project_root, args.db)
        elif command == 'info':
            data = {'name': spec['name'], 'command': spec['command'], 'version': spec['version'],
                    'status': spec['status'], 'project_root': str(project_root(spec, args.project_root)), 'backend': spec['backend']}
        elif command == 'capabilities':
            data = {'builtins': [{'name': n, 'mutates': False} for n in ('doctor', 'info', 'capabilities')],
                    'commands': spec['commands'], 'unsupported': spec.get('unsupported', [])}
        else:
            selected = next(c for c in spec['commands'] if c['name'] == command)
            data = run_command(spec, selected, vars(args), args.project_root)
        if json_output:
            print(json.dumps({'ok': True, 'command': command, 'data': data,
                              'meta': {'duration_ms': round((time.monotonic()-started)*1000)}}, ensure_ascii=False))
        else:
            human(command, data)
        return 0
    except BackendError as exc:
        return failure(command, exc, json_output)
    except sqlite3.Error:
        return failure(command, BackendError('cache_error', '无法读取文章缓存。', 4, '用 doctor 检查缓存路径与文件状态。'), json_output)
    except OSError:
        return failure(command, BackendError('io_error', '无法完成文件读写。', 4, '检查路径权限和可用空间。'), json_output)
    except (ValueError, TypeError):
        return failure(command, BackendError('invalid_data', '本地数据或采集结果无法读取。', 4, '用 doctor 检查运行依赖。'), json_output)
    except KeyboardInterrupt:
        return failure(command, BackendError('interrupted', '操作已中断，已采集的文章会保留。', 130), json_output)


if __name__ == '__main__':
    raise SystemExit(main())
