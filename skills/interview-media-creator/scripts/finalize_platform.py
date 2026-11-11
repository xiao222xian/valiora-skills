#!/usr/bin/env python3
"""Mux the rendered picture with the approved mix into a WeChat Channels file, then run the encoded-file checks.

usage: finalize_platform.py --video render/review-v0.1-video.mp4 --audio audio/mix-v0.1/final-mix.wav \
         --out deliverables/review-v0.1.mp4 --title "片名" --artist "出品方" [--qc-dir qc] [--contact-fps 5]
         [--timeline remotion/public/data/timeline.json] [--phone] [--no-scan]

1. H.264 High@4.1, CRF 20 with maxrate 9 Mbps (Channels recommends <= 10 Mbps), GOP 60, AAC 256 kbps 48 kHz,
   faststart. Metadata carries only title and producer.
2. bt709 colour tags are written into the H.264 bitstream with h264_metadata (the -colorspace/-color_*
   output flags alone were observed to read back as "unknown").
3. Full decode with -xerror. Contact sheets from the encoded file: qc/contact-<stem>-01.jpg ... at --contact-fps
   (default 5, the delivery-contract floor), 48 tiles a page, for the frame-by-frame look; plus an overview
   every 3 s, qc/contact-<stem>-overview-01.jpg ..., 60 tiles a page. Old pages of the same stem are replaced.
4. One decode pass over every frame of the encoded file:
   - privacy scan: OpenCV QR detectors (about 40 ms a frame at 1080x1920). Hits are candidates for a human to
     judge; no hits does not replace looking at every contact sheet page. --no-scan skips it.
   - single-frame glitch scan (glitch_scan.py): a frame that differs from both neighbours while they agree, which
     the 5 fps sheets step over; a previous / this / next strip per hit in qc/glitch-<stem>/. --timeline (this
     version's timeline.json) tags hits inside the outro and photo-insert flashes; every hit is judged on its strip.
5. --phone: a 540x960 copy for reviewing on a phone; the video bitrate is derived from the duration so the file
   stays under 28 MB, and a WARN is printed if it still exceeds the 30 MB remote file transfer limit.
Writes qc/finalize-<stem>.json (probe, sha256, sheets, QR and glitch scans). Run lov-media-creator's audio_qc.py and
media_probe.py on the output as well.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import pathlib
import subprocess
import sys

import cv2
import numpy as np

sys.dont_write_bytecode = True  # importing glitch_scan must not leave __pycache__ inside the skill
spec = importlib.util.spec_from_file_location("glitch_scan", pathlib.Path(__file__).resolve().parent / "glitch_scan.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def sh(cmd):
    subprocess.run(cmd, check=True)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--video", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--artist", required=True)
    ap.add_argument("--qc-dir", default="qc")
    ap.add_argument("--contact-fps", type=float, default=5.0, help="tiles per second on the paginated contact sheets")
    ap.add_argument("--timeline", help="this version's remotion/public/data/timeline.json: tags glitch-scan hits in the outro and flash inserts")
    ap.add_argument("--phone", action="store_true")
    ap.add_argument("--no-scan", action="store_true", help="skip the QR privacy scan (the glitch scan still runs)")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.mp4")
    sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", a.video, "-i", a.audio, "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "9M", "-bufsize", "18M", "-profile:v", "high",
        "-level", "4.1", "-g", "60", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
        "-shortest", "-map_metadata", "-1", str(tmp)])
    sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(tmp), "-map", "0", "-c", "copy",
        "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0",
        "-movflags", "+faststart", "-metadata", f"title={a.title}", "-metadata", f"artist={a.artist}", str(out)])
    tmp.unlink()
    sh(["ffmpeg", "-v", "error", "-xerror", "-i", str(out), "-f", "null", "-"])
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                    "format=duration,bit_rate:stream=codec_name,width,height,r_frame_rate,bit_rate,color_primaries,color_transfer,sample_rate,channels",
                                    "-of", "json", str(out)], capture_output=True, text=True).stdout)
    dur = float(pr["format"]["duration"])
    v = next(s for s in pr["streams"] if s["codec_name"] == "h264")
    num, den = v["r_frame_rate"].split("/")
    fps = int(num) / int(den)
    qc = pathlib.Path(a.qc_dir)
    qc.mkdir(parents=True, exist_ok=True)
    sheets = {}
    for name, rate, cols, rows in (("", a.contact_fps, 8, 6), ("overview-", 1 / 3, 10, 6)):
        pattern = qc / f"contact-{out.stem}-{name}%02d.jpg"
        for old in qc.glob(f"contact-{out.stem}-{name}[0-9]*.jpg"):
            old.unlink()
        sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(out), "-vf",
            # round=up: with the default rounding the 1/3 fps overview tiles were labelled ~1.5 s before the frame shown
            f"fps={rate}:round=up,scale=180:-2,drawtext=text='%{{pts\\:hms}}':x=3:y=3:fontsize=14:fontcolor=yellow:box=1:boxcolor=black,"
            f"tile={cols}x{rows}:padding=4:color=gray", "-fps_mode", "passthrough", str(pattern)])
        pages = len(list(qc.glob(f"contact-{out.stem}-{name}[0-9]*.jpg")))
        need = math.ceil(dur * rate / (cols * rows))
        sheets[name.rstrip("-") or "frames"] = {"fps": round(rate, 3), "tiles_per_page": cols * rows, "pages": pages,
                                                "pattern": str(pattern)}
        if pages < need:
            raise SystemExit(f"contact sheet {pattern}: {pages} pages, {need} needed for {dur:.1f}s")
    report = {"file": str(out), "sha256": sha(out), "probe": pr, "contact_sheets": sheets}
    cap = cv2.VideoCapture(str(out))
    dets = []
    if not a.no_scan:
        dets = [cv2.QRCodeDetector()]
        try:
            dets.append(cv2.QRCodeDetectorAruco())
        except AttributeError:
            pass
    gs = G.Scan(fps, qc / f"glitch-{out.stem}")
    hits, n = [], 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        gs.push(im)
        h, w = im.shape[:2]
        for d in dets:
            for img, sc in ((cv2.resize(im, (w // 2, h // 2)), 2), (im, 1)):
                try:
                    ok2, pts = d.detectMulti(img)
                except cv2.error:
                    ok2, pts = False, None
                if ok2 and pts is not None and len(pts):
                    hits.append({"t": round(n / fps, 2), "pts": (np.array(pts) * sc).astype(int).tolist()})
                    break
        n += 1
    if not a.no_scan:
        report["privacy_scan"] = {"frames_scanned": n, "frames_total": round(dur * fps), "hits": hits}
    report["glitch_scan"] = gs.report(a.timeline)
    if a.phone:
        phone = out.with_name(out.stem + "-phone540p.mp4")
        kbps = max(200, min(1100, int(28e6 * 8 / dur / 1000 * 0.96) - 96))
        sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(out), "-vf", "scale=540:-2", "-c:v", "libx264", "-preset", "slow",
            "-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.3)}k", "-bufsize", f"{kbps * 2}k", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(phone)])
        mb = phone.stat().st_size / 1e6
        report["phone_preview"] = {"file": str(phone), "video_kbps": kbps, "mb": round(mb, 1)}
        if mb > 30:
            print(f"WARN {phone} is {mb:.1f} MB, over the 30 MB transfer limit")
    (qc / f"finalize-{out.stem}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    scan, glitch = report.get("privacy_scan"), report["glitch_scan"]
    print(f"{out}: {dur:.2f}s, {v['width']}x{v['height']}, video {int(v.get('bit_rate', 0)) / 1e6:.2f} Mbps, "
          f"colour {v.get('color_primaries')}/{v.get('color_transfer')}, sha256 {report['sha256'][:16]}")
    print(f"contact sheets: {sheets['frames']['pages']} pages at {a.contact_fps:g} fps, {sheets['overview']['pages']} overview pages; "
          + (f"QR scan {scan['frames_scanned']}/{scan['frames_total']} frames, {len(scan['hits'])} hits" if scan else "QR scan skipped")
          + f"; glitch scan {glitch['frames']} frames, {len(glitch['hits'])} single-frame hits"
          + (f"; phone preview {report['phone_preview']['mb']} MB" if a.phone else ""))
    if glitch.get("timeline_note"):
        print(f"WARN timeline {glitch['timeline_note']}")
    if glitch["hits"]:
        print(f"glitch scan hits (judge each strip in {glitch['strips']}):")
        print("\n".join(G.lines(glitch)))


if __name__ == "__main__":
    main()
