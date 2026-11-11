#!/usr/bin/env python3
"""Fill each segment's fixed "crop" (horizontal face centre, 0..1) in an EDL for a landscape source cut to the vertical target.

usage: crop_centers.py EDL.json [--yunet PATH] [--samples 5] [--score 0.7] [--min-width 0.11]
                       [--guest-side any|left|right] [--write]

- The framed person is the segment's "crop_on" ("G" | "Q" | "none"), else its speaker. "none" removes "crop":
  build_timeline.py then centres the whole landscape frame over a blurred copy of itself. Use it for a line during which
  the guest sits at the very edge of the frame, where a full-height crop shows half his face (对话符尧: two questions).
- Face rule, shared with reframe.py: the largest face wider than --min-width of the frame. Largest rather than left-most,
  so a smaller background face never wins while the guest covers his face. With --guest-side left|right (both people
  in the frame) only faces whose centre is in that person's half count: G = the guest's side, Q = the other side.
  A wide two-shot with faces about 5 % of the width (采访 Ricky) needs --min-width 0.04.
- --samples frames spread over the segment's pieces; the median centre is kept, so the segment has one framing.
  Run reframe.py afterwards: it adds a moving "crop_track" where this fixed crop would cut the face, and a recomputed
  segment drops its old track here. A segment with a numeric "crop" and "crop_fixed": true is left alone.
- Without --write the centres are only printed.
"""
import argparse
import importlib.util
import json
import pathlib
import statistics
import subprocess
import sys

import cv2
import numpy as np

sys.dont_write_bytecode = True  # importing reframe must not leave __pycache__ inside the skill
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reframe", HERE / "reframe.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
FALLBACK = {None: 0.5, "left": 0.25, "right": 0.75}  # no face found: the middle of the person's half


def frame_at(src, t, size):
    w, h = size
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3) if len(raw) == w * h * 3 else None


def sample_times(pieces, n):
    span = [(q[0], q[1]) for q in pieces]
    total = sum(b - a for a, b in span)
    ts = []
    for k in range(n):
        x = total * (k + 0.5) / n
        for a, b in span:
            if x <= b - a:
                ts.append(a + x)
                break
            x -= b - a
    return ts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--yunet")
    ap.add_argument("--samples", type=int, default=5, help="frames sampled per segment")
    ap.add_argument("--score", type=float, default=0.7, help="YuNet score threshold")
    ap.add_argument("--min-width", type=float, default=0.11,
                    help="ignore faces narrower than this fraction of the width (wide two-shots: about 0.04)")
    ap.add_argument("--guest-side", choices=("any", "left", "right"), default="any",
                    help="the guest's half of the frame when both people are in it; any = one person in frame")
    ap.add_argument("--write", action="store_true", help="write crop into the EDL")
    a = ap.parse_args()
    p = pathlib.Path(a.edl).resolve()
    edl = json.loads(p.read_text())
    src = (p.parent / edl["source"]["video"]).resolve()
    src_size = R.B.probe_display_size(src)
    if R.crop_fraction(src_size, edl["target"]) >= 1:
        raise SystemExit("the source is not wider than the target: no crop needed")
    size = R.detect_size(src_size)
    det = cv2.FaceDetectorYN.create(R.model_path(a.yunet), "", size, a.score)
    for seg in edl["segments"]:
        if isinstance(seg.get("crop"), (int, float)) and seg.get("crop_fixed"):
            continue
        seg.pop("crop_track", None)
        who = seg.get("crop_on") or seg.get("speaker") or "G"
        if who == "none":
            seg.pop("crop", None)
            print(f"{seg['id']:>5} none: centred over a blurred copy")
            continue
        side = R.face_side(who, a.guest_side)
        cx, ts = [], sample_times(seg["pieces"], a.samples)
        for t in ts:
            im = frame_at(src, t, size)
            box = R.largest_face(det, im, a.min_width, side) if im is not None else None
            if box:
                cx.append((box[0] + box[1]) / 2)
        if cx:
            seg["crop"] = round(statistics.median(cx), 3)
        else:
            seg["crop"] = FALLBACK[side]
            print(f"WARN {seg['id']}: no {who} face found, default crop {seg['crop']}")
        print(f"{seg['id']:>5} {who} crop {seg['crop']:.3f}  samples {len(cx)}/{len(ts)}  spread "
              f"{(max(cx) - min(cx)) if cx else 0:.3f}")
    if a.write:
        p.write_text(json.dumps(edl, ensure_ascii=False, indent=1))
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
