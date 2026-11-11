#!/usr/bin/env python3
"""Find single-frame render glitches: one frame that differs from both neighbours while the neighbours agree.

usage: glitch_scan.py VIDEO [--qc-dir qc] [--timeline work/remotion/public/data/timeline.json] [--ratio 3] [--floor 20]

A Remotion render now and then writes one bad frame (a garbled band, a tile shifted out of place). It lasts 33 ms, so
the 5 fps contact sheets step over it: 对话易七猫 v0.1 had two (frames 1593 and 1881), found only when the re-render
was compared with it frame by frame. finalize_platform.py runs this scan on every frame of the encoded file; run it
on its own for a render, or for a version that does not go through finalize_platform (the B站 16:9 file).

Per frame n, grey at 270x480 (480x270 landscape) in a 6 x 8 grid of blocks, mean absolute difference per block (a
whole-frame mean averaged the garbled strip along the top of frame 1593 away): d1 = |f(n) - f(n-1)|,
d2 = |f(n+1) - f(n)|, d0 = |f(n+1) - f(n-1)|. A block hits when min(d1, d2) - ratio * d0 > floor. Only one-frame
faults are caught: when two frames in a row are bad they match each other and no block hits.

Each hit frame is printed with its time code, the peak block (row and column from the top left, 0-based), the number
of hit blocks and their box in source pixels, and gets a strip qc/glitch-<stem>/f<frame>.jpg: previous / this / next
frame on top (red: box of the hit blocks, yellow: peak block), the peak block and its neighbours enlarged below.
Everything goes to qc/glitch-<stem>.json; old strips of the same stem are replaced.

Measures per hit, over the hit blocks: around = the largest d0 of the blocks touching them (motion nearby between
n-1 and n+1); edges = mean |Laplacian| of this frame / the larger of the two neighbours' (above 1: this frame has
harder edges); texture = this frame's mean |Laplacian| (540x960 grey). Over the whole frame: change = median d0 of
all blocks (how much of the picture changed between n-1 and n+1).

Tags name the known look-alikes. A tagged hit is still listed; every hit is judged on its strip:
- outro: inside the timeline's outro. lov-logo-sting flashes the whole frame for one frame on its bar hit (local
  frame 72 at the reference timing; the sting fills the last frames of the outro); the starter's LogoCard does not.
- insert-flash: from the frame before a photo insert with "flash": true to 9 frames in. The starter's shutter flash
  rises from nothing on the insert's first frame to 90 % white on its third, so the first frame, darker than both
  neighbours, can hit. Every insert covers frames round(start * fps) .. round(end * fps). A starter set up before
  0.5.1 showed photos and reference cards from the first frame with frame / fps >= start (seconds rounded to 3
  decimals): a start rounded up came one frame late and left that frame to what is underneath, over the outro black.
- flat: this frame is a plain field over the hit blocks (texture < 0.8): a flash, a black frame, a blurred backdrop.
- cut: most of the picture changed between n-1 and n+1 (change >= 30; 58-88 at the cuts seen, 0.7-16 inside a shot):
  this frame sits next to a cut or a whip pan, so around says nothing about motion and no motion tag is given.
- motion: a hand or an object moving, usually motion-blurred: motion nearby and this frame not sharper than either
  neighbour (around >= 30, edges < 1.5), or this frame clearly softer than both with some motion nearby (around >= 15,
  edges < 0.8). The two render glitches of 对话易七猫 v0.1 sat in a still neighbourhood (around 1.2 and 18) and added
  hard edges (edges 1.7 and 2.5). Small to-and-fro movements (fingers) stay untagged (around 8-26, edges about 1).
Without --timeline only the picture tags are given; a timeline whose frame count differs from the video's (another
version) is not used.
With --timeline each hit also lists what is on screen: the segment or card, and the insert's picture; inside an album
the photo on top of the pile, e.g. "img/life-3.jpg (album 3/5)". An album has no tag of its own: its cards land and
its backdrops fade in over several frames (对话易七猫 v0.3 had no hit inside its album).
"""
import argparse
import json
import math
import pathlib

import cv2
import numpy as np


def timecode(t):
    cs = round(t * 100)
    return f"{cs // 6000}:{cs % 6000 / 100:05.2f}"


