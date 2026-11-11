"""Structure analysis for BGM candidates (numpy/scipy only): loudness envelope, tempo and
beat phase, novelty-based section boundaries, plus a PNG overview (spectrogram + RMS +
novelty + boundaries) so the arc can be checked visually against the picture plan.

  python3 audio/analyze.py candidates/a.mp3 candidates/b.mp3   # -> audio/structure.json, <input>-overview.png
  python3 audio/analyze.py bgm.wav --out audio/structure.json
"""
import argparse, json, subprocess
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks, stft
from scipy.ndimage import uniform_filter1d

SR = 22050


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def mel_fb(n_fft, n_mels=48, fmin=40, fmax=10000):
    mel = lambda f: 2595 * np.log10(1 + f / 700)
    imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = imel(np.linspace(mel(fmin), mel(fmax), n_mels + 2))
    bins = np.floor((n_fft + 1) * pts / SR).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for i in range(n_mels):
        a, b, c = bins[i], bins[i + 1], bins[i + 2]
        fb[i, a:b] = (np.arange(a, b) - a) / max(b - a, 1)
        fb[i, b:c] = (c - np.arange(b, c)) / max(c - b, 1)
    return fb


def analyze(path):
    y = load(path)
    dur = len(y) / SR
    hop = 512
    f, t, Z = stft(y, SR, nperseg=2048, noverlap=2048 - hop, boundary=None)
    S = np.abs(Z)
    M = np.log(mel_fb(2048) @ S + 1e-6)
    # loudness envelope (100 ms)
    w = int(0.1 * SR)
    n = len(y) // w
    rms = 20 * np.log10(np.sqrt((y[: n * w].reshape(n, w) ** 2).mean(1)) + 1e-9)
    # onset strength: positive spectral flux on log-mel
    flux = np.maximum(np.diff(M, axis=1), 0).sum(0)
    flux = np.r_[0, flux]
    flux = flux - uniform_filter1d(flux, 32)
    flux = np.maximum(flux, 0)
    fps = SR / hop
    # tempo by autocorrelation over 70-180 BPM
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
    lags = np.arange(len(ac))
    bpm = 60 * fps / np.maximum(lags, 1)
    ok = (bpm >= 70) & (bpm <= 180)
    lag = lags[ok][np.argmax(ac[ok])]
    tempo = 60 * fps / lag
    # refine tempo + phase by comb search
    best = (0, 0, 0)
    for bp in np.arange(tempo - 3, tempo + 3, 0.05):
        period = 60 / bp * fps
        for ph in np.arange(0, period, 0.5):
            idx = (ph + period * np.arange(int((len(flux) - ph) / period))).astype(int)
            sc = flux[idx].mean()
            if sc > best[0]:
                best = (sc, bp, ph / fps)
    _, bpm_ref, phase = best
    # novelty from self-similarity of 0.5 s mel frames
    blk = int(0.5 * fps)
    nb = M.shape[1] // blk
    F = M[:, : nb * blk].reshape(M.shape[0], nb, blk).mean(2)
    F = (F - F.mean(1, keepdims=True))
    F = F / (np.linalg.norm(F, axis=0, keepdims=True) + 1e-9)
    SSM = F.T @ F
    L = 16  # 8 s kernel
    g = np.outer(np.hanning(2 * L), np.hanning(2 * L))
    ck = g * np.block([[np.ones((L, L)), -np.ones((L, L))], [-np.ones((L, L)), np.ones((L, L))]])
    nov = np.zeros(nb)
    P = np.pad(SSM, L, mode="edge")
    for i in range(nb):
        nov[i] = (P[i:i + 2 * L, i:i + 2 * L] * ck).sum()
    nov = np.maximum(nov, 0); nov /= nov.max() + 1e-9
    pk, _ = find_peaks(nov, distance=10, prominence=0.08)
    bounds = sorted((round(p * 0.5, 1), round(float(nov[p]), 2)) for p in pk)
    # per-second loudness for reading the arc
    sec = [round(float(np.mean(rms[i * 10:(i + 1) * 10])), 1) for i in range(int(dur))]
    # strongest single onsets (hits)
    hits_idx, _ = find_peaks(flux, distance=int(fps * 2), height=np.percentile(flux, 99.5))
    hits = [round(i / fps, 2) for i in hits_idx]
    return {"file": path, "duration": round(dur, 3), "bpm": round(float(bpm_ref), 2), "beat_phase_s": round(float(phase), 3),
            "boundaries": bounds, "loudness_per_second_db": sec, "hits": hits,
            "_plot": (S, t, rms, nov, flux, fps)}


def plot(res, out_png):
    """Render the overview as a PNG without matplotlib: rows = spectrogram, RMS, novelty."""
    S, t, rms, nov, flux, fps = res["_plot"]
    Wpx, dur = 1800, res["duration"]
    spec = np.log(S[:400] + 1e-5)  # up to ~4.3 kHz
    cols = np.linspace(0, spec.shape[1] - 1, Wpx).astype(int)
    img = spec[::-1][:, cols]
    img = (img - np.percentile(img, 5)) / (np.percentile(img, 99.5) - np.percentile(img, 5))
    img = np.clip(img, 0, 1)
    rows = np.linspace(0, img.shape[0] - 1, 260).astype(int)
    spec_img = (img[rows] * 255).astype(np.uint8)
    canvas = np.full((260 + 140 + 100 + 30, Wpx, 3), 250, np.uint8)
    canvas[:260] = np.stack([spec_img] * 3, -1)
    # RMS panel
    r = np.interp(np.linspace(0, len(rms) - 1, Wpx), np.arange(len(rms)), rms)
    for x in range(Wpx):
        h = int(np.clip((r[x] + 60) / 60, 0, 1) * 130)
        canvas[400 - h:400, x] = (60, 90, 160)
    # novelty panel
    nv = np.interp(np.linspace(0, len(nov) - 1, Wpx), np.arange(len(nov)), nov)
    for x in range(Wpx):
        h = int(nv[x] * 95)
        canvas[500 - h:500, x] = (190, 80, 60)
    # 10 s grid + boundaries
    for s in range(0, int(dur) + 1, 10):
        x = int(s / dur * (Wpx - 1)); canvas[:, x] = (200, 200, 200) if s % 30 else (150, 150, 150)
    for b, _ in res["boundaries"]:
        x = int(b / dur * (Wpx - 1)); canvas[:500, x] = (220, 30, 30)
    for hsec in res["hits"]:
        x = int(hsec / dur * (Wpx - 1)); canvas[500:530, x] = (20, 20, 20)
    h, w, _ = canvas.shape
    raw = b"".join(b"\x00" + canvas[y].tobytes() for y in range(h))
    import zlib, struct
    def chunk(tag, d):
        c = struct.pack(">I", len(d)) + tag + d
        return c + struct.pack(">I", zlib.crc32(tag + d) & 0xFFFFFFFF)
    open(out_png, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                              + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "structure.json"))
    args = ap.parse_args()
    allres = {}
    for p in args.inputs:
        res = analyze(p)
        plot(res, p.rsplit(".", 1)[0] + "-overview.png")
        res.pop("_plot")
        allres[p] = res
        print(f"{p}: {res['duration']}s  bpm {res['bpm']}  phase {res['beat_phase_s']}s")
        print("  boundaries:", res["boundaries"])
        print("  hits:", res["hits"])
        ls = res["loudness_per_second_db"]
        print("  loud/5s:", [round(float(np.mean(ls[i:i + 5]))) for i in range(0, len(ls), 5)])
    json.dump(allres, open(args.out, "w"), indent=1)
    print(args.out)
