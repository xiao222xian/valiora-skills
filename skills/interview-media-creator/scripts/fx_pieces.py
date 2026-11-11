#!/usr/bin/env python3
"""Per-piece skin smoothing (natural or strong) + face boxes, cached, then concat into the mezzanine.

usage: fx_pieces.py EDL.json [--yunet PATH] [--level natural|strong] [--strength 0.7] [-j 4] [--no-beauty]
                    [--copy-to work/remotion/public/media] [--remotion-data remotion/public/data]
       fx_pieces.py --photo IN.jpg OUT.jpg [--yunet PATH] [--level natural|strong] [--strength 0.6]

- Faces: OpenCV YuNet (face_detection_yunet ONNX) at half resolution; boxes smoothed across frames, kept
  for 8 frames when lost. The model path comes from --yunet, $YUNET_MODEL, or ~/models/yunet.onnx.
- Beauty: edge-preserving bilateral smoothing inside (skin chroma ∩ face ellipse), feathered, lifted,
  blended at --strength (default: the level's). Face shape and background are untouched at both levels.
  --no-beauty only measures faces.
  - natural (default): sigmaColor 26, sigmaSpace face width / 24, lift x1.05 + 3, strength 0.7.
  - strong, for a guest who asks for visible retouching (对话易七猫 v0.3, 「要修！」): bilateral at half
    resolution (sigmaColor 40, sigmaSpace face width / 32 there) scaled back, lift x1.06 + 4, then gamma 0.91
    on the whole frame, strength 1.0. The gamma comes from the guest's own retouched copy, measured against the
    same frame of v0.2: the whole frame +8.8 Y, the face +8.3.
  Speed trap: at full resolution the strong kernel is about a fifth of the face width (113 px for a 595 px
  face): 0.5-1 s per face against 56-93 ms at half resolution, and four workers managed only 2.6 frames/s on
  对话易七猫. Half and full resolution differ by 0.4-0.6 levels on average. At half resolution strong is faster
  than natural, which runs at full resolution (112-125 ms against 280-406 ms per frame on two close-ups).
- Colour: pieces are decoded with the BT.709 matrix and re-encoded as BT.709 limited range with bt709 tags,
  the same as build_timeline's pieces, so Remotion decodes the mezzanine without a colour shift.
- Every render/seg/v-*.mp4 becomes v-*.fx.mp4 + v-*.faces.json (per frame [cx, cy, w] in 0..1 or null) +
  v-*.fx.json (the level / strength / beauty / model it was made with), so editing the EDL only processes new
  pieces and changing --level, --strength or --no-beauty recomputes. A piece whose encoder or decoder fails, or
  whose output frame count differs from the source piece, is not cached and the run exits 1.
- The concat list is rewritten to the .fx files and render/mezz-<version>.mp4 is assembled losslessly. Its
  frame count must equal timeline.json "frames" when <EDL dir>/<--remotion-data>/timeline.json exists
  (exit 1 otherwise). --copy-to DIR then clones it into DIR (APFS clone, else a copy) for Remotion.
- Show the author a close-up before/after crop before delivery; switch off when they say so.
"""
import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import cv2
import numpy as np


def model_path(arg):
    for p in (arg, os.environ.get("YUNET_MODEL"), str(pathlib.Path.home() / "models" / "yunet.onnx")):
        if p and pathlib.Path(p).exists():
            return p
    raise SystemExit("YuNet model not found: pass --yunet PATH or set YUNET_MODEL "
                     "(face_detection_yunet_2023mar.onnx from the OpenCV model zoo)")


SKIN_ALGO = "adaptive-v1"  # recorded in <piece>.fx.json so a change of algorithm recomputes cached pieces

# space = (d, floor): sigmaSpace = max(floor, face width / d) at the resolution the bilateral runs at
LEVELS = {
    "natural": {"strength": 0.7, "half": False, "sigma_color": 26, "space": (24, 3.0), "lift": (1.05, 3), "gamma": None},
    "strong": {"strength": 1.0, "half": True, "sigma_color": 40, "space": (32, 1.5), "lift": (1.06, 4), "gamma": 0.91},
}


def skin_mask(ycc, centre, bw, bh):
    """Skin = pixels whose chroma is close to this face's own skin chroma, sampled on the cheeks and nose.
    A fixed YCrCb range (Cr 133-175, Cb 77-128) misses most of the face under coloured light: under a purple
    mood light the face measured Cr 176-181, and the fixed range covered only 5-18 % of it. Falls back to the
    fixed range when the sampled chroma does not look like skin at all."""
    inner = np.zeros(ycc.shape[:2], np.uint8)
    cv2.ellipse(inner, (int(centre[0]), int(centre[1])), (max(2, int(bw * 0.3)), max(2, int(bh * 0.3))), 0, 0, 360, 255, -1)
    sel = (inner > 0) & (ycc[..., 0] >= 60)
    if sel.sum() < 50:
        return cv2.inRange(ycc, (0, 133, 77), (255, 175, 128))
    cr0, cb0 = float(np.median(ycc[..., 1][sel])), float(np.median(ycc[..., 2][sel]))
    if not (125 <= cr0 <= 200 and 70 <= cb0 <= 150):
        return cv2.inRange(ycc, (0, 133, 77), (255, 175, 128))
    lo = (60, max(0, cr0 - 12), max(0, cb0 - 12))
    hi = (255, min(255, cr0 + 12), min(255, cb0 + 12))
    return cv2.inRange(ycc, tuple(int(round(v)) for v in lo), tuple(int(round(v)) for v in hi))


