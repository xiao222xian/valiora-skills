#!/usr/bin/env python3
"""Verify cut points empirically: list voiced intervals around a cut and re-transcribe trial cuts.

usage:
  probe_cuts.py SOURCE.wav intervals 476.0:478.8 [218.4:219.6 ...]
  probe_cuts.py SOURCE.wav in  '[["5a",[477.8,478.1,478.33],2.2]]' [--models large-v3,turbo]
  probe_cuts.py SOURCE.wav out '[["6d",543.3,[545.48,545.8]]]'

- intervals: speech-band (300-3400 Hz) 10 ms envelope above -52 dB, merged into voiced intervals.
  Candidate in points sit just before an interval, candidate out points just after one.
- in: for each candidate start t, transcribe [t, t+dur] with two Whisper models. Pick the earliest
  candidate whose transcript starts with the intended first word and carries no leftover filler.
- out: for each candidate end t, transcribe [start, t]. Pick the candidate whose transcript ends with the
  intended last word ("一下", "合照") without picking up the next speaker.
- in / out cut every window first, then each model loads once and transcribes all of them (progress on
  stderr); the table prints after both models finish. mlx-whisper keeps a single model in memory, so
  switching models per window reloads the weights (about 3 GB for large-v3) for every candidate.
- Short windows (< 1.5 s) make Whisper hallucinate ("请不吝点赞订阅…", repeated syllables). Treat those as
  noise and lengthen the window; one model agreeing with the envelope is enough.
- Whisper word timestamps from a long pass can be ~0.5 s early late in the file: never trust them for a
  final cut without this probe.
- --models: the aliases large-v3 and turbo (default both), Hugging Face repos or local model directories.
  The first run downloads both (about 3.1 GB + 1.6 GB); once they are cached, HF_HUB_OFFLINE=1 skips the
  online check. Rebuilding a cleared cache without the Python downloader: SKILL.md Step 0.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

MODEL_ALIASES = {"large-v3": "mlx-community/whisper-large-v3-mlx", "turbo": "mlx-community/whisper-large-v3-turbo"}
PROMPT = "以下是普通话访谈，使用简体中文。"


def envelope(wav):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-af", "highpass=f=300,lowpass=f=3400", "-f", "f32le",
                          "-ac", "1", "-ar", "48000", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    n = len(x) // 480
    return 20 * np.log10(np.sqrt((x[: n * 480].reshape(n, 480) ** 2).mean(1)) + 1e-9)


def intervals(db, a, b, thr=-52.0, min_frames=3):
    seg = db[int(a * 100):int(b * 100)]
    out, st = [], None
    for i, v in enumerate(seg):
        if v > thr and st is None:
            st = i
        if v <= thr and st is not None:
            if i - st >= min_frames:
                out.append((round(a + st / 100, 2), round(a + i / 100, 2), round(float(seg[st:i].max()), 1)))
            st = None
    if st is not None:
        out.append((round(a + st / 100, 2), round(b, 2), round(float(seg[st:].max()), 1)))
    return out


def model_list(spec):
    return [MODEL_ALIASES.get(m.strip(), os.path.expanduser(m.strip())) for m in spec.split(",") if m.strip()]


def cut(wav, a, b, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-to", str(b), "-i", wav, "-ac", "1", "-ar", "16000",
                    "-af", f"afade=t=in:d=0.006,afade=t=out:st={max(0.0, b - a - 0.01):.3f}:d=0.01", out], check=True)
    return out


def transcribe_all(wavs, models):
    """-> per WAV, one transcript per model. Model by model: mlx-whisper caches only the last model it loaded."""
    import mlx_whisper
    try:
        import opencc
        conv = opencc.OpenCC("t2s").convert
    except ImportError:
        conv = lambda s: s  # noqa: E731
    out = [[] for _ in wavs]
    for m in models:
        print(f"transcribing {len(wavs)} windows with {m.rstrip('/').split('/')[-1]}", file=sys.stderr, flush=True)
        for o, f in zip(out, wavs):
            o.append(conv(mlx_whisper.transcribe(f, path_or_hf_repo=m, language="zh", temperature=0.0, initial_prompt=PROMPT,
                                                 condition_on_previous_text=False)["text"]).strip())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("source", help="mono WAV of the source recording (48 kHz or 16 kHz)")
    ap.add_argument("mode", choices=["intervals", "in", "out"])
    ap.add_argument("spec", nargs="+")
    ap.add_argument("--models", default="large-v3,turbo",
                    help="comma-separated: large-v3, turbo, Hugging Face repos or local model directories")
    a = ap.parse_args()
    models = model_list(a.models)
    if a.mode == "intervals":
        db = envelope(a.source)
        for s in a.spec:
            t0, t1 = map(float, s.split(":"))
            print(f"{t0}-{t1}:", intervals(db, t0, t1))
        return
    tests = json.loads(a.spec[0])
    if a.mode == "in":  # (name, candidate, window start, window end)
        rows = [(name, c, c, c + dur) for name, cands, dur in tests for c in cands]
    else:
        rows = [(name, c, start, c) for name, start, cands in tests for c in cands]
    with tempfile.TemporaryDirectory() as tmp:
        texts = transcribe_all([cut(a.source, t0, t1, f"{tmp}/{i:04d}.wav") for i, (_, _, t0, t1) in enumerate(rows)], models)
    for (name, c, _, _), o in zip(rows, texts):
        if a.mode == "in":
            print(f"{name:5s} in  {c:8.2f} | " + " | ".join(f"{x[:28]:30s}" for x in o))
        else:
            print(f"{name:5s} out {c:8.2f} | " + " | ".join(f"…{x[-28:]:30s}" for x in o))


if __name__ == "__main__":
    main()
