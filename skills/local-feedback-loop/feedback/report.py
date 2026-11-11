"""Build a private self-contained dashboard from the current database snapshot."""
import json
import os
import tempfile
from pathlib import Path
from .store import now, stats

ROOT = Path(__file__).resolve().parents[1]


def write_private(path, text):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.report-')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def render(store):
    events = store.snapshot()
    payload = {'generated_at': now(), 'events': events, 'stats': stats(events)}
    # Embedded JSON must never terminate its script element.
    data = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = (ROOT / 'assets/dashboard.html').read_text()
    output = store.directory / 'dashboard.html'
    write_private(output, template.replace('__FEEDBACK_DATA__', data))
    # Only one current report: deletion cannot leave older generated exports behind here.
    return str(output)
