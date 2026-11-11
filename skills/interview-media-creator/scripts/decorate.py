#!/usr/bin/env python3
"""Add packaging data to the Remotion timeline from a spec: title card, chapter short names, name tag,
location tag, explanatory callouts, photo inserts and albums, caption highlights and punch-in centres.

usage: decorate.py EDL.json PACKAGE.json [--remotion-data remotion/public/data]

Starts from the undecorated timeline.base.json written by build_timeline.py (falls back to timeline.json
with title / nametag / location / callouts / inserts removed), so a key deleted from the package disappears
from the film when only this script is re-run.

Every time is anchored to the spoken words, never typed as a timecode. A time reference is one of:
  {"anchor": "关键词", "segment": "3i", "delay": 0.2}   caption line in that segment containing the text, + delay
  {"segment_start": "1a", "delay": 0.2} / {"segment_end": "3c"}
  {"after": 3.2}             (end only) seconds after this element's start
  {"outro_end_minus": 1.8}   seconds before the end of the film (outro cards)

An anchor must sit inside one caption line. Put every anchor and every highlight key into the EDL "nouns"
list before build_timeline.py / subs_from_lines.py, so line breaking never splits them; an anchor that is in
the segment text but split across lines stops the script with that instruction.

PACKAGE.json (full worked example: assets/templates/package.example.json):
  {"title": {"lines": ["主标题第一行", "第二行", "重音词"], "byline": "对话 · 被访者名"},
   "chapter_short": {"ch1": "章节短名", ...},
   "nametag": {"start": {"segment_start": "1a", "delay": 0.2}, "seconds": 4.6, "name": "被访者名", "en": "English name", "desc": "身份 · ..."},
   "location": {"start": {...}, "seconds": 4.6, "text": "城市 · 地点"},
   "callouts": [{"kind": "equation", "start": {...}, "end": {...}, "steps": [{"at": {...}, "text": "部件", "op": ""}]},
                {"kind": "stamp", "start": {...}, "end": {...}, "text": "金句"},
                {"kind": "number", "start": {...}, "end": {...}, "value": "800万", "unit": "个", "label": "..."},
                {"kind": "arrow", "start": {...}, "end": {...}, "from": "-1", "to": "0", "label": "阶段"}],
   "inserts": [{"img": "img/bts.jpg", "start": {...}, "end": {...}, "focus": [0.82, 0.45], "flash": false},
               {"album": [{"img": "img/life-1.jpg", "ar": 0.75, "focus": [0.5, 0.42]}, ...], "start": {...}, "end": {...}}],
   "highlights": {"keys": ["关键词", ...], "reuse": ["可重复高亮的金句"]},
   "media": {"video": "media/mezz-v0.1.mp4", "audio": "audio/mix-v0.1.m4a"},
   "logo_seconds": 1.8}

Highlights: only the guest's lines (speaker G), at most one key per caption line, each key once unless
listed in "reuse". The script reports how many answer lines got a highlight; keep it near a third.

An album (the guest's own photos as a pile of cards, ar = width / height) needs no "img" of its own: the first
photo is copied into it, so every insert in the timeline names a picture.
"""
import argparse
import json
import pathlib
import re
import statistics

DECOR = ("title", "nametag", "location", "callouts", "inserts", "logo_frames", "media")


