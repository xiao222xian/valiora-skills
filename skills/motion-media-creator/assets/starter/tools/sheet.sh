#!/bin/bash
# Render every Nth frame of a frame range and tile them into one contact sheet for review.
# usage: tools/sheet.sh <composition> <from> <to> <every> <out.jpg> [cols] [scale]
set -euo pipefail
COMP=$1; FROM=$2; TO=$3; EVERY=$4; OUT=$5; COLS=${6:-4}; SCALE=${7:-0.25}
TMP=$(mktemp -d "${TMPDIR:-/tmp}/sheet_XXXXXX")
npx remotion render src/index.ts "$COMP" "$TMP" --sequence --frames="$FROM-$TO" --every-nth-frame="$EVERY" \
  --image-format=jpeg --jpeg-quality=85 --scale="$SCALE" --log=error --concurrency=8 >/dev/null
N=$(ls "$TMP" | wc -l | tr -d ' ')
ROWS=$(( (N + COLS - 1) / COLS ))
ffmpeg -v error -y -pattern_type glob -i "$TMP/*.jpeg" -vf "drawtext=text='%{frame_num}':start_number=0:x=6:y=6:fontsize=14:fontcolor=white:box=1:boxcolor=black@0.5,tile=${COLS}x${ROWS}:padding=4:color=white" -frames:v 1 "$OUT"
echo "$OUT ($N frames)"
rm -rf "$TMP"