class Beauty:
    def __init__(self, w, h, model, strength=0.7, enabled=True, level="natural"):
        self.w, self.h, self.k, self.enabled, self.lv = w, h, strength, enabled, LEVELS[level]
        self.det = cv2.FaceDetectorYN.create(model, "", (w // 2, h // 2), 0.7, 0.3, 50)
        self.tracks = []
        g = self.lv["gamma"]
        self.lut = np.clip(np.round(255 * (np.arange(256) / 255) ** g), 0, 255).astype(np.uint8) if g else None

    def faces(self, im):
        small = cv2.resize(im, (self.w // 2, self.h // 2), interpolation=cv2.INTER_AREA)
        _, f = self.det.detect(small)
        boxes = [np.array(r[:4], np.float32) * 2 for r in (f if f is not None else []) if r[2] * 2 >= 50]
        new = []
        for b in boxes:
            c = b[:2] + b[2:] / 2
            best = min(self.tracks, key=lambda t: np.linalg.norm(t[0][:2] + t[0][2:] / 2 - c), default=None)
            if best is not None and np.linalg.norm(best[0][:2] + best[0][2:] / 2 - c) < 0.6 * b[2]:
                best[0][:] = 0.6 * best[0] + 0.4 * b
                best[1] = 8
                new.append(best)
            else:
                new.append([b.copy(), 8])
        for t in self.tracks:
            if all(t is not n for n in new) and t[1] > 0:
                t[1] -= 1
                new.append(t)
        self.tracks = [t for t in new if t[1] > 0]
        return [t[0] for t in self.tracks], bool(boxes)

    def apply(self, im):
        faces, detected = self.faces(im)
        if self.enabled:
            for (x, y, bw, bh) in faces:
                x0, y0 = int(max(0, x - 0.35 * bw)), int(max(0, y - 0.45 * bh))
                x1, y1 = int(min(self.w, x + 1.35 * bw)), int(min(self.h, y + 1.25 * bh))
                if x1 - x0 < 20 or y1 - y0 < 20:
                    continue
                roi = im[y0:y1, x0:x1]
                skin = skin_mask(cv2.cvtColor(roi, cv2.COLOR_BGR2YCrCb), (x + bw / 2 - x0, y + bh * 0.55 - y0), bw, bh)
                skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
                ell = np.zeros_like(skin)
                cv2.ellipse(ell, (int(x + bw / 2 - x0), int(y + bh * 0.48 - y0)), (int(bw * 0.62), int(bh * 0.82)), 0, 0, 360, 255, -1)
                m = cv2.GaussianBlur(cv2.bitwise_and(skin, ell).astype(np.float32) / 255.0, (0, 0), max(2.0, bw / 14))[..., None]
                div, floor = self.lv["space"]
                src = roi
                if self.lv["half"]:
                    src = cv2.resize(roi, (max(1, roi.shape[1] // 2), max(1, roi.shape[0] // 2)), interpolation=cv2.INTER_AREA)
                sm = cv2.bilateralFilter(src, d=0, sigmaColor=self.lv["sigma_color"], sigmaSpace=max(floor, bw / div))
                if self.lv["half"]:
                    sm = cv2.resize(sm, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_CUBIC)
                g, o = self.lv["lift"]
                lift = np.clip(sm.astype(np.float32) * g + o, 0, 255)
                im[y0:y1, x0:x1] = np.clip(roi.astype(np.float32) * (1 - self.k * m) + lift * (self.k * m), 0, 255).astype(np.uint8)
            if self.lut is not None:
                im = cv2.LUT(im, self.lut)
        big = max(faces, key=lambda b: b[2], default=None) if detected else None
        return im, big


def dims(path):
    s = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                        "-of", "json", str(path)], capture_output=True, text=True).stdout
    st = json.loads(s)["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    return st["width"], st["height"], round(int(num) / int(den))


def frame_count(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return int(re.sub(r"\D", "", out) or 0)


def one(job):
    src, model, strength, enabled, level = job
    src = pathlib.Path(src)
    dst = src.with_name(src.stem + ".fx.mp4")
    fj = src.with_name(src.stem + ".faces.json")
    meta = src.with_name(src.stem + ".fx.json")
    params = {"level": level, "strength": strength, "beauty": enabled, "model": pathlib.Path(model).name, "skin": SKIN_ALGO}
    if dst.exists() and fj.exists() and meta.exists() and json.loads(meta.read_text()) == params:
        return src.name, "cached", None
    W, H, fps = dims(src)
    want = frame_count(src)
    b = Beauty(W, H, model, strength, enabled, level)
    # swscale's default fast path darkens a YUV -> RGB -> YUV round trip by ~2 levels of Y; these flags make it exact
    sws = "flags=accurate_rnd+full_chroma_int"
    dec = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", str(src), "-vf", f"scale=in_color_matrix=bt709:{sws}",
                            "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    tmp = dst.with_suffix(".tmp.mp4")
    # ffmpeg 9 takes primaries / transfer from the frames: the -color_* output flags alone read back as "unknown",
    # so setparams tags the frames too
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-vf", f"scale=out_color_matrix=bt709:out_range=tv:{sws},"
                            "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv",
                            "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p",
                            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-video_track_timescale", "15360", str(tmp)], stdin=subprocess.PIPE)
    faces = []
    try:
        while True:
            buf = dec.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            im, big = b.apply(np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy())
            faces.append(None if big is None else [round(float(big[0] + big[2] / 2) / W, 4), round(float(big[1] + big[3] / 2) / H, 4),
                                                   round(float(big[2]) / W, 4)])
            enc.stdin.write(im.tobytes())
        enc.stdin.close()
    except BrokenPipeError:
        dec.kill()
        try:
            enc.stdin.close()
        except BrokenPipeError:
            pass
    rc_enc, rc_dec = enc.wait(), dec.wait()
    got = frame_count(tmp) if tmp.exists() else 0
    err = None
    if rc_dec != 0 or rc_enc != 0:
        err = f"decoder exit {rc_dec}, encoder exit {rc_enc}"
    elif not (len(faces) == got == want):
        err = f"source {want} frames, processed {len(faces)}, encoded {got}"
    if err:
        tmp.unlink(missing_ok=True)
        return src.name, "FAILED", err
    tmp.rename(dst)
    fj.write_text(json.dumps(faces))
    meta.write_text(json.dumps(params))
    return src.name, len(faces), None


def clone(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.unlink(missing_ok=True)
    if subprocess.run(["cp", "-c", str(src), str(dst)], capture_output=True).returncode != 0:
        shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl", nargs="?")
    ap.add_argument("--yunet")
    ap.add_argument("--level", choices=list(LEVELS), default="natural", help="strong: the guest asked for visible retouching")
    ap.add_argument("--strength", type=float, help="blend of the smoothed skin (default: natural 0.7, strong 1.0)")
    ap.add_argument("-j", type=int, default=4)
    ap.add_argument("--no-beauty", action="store_true")
    ap.add_argument("--photo", nargs=2, metavar=("IN", "OUT"))
    ap.add_argument("--copy-to", metavar="DIR", help="clone the mezzanine into DIR, e.g. work/remotion/public/media")
    ap.add_argument("--remotion-data", default="remotion/public/data", help="where timeline.json is (relative to EDL)")
    a = ap.parse_args()
    model = model_path(a.yunet)
    strength = LEVELS[a.level]["strength"] if a.strength is None else a.strength
    if a.photo:
        im = cv2.imread(a.photo[0])
        h, w = im.shape[:2]
        out, _ = Beauty(w, h, model, strength, not a.no_beauty, a.level).apply(im)
        cv2.imwrite(a.photo[1], out, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print("photo ->", a.photo[1])
        return
    if not a.edl:
        ap.error("EDL.json is required unless --photo is used")
    edl_path = pathlib.Path(a.edl).resolve()
    root, edl = edl_path.parent, json.loads(edl_path.read_text())
    ver = edl["version"]
    lst = [line.split("'")[1] for line in (root / "render" / f"concat-{ver}.txt").read_text().splitlines() if line.strip()]
    pieces = sorted({x for x in lst if pathlib.Path(x).name.startswith("v-")})
    failed = []
    with cf.ProcessPoolExecutor(a.j) as ex:
        for name, r, err in ex.map(one, [(p, model, strength, not a.no_beauty, a.level) for p in pieces]):
            print(name, r, err or "", flush=True)
            if err:
                failed.append(name)
    if failed:
        sys.exit(f"{len(failed)} piece(s) failed, nothing cached for them: {' '.join(failed)}")
    fx = [str(pathlib.Path(x).with_name(pathlib.Path(x).stem + ".fx.mp4")) if pathlib.Path(x).name.startswith("v-") else x for x in lst]
    lst_fx = root / "render" / f"concat-fx-{ver}.txt"
    lst_fx.write_text("".join(f"file '{x}'\n" for x in fx))
    out = root / "render" / f"mezz-{ver}.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst_fx), "-c", "copy",
                    "-movflags", "+faststart", str(out)], check=True)
    n = frame_count(out)
    print(f"mezzanine {out} {n} frames")
    tl = root / a.remotion_data / "timeline.json"
    if tl.exists():
        want = json.loads(tl.read_text())["frames"]
        if n != want:
            sys.exit(f"mezzanine has {n} frames, {tl} has {want}: rebuild the timeline and pieces from the same EDL")
        print(f"frames match {tl}")
    if a.copy_to:
        dst = pathlib.Path(a.copy_to) / out.name
        clone(out, dst)
        print(f"copied -> {dst}")


if __name__ == "__main__":
    main()
