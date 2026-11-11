#!/usr/bin/env python3
"""Run the packaged app engine in an isolated temporary source tree."""
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PAYLOAD = None
DEPENDENCIES = ['httpx>=0.27.0', 'curl-cffi>=0.7.0', 'rich>=13.7.0', 'typer>=0.12.0',
                'platformdirs>=4.0.0', 'markdownify>=0.11.6', 'beautifulsoup4>=4.12.0', 'lxml>=5.0.0']


def execute(root):
    uv = shutil.which('uv')
    if not uv:
        message = '需要先安装 uv，再运行微探命令。'
        if '--json' in sys.argv:
            print(json.dumps({'ok': False, 'command': 'doctor', 'error': {'code': 'uv_missing', 'message': message}}, ensure_ascii=False))
        else:
            print(message, file=sys.stderr)
        return 3
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join([str(root/'agent-harness/src'), str(root/'vendor/wcx')])
    env['LOV_WXMP_PROJECT_ROOT'] = str(root)
    args = [uv, 'run', '--no-project', '--quiet', '--python', '>=3.10']
    for dependency in DEPENDENCIES:
        args.extend(['--with', dependency])
    args += ['python', '-m', 'lov_wxmp_cli', *sys.argv[1:]]
    return subprocess.call(args, env=env)


def main():
    if PAYLOAD is None:
        return execute(Path(__file__).resolve().parents[1]/'runtime')
    with tempfile.TemporaryDirectory(prefix='wxmp-runtime-') as temp:
        root = Path(temp)
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD))) as archive:
            for item in archive.infolist():
                target = (root/item.filename).resolve()
                if root.resolve() not in target.parents:
                    raise ValueError('invalid runtime path')
            archive.extractall(root)
        return execute(root)


if __name__ == '__main__':
    raise SystemExit(main())
