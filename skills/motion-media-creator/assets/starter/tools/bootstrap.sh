#!/bin/bash
# First run in a fresh copy of the starter: fill public/ with everything src/ loads.
# Safe to re-run: each step skips what is already there; fonts are always re-subset.
#   tools/bootstrap.sh
#   FILM_LOGO=/path/to/logo.png tools/bootstrap.sh   # official logo, copied as supplied
#   FILM_SEAL_DIR=/path/to/seal tools/bootstrap.sh   # brand seal: SealFinal.tsx + sealF-geom.ts + types.ts
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -c 'import numpy, fontTools' 2>/dev/null || { echo "needs: python3 -m pip install numpy fonttools" >&2; exit 1; }
# every font subset is checked with OpenType Sanitizer (what Chrome runs before it loads a font)
python3 -c 'import ots' 2>/dev/null || command -v uv >/dev/null || { echo "needs: python3 -m pip install opentype-sanitizer (or uv)" >&2; exit 1; }
# fail fast on a wrong logo before the slow steps
if [ -n "${FILM_LOGO:-}" ] && ! python3 -c 'import sys; sys.exit(open(sys.argv[1], "rb").read(8) != b"\x89PNG\r\n\x1a\n")' "$FILM_LOGO"; then echo "FILM_LOGO must be a PNG: $FILM_LOGO" >&2; exit 1; fi

# paper + grain textures (deterministic, ~1 min the first time)
missing=0
for f in paper grain0 grain1 grain2 grain3 grain4 grain5; do [ -f "public/tex/$f.png" ] || missing=1; done
if [ "$missing" = 1 ]; then python3 tools/textures.py; else echo "textures: present"; fi

# typefaces: extract all faces when any is missing (re-extracts every face), then subset to the characters src/ uses
need=$(python3 -c 'import sys; sys.path.insert(0, "tools"); from fonts import FACES, SRC_DIR; print(sum(not (SRC_DIR / f"{f}.ttf").exists() for f in FACES))')
if [ "$need" != 0 ]; then python3 tools/fonts.py extract; else echo "fonts-src: present"; fi
python3 tools/fonts.py subset

# brand logo: FILM_LOGO wins every run; otherwise keep whatever is there, else a placeholder
mkdir -p public/brand
if [ -n "${FILM_LOGO:-}" ]; then
  case "$FILM_LOGO" in *.png | *.PNG) ;; *) echo "FILM_LOGO must be a PNG: $FILM_LOGO" >&2; exit 1 ;; esac
  cp "$FILM_LOGO" public/brand/logo.png
  echo "logo: $FILM_LOGO"
elif [ ! -f public/brand/logo.png ]; then
  python3 tools/textures.py --logo public/brand/logo.png >/dev/null
  echo "logo: placeholder (set FILM_LOGO=<png> and re-run)"
else
  echo "logo: present"
fi

# brand seal: replace the placeholder with the brand's own seal component when one is supplied
if [ -n "${FILM_SEAL_DIR:-}" ]; then
  for f in SealFinal.tsx sealF-geom.ts types.ts; do [ -f "$FILM_SEAL_DIR/$f" ] || { echo "FILM_SEAL_DIR lacks $f" >&2; exit 1; }; done
  cp "$FILM_SEAL_DIR/SealFinal.tsx" "$FILM_SEAL_DIR/sealF-geom.ts" "$FILM_SEAL_DIR/types.ts" src/brand/
  printf "// Brand seal supplied by FILM_SEAL_DIR at bootstrap.\nexport {SealFinal as BrandSeal} from './SealFinal';\n" > src/brand/Seal.tsx
  echo "seal: $FILM_SEAL_DIR"
else
  echo "seal: placeholder (set FILM_SEAL_DIR=<dir> and re-run)"
fi

# placeholder music: silence of the film's length so Main renders before the BGM is chosen
# (the chosen track goes to public/audio/bgm-music.wav; tools/voice_mix.py then writes this master)
if [ ! -f public/audio/bgm-master.wav ]; then
  python3 - <<'PY'
import re, wave
from pathlib import Path
src = Path("src/timeline.ts").read_text(encoding="utf-8")
num = lambda k: int(re.search(rf"export const {k} = (\d+)", src).group(1))
frames, fps, sr = num("TOTAL_FRAMES"), num("FPS"), 48000
n = round(frames / fps * sr)
out = Path("public/audio/bgm-master.wav")
out.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(out), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(bytes(n * 4))
print(f"audio: placeholder silence {n / sr:.2f} s ({frames} frames @ {fps} fps)")
PY
else
  echo "audio: present"
fi

echo "next: npx tsc --noEmit -p . && npx remotion studio src/index.ts"
