#!/usr/bin/env python3
"""Check the decorated Remotion data of an interview short before Studio review and rendering.

usage: check_timeline.py remotion/public/data [--public remotion/public] [--mezz render/mezz-v0.1.mp4]

Fails (exit 1) on: gaps or overlaps in the output timeline, pieces shorter than one frame, captions that
overlap, end before they start or sit outside the film, highlights that are not in their caption,
callouts / inserts / name tag outside the film, an album photo without a positive ar, an empty media.video,
files referenced by the data that are missing under --public (default: the parent of the data dir):
media.video, media.audio, every insert img and album photo, cover.json base.img (and wide.img), and with
--mezz a mezzanine whose frame count differs from the timeline or whose color_space is not bt709.
Warns when fewer than 20 % or more than 50 % of the guest's lines carry a highlight, when a caption is
shorter than 0.35 s, when a chapter is shorter than 10 s, when the film is outside 2–4 minutes, when the
name tag overlaps a number / stamp / arrow callout in time, when the location tag overlaps an equation, and
when either tag is on screen together with an album (both leave before the album starts).

The skill-level timeline_check.py in lov-media-creator assumes source-ordered EDLs; an interview is
re-ordered and the cold open reuses lines, so its overlap errors are expected there. This check works on
the output clock instead.
"""
import argparse
import json
import math
import pathlib
import re
import subprocess
import sys


