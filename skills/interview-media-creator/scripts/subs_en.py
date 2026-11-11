#!/usr/bin/env python3
"""Attach English lines to the captions for bilingual subtitles and rewrite the SRT with two lines per cue.

usage: subs_en.py EDL.json [--en work/subs-en.json] [--remotion-data remotion/public/data] [--srt PATH]

- subs-en.json maps a segment id to one English line per Chinese caption line of that segment, in order
  ({"1a": ["Could you start by introducing yourself?"], ...}); it defaults to subs-en.json next to the EDL.
- Run it after subs_from_lines.py (which rewrites subs.json and drops "en"); decorate.py keeps the field.
  A segment whose caption count differs from its English list stops the run: line breaks changed, so update the
  translation (English kept short and spoken; brand names as they are; money in yuan).
- Writes "en" into <remotion-data>/subs.json (the starter shows it under the Chinese line) and rewrites
  render/subs-<version>.srt (or --srt) with the Chinese and English line of every cue.
"""
import argparse
import importlib.util
import json
import pathlib
import sys
from collections import defaultdict

sys.dont_write_bytecode = True  # importing build_timeline must not leave __pycache__ inside the skill
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_timeline", HERE / "build_timeline.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--en", help="segment id -> English lines (default subs-en.json next to the EDL)")
    ap.add_argument("--remotion-data", default="remotion/public/data", help="where subs.json is (relative to EDL)")
    ap.add_argument("--srt", help="bilingual SRT (default render/subs-<version>.srt next to the EDL)")
    a = ap.parse_args()
    edl_path = pathlib.Path(a.edl).resolve()
    root, edl = edl_path.parent, json.loads(edl_path.read_text())
    data = (root / a.remotion_data).resolve()
    subs = json.loads((data / "subs.json").read_text())
    en = json.loads(pathlib.Path(a.en or root / "subs-en.json").read_text())
    by = defaultdict(list)
    for s in subs:
        by[s["seg"]].append(s)
    bad = [f"{k}: {len(v)} captions vs {len(en.get(k, []))} English lines {[x['text'] for x in v]}"
           for k, v in by.items() if len(v) != len(en.get(k, []))]
    if bad:
        raise SystemExit("caption/English mismatch:\n" + "\n".join(bad))
    for k, v in by.items():
        for s, e in zip(v, en[k]):
            s["en"] = e
    (data / "subs.json").write_text(json.dumps(subs, ensure_ascii=False, indent=1))
    srt = pathlib.Path(a.srt) if a.srt else root / "render" / f"subs-{edl['version']}.srt"
    srt.parent.mkdir(parents=True, exist_ok=True)
    B.write_srt([dict(s, text=f"{s['text']}\n{s['en']}") for s in subs], srt)
    print(f"{len(subs)} captions with English -> {data / 'subs.json'}, {srt}; "
          f"longest English line {max(len(s['en']) for s in subs)} chars")


if __name__ == "__main__":
    main()
