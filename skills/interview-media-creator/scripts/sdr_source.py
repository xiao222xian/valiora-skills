#!/usr/bin/env python3
"""Detect Dolby Vision in an interview recording and make its SDR video source with Apple's own tone mapping
(macOS avconvert), verified frame for frame against the original.

usage: sdr_source.py SOURCE.MOV [--out work/src/<stem>-sdr709.mov] [--edl-dir work] [--check] [--force] [--replace]

- Detection: ffprobe side data "DOVI configuration record" on the video stream (iPhone HDR video is Dolby
  Vision profile 8.4: an HLG base layer plus RPU metadata). Without it the script reports the transfer curve
  and exits 0: build_timeline.py tone-maps plain HLG/PQ itself.
- Why: ffmpeg zscale + tonemap ignores the Dolby Vision metadata. On iPhone 17 Pro profile 8.4 footage it
  rendered a wall at luma 205 where Apple's pipeline gives 129 and turned a brown shirt pink; the
  avconvert PresetHighestQuality output matched the on-site photos and AVAssetImageGenerator frames.
- Conversion: avconvert --preset PresetHighestQuality (H.264, bt709, rotation applied) into --out, about
  10 Mbps for 1080p30 (27 minutes -> 2.2 GB); run it in the background for a long recording. An existing
  --out is only verified, unless --replace.
- Verification (exit 1 on failure): the output video is bt709 (primaries, transfer, matrix); its frame
  count (packets, or duration x frame rate when an edit list makes them differ), start time and duration
  match the source video within one frame, and its start matches the
  source audio start. The audio stays the original: extract audio/source-*.wav from SOURCE.MOV, never
  from the SDR file.
- Writes <out>.json (both probes and the checks) and prints the path for EDL "source.video", relative to
  --edl-dir (default work, where the EDL lives).
- --check: detect and print only. --force: convert even without Dolby Vision.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
from fractions import Fraction


def probe(path):
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                   "stream=index,codec_type,codec_name,width,height,color_space,color_transfer,"
                                   "color_primaries,r_frame_rate,start_time,duration,nb_frames:stream_side_data",
                                   "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout)
    v = next((s for s in d["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in d["streams"] if s.get("codec_type") == "audio"), None)
    if v is None:
        raise SystemExit(f"{path}: no video stream")
    return v, a


def dovi(v):
    for sd in v.get("side_data_list", []) or []:
        if sd.get("side_data_type") == "DOVI configuration record":
            return {k: sd.get(k) for k in ("dv_profile", "dv_level", "dv_bl_signal_compatibility_id",
                                           "rpu_present_flag", "el_present_flag", "bl_present_flag")}
    return None


def num(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("source")
    ap.add_argument("--out", help="SDR file (default work/src/<stem>-sdr709.mov)")
    ap.add_argument("--edl-dir", default="work", help="directory of the EDL, for the printed source.video path")
    ap.add_argument("--check", action="store_true", help="only detect and print")
    ap.add_argument("--force", action="store_true", help="convert even without Dolby Vision")
    ap.add_argument("--replace", action="store_true", help="convert again although --out exists")
    a = ap.parse_args()

    src = pathlib.Path(a.source).resolve()
    v, au = probe(src)
    dv = dovi(v)
    transfer = v.get("color_transfer") or "unknown"
    if dv:
        print(f"Dolby Vision profile {dv['dv_profile']}.{dv['dv_bl_signal_compatibility_id']} level {dv['dv_level']}, "
              f"base layer transfer {transfer}: use the avconvert SDR source")
    else:
        print(f"no Dolby Vision (transfer {transfer})"
              + ("; build_timeline.py tone-maps HLG/PQ itself" if transfer in ("arib-std-b67", "smpte2084") else ""))
    if a.check or not (dv or a.force):
        return

    out = pathlib.Path(a.out) if a.out else pathlib.Path("work/src") / f"{src.stem}-sdr709.mov"
    out = pathlib.Path(os.path.abspath(out))  # keep a symlinked --out in place
    out.parent.mkdir(parents=True, exist_ok=True)
    fps = Fraction(v.get("r_frame_rate") or "30/1")
    frame = float(1 / fps) if fps else 1 / 30
    dur = num(v.get("duration"), 0.0)
    if a.replace or not out.exists():
        if not shutil.which("avconvert"):
            raise SystemExit("avconvert is macOS-only: without it build_timeline.py falls back to ffmpeg tone mapping, "
                             "which renders Dolby Vision too bright and magenta; tell the author before rendering")
        w, h = v.get("width") or 1920, v.get("height") or 1080
        est = dur * 10.6e6 / 8 * (w * h) / (1920 * 1080) * float(fps) / 30
        free = shutil.disk_usage(out.parent).free
        if free < est * 1.5:
            raise SystemExit(f"not enough disk: about {est / 1e9:.1f} GB needed (x1.5), {free / 1e9:.1f} GB free")
        tmp = out.with_name(out.stem + ".part.mov")
        print(f"avconvert {src.name} -> {out.name} (about {est / 1e9:.1f} GB, {dur / 60:.0f} min of video)", flush=True)
        r = subprocess.run(["avconvert", "--source", str(src), "--output", str(tmp), "--preset", "PresetHighestQuality",
                            "--replace"], capture_output=True, text=True)
        if r.returncode != 0 or not tmp.exists():
            raise SystemExit(f"avconvert failed ({r.returncode}): {(r.stderr or r.stdout)[-400:]}")
        tmp.replace(out)

    ov, _ = probe(out)
    shown = [round(num(s.get("duration"), 0.0) * float(fps)) for s in (v, ov)]  # an edit list makes packet counts differ
    checks = {
        "bt709": all(ov.get(k) == "bt709" for k in ("color_primaries", "color_transfer", "color_space")),
        "frames": v.get("nb_frames") == ov.get("nb_frames") or abs(shown[0] - shown[1]) <= 1,
        "start": abs(num(ov.get("start_time"), 0.0) - num(v.get("start_time"), 0.0)) <= frame,
        "duration": abs(num(ov.get("duration"), 0.0) - dur) <= frame,
        "audio_start": au is None or abs(num(ov.get("start_time"), 0.0) - num(au.get("start_time"), 0.0)) <= frame,
    }
    report = {"source": str(src), "out": str(out), "dolby_vision": dv, "checks": checks,
              "source_video": v, "source_audio": au, "sdr_video": ov}
    out.with_suffix(out.suffix + ".json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"frames {v.get('nb_frames')} / {ov.get('nb_frames')} (by duration {shown[0]} / {shown[1]}), start {v.get('start_time')} / {ov.get('start_time')}, "
          f"duration {v.get('duration')} / {ov.get('duration')}, colour {ov.get('color_primaries')}/"
          f"{ov.get('color_transfer')}/{ov.get('color_space')}")
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise SystemExit(f"FAIL {', '.join(failed)}: do not use {out.name} as the EDL source")
    print(f'EDL "source.video": "{os.path.relpath(out, pathlib.Path(a.edl_dir).resolve())}"  '
          f"(audio stays the original: extract the WAVs from {src.name})")


if __name__ == "__main__":
    main()