def probe(path, entries, extra=()):
    out = subprocess.run(["ffprobe", "-v", "error", *extra, "-select_streams", "v:0", "-show_entries", f"stream={entries}",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True).stdout
    return out.strip().splitlines()[0].strip() if out.strip() else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("data")
    ap.add_argument("--public", help="Remotion public dir the data refers to (default: parent of DATA)")
    ap.add_argument("--mezz", help="mezzanine video: frame count and bt709 tags must match")
    a = ap.parse_args()
    d = pathlib.Path(a.data)
    pub = pathlib.Path(a.public) if a.public else d.resolve().parent
    tl = json.loads((d / "timeline.json").read_text())
    subs = json.loads((d / "subs.json").read_text())
    fps, frames = tl["fps"], tl["frames"]
    errs, warns = [], []
    spans = []
    for it in tl["items"]:
        if it["kind"] == "speech":
            spans += [(p["start"], p["frames"]) for p in it["pieces"]]
        else:
            spans.append((it["start"], it["frames"]))
    cur = 0
    for s, n in sorted(spans):
        if n < 1:
            errs.append(f"piece at frame {s} has {n} frames")
        if s != cur:
            errs.append(f"timeline {'gap' if s > cur else 'overlap'} at frame {cur}->{s}")
        cur = s + n
    if cur != frames:
        errs.append(f"timeline ends at {cur}, declared {frames}")
    end = frames / fps
    for i, s in enumerate(subs):
        if s["end"] <= s["start"] or s["start"] < 0 or s["end"] > end + 0.01:
            errs.append(f"caption {i} '{s['text']}' has bad times {s['start']}-{s['end']}")
        elif s["end"] - s["start"] < 0.349:
            warns.append(f"caption {i} '{s['text']}' is on screen only {s['end'] - s['start']:.2f}s")
        if i and s["start"] < subs[i - 1]["end"] - 0.001:
            errs.append(f"caption {i} overlaps the previous one")
        if s.get("hl") and s["hl"] not in s["text"]:
            errs.append(f"caption {i} highlight '{s['hl']}' not in text")
    callouts = tl.get("callouts", [])
    for c in callouts + tl.get("inserts", []):
        if not (0 <= c["start"] < c["end"] <= end + 0.01):
            errs.append(f"{c.get('kind')} {c.get('text', c.get('img', ''))} has bad times {c['start']}-{c['end']}")
    for k in ("nametag", "location"):
        if k in tl and not (0 <= tl[k]["start"] < tl[k]["end"] <= frames):
            errs.append(f"{k} frames {tl[k]['start']}-{tl[k]['end']} outside the film")
    # tags and callouts share the lower third: warn when they are on screen together
    for k, kinds in (("nametag", ("number", "stamp", "arrow")), ("location", ("equation",))):
        if k not in tl:
            continue
        t0, t1 = tl[k]["start"] / fps, tl[k]["end"] / fps
        for c in callouts:
            if c.get("kind") in kinds and c["start"] < t1 and t0 < c["end"]:
                warns.append(f"{k} {t0:.2f}-{t1:.2f}s overlaps {c['kind']} callout {c['start']:.2f}-{c['end']:.2f}s "
                             f"(texts collide; move one of them)")
        # an album fills the frame; Film.tsx shows an insert on frames Math.round(start * fps) .. Math.round(end * fps)
        for ins in tl.get("inserts", []):
            if not ins.get("album"):
                continue
            on, off = (math.floor(ins[e] * fps + 0.5) for e in ("start", "end"))
            if on < tl[k]["end"] and tl[k]["start"] < off:
                warns.append(f"{k} {t0:.2f}-{t1:.2f}s overlaps the album {ins['start']:.2f}-{ins['end']:.2f}s "
                             f"(shorten its seconds so it leaves before the album starts)")
    media = tl.get("media", {}) or {}
    if not media.get("video"):
        errs.append("media.video missing (run decorate.py)")
    refs = [("media.video", media.get("video")), ("media.audio", media.get("audio"))]
    for i, ins in enumerate(tl.get("inserts", [])):
        refs.append((f"insert {i}", ins.get("img")))
        for n, p in enumerate(ins.get("album") or [], 1):
            refs.append((f"insert {i} album photo {n}", p.get("img")))
            if not isinstance(p.get("ar"), (int, float)) or p["ar"] <= 0:
                errs.append(f"insert {i} album photo {n} '{p.get('img')}' needs ar = width / height (it sizes the card)")
    cover_f = d / "cover.json"
    if cover_f.exists():
        cover = json.loads(cover_f.read_text())
        refs += [("cover.json base.img", (cover.get("base") or {}).get("img")),
                 ("cover.json wide.img", (cover.get("wide") or {}).get("img"))]
    for what, rel in refs:
        if rel and not (pub / rel).exists():
            errs.append(f"{what} '{rel}' not found under {pub}")
    g = [s for s in subs if s["speaker"] == "G"]
    if g:
        share = sum(1 for s in g if s.get("hl")) / len(g)
        if not 0.2 <= share <= 0.5:
            warns.append(f"{share:.0%} of guest lines are highlighted (aim for about a third)")
    chap = [i for i in tl["items"] if i["kind"] == "chapter"]
    outro = next((i for i in tl["items"] if i["kind"] == "outro"), None)
    for i, c in enumerate(chap):
        nxt = chap[i + 1]["start"] if i + 1 < len(chap) else (outro["start"] if outro else frames)
        if (nxt - c["start"]) / fps < 10:
            warns.append(f"chapter {c['chapter']} lasts {(nxt - c['start']) / fps:.1f}s (< 10 s)")
    if not 120 <= end <= 240:
        warns.append(f"film is {end:.1f}s (default range 2–4 minutes)")
    if a.mezz:
        if not pathlib.Path(a.mezz).exists():
            errs.append(f"mezzanine {a.mezz} not found")
        else:
            n = int(re.sub(r"\D", "", probe(a.mezz, "nb_read_packets", ["-count_packets"])) or 0)
            if n != frames:
                errs.append(f"mezzanine has {n} frames, timeline {frames}")
            cs = probe(a.mezz, "color_space")
            if cs != "bt709":
                errs.append(f"mezzanine color_space is '{cs or 'unknown'}', expected bt709 (re-run fx_pieces.py)")
    for w in warns:
        print("WARN", w)
    for e in errs:
        print("ERROR", e)
    print(f"{'FAIL' if errs else 'PASS'}: {len(spans)} pieces, {frames} frames ({end:.2f}s), {len(subs)} captions, "
          f"{len(chap)} chapters, {len(errs)} errors, {len(warns)} warnings")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
