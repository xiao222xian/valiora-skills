# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["librosa", "numpy"]
# ///
"""Beat-phase check of the music bed: does every chapter's cue beat on the picture's beat grid?

  uv run --quiet --python 3.12 --with librosa python qc/beat_phase.py                  # public/audio/bgm-music.wav
  uv run --quiet --python 3.12 --with librosa python qc/beat_phase.py <bed.wav> [--tol 25] [--all] [--json out.json]

The grid is where the chapters start: the most common start mod BEAT frames (chapters after the first). For each
chapter's body (from the end of the outgoing cue's tail to the start of the next cue's pre-lap, so each chapter is
measured on its own music) the bed's onset strength is folded by (t - grid) mod beat, and the peak of that histogram
is the chapter's beat phase in ms from the grid: half a beat off reads about +-250 at 120 BPM.

Passes when every judged chapter is within --tol ms (default 25) of the grid, all of them are within --tol ms of
each other (max - min), and every join between the full-length track and a cue is in time (below); exits 1
otherwise. Judged are the chapters on their own cue (what tools/music_bed.py places); chapters on the full-length
track are measured and flagged but judged only with --all, because that track was there first (the picture was cut
to it) and its ending may slow down. Check bgm-music.wav, not the master: the voice-over brings onsets of its own.
A correctly placed cue reads about -10 ms (these 64-sample onset frames peak a little earlier than the 256-sample
ones analyze.py fits the grid on). `peak` is the histogram peak over its mean: below about 1.5 the beat is too soft
to measure, so listen instead.

Joins. Where the full-length track meets a cue (into chapter 01 from the opening, out of the last cue into the
outro), both play at once for the pre-lap, so their beats must agree or the overlap flams. Each side is measured
next to the overlap, up to JOIN_WIN s of it (the same edges are left out as for the chapters), and the join passes
when the two phases are within --tol ms of each other. Gated by default, with or without --all; tools/music_bed.py
shifts the full track onto the cues' grid so that it passes.

(2026-10-12, 《如何打造一款特斯拉》 v0.5: with the third bar taken as first detected beat + 4 s, 6 of 13 cues sat
94-244 ms off the grid; with the fitted grid all 13 sat within 11 ms of each other. The unshifted full track read
+82 ms (opening) and +81 ms (outro), so both joins overlapped beats about 90 ms apart: this check passed without
--all and said nothing.)
"""
import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "audio" / "chapters"
SKIP_IN = 0.8  # s left out after a chapter's first frame (the outgoing cue runs 0.75 s past it)
SKIP_OUT = 1.05  # s left out before the next chapter (the incoming cue fades in over the last 1 s)
SR, HOP = 22050, 64  # onset frames of 2.9 ms
BINS = 100  # phase histogram bins per beat (5 ms at 120 BPM)
JOIN_WIN = 8.0  # s measured on each side of a join between the full-length track and a cue (16 beats)


