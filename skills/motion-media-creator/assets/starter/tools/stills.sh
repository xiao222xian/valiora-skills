#!/bin/bash
# Bundle once, then render stills in parallel from the bundle.
# usage: tools/stills.sh <prefix> <composition> <scale> <frame> [frame...]
#        tools/stills.sh covers [scale]   # Cover-16x9, Cover-4x3, Cover-3x4 -> $STILLS_DIR/cover-<ratio>.jpg (scale 1)
#   STILLS_DIR (default ../qc/stills), BUNDLE_DIR (default ../build/stills), REBUNDLE=0 reuses an existing bundle.
set -euo pipefail
usage() { echo "usage: tools/stills.sh <prefix> <composition> <scale> <frame> [frame...] | tools/stills.sh covers [scale]" >&2; exit 2; }
OUT=${STILLS_DIR:-../qc/stills}; BUILD=${BUNDLE_DIR:-../build/stills}
if [ "${1:-}" = "covers" ]; then
  [ $# -le 2 ] || usage
  SCALE=${2:-1}; mkdir -p "$OUT"
  if [ "${REBUNDLE:-1}" = "1" ] || [ ! -d "$BUILD" ]; then tools/bundle.sh src/index.ts "$BUILD"; fi
  # which picture each cover takes (the same order as src/Cover.tsx): its own, then the 16:9 one, else the fallback
  for r in 16x9 4x3 3x4; do
    src=fallback
    for c in "ai-$r.png:own" "ai-$r.jpg:own" "ai-16x9.png:16x9 band" "ai-16x9.jpg:16x9 band"; do
      f=${c%%:*}; [ "$r" = 16x9 ] && [ "${c#*:}" != own ] && continue
      [ -f "public/assets/cover/$f" ] && { src="$f (${c#*:})"; break; }
    done
    echo "cover $r: $src"
  done
  pids=()
  for r in 16x9 4x3 3x4; do
    rm -f "$OUT/cover-$r.jpg"
    npx remotion still "$BUILD" "Cover-$r" "$OUT/cover-$r.jpg" --frame=0 --scale="$SCALE" --log=error --jpeg-quality=90 &
    pids+=("$!")
  done
  fail=0
  for p in "${pids[@]}"; do wait "$p" || fail=1; done
  [ "$fail" = 0 ] || { echo "stills.sh: some covers failed" >&2; exit 1; }
  echo "look at $OUT/cover-16x9.jpg, cover-4x3.jpg, cover-3x4.jpg: title and seal clear of the subject"
  exit 0
fi
[ $# -ge 4 ] || usage
PREFIX=$1; COMP=$2; SCALE=$3; shift 3
mkdir -p "$OUT"
if [ "${REBUNDLE:-1}" = "1" ] || [ ! -d "$BUILD" ]; then tools/bundle.sh src/index.ts "$BUILD"; fi
pids=()
for f in "$@"; do
  rm -f "$OUT/$PREFIX-$f.jpg"   # a failed render must not leave the previous still behind
  npx remotion still "$BUILD" "$COMP" "$OUT/$PREFIX-$f.jpg" --frame="$f" --scale="$SCALE" --log=error --jpeg-quality=85 &
  pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done   # a bare `wait` always returns 0
[ "$fail" = 0 ] || { echo "stills.sh: some stills failed" >&2; exit 1; }
echo done
