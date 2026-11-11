#!/usr/bin/env python3
"""Check BGM candidates and the final music stem.

usage:
  bgm_check.py candidates music/gen/a.mp3 music/gen/b.mp3 --lib music/lib [--isolate-bin PATH]
  bgm_check.py stem audio/mix-v0.1/stem-music.wav [--max-gap 2.0]

candidates: converts each file to 48 kHz stereo WAV in --lib, measures loudness, finds the audible end
(the point after which the track is digital silence: align cue ends to it, not to the file length), and
estimates vocals with Apple's voice isolation (AUSoundIsolation, macOS): the isolated "voice" of a clean
instrumental sits ~20 dB below the mix; less than 12 dB means sung or vocal-like content -> reject.
Whisper is not used for this: it hallucinates lyrics on instrumentals.
The isolation tool is compiled once from assets/tools/isolate.swift with swiftc (Xcode command line tools).

stem: longest run below -60 dBFS in the music stem; runs over --max-gap seconds are gaps to fix unless the
author asked for silence there.
"""
import argparse
import os
import pathlib
import re
import subprocess

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent


def lufs(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
    return float(m[-1]) if m else None


def rms_frames(path, hop_s=0.1):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    hop = int(48000 * hop_s)
    n = len(x) // hop
    return 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)


def isolate_bin(arg):
    if arg:
        return arg
    cache = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "lov-interview-media-creator"
    exe = cache / "isolate"
    if not exe.exists():
        cache.mkdir(parents=True, exist_ok=True)
        src = HERE.parent / "assets" / "tools" / "isolate.swift"
        subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], check=True)
    return str(exe)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=["candidates", "stem"])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--lib", default="music/lib")
    ap.add_argument("--isolate-bin")
    ap.add_argument("--max-gap", type=float, default=2.0)
    a = ap.parse_args()
    if a.mode == "stem":
        db = rms_frames(a.files[0], 0.01)
        low = db < -60
        run = worst = at = 0
        for i, v in enumerate(low):
            run = run + 1 if v else 0
            if run > worst:
                worst, at = run, i
        verdict = "GAP" if worst / 100 > a.max_gap else "ok"
        print(f"{verdict}: longest run below -60 dBFS {worst / 100:.2f}s ending at {at / 100:.2f}s of {len(db) / 100:.2f}s")
        return
    lib = pathlib.Path(a.lib)
    lib.mkdir(parents=True, exist_ok=True)
    exe = isolate_bin(a.isolate_bin)
    for f in a.files:
        f = pathlib.Path(f)
        wav = lib / f"gen-{f.stem}.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(f), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(wav)],
                       check=True)
        iso = lib / f".iso-{f.stem}.wav"
        subprocess.run([exe, str(wav), str(iso), "100"], check=True, capture_output=True)
        l_mix, l_iso = lufs(wav), lufs(iso)
        iso.unlink(missing_ok=True)
        db = rms_frames(wav)
        loud = np.where(db > -50)[0]
        audible_end = round((loud[-1] + 1) * 0.1, 1) if len(loud) else 0.0
        dur = len(db) * 0.1
        gap = None if l_mix is None or l_iso is None else round(l_mix - l_iso, 1)
        verdict = "instrumental" if gap is not None and gap >= 12 else "VOCAL-LIKE: reject"
        print(f"{f.name}: {dur:.1f}s, audible end {audible_end}s, {l_mix} LUFS, isolated voice {l_iso} LUFS "
              f"(gap {gap} dB) -> {verdict}; wav {wav}")


if __name__ == "__main__":
    main()