def timeline():
    js = ("import('./src/timeline.ts').then(m=>console.log(JSON.stringify({fps:m.FPS,beat:m.BEAT,total:m.TOTAL_FRAMES,"
          "ch:m.CHAPTERS.map((c,i)=>({id:c.id,start:c.start,dur:m.chapterDur(i)}))})))")
    out = subprocess.run(["node", "--disable-warning=MODULE_TYPELESS_PACKAGE_JSON", "-e", js],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def kind(cid, picks):
    """What tools/music_bed.py plays on a chapter: one of its own takes, or the full-length track."""
    p = picks.get(cid, {})
    if p.get("take") == "full" or (not any(CH.glob(f"{cid}-*.mp3")) and "take" not in p):
        return "full"
    return "cue"


def phase(t, o, grid, beat):
    """Peak of the onset strength folded by (t - grid) mod beat, in s from the grid (-beat/2..beat/2),
    and the peak's height over the histogram mean."""
    h, _ = np.histogram((t - grid) % beat, bins=BINS, range=(0, beat), weights=o.astype(np.float64))
    hs = 0.25 * np.roll(h, 1) + 0.5 * h + 0.25 * np.roll(h, -1)  # circular smoothing
    i = int(np.argmax(hs))
    a, b, c = hs[i - 1], hs[i], hs[(i + 1) % BINS]
    den = a - 2 * b + c
    frac = 0.5 * (a - c) / den if den else 0.0  # parabolic peak
    p = ((i + 0.5 + frac) * beat / BINS) % beat
    return float(p if p < beat / 2 else p - beat), float(b / (hs.mean() + 1e-12))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav", nargs="?", default=str(ROOT / "public" / "audio" / "bgm-music.wav"))
    ap.add_argument("--tol", type=float, default=25.0, help="ms: pass band around the grid and for the spread")
    ap.add_argument("--all", action="store_true", help="also judge the chapters on the full-length track")
    ap.add_argument("--json", help="also write the measurements here")
    args = ap.parse_args()

    tl = timeline()
    fps, beat_f = tl["fps"], tl["beat"]
    beat = beat_f / fps
    starts = [c["start"] for c in tl["ch"] if c["start"] > 0]
    grid_f = Counter(s % beat_f for s in starts).most_common(1)[0][0]
    grid = grid_f / fps
    picks = json.loads((CH / "picks.json").read_text()) if (CH / "picks.json").exists() else {}

    y, sr = librosa.load(args.wav, sr=SR, mono=True)
    o = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    t = librosa.frames_to_time(np.arange(len(o)), sr=sr, hop_length=HOP)

    def measure(a, b):
        """Phase (ms) and peak of the bed between a and b s, or (None, None) when that is too short or silent."""
        m = (t >= a) & (t < b)
        if b - a < 2 * beat or not m.any() or o[m].sum() <= 0:
            return None, None
        off, peak = phase(t[m], o[m], grid, beat)
        return round(off * 1000, 1), round(peak, 2)

    rows, body = [], []
    last = len(tl["ch"]) - 1
    for i, c in enumerate(tl["ch"]):
        a = c["start"] / fps + (SKIP_IN if c["start"] > 0 else 0.0)
        b = (c["start"] + c["dur"]) / fps - (SKIP_OUT if i < last else 1.0)  # the film's last second may fade out
        body.append((a, b))
        r = {"id": c["id"], "kind": kind(c["id"], picks), "ms": None, "peak": None,
             "on_grid": c["start"] == 0 or c["start"] % beat_f == grid_f}
        r["ms"], r["peak"] = measure(a, b)
        r["judged"] = r["ms"] is not None and (r["kind"] == "cue" or args.all)
        rows.append(r)

    # joins between the full-length track and a cue: each side next to the overlap
    joins = []
    for i in range(1, len(rows)):
        if rows[i - 1]["kind"] == rows[i]["kind"]:
            continue
        (a0, b0), (a1, b1) = body[i - 1], body[i]
        side = {"out": measure(max(a0, b0 - JOIN_WIN), b0), "in": measure(a1, min(b1, a1 + JOIN_WIN))}
        full, cue = ("out", "in") if rows[i - 1]["kind"] == "full" else ("in", "out")
        jn = {"from": rows[i - 1]["id"], "to": rows[i]["id"], "full_ms": side[full][0], "full_peak": side[full][1],
              "cue_ms": side[cue][0], "cue_peak": side[cue][1], "gap_ms": None}
        if jn["full_ms"] is not None and jn["cue_ms"] is not None:
            jn["gap_ms"] = round(jn["full_ms"] - jn["cue_ms"], 1)
        joins.append(jn)

    vals = [r["ms"] for r in rows if r["judged"]]
    spread = round(max(vals) - min(vals), 1) if vals else 0.0
    worst = max((abs(v) for v in vals), default=0.0)
    gaps = [abs(j["gap_ms"]) for j in joins if j["gap_ms"] is not None]
    worst_join = max(gaps, default=0.0)
    ok = bool(vals) and worst <= args.tol and spread <= args.tol and worst_join <= args.tol
    print(f"{Path(args.wav).name}: grid at start mod {beat_f} = {grid_f} frames ({grid * 1000:.0f} ms), beat {beat * 1000:.0f} ms")
    for r in rows:
        if r["ms"] is None:
            print(f"  {r['id']:12s} {r['kind']:4s}  too short to measure")
            continue
        flag = "" if abs(r["ms"]) <= args.tol else "  OFF"
        flag += "" if r["on_grid"] else "  (start not on the grid)"
        flag += "" if r["judged"] else "  (full track: not judged, see --all)"
        flag += "  (soft beat: listen)" if r["peak"] < 1.5 else ""
        print(f"  {r['id']:12s} {r['kind']:4s}  {r['ms']:+7.1f} ms  peak {r['peak']:5.2f}{flag}")
    if joins:
        print(f"joins between the full-length track and a cue (up to {JOIN_WIN:.0f} s on each side of the overlap):")
    for j in joins:
        head = f"  {j['from'] + ' -> ' + j['to']:24s}"
        if j["gap_ms"] is None:
            print(f"{head} too short to measure: listen")
            continue
        flag = "" if abs(j["gap_ms"]) <= args.tol else "  OFF: the pre-lap overlaps two beats; re-run tools/music_bed.py"
        flag += "  (soft beat: listen)" if min(j["full_peak"], j["cue_peak"]) < 1.5 else ""
        print(f"{head} full {j['full_ms']:+7.1f} ms, cue {j['cue_ms']:+7.1f} ms, gap {j['gap_ms']:+7.1f} ms{flag}")
    print(f"{'PASS' if ok else 'FAIL'}: {len(vals)} chapters judged, worst {worst:.1f} ms from the grid, spread {spread:.1f} ms; "
          f"{len(gaps)} joins, worst gap {worst_join:.1f} ms (limit {args.tol:.0f} ms each)")
    if args.json:
        Path(args.json).write_text(json.dumps({"wav": str(args.wav), "grid_frames": grid_f, "tol_ms": args.tol,
                                               "worst_ms": worst, "spread_ms": spread, "worst_join_ms": worst_join,
                                               "pass": ok, "chapters": rows, "joins": joins}, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
