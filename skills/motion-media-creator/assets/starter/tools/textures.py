#!/usr/bin/env python3
"""Procedural rice-paper fibre texture and film-grain tiles (grayscale PNG), plus a neutral
placeholder logo. Deterministic (fixed seeds) so re-running reproduces the same files.

  python3 tools/textures.py               # public/tex/paper.png + grain0..5.png
  python3 tools/textures.py --logo PATH   # placeholder logo (framed cross, transparent) until the real one is supplied
"""
import argparse
import struct
import zlib
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent.parent / "public" / "tex"


def png(path, a):
    """(h, w) -> grayscale, (h, w, 2) -> grayscale + alpha."""
    a = np.clip(a, 0, 255).astype(np.uint8)
    h, w = a.shape[:2]
    ctype = 4 if a.ndim == 3 else 0
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    Path(path).write_bytes(data)


def smooth_noise(rng, n, cells):
    g = rng.standard_normal((cells + 1, cells + 1))
    g[-1, :] = g[0, :]; g[:, -1] = g[:, 0]
    x = np.linspace(0, cells, n, endpoint=False)
    i = x.astype(int); f = x - i; f = f * f * (3 - 2 * f)
    a = g[np.ix_(i, i)]; b = g[np.ix_(i, i + 1)]; c = g[np.ix_(i + 1, i)]; d = g[np.ix_(i + 1, i + 1)]
    fx = f[None, :]; fy = f[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def paper(n=2048, seed=7):
    rng = np.random.default_rng(seed)
    base = sum(smooth_noise(rng, n, c) / (i + 1) for i, c in enumerate([4, 9, 23, 61, 160]))
    base = (base - base.mean()) / base.std()
    img = 200 + 9 * base
    # fibres: short random walks drawn as soft dark/light streaks
    fib = np.zeros((n, n))
    for _ in range(9000):
        x, y = rng.uniform(0, n, 2)
        ang = rng.uniform(0, np.pi); L = rng.uniform(20, 140)
        k = rng.uniform(-0.02, 0.02); s = rng.choice([-1, 1]) * rng.uniform(0.4, 1.0)
        for t in np.arange(0, L, 1.0):
            ang += k
            xi = int(x + t * np.cos(ang)) % n; yi = int(y + t * np.sin(ang)) % n
            fib[yi, xi] += s
    k = np.array([0.25, 0.5, 0.25])
    for _ in range(2):
        fib = np.apply_along_axis(lambda r: np.convolve(np.r_[r[-1], r, r[0]], k, "valid"), 1, fib)
        fib = np.apply_along_axis(lambda r: np.convolve(np.r_[r[-1], r, r[0]], k, "valid"), 0, fib)
    img += 22 * fib
    img += rng.normal(0, 3, (n, n))
    png(OUT / "paper.png", img)


def grain(n=512, count=6, seed=11):
    rng = np.random.default_rng(seed)
    for i in range(count):
        g = rng.normal(128, 38, (n, n))
        png(OUT / f"grain{i}.png", g)


def logo(path, w=600, h=200, t=4):
    # mid grey reads on both light paper and dark chapters; the cross marks it as "replace me"
    y, x = np.mgrid[0:h, 0:w]
    frame = (x < t) | (x >= w - t) | (y < t) | (y >= h - t)
    d = np.hypot(w, h)
    cross = (np.abs(y * w - x * h) / d < t / 2) | (np.abs((h - y) * w - x * h) / d < t / 2)
    a = np.zeros((h, w, 2))
    a[..., 0] = 128
    a[..., 1] = np.where(frame, 255, np.where(cross, 150, 0))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    png(path, a)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--logo", help="write a placeholder logo PNG here instead of textures")
    args = ap.parse_args()
    if args.logo:
        logo(args.logo)
        print(args.logo)
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        paper(); grain()
        print(sorted(p.name for p in OUT.iterdir()))
