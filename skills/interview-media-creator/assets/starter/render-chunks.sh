#!/bin/zsh
# Chunked render + lossless concat: zsh render-chunks.sh <composition> <out.mp4> <lastFrame> [chunks=4]
# Each chunk retries up to 3 times; chunks that already have the right frame count are skipped, so it can resume.
set -u
COMP=$1; OUT=$2; LAST=$3; N=${4:-4}
DIR="${OUT:r}-chunks"; mkdir -p "$DIR"
TOTAL=$((LAST + 1)); STEP=$(( (TOTAL + N - 1) / N ))
# Sets HAVE to the packet count of $1 (0 when missing). ffprobe's csv gains a trailing comma when the stream
# carries side data (Remotion writes an ICC profile), so keep the digits only.
count() {
  HAVE=$(ffprobe -v error -count_packets -select_streams v:0 -show_entries stream=nb_read_packets -of csv=p=0 "$1" 2>/dev/null)
  HAVE=${HAVE//[^0-9]/}; HAVE=${HAVE:-0}
}
: > "$DIR/list.txt"
for i in $(seq 0 $((N - 1))); do
  A=$((i * STEP)); B=$(( (i + 1) * STEP - 1 )); (( B > LAST )) && B=$LAST
  F="$DIR/part$i.mp4"; WANT=$((B - A + 1)); RC=0
  for try in 1 2 3; do
    count "$F"; (( HAVE == WANT )) && break
    echo "$(date '+%H:%M:%S') part$i frames $A-$B try $try"
    node render-range-log.mjs "$COMP" "$F" $A $B > "$DIR/part$i.log" 2>&1; RC=$?
  done
  count "$F"
  if (( HAVE != WANT )); then
    if (( RC != 0 )); then
      echo "FAILED part$i: render exited $RC on the last try, see $DIR/part$i.log"
    else
      echo "FAILED part$i: render finished but the file has $HAVE frames, expected $WANT (frames $A-$B), see $DIR/part$i.log"
    fi
    exit 1
  fi
  echo "file '${F:a}'" >> "$DIR/list.txt"
done
ffmpeg -nostdin -v error -y -f concat -safe 0 -i "$DIR/list.txt" -c copy -movflags +faststart "$OUT" || { echo "FAILED concat"; exit 1; }
count "$OUT"
(( HAVE == TOTAL )) || { echo "FAILED concat: $OUT has $HAVE frames, expected $TOTAL"; exit 1; }
echo "DONE $HAVE frames"
