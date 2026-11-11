# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["librosa", "numpy"]
# ///
"""Beat analysis of the per-chapter music takes (librosa; not installed system-wide, so run it through uv):

  uv run --quiet --python 3.12 --with librosa python audio/chapters/analyze.py          # every *.mp3 next to this file
  uv run --quiet --python 3.12 --with librosa python audio/chapters/analyze.py a.mp3 ...

Writes audio/chapters/analysis.json, read by tools/music_bed.py. Two passes per take:

Selection (picks the take): first beat, beat clarity (mean onset strength on the beats over the overall mean:
higher = a clearer beat), ibi_cv (spread of the inter-beat intervals: lower = steadier) and the first loud moment.
These numbers and the auto-pick thresholds in music_bed.py were calibrated together; keep them as they are.

Beat grid (places the take): a least-squares line through the steady beats (after SETTLE s: librosa's first beats
are unstable while the tracker settles), giving the beat period and phase, and resid_ms, the median distance of
the beats from that line. A good take reads about 3 ms; a take whose tempo wanders reads tens of ms and music_bed.py
passes it over for the other take (MAX_RESID_MS there). The bar phase is the one of every four grid beats with
the most onset strength; downbeats lists those bar starts in the take's own seconds (when the four bar_strength
values are close the bar is a guess; the beat under it is still on the grid). bpm is 60 / period.
librosa's own tempo estimate is quantised to its frame grid (a 120 BPM take reads 117.45 or 123.05 there, single
beat intervals likewise), so judge the tempo by bpm, never by tempo.

(2026-10-12, 《如何打造一款特斯拉》 v0.5: placing the third bar at first beat + 4 s put 6 of 13 cues 94-244 ms off
the picture's beat grid, two of them by half a beat; the fitted grid puts all 13 on the same phase.)
"""
import glob
import json
import os
import sys

import librosa
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SETTLE = 1.0  # s: beats before this stay out of the grid fit
GRID_HOP = 256  # finer onset frames for the grid (11.6 ms at 22050 Hz)


def fit_grid(y, sr):
    """Beat period and phase from the steady beats, the fit residual, and the bar downbeats."""
    dur = len(y) / sr
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=GRID_HOP)
    _, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=GRID_HOP, units="time",
                                       start_bpm=120, tightness=200)
    b = beats[beats > SETTLE]
    if len(b) < 8:
        return {"period": None, "resid_ms": None, "downbeats": []}
    d = np.diff(b)
    # beat index of each tracked beat: whole steps of the median interval, so a dropped beat counts as two
    k = np.concatenate([[0], np.cumsum(np.maximum(1, np.round(d / np.median(d))))])
    period, t0 = np.polyfit(k, b, 1)
    resid = float(np.median(np.abs(b - (t0 + period * k))))
    # every grid beat in the take, and which of every four carries the most onset strength
    idx = np.arange(-int(np.floor(t0 / period)), int((dur - t0) / period) + 1)
    grid = t0 + period * idx
    keep = (grid >= 0) & (grid < dur)
    grid, idx = grid[keep], idx[keep]
    fr = np.clip(librosa.time_to_frames(grid, sr=sr, hop_length=GRID_HOP), 0, len(oenv) - 1)
    strength = oenv[fr]
    bar = [float(np.mean(strength[idx % 4 == j])) for j in range(4)]
    j = int(np.argmax(bar))
    return {"period": round(float(period), 6), "phase": round(float(t0), 4), "resid_ms": round(resid * 1000, 1),
            "bar_strength": [round(v, 2) for v in bar], "downbeats": [round(float(t), 4) for t in grid[idx % 4 == j]]}


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(HERE, "*.mp3")))
    out = os.path.join(HERE, "analysis.json")
    res = json.load(open(out)) if os.path.exists(out) else {}
    for f in files:
        y, sr = librosa.load(f, sr=22050, mono=True)
        oenv = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, units="time", start_bpm=120, tightness=120)
        tempo = float(np.atleast_1d(tempo)[0])
        bframes = librosa.time_to_frames(beats, sr=sr)
        bframes = bframes[bframes < len(oenv)]
        clarity = float(np.mean(oenv[bframes]) / (np.mean(oenv) + 1e-9)) if len(bframes) else 0.0
        ibi = np.diff(beats)
        ibi_cv = float(np.std(ibi) / (np.mean(ibi) + 1e-9)) if len(ibi) > 2 else 1.0
        rms = librosa.feature.rms(y=y)[0]
        first_loud = float(librosa.frames_to_time(np.argmax(rms > 0.25 * rms.max()), sr=sr))
        g = fit_grid(y, sr)
        res[os.path.basename(f)] = {
            "tempo": round(tempo, 2), "bpm": round(60 / g["period"], 2) if g["period"] else 0.0,
            "first_beat": round(float(beats[0]) if len(beats) else -1, 3), "clarity": round(clarity, 2),
            "ibi_cv": round(ibi_cv, 3), "first_loud": round(first_loud, 2), "dur": round(len(y) / sr, 2), **g}
    json.dump(res, open(out, "w"), indent=1)
    for k in sorted(res):
        v = res[k]
        resid = f"{v['resid_ms']:5.1f} ms" if v.get("resid_ms") is not None else "  none  "
        print(f"{k:20s} bpm {v['bpm']:6.2f}  grid resid {resid}  first beat {v['first_beat']:.2f}  clarity {v['clarity']:.2f}  "
              f"ibi_cv {v['ibi_cv']:.3f}  downbeats {v.get('downbeats', [])[:3]}  {v['dur']} s")
    print(out)


if __name__ == "__main__":
    main()
