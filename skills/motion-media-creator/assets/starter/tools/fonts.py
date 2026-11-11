#!/usr/bin/env python3
"""Extract the per-era typefaces from macOS system collections, then subset them
to the characters the film actually uses (scanned from src/**/*.ts[x]).

  python3 tools/fonts.py extract   # once: TTC faces -> fonts-src/*.ttf (full, not served)
  python3 tools/fonts.py subset    # after any copy change: fonts-src -> public/fonts (subset + OTS check)
  python3 tools/fonts.py validate  # OTS check of public/fonts only

Subsetting matters: full CJK faces are 10-30 MB each and every render tab loads all of them.
Chrome loads web fonts through OpenType Sanitizer (OTS): a face it rejects fails FontFace.load()
with a bare "NetworkError" and delayRender cancels the render, so every subset is checked with OTS
(module `ots` from opentype-sanitizer, or a throwaway `uv run --with opentype-sanitizer`).
"""
import shutil
import subprocess
import sys
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTCollection, TTFont

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "fonts-src"
OUT_DIR = ROOT / "public" / "fonts"
A8 = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8"

# css family -> (collection or file, face index or None)
# Apple's /System/Library/Fonts/Courier.ttc has no OS/2 table, which OTS rejects: for Courier use
# /System/Library/Fonts/Supplemental/Courier New.ttf (and "Courier New Bold.ttf").
FACES = {
    "ZL-Kai": (f"{A8}/88d6cc32a907955efa1d014207889413890573be.asset/AssetData/Kaiti.ttc", 3),
    "ZL-KaiBlack": (f"{A8}/88d6cc32a907955efa1d014207889413890573be.asset/AssetData/Kaiti.ttc", 5),
    "ZL-Li": (f"{A8}/a304e3396d019087ab67af77f5e398977529007d.asset/AssetData/Libian.ttc", 0),
    "ZL-Baoli": (f"{A8}/70875a1270987c17cfd6f40cd3d755ec04d03b33.asset/AssetData/Baoli.ttc", 0),
    "ZL-Weibei": (f"{A8}/c745f84f5eb15b1f594d3769dc86146fccee61ff.asset/AssetData/WeibeiSC-Bold.otf", None),
    "ZL-Xingkai": (f"{A8}/13b8ce423f920875b28b551f9406bf1014e0a656.asset/AssetData/Xingkai.ttc", 0),
    "ZL-SongBlack": ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),
    "ZL-SongBold": ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),  # Songti SC Bold: has 昇, Black does not
    "ZL-Song": ("/System/Library/Fonts/Supplemental/Songti.ttc", 6),
    "ZL-SongLight": ("/System/Library/Fonts/Supplemental/Songti.ttc", 3),
    "ZL-HeiHeavy": (f"{A8}/f14049099a04e570b893c01d9a4cd71f87c9e8d8.asset/AssetData/Lantinghei.ttc", 2),
    "ZL-Hei": (f"{A8}/f14049099a04e570b893c01d9a4cd71f87c9e8d8.asset/AssetData/Lantinghei.ttc", 0),
    "ZL-HeiLight": (f"{A8}/f14049099a04e570b893c01d9a4cd71f87c9e8d8.asset/AssetData/Lantinghei.ttc", 1),
    "ZL-Fangsong": (f"{A8}/1b6b2f148cdf17dd0d788706c83c61ca1998c3a6.asset/AssetData/STFANGSO.ttf", None),
    "ZL-Serif": ("/System/Library/Fonts/NewYork.ttf", None),
    "ZL-Mono": ("/System/Library/Fonts/SFNSMono.ttf", None),
}
LATIN_ONLY = {"ZL-Serif", "ZL-Mono"}
# Faces used only for a few headline strings; any other missing glyph falls back silently in the
# browser, so treat it as a build error.
FALLBACK_OK = {"ZL-SongBlack"}
ALWAYS = "".join(chr(c) for c in range(0x20, 0x7F)) + "—–·。，、：；！？「」『』《》（）“”‘’…—　％°′″±×"


def extract():
    SRC_DIR.mkdir(exist_ok=True)
    for fam, (path, idx) in FACES.items():
        font = TTCollection(path).fonts[idx] if idx is not None else TTFont(path)
        if "OS/2" not in font:
            sys.exit(f"{fam}: {Path(path).name}[{idx}] has no OS/2 table; browsers reject it, pick another file")
        out = SRC_DIR / f"{fam}.ttf"
        font.save(out)
        print(f"{fam:14s} <- {Path(path).name}[{idx}]  {out.stat().st_size/1e6:.1f} MB")


def used_chars():
    chars = set(ALWAYS)
    for f in (ROOT / "src").rglob("*.ts*"):
        chars |= set(f.read_text(encoding="utf-8"))
    return {c for c in chars if c.isprintable() or c == "　"}


# prints one line per rejected file and exits 1 when OTS rejects any
OTS_CHECK = """
import sys, ots
bad = 0
for f in sys.argv[1:]:
    r = ots.sanitize(f, "/dev/null", capture_output=True, text=True)
    if r.returncode:
        bad += 1
        print(f"OTS rejected {f}: {(r.stderr or r.stdout).strip()}")
sys.exit(1 if bad else 0)
"""


def validate(paths=None):
    paths = [str(p) for p in (paths or sorted(OUT_DIR.glob("*.ttf")))]
    if not paths:
        sys.exit(f"no fonts to validate in {OUT_DIR}")
    try:
        import ots  # noqa: F401
        cmd = [sys.executable, "-c", OTS_CHECK]
    except ImportError:
        if not shutil.which("uv"):
            sys.exit("font check needs OpenType Sanitizer: python3 -m pip install opentype-sanitizer (or install uv)")
        cmd = ["uv", "run", "--no-project", "--quiet", "--with", "opentype-sanitizer", "python", "-c", OTS_CHECK]
    if subprocess.run(cmd + paths).returncode:
        sys.exit("OpenType Sanitizer rejected fonts: Chrome will not load them")
    print(f"OTS: {len(paths)} fonts pass")


def subset():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = []
    chars = used_chars()
    cjk = sorted(c for c in chars if ord(c) > 0x2E80)
    gaps = []
    for fam in FACES:
        src = SRC_DIR / f"{fam}.ttf"
        font = TTFont(src)
        opts = Options()
        opts.layout_features = ["*"]
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        opts.drop_tables += ["DSIG"]
        text = "".join(c for c in chars if ord(c) < 0x2E80) if fam in LATIN_ONLY else "".join(chars)
        sub = Subsetter(options=opts)
        sub.populate(text=text)
        sub.subset(font)
        out = OUT_DIR / f"{fam}.ttf"
        font.save(out)
        done.append(out)
        cmap = font.getBestCmap() or {}
        missing = [c for c in cjk if ord(c) not in cmap] if fam not in LATIN_ONLY else []
        note = f"  missing {len(missing)}: {''.join(missing[:40])}" if missing else ""
        if missing and fam not in FALLBACK_OK:
            gaps.append(f"{fam}: {''.join(missing)}")
        print(f"{fam:14s} {out.stat().st_size/1e3:8.1f} KB{note}")
    print(f"{len(cjk)} CJK chars in use")
    if gaps:
        sys.exit("missing glyphs (fix copy or face): " + "; ".join(gaps))
    validate(done)


if __name__ == "__main__":
    {"extract": extract, "subset": subset, "validate": validate}[sys.argv[1]]()
