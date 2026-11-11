#!/bin/bash
# Steady-state render time per frame of one chapter at full size: the number the 0.6 s budget is about. Renders one
# frame, then N frames from the same frame, both at concurrency 1 from the chapter's preview bundle, and divides the
# difference by N-1, so the start-up that every single still pays (browser tab, shader compile, textures, fonts:
# 1.3-2.9 s a still on the example film, 2026-10-13) drops out. Run from work/remotion.
#   tools/frametime.sh <id> <localFrom> [frames=30] [16x9|9x16]
# env: GL (default angle), REBUNDLE=0 reuses the bundle of the last tools/preview.sh run
set -euo pipefail
[ $# -ge 2 ] || { sed -n '2,7p' "$0" >&2; exit 2; }
ID=$1; FROM=$2; N=${3:-30}; ASP=${4:-16x9}
cd "$(dirname "$0")/.."
BUILD=../build/preview-$ID
if [ "${REBUNDLE:-1}" = "1" ] || [ ! -d "$BUILD" ]; then tools/preview.sh "$ID" bundle >/dev/null; fi
START=$(node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON -e "import('./src/timeline.ts').then(m=>console.log(m.CHAPTERS.find(c=>c.id==='$ID').start))")
A=$((START + FROM))
T=$(mktemp -d "${TMPDIR:-/tmp}/frametime_XXXXXX")
trap 'rm -rf "$T"' EXIT
timed() {
  local t0 t1
  t0=$(python3 -c 'import time; print(time.time())')
  npx remotion render "$BUILD" "H-$ASP" "$T/$1" --sequence --frames="$2" --concurrency=1 --image-format=jpeg --log=error --gl="${GL:-angle}" >/dev/null
  t1=$(python3 -c 'import time; print(time.time())')
  python3 -c "print($t1 - $t0)"
}
one=$(timed one "$A-$A")
many=$(timed many "$A-$((A + N - 1))")
python3 - "$one" "$many" "$N" "$ID" "$FROM" "$ASP" <<'PY'
import sys
one, many, n = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
per = (many - one) / (n - 1)
print(f"{sys.argv[4]} {sys.argv[6]} local {sys.argv[5]}+{n}: 1 frame {one:.1f} s, {n} frames {many:.1f} s, steady {per:.3f} s/frame "
      f"({'within' if per <= 0.6 else 'over'} the 0.6 s budget)")
PY
