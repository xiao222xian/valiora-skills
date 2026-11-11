#!/usr/bin/env python3
"""Per-chapter music: two 30 s Lyria 3 Clip takes per chapter through OpenRouter (google/lyria-3-clip-preview,
$0.04 per clip on 2026-10-12; say the price before running).

  python3 audio/gen_chapter_music.py --dry-run      # list what would be generated and the cost
  python3 audio/gen_chapter_music.py [chapter ...]  # missing files only

Brief: audio/chapters/briefs.json ("common" is appended to every chapter's line; the keys of "chapters" are the
chapter ids in src/timeline.ts). Take b asks for a different arrangement. Writes audio/chapters/<id>-<a|b>.mp3 and
<id>-<a|b>.json (prompt, usage, cost). Empty streams, dropped connections, 5xx, 408 and 429 are retried, and each
of those requests adds a line to the cost ledger (tools/ledger.py: 1 clip, OpenRouter's usage.cost when the
response carried it, ok false when it failed). Any other 4xx (400 bad request, 401 wrong key, 402 balance, 403) is
refused before any music is made: that clip stops at once with no retry and no ledger line, and after a 401, 402
or 403 the clips not yet started are skipped (the key or the account is wrong for all of them).
Needs OPENROUTER_API_KEY in the environment (never printed).
Next: audio/chapters/analyze.py, then tools/music_bed.py.
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
from ledger import record, usage_cost  # noqa: E402  tools/ledger.py: one line per paid call

OUT = HERE / "chapters"
MODEL = "google/lyria-3-clip-preview"
PRICE = 0.04  # USD per clip
TAKES = "ab"
MIN_BYTES = 50000  # an empty stream comes back as 0 bytes at no cost
ACCOUNT_CODES = (401, 402, 403)  # wrong key, balance, forbidden: every other clip would be refused the same way
STOP = []  # the first such HTTP status; clips not yet started are skipped


def refused(e):
    """A 4xx other than 408/429: the request was turned down before any music was made, so nothing was billed
    and a retry fails the same way."""
    return isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code not in (408, 429)


def load_briefs():
    b = json.loads((OUT / "briefs.json").read_text(encoding="utf-8"))
    chapters = {k: v for k, v in b["chapters"].items() if not k.startswith("_")}
    todo = [k for k, v in [("common", b["common"]), *chapters.items()] if re.search(r"<[^>]+>", v)]
    if todo:
        sys.exit(f"briefs.json still has placeholders in: {', '.join(todo)}")
    return b["common"], chapters


def gen(common, brief, cid, v):
    out = OUT / f"{cid}-{v}.mp3"
    if out.exists() and out.stat().st_size > MIN_BYTES:
        return f"{cid}-{v} cached"
    prompt = f"{brief} {common}"
    if v == "b":
        prompt += " A different arrangement and instrumentation from the obvious choice."
    for attempt in range(4):
        if STOP:
            return f"{cid}-{v} FAILED: not sent, an earlier request got HTTP {STOP[0]}"
        audio, usage, err = bytearray(), None, None
        try:
            body = {"model": MODEL, "modalities": ["text", "audio"], "stream": True, "messages": [{"role": "user", "content": prompt}]}
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(), method="POST",
                                         headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json",
                                                  "X-Title": "motion-media-creator chapter music"})
            with urllib.request.urlopen(req, timeout=600) as r:
                for raw in r:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                        continue
                    d = json.loads(line[5:])
                    usage = d.get("usage") or usage
                    for ch in d.get("choices", []):
                        a = (ch.get("delta") or {}).get("audio") or {}
                        if a.get("data"):
                            audio += base64.b64decode(a["data"])
            if len(audio) < MIN_BYTES:
                raise RuntimeError(f"short audio {len(audio)} bytes")
            out.write_bytes(audio)
            (OUT / f"{cid}-{v}.json").write_text(json.dumps({"prompt": prompt, "model": MODEL, "usage": usage}, ensure_ascii=False, indent=1))
        except urllib.error.HTTPError as e:
            if refused(e):
                try:
                    detail = e.read()[:200]
                except Exception:  # noqa: BLE001 - the status is what matters
                    detail = b""
                if e.code in ACCOUNT_CODES:
                    STOP.append(e.code)
                hint = (" (balance too low: top up first; OpenRouter also refuses image output under a $1.00 balance, "
                        "2026-10-12)" if e.code == 402 else "")
                return f"{cid}-{v} FAILED: HTTP {e.code} {detail!r}{hint}"
            err = e  # 5xx, 408, 429: transient
        except Exception as e:  # empty stream, dropped connection: transient
            err = e
        # outside the try: a ledger problem must not look like a failed request (a retry pays again)
        record(kind="music", provider="openrouter", model=MODEL, qty=1, unit="clip", cost_usd=usage_cost(usage),
               ok=err is None, ref=out.relative_to(HERE.parent))
        if err is None:
            return f"{cid}-{v} ok {len(audio)} bytes cost {usage_cost(usage)}"
        print(f"retry {cid}-{v}: {err}", flush=True)
        time.sleep(4 + attempt * 4)
    return f"{cid}-{v} FAILED"


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    common, chapters = load_briefs()
    unknown = [a for a in args if a not in chapters]
    if unknown:
        sys.exit(f"not in briefs.json: {', '.join(unknown)}")
    ids = args or list(chapters)
    jobs = [(c, v) for c in ids for v in TAKES if not ((OUT / f"{c}-{v}.mp3").exists() and (OUT / f"{c}-{v}.mp3").stat().st_size > MIN_BYTES)]
    print(f"{len(jobs)} clips to generate x ${PRICE:.2f} = ${len(jobs) * PRICE:.2f} ({MODEL})", flush=True)
    if "--dry-run" in sys.argv or not jobs:
        return
    if not os.environ.get("OPENROUTER_API_KEY"):
        sys.exit("OPENROUTER_API_KEY is not set")
    failed = 0
    with ThreadPoolExecutor(6) as ex:
        for r in ex.map(lambda t: gen(common, chapters[t[0]], *t), jobs):
            print(r, flush=True)
            failed += " FAILED" in r
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
