"""Snap planned chapter starts to the chosen track's real onsets on its beat grid.

  python3 audio/snap.py --plan 0,10,24.5,46                     # public/audio/bgm-music.wav (else bgm-master.wav), tempo from analyze.py
  python3 audio/snap.py --input bgm.wav --plan ... --bpm 120 --phase 0.023 --window 0.5 --out audio/snaps.json
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.signal import stft
from scipy.ndimage import uniform_filter1d

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze import analyze, load, SR

ap = argparse.ArgumentParser()
# onsets come from the music alone: the master may already carry the voice-over (tools/voice_mix.py)
MUSIC = HERE.parent / "public" / "audio" / "bgm-music.wav"
ap.add_argument("--input", default=str(MUSIC if MUSIC.exists() else HERE.parent / "public" / "audio" / "bgm-master.wav"))
ap.add_argument("--plan", required=True, help="planned chapter starts in seconds, comma-separated")
ap.add_argument("--bpm", type=float, help="default: estimated from the track by analyze.py")
ap.add_argument("--phase", type=float, help="first beat in seconds; default: estimated from the track")
ap.add_argument("--window", type=float, default=0.5, help="search +/- this many seconds around each planned start")
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--out", default=str(HERE / "snaps.json"))
args = ap.parse_args()

path = args.input
plan = [float(x) for x in args.plan.split(",")]
bpm, phase = args.bpm, args.phase
if bpm is None or phase is None:
    est = analyze(path)
    bpm = est["bpm"] if bpm is None else bpm
    phase = est["beat_phase_s"] if phase is None else phase
    print(f"tempo from analyze.py: bpm {bpm}  phase {phase}s")
period = 60 / bpm
y = load(path)
hop = 256
f, t, Z = stft(y, SR, nperseg=1024, noverlap=1024 - hop, boundary=None)
M = np.log(np.abs(Z) + 1e-6)
flux = np.r_[0, np.maximum(np.diff(M, axis=1), 0).sum(0)]
flux = np.maximum(flux - uniform_filter1d(flux, 64), 0)
fps = SR / hop
beats = phase + period * np.arange(int(len(y) / SR / period) + 1)
beats = beats[(beats * fps).astype(int) < len(flux)]  # a track padded to a whole beat ends past the last STFT frame
def strength(tsec):
    i = int(tsec * fps); return float(flux[max(i - 3, 0):i + 4].max())
bs = np.array([strength(b) for b in beats])
# bar phase: which beat offset (mod 4) carries the strongest accents
acc = [bs[k::4].mean() for k in range(4)]
bar_off = int(np.argmax(acc))
print("beat accents by offset mod 4:", [round(a, 1) for a in acc], "-> downbeat offset", bar_off)
med = np.median(bs)
out = []
for p in plan:
    near = [(abs(b - p), b, s) for b, s in zip(beats, bs) if abs(b - p) <= args.window]
    if not near:
        sys.exit(f"no beat within +/-{args.window}s of {p}s at {bpm} BPM; widen --window")
    cand = sorted(near, key=lambda x: (-x[2] / med + x[0] * 0.6))
    best = cand[0]
    k = int(round((best[1] - phase) / period))
    frame = int(round(best[1] * args.fps))
    out.append({"plan": p, "snap_s": round(best[1], 3), "frame": frame, "beat": k,
                "downbeat": (k - bar_off) % 4 == 0, "rel_strength": round(best[2] / med, 2)})
    print(f"plan {p:6.1f} -> {best[1]:7.3f}s  frame {frame:5d}  beat {k:3d}  downbeat {(k-bar_off)%4==0}  strength x{best[2]/med:.1f}")
json.dump({"input": path, "bpm": bpm, "phase": phase, "window": args.window, "fps": args.fps, "bar_offset": bar_off, "snaps": out},
          open(args.out, "w"), indent=1)
print(args.out)
