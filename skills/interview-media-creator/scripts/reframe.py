#!/usr/bin/env python3
"""Pan the full-height crop with the guest's face where a segment's fixed "crop" would cut it off (landscape source).

usage: reframe.py EDL.json [--yunet PATH] [--fps 4] [--margin 0.07] [--score 0.5] [--min-width 0.11]
                  [--guest-side any|left|right] [--write]

Run after crop_centers.py has written each segment's fixed "crop", before build_timeline.py --video.
- Every piece of a segment with a numeric "crop" (title segments excepted) is decoded once at --fps, 960 px wide, and
  faces are found with OpenCV YuNet (--yunet, $YUNET_MODEL or ~/models/yunet.onnx). The framed face is the largest one
  wider than --min-width of the frame, the same rule as crop_centers.py: largest, not left-most, so that while the guest
  covers his face a smaller background face cannot pull the crop away. With --guest-side left|right only faces whose
  centre is in that person's half count ("crop_on", else the speaker: G = the guest's side, Q = the other side).
- A segment whose face always stays inside its fixed crop with --margin of the frame width to spare keeps the fixed crop.
  Otherwise it gets "crop_track": [[source_t, centre], ...]. Per piece, each sample allows the centres that keep the face
  inside the crop with the margin; a forward and a backward "lazy" pass (move only when the face would leave the frame)
  are averaged, smoothed over about 1 s, clamped back into the allowed corridor and simplified (Ramer-Douglas-Peucker,
  0.004 of the width). Samples without a face borrow the nearest sample's corridor.
- --margin 0.07: YuNet's box is narrower than the head when the guest turns sideways, so 0.03 still cut the face at the
  edge in 4 segments of 对话符尧; 0.07 leaves room on the side he faces. The Remotion punch-in (1.07-1.14x) eats a
  further 3-6 % of each edge, so check the contact sheet after rendering.
- build_timeline.py turns "crop_track" into a piecewise-linear crop x expression per piece (cache key includes it).
  Without --write the plan is only printed.
- A segment may carry "reframe": {"margin": 0.07, "score": 0.5, "why": "..."}; its values override the command line
  for that segment. Record there whatever differs from the film's run (e.g. the segments the contact sheet caught at
  the edge, with the time codes as "why"), and note the run's own flags in the delivery report: the result is
  deterministic, so re-running with the same flags rebuilds the same tracks and build_timeline re-renders nothing.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import cv2
import numpy as np

sys.dont_write_bytecode = True  # importing build_timeline must not leave __pycache__ inside the skill
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_timeline", HERE / "build_timeline.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
DW = 960  # detection width


def model_path(arg):
    for p in (arg, os.environ.get("YUNET_MODEL"), str(pathlib.Path.home() / "models" / "yunet.onnx")):
        if p and pathlib.Path(p).exists():
            return p
    raise SystemExit("YuNet model not found: pass --yunet PATH or set YUNET_MODEL "
                     "(face_detection_yunet_2023mar.onnx from the OpenCV model zoo)")


def detect_size(src_size):
    sw, sh = src_size
    return DW, int(round(DW * sh / sw / 2)) * 2


def crop_fraction(src_size, target):
    """Width of the full-height crop at the target aspect as a fraction of the source width (as in build_timeline)."""
    sw, sh = src_size
    return min(sw, int(round(sh * target["width"] / target["height"] / 2)) * 2) / sw


def face_side(who, guest_side):
    """Half of the frame the framed person sits in, or None to search the whole frame."""
    if guest_side == "any":
        return None
    return guest_side if who == "G" else {"left": "right", "right": "left"}[guest_side]


def largest_face(det, im, min_width, side=None):
    """(left, right) edges of the framed face as fractions of the width, or None."""
    w = im.shape[1]
    _, f = det.detect(im)
    f = [r for r in (f if f is not None else []) if r[2] / w > min_width]
    if side:
        f = [r for r in f if ((r[0] + r[2] / 2) / w < 0.5) == (side == "left")]
    if not f:
        return None
    r = max(f, key=lambda r: r[2])
    return float(r[0] / w), float((r[0] + r[2]) / w)


def faces_over(src, t0, t1, fps, det, size, min_width, side):
    w, h = size
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{t1 - t0:.3f}",
                          "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    out = []
    for i in range(len(raw) // (w * h * 3)):
        im = np.frombuffer(raw[i * w * h * 3:(i + 1) * w * h * 3], np.uint8).reshape(h, w, 3)
        box = largest_face(det, im, min_width, side)
        out.append((t0 + i / fps, *(box or (None, None))))
    return out


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (t0, x0), (t1, x1) = pts[0], pts[-1]
    d = [abs(x - (x0 + (x1 - x0) * (t - t0) / (t1 - t0 or 1))) for t, x in pts[1:-1]]
    i = int(np.argmax(d))
    if d[i] > eps:
        return rdp(pts[:i + 2], eps)[:-1] + rdp(pts[i + 1:], eps)
    return [pts[0], pts[-1]]


def track(samples, c0, margin, cw):
    lo, hi = [], []
    for _, a, b in samples:
        if a is None:
            lo.append(None)
            hi.append(None)
            continue
        l, h = b + margin - cw / 2, a - margin + cw / 2
        if l > h:  # face wider than the crop minus both margins: centre it
            l = h = (l + h) / 2
        lo.append(max(l, cw / 2))
        hi.append(min(h, 1 - cw / 2))
    idx = [i for i, v in enumerate(lo) if v is not None]
    for i in range(len(lo)):
        if lo[i] is None and idx:
            j = min(idx, key=lambda k: abs(k - i))
            lo[i], hi[i] = lo[j], hi[j]
    n = len(lo)
    fwd, c = [], c0
    for i in range(n):
        c = min(max(c, lo[i]), hi[i])
        fwd.append(c)
    bwd, c = [0.0] * n, fwd[-1]
    for i in range(n - 1, -1, -1):
        c = min(max(c, lo[i]), hi[i])
        bwd[i] = c
    path = np.array([(f + b) / 2 for f, b in zip(fwd, bwd)])
    k = 5
    pad = np.pad(path, (k // 2, k // 2), mode="edge")
    path = np.convolve(pad, np.ones(k) / k, mode="valid")
    path = np.array([min(max(p, l), h) for p, l, h in zip(path, lo, hi)])
    pad = np.pad(path, (1, 1), mode="edge")
    return np.convolve(pad, np.ones(3) / 3, mode="valid")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--yunet")
    ap.add_argument("--fps", type=float, default=4, help="face samples per second of source")
    ap.add_argument("--margin", type=float, default=0.07, help="room between face box and crop edge (fraction of width)")
    ap.add_argument("--score", type=float, default=0.5, help="YuNet score threshold (0.5 also finds a turned-away profile)")
    ap.add_argument("--min-width", type=float, default=0.11,
                    help="ignore faces narrower than this fraction of the width (wide two-shots: about 0.04)")
    ap.add_argument("--guest-side", choices=("any", "left", "right"), default="any",
                    help="the guest's half of the frame when both people are in it; any = one person in frame")
    ap.add_argument("--write", action="store_true", help="write crop_track into the EDL")
    a = ap.parse_args()
    p = pathlib.Path(a.edl).resolve()
    edl = json.loads(p.read_text())
    src = (p.parent / edl["source"]["video"]).resolve()
    src_size = B.probe_display_size(src)
    size = detect_size(src_size)
    cw = crop_fraction(src_size, edl["target"])
    if cw >= 1:
        raise SystemExit("the source is not wider than the target: nothing to reframe")
    model, dets = model_path(a.yunet), {}
    for seg in edl["segments"]:
        seg.pop("crop_track", None)
        c = seg.get("crop")
        if c is None or seg["part"] == "title":
            continue
        o = seg.get("reframe") or {}
        margin, score = o.get("margin", a.margin), o.get("score", a.score)
        if score not in dets:
            dets[score] = cv2.FaceDetectorYN.create(model, "", size, score)
        side = face_side(seg.get("crop_on") or seg.get("speaker") or "G", a.guest_side)
        pieces, need = [], False
        for q in seg["pieces"]:
            s = faces_over(src, q[0], q[1], a.fps, dets[score], size, a.min_width, side)
            pieces.append(s)
            for _, x0, x1 in s:
                if x0 is not None and (x0 - (c - cw / 2) < margin or (c + cw / 2) - x1 < margin):
                    need = True
        if not need:
            print(f"{seg['id']:>4} fixed {c}")
            continue
        pts = []
        for s in pieces:
            path = track(s, c, margin, cw)
            pts += rdp([(round(t, 3), round(float(x), 4)) for (t, _, _), x in zip(s, path)], 0.004)
        seg["crop_track"] = [list(x) for x in pts]
        xs = [x for _, x in pts]
        print(f"{seg['id']:>4} track {len(pts)} points, centre {min(xs):.3f}-{max(xs):.3f} (fixed was {c})")
    if a.write:
        p.write_text(json.dumps(edl, ensure_ascii=False, indent=1))
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
