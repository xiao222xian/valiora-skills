#!/bin/bash
# Hidden time dependence check: render the same local frames of one chapter twice, at concurrency 1 and 4 (separate
# browsers, so every frame lands in a different tab and at a different place in its tab's sequence), and compare
# frame by frame. Anything that reads the clock, Math.random, or bakes once per tab (frames={1}) shows up as differing
# frames. Pass: largest difference <= 24/255 and at most 0.1 % of pixels differ by more than 8/255 (the first 3D
# film's tools/determinism.sh, 2026-10-12). Run from work/remotion; needs numpy and Pillow.
#   tools/determinism.sh <id> <localFrom> <localTo> [16x9|9x16]
# env: GL (default angle), REBUNDLE=0 reuses the bundle of the last tools/preview.sh run
set -euo pipefail
[ $# -ge 3 ] || { sed -n '2,8p' "$0" >&2; exit 2; }
ID=$1; FROM=$2; TO=$3; ASP=${4:-16x9}
cd "$(dirname "$0")/.."
python3 -c 'import numpy, PIL' 2>/dev/null || { echo "needs: python3 -m pip install numpy pillow" >&2; exit 1; }
BUILD=../build/preview-$ID
if [ "${REBUNDLE:-1}" = "1" ] || [ ! -d "$BUILD" ]; then tools/preview.sh "$ID" bundle >/dev/null; fi
START=$(node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON -e "import('./src/timeline.ts').then(m=>console.log(m.CHAPTERS.find(c=>c.id==='$ID').start))")
T=$(mktemp -d "${TMPDIR:-/tmp}/det_XXXXXX")
trap 'rm -rf "$T"' EXIT
for c in 1 4; do
  npx remotion render "$BUILD" "H-$ASP" "$T/c$c" --sequence --frames="$((START + FROM))-$((START + TO))" --concurrency=$c \
    --image-format=png --scale=0.5 --log=error --gl="${GL:-angle}" >/dev/null
done
python3 - "$T" "$ID" <<'PY'
import os
import sys

import numpy as np
from PIL import Image

t, cid = sys.argv[1], sys.argv[2]
names = sorted(os.listdir(f"{t}/c1"))
bad, worst = [], 0
for f in names:
    x = np.asarray(Image.open(f"{t}/c1/{f}").convert("RGB"), dtype=np.int16)
    y = np.asarray(Image.open(f"{t}/c4/{f}").convert("RGB"), dtype=np.int16)
    d = np.abs(x - y)
    worst = max(worst, int(d.max()))
    if d.max() > 24 or (d > 8).mean() > 0.001:
        bad.append((f, int(d.max()), round(float((d > 8).mean()) * 100, 3)))
print(f"{cid}: {len(names)} frames compared, largest difference {worst}/255, {len(bad)} over the threshold")
for b in bad[:20]:
    print(f"  {b[0]}: max {b[1]}/255, {b[2]} % of pixels > 8/255")
sys.exit(1 if bad else 0)
PY
