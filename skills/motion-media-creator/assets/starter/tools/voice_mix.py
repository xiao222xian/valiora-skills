#!/usr/bin/env python3
"""Master the film's sound: music + voice-over (+ an optional effects stem) -> public/audio/bgm-master.wav.

  python3 tools/voice_mix.py

Music    public/audio/bgm-music.wav             the chosen track, any level
Voice    audio/narration/timing.json + clips/   from tools/narration.py; no timing.json = music only
Effects  audio/sfx/sfx-stem.wav                 optional premixed effects stem laid from frame 0
The voice stem is levelled once to about -17 LUFS; music ducks about -9 dB and effects about -4 dB under it
(0.2 s attack before each line, 0.6 s release after). Master: one linear gain to -16 LUFS integrated, then a
4x-oversampled limiter so the true peak stays at or below -1 dBTP. Nothing else touches dynamics.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "public" / "audio"
NAR = ROOT / "audio" / "narration"
SFX_STEM = ROOT / "audio" / "sfx" / "sfx-stem.wav"
SR = 48000
TARGET_I = -16.0
TP_CEIL = -1.0
VOICE_LUFS = -17.0
DUCK_MUSIC_DB = -9.0
DUCK_SFX_DB = -4.0
DUCK_ATTACK = 0.2  # s, ramp down before the voice starts
DUCK_RELEASE = 0.6  # s, ramp back up after it ends


def fps() -> int:
    src = (ROOT / "src" / "timeline.ts").read_text(encoding="utf-8")
    return int(re.search(r"export const FPS = (\d+)", src).group(1))


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, check=True, **kw)


def decode(path: Path) -> np.ndarray:
    raw = sh(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()


def measure(path: Path):
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    i = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1])
    tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)[-1])
    lra = float(re.findall(r"LRA:\s+(-?[\d.]+) LU", e)[-1])
    return i, tp, lra


def write_wav(path: Path, x: np.ndarray, codec="pcm_f32le"):
    p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", codec, str(path)],
                       input=x.astype("<f4").tobytes(), capture_output=True)
    if p.returncode:
        sys.exit(p.stderr.decode()[-500:])


def fit(x: np.ndarray, n: int) -> np.ndarray:
    return x[:n] if len(x) >= n else np.vstack([x, np.zeros((n - len(x), 2), dtype=np.float32)])


def build_voice(n: int):
    """Voice stem levelled to VOICE_LUFS, and the 0-1 ducking envelope (1 while a line is spoken)."""
    timing = NAR / "timing.json"
    rows = json.loads(timing.read_text(encoding="utf-8")) if timing.exists() else []
    if not rows:
        return None, None
    rate = fps()
    voice = np.zeros((n, 2), dtype=np.float32)
    env = np.zeros(n, dtype=np.float32)
    for r in rows:
        x = decode(NAR / "clips" / f"{r['id']}.wav")
        start = int(round(r["voiceFrom"] / rate * SR))
        if start >= n:
            sys.exit(f"{r['id']} starts after the music ends: re-run tools/narration.py against this timeline")
        end = min(n, start + len(x))
        voice[start:end] += x[: end - start]
        a = max(0, start - int(DUCK_ATTACK * SR))
        b = min(n, end + int(DUCK_RELEASE * SR))
        env[a:start] = np.maximum(env[a:start], np.linspace(0, 1, start - a, dtype=np.float32))
        env[start:end] = 1
        if b > end:
            env[end:b] = np.maximum(env[end:b], np.linspace(1, 0, b - end, dtype=np.float32))
    # level the whole voice stem once (gated loudness of the stem)
    tmp = NAR / "voice-stem-raw.wav"
    write_wav(tmp, voice)
    i, _, _ = measure(tmp)
    voice *= 10 ** ((VOICE_LUFS - i) / 20)
    write_wav(NAR / "voice-stem.wav", voice)
    tmp.unlink(missing_ok=True)
    print(f"voice: {len(rows)} lines, stem {i:.1f} -> {VOICE_LUFS:.1f} LUFS")
    return voice, env


def main():
    music_path = AUDIO / "bgm-music.wav"
    if not music_path.exists():
        sys.exit("no music at public/audio/bgm-music.wav: put the chosen track there (before one is chosen, "
                 "start from the placeholder: cp public/audio/bgm-master.wav public/audio/bgm-music.wav)")
    music = decode(music_path)
    n = len(music)
    voice, env = build_voice(n)
    sfx = fit(decode(SFX_STEM), n) if SFX_STEM.exists() else None
    if voice is not None:
        mix = music * (1 - (1 - 10 ** (DUCK_MUSIC_DB / 20)) * env)[:, None] + voice
        if sfx is not None:
            mix += sfx * (1 - (1 - 10 ** (DUCK_SFX_DB / 20)) * env)[:, None]
    else:
        mix = music + sfx if sfx is not None else music
    master_path = AUDIO / "bgm-master.wav"
    if float(np.abs(mix).max()) < 1e-6:
        write_wav(master_path, mix, "pcm_s24le")
        print("silent mix (placeholder music, no voice): wrote it unchanged; choose the music, then re-run")
        return
    tmp = ROOT / "audio" / "mix-raw.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    write_wav(tmp, mix)
    i0, tp0, _ = measure(tmp)
    gain_db = TARGET_I - i0
    for attempt in range(4):
        write_wav(tmp, mix * (10 ** (gain_db / 20)))
        ceiling = 10 ** ((TP_CEIL - 0.5 - 0.2 * attempt) / 20)
        sh(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af",
            f"aresample={SR * 4},alimiter=limit={ceiling:.4f}:attack=1:release=60:level=disabled,aresample={SR}",
            "-c:a", "pcm_s24le", str(master_path)])
        i1, tp1, lra1 = measure(master_path)
        print(f"master try {attempt}: gain {gain_db:+.2f} dB -> I {i1:.1f} LUFS, TP {tp1:.1f} dBTP, LRA {lra1:.1f}")
        if abs(i1 - TARGET_I) <= 0.3 and tp1 <= TP_CEIL:
            break
        gain_db += TARGET_I - i1
    else:
        print("WARNING: master missed -16 LUFS +/-0.3 or -1 dBTP after 4 tries; check the numbers above", file=sys.stderr)
    tmp.unlink(missing_ok=True)
    print(f"mix before gain: I {i0:.1f} LUFS, TP {tp0:.1f}; wrote {master_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