class Scan:
    """Feed decoded BGR frames in order with push(); report() once the last frame is in."""

    def __init__(self, fps, strip_dir=None, ratio=3.0, floor=20.0):
        self.fps, self.ratio, self.floor = fps, ratio, floor
        self.strip_dir = pathlib.Path(strip_dir) if strip_dir else None
        if self.strip_dir:
            self.strip_dir.mkdir(parents=True, exist_ok=True)
            for old in self.strip_dir.glob("f*.jpg"):
                old.unlink()
        self.win, self.n, self.hits, self.grid = [], -1, [], None

    def push(self, bgr):
        if self.grid is None:
            h, w = bgr.shape[:2]
            self.grid, self.small = ((8, 6), (270, 480)) if h >= w else ((6, 8), (480, 270))  # (rows, cols), (w, h)
        self.n += 1
        g = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), self.small).astype(np.int16)
        self.win = (self.win + [(g, bgr)])[-3:]
        if len(self.win) == 3:
            self._check(self.n - 1)

    def _blocks(self, a):
        rows, cols = self.grid
        return a.reshape(rows, a.shape[0] // rows, cols, a.shape[1] // cols).mean(axis=(1, 3))

    def _check(self, n):
        (a, fa), (b, fb), (c, fc) = self.win
        d1, d2, d0 = (self._blocks(np.abs(x - y)) for x, y in ((b, a), (c, b), (c, a)))
        score = np.minimum(d1, d2) - self.ratio * d0
        if score.max() <= self.floor:
            return
        hit = score > self.floor
        r, k = (int(x) for x in np.unravel_index(int(np.argmax(score)), score.shape))
        ring = cv2.dilate(hit.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~hit
        around = float(d0[ring].max()) if ring.any() else 0.0
        mids = [cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (self.small[0] * 2, self.small[1] * 2)).astype(np.float32)
                for f in (fa, fb, fc)]
        lap = [float(self._blocks(np.abs(cv2.Laplacian(m, cv2.CV_32F)))[hit].mean()) for m in mids]
        edges = lap[1] / max(lap[0], lap[2], 0.05)
        change = float(np.median(d0))
        moving = (around >= 30 and edges < 1.5) or (around >= 15 and edges < 0.8)
        tags = ["flat"] if lap[1] < 0.8 else []
        if change >= 30:
            tags.append("cut")
        elif moving and not tags:
            tags.append("motion")
        hh, ww = fb.shape[:2]
        bh, bw = hh / self.grid[0], ww / self.grid[1]
        rr, cc = np.nonzero(hit)
        rec = {"frame": n, "t": round(n / self.fps, 3), "tc": timecode(n / self.fps), "score": round(float(score[r, k]), 1),
               "peak": [r, k], "blocks": int(hit.sum()),
               "box": [int(round(x)) for x in (cc.min() * bw, rr.min() * bh, (cc.max() + 1) * bw, (rr.max() + 1) * bh)],
               "d1_d2_d0": [round(float(x[r, k]), 1) for x in (d1, d2, d0)],
               "around": round(around, 1), "edges": round(edges, 2), "texture": round(lap[1], 2), "change": round(change, 1),
               "tags": tags}
        if self.strip_dir:
            rec["strip"] = str(self.strip_dir / f"f{n:05d}.jpg")
            self._strip(rec, (fa, fb, fc), bh, bw)
        self.hits.append(rec)

    def _strip(self, rec, frames, bh, bw):
        hh, ww = frames[1].shape[:2]
        s = 360 / min(hh, ww)
        pw, ph = round(ww * s), round(hh * s)
        r, k = rec["peak"]
        x0, y0, x1, y1 = rec["box"]
        zy0, zy1 = round(max(0, r - 1) * bh), round(min(self.grid[0], r + 2) * bh)
        zx0, zx1 = round(max(0, k - 1) * bw), round(min(self.grid[1], k + 2) * bw)
        zh = round((zy1 - zy0) * pw / (zx1 - zx0))
        n = rec["frame"]
        labels = [f"{n - 1}  previous", f"{n}  {rec['tc']}  score {rec['score']}", f"{n + 1}  next"]
        cols = []
        for f, text in zip(frames, labels):
            top = cv2.resize(f, (pw, ph), interpolation=cv2.INTER_AREA)
            cv2.rectangle(top, (round(x0 * s), round(y0 * s)), (round(x1 * s) - 1, round(y1 * s) - 1), (0, 0, 255), 2)
            cv2.rectangle(top, (round(k * bw * s), round(r * bh * s)), (round((k + 1) * bw * s) - 1, round((r + 1) * bh * s) - 1),
                          (0, 255, 255), 1)
            zoom = cv2.resize(f[zy0:zy1, zx0:zx1], (pw, zh), interpolation=cv2.INTER_AREA)
            band = np.zeros((26, pw, 3), np.uint8)
            cv2.putText(band, text, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cols.append(np.vstack([band, top, np.full((4, pw, 3), 255, np.uint8), zoom]))
        sep = np.full((cols[0].shape[0], 4, 3), 255, np.uint8)
        cv2.imwrite(rec["strip"], np.hstack([cols[0], sep, cols[1], sep, cols[2]]), [cv2.IMWRITE_JPEG_QUALITY, 85])

    def report(self, timeline=None):
        rep = {"frames": self.n + 1, "fps": round(self.fps, 3), "grid_rows_cols": self.grid and list(self.grid),
               "ratio": self.ratio, "floor": self.floor, "timeline": str(timeline) if timeline else None,
               "strips": str(self.strip_dir) if self.strip_dir else None}
        if timeline:
            note = label(self.hits, timeline, self.n + 1)
            if note:
                rep["timeline_note"] = note
        rep["hits"] = self.hits
        return rep


def label(hits, timeline, frames):
    """Tag hits inside the outro or a flash insert and name what is on screen; returns a note when the timeline is not used."""
    tl = json.loads(pathlib.Path(timeline).read_text())
    if tl.get("frames") != frames:
        return f"{timeline} has {tl.get('frames')} frames, the video {frames}: not used (another version?)"
    fps = tl["fps"]

    def first(sec):  # starter Film.tsx: every insert covers frames Math.round(start * fps) .. Math.round(end * fps);
        # in a starter set up before 0.5.1 photos and reference cards can start one frame later, still inside the flash window
        return math.floor(sec * fps + 0.5)

    for h in hits:
        f = h["frame"]
        on = []
        for it in tl["items"]:
            if it["start"] <= f < it["start"] + it["frames"]:
                on.append(it.get("id") or it.get("chapter") or it["kind"])
                if it["kind"] == "outro":
                    h["tags"].append("outro")
                    h["outro_frame"] = [f - it["start"], it["frames"]]
        for ins in tl.get("inserts") or []:
            a, b = first(ins["start"]), first(ins["end"])
            if a <= f < b:
                album = ins.get("album")
                if album:  # Film.tsx drops the next photo on the pile every (b - a) / len(album) frames
                    k = min(len(album), math.floor((f - a) / ((b - a) / len(album))) + 1) - 1
                    on.append(f"{album[k]['img']} (album {k + 1}/{len(album)})")
                else:
                    on.append(ins["img"])
            if ins.get("flash") and a - 1 <= f <= a + 9:
                h["tags"].append("insert-flash")
        h["on_screen"] = on
    return None


def lines(rep):
    out = []
    for h in rep["hits"]:
        x0, y0, x1, y1 = h["box"]
        where = f"  [{', '.join(h['on_screen'])}]" if h.get("on_screen") else ""
        at = f" {h['outro_frame'][0]}/{h['outro_frame'][1]}" if "outro_frame" in h else ""
        out.append(f"  frame {h['frame']:>5}  {h['tc']}  score {h['score']:>5}  peak r{h['peak'][0]}c{h['peak'][1]}, "
                   f"{h['blocks']} block(s) x {x0}-{x1} y {y0}-{y1}  around {h['around']} edges {h['edges']} "
                   f"texture {h['texture']} change {h['change']}  "
                   f"{' '.join(h['tags']) or 'untagged'}{at}{where}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--qc-dir", default="qc")
    ap.add_argument("--timeline", help="this version's remotion/public/data/timeline.json: tags the outro and flash inserts")
    ap.add_argument("--ratio", type=float, default=3.0)
    ap.add_argument("--floor", type=float, default=20.0)
    a = ap.parse_args()
    video = pathlib.Path(a.video)
    qc = pathlib.Path(a.qc_dir)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video}")
    sc = Scan(cap.get(cv2.CAP_PROP_FPS), qc / f"glitch-{video.stem}", a.ratio, a.floor)
    while True:
        ok, im = cap.read()
        if not ok:
            break
        sc.push(im)
    rep = sc.report(a.timeline)
    (qc / f"glitch-{video.stem}.json").write_text(json.dumps({"file": str(video), **rep}, ensure_ascii=False, indent=1))
    tagged = sum(1 for h in rep["hits"] if h["tags"])
    print(f"{video}: {rep['frames']} frames, {len(rep['hits'])} single-frame hits ({tagged} tagged), strips in {rep['strips']}")
    if rep.get("timeline_note"):
        print(f"WARN timeline {rep['timeline_note']}")
    print("\n".join(lines(rep)))


if __name__ == "__main__":
    main()