def plain(t):
    return re.sub(r"[，。？！、,.?!：:；;“”\"' @\s]", "", t)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("package")
    ap.add_argument("--remotion-data", default="remotion/public/data")
    a = ap.parse_args()
    edl_path = pathlib.Path(a.edl).resolve()
    root = edl_path.parent
    pkg = json.loads(pathlib.Path(a.package).read_text())
    data = (root / a.remotion_data).resolve()
    base = data / "timeline.base.json"
    tl = json.loads((base if base.exists() else data / "timeline.json").read_text())
    for k in DECOR:
        tl.pop(k, None)
    subs = json.loads((data / "subs.json").read_text())
    fps = tl["fps"]
    seg = {i["id"]: i for i in tl["items"] if i["kind"] == "speech"}

    def split_hint(word, segment=None):
        """Segments whose full text contains the word although no single caption line does."""
        return [i for i, it in seg.items() if (segment is None or i == segment) and plain(word) in plain(it["text"])
                and not any(word in s["text"] for s in subs if s["seg"] == i)]
    outro = next(i for i in tl["items"] if i["kind"] == "outro")
    film_end = tl["frames"] / fps

    def when(ref, base=None):
        if "anchor" in ref:
            hits = [s for s in subs if ref["anchor"] in s["text"] and (ref.get("segment") is None or s["seg"] == ref["segment"])]
            if not hits:
                if ref.get("segment") and ref["segment"] not in seg:
                    raise SystemExit(f"anchor {ref}: no speech segment '{ref['segment']}' in the timeline")
                split = split_hint(ref["anchor"], ref.get("segment"))
                if split:
                    lines = [s["text"] for s in subs if s["seg"] == split[0]]
                    raise SystemExit(f"anchor '{ref['anchor']}' is in segment {split[0]} but split across caption lines {lines}: "
                                     f"add it to the EDL \"nouns\" list, re-run build_timeline.py and subs_from_lines.py, then decorate.py")
                raise SystemExit(f"anchor not found in the segment text: {ref}")
            return round(hits[0]["start"] + ref.get("delay", 0.0), 3)
        if "segment_start" in ref:
            it = seg[ref["segment_start"]]
            return round(it["start"] / fps + ref.get("delay", 0.0), 3)
        if "segment_end" in ref:
            it = seg[ref["segment_end"]]
            return round((it["start"] + it["frames"]) / fps + ref.get("delay", 0.0), 3)
        if "after" in ref:
            return round(base + ref["after"], 3)
        if "outro_end_minus" in ref:
            return round(film_end - ref["outro_end_minus"], 3)
        if "t" in ref:
            return float(ref["t"])
        raise SystemExit(f"unknown time reference: {ref}")

    short = pkg.get("chapter_short", {})
    for c in tl["chapters"]:
        c["short"] = short.get(c["id"], c["title"])
    if "title" in pkg:
        tl["title"] = pkg["title"]
    for k in ("nametag", "location"):
        if k in pkg:
            spec = dict(pkg[k])
            st = when(spec.pop("start"))
            secs = spec.pop("seconds", 4.6)
            tl[k] = dict(spec, start=int(round(st * fps)), end=int(round((st + secs) * fps)))
    callouts = []
    for c in pkg.get("callouts", []):
        c = dict(c)
        st = when(c.pop("start"))
        en = when(c.pop("end"), st)
        if c["kind"] == "equation":
            c["steps"] = [dict(s, at=when(s["at"])) for s in c["steps"]]
        callouts.append(dict(c, start=st, end=en))
    tl["callouts"] = callouts
    inserts = []
    for ins in pkg.get("inserts", []):
        ins = dict(ins)
        if ins.get("album"):
            ins.setdefault("img", ins["album"][0]["img"])
        st = when(ins.pop("start"))
        inserts.append(dict(ins, kind="photo", start=st, end=when(ins.pop("end"), st)))
    tl["inserts"] = inserts
    tl["logo_frames"] = int(round(pkg.get("logo_seconds", 1.8) * fps))
    tl["media"] = pkg["media"]

    hl = pkg.get("highlights", {})
    keys, reuse, used = hl.get("keys", []), set(hl.get("reuse", [])), set()
    for s in subs:
        s["hl"] = None
        if s["speaker"] != "G":
            continue
        for k in keys:
            if k in s["text"] and (k not in used or k in reuse):
                s["hl"] = k
                used.add(k)
                break

    for k in keys:
        if k in used:
            continue
        split = split_hint(k)
        why = (f"split across caption lines in {split}: add it to the EDL \"nouns\"" if split else
               "only on guest lines that already carry another key" if any(k in s["text"] for s in subs if s["speaker"] == "G")
               else "not in any guest caption")
        print(f"WARN highlight key '{k}' never shown: {why}")

    no_face = 0
    for it in tl["items"]:
        if it["kind"] != "speech":
            continue
        for p in it["pieces"]:
            fj = root / "render" / "seg" / (pathlib.Path(p["file"]).stem + ".faces.json")
            fs = [f for f in json.loads(fj.read_text()) if f] if fj.exists() else []
            if len(fs) >= 0.5 * p["frames"]:
                p["face"] = {"cx": round(statistics.median(f[0] for f in fs), 4), "cy": round(statistics.median(f[1] for f in fs), 4),
                             "w": round(statistics.median(f[2] for f in fs), 4)}
            else:
                p["face"] = None
                no_face += 1

    (data / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1))
    (data / "subs.json").write_text(json.dumps(subs, ensure_ascii=False, indent=1))
    answers = sum(1 for s in subs if s["speaker"] == "G")
    print(f"callouts {len(callouts)}, inserts {len(inserts)}, highlighted {sum(1 for s in subs if s['hl'])}/{answers} answer lines, "
          f"pieces without a face {no_face}, outro starts {outro['start'] / fps:.2f}s")


if __name__ == "__main__":
    main()
