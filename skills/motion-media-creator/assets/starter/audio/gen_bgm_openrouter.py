#!/usr/bin/env python3
"""Generate a content-specific BGM candidate with Google Lyria 3 through OpenRouter.

Brief (from this piece): a ~178 s text-only motion-design film on Chinese history,
13 era chapters each in its own visual language; ink-drop opening, steady build,
unification hit (~46 s), Silk Road journey, Tang climax (~81-97 s), light Song
section, Ming ocean swell, 1840 rupture (~141 s), modern-era march, calm resolve.
Instrumental only (the picture carries all text).

Usage: python3 audio/gen_bgm_openrouter.py --name a --prompt-file prompts/a.txt --out audio/candidates/a
Writes <out>.<ext> (decoded audio), <out>.json (request + response metadata, audio stripped).
The request adds a line to the cost ledger (tools/ledger.py: 1 track, OpenRouter's usage.cost when the response
carried it, ok false on a 5xx, 408 or 429, a dropped stream or no audio). Other 4xx (400, 401 wrong key, 402
balance, 403) are refused before any music is made and add no line.
Needs OPENROUTER_API_KEY in the environment (never printed).
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from ledger import record, usage_cost  # noqa: E402  tools/ledger.py: one line per paid call

URL = "https://openrouter.ai/api/v1/chat/completions"


def find_audio(node, path="$"):
    """Yield (path, base64-ish string, format hint) for audio payloads anywhere in the response."""
    if isinstance(node, dict):
        fmt = node.get("format") or node.get("mime_type") or node.get("type")
        for k, v in node.items():
            if isinstance(v, str) and k in ("data", "b64_json", "url") and (len(v) > 1000 or v.startswith("data:audio")):
                yield f"{path}.{k}", v, fmt
            else:
                yield from find_audio(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from find_audio(v, f"{path}[{i}]")


def strip(node):
    if isinstance(node, dict):
        return {k: (f"<{len(v)} chars>" if isinstance(v, str) and len(v) > 400 else strip(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [strip(v) for v in node]
    return node


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--model", default="google/lyria-3-pro-preview")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.prompt_file:
        args.prompt = Path(args.prompt_file).read_text().strip()

    body = {"model": args.model, "modalities": ["text", "audio"], "stream": True,
            "messages": [{"role": "user", "content": args.prompt}]}
    if args.seed is not None:
        body["seed"] = args.seed
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json",
        "X-Title": "motion-media-creator bgm"})
    t0 = time.time()
    audio = bytearray()
    text, fmt_hint, usage, last, chunks = [], None, None, None, 0
    out = Path(args.out)

    def ledger(ok):
        record(kind="music", provider="openrouter", model=args.model, qty=1, unit="track",
               cost_usd=usage_cost(usage), ok=ok, ref=out.resolve())

    try:
        r = urllib.request.urlopen(req, timeout=900)
    except urllib.error.HTTPError as e:
        if not (400 <= e.code < 500 and e.code not in (408, 429)):
            ledger(False)  # the request may have reached the model; a refused one (other 4xx) made nothing
        raise SystemExit(f"HTTP {e.code}: {e.read()[:600]!r}")
    except Exception:
        ledger(False)
        raise
    try:
        with r:
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                ev = json.loads(payload)
                last = ev
                if ev.get("usage"):
                    usage = ev["usage"]
                for ch in ev.get("choices") or []:
                    d = ch.get("delta") or {}
                    if d.get("content"):
                        text.append(d["content"])
                    a = d.get("audio") or {}
                    if a.get("data"):
                        audio.extend(base64.b64decode(a["data"]))
                        chunks += 1
                    fmt_hint = a.get("format") or fmt_hint
    except Exception:  # a dropped stream after the model ran can still be billed (2026-10-12)
        ledger(False)
        raise
    ledger(bool(audio))
    wall = round(time.time() - t0, 1)
    head = bytes(audio[:12])
    ext = "mp3" if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2") else \
          "wav" if head[:4] == b"RIFF" else "ogg" if head[:4] == b"OggS" else "flac" if head[:4] == b"fLaC" else "pcm"
    out.parent.mkdir(parents=True, exist_ok=True)
    f = out.with_suffix("." + ext)
    f.write_bytes(bytes(audio))
    meta = {"name": args.name, "request": body, "wall_seconds": wall, "audio_file": str(f), "bytes": len(audio),
            "chunks": chunks, "format_hint": fmt_hint, "detected": ext, "usage": usage,
            "text": "".join(text)[:2000], "last_event": strip(last)}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps({k: meta[k] for k in ("audio_file", "bytes", "chunks", "format_hint", "detected", "usage", "wall_seconds")}, ensure_ascii=False))
    print("text:", meta["text"][:400])


if __name__ == "__main__":
    main()
