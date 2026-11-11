#!/bin/bash
# Render a master for one aspect, derive the platform file, and run the delivery QC on the
# encoded file itself (not on Studio). Run from work/remotion.
#   tools/deliver.sh 16x9 v0.2 [concurrency]   # the default delivery: 16:9 only
#   tools/deliver.sh 9x16 v0.2 [concurrency]   # only when the user asks for the vertical cut (or both)
#   tools/deliver.sh covers v0.2               # the three covers, named by ratio: 封面16x9, 封面4x3, 封面3x4 (PNG + JPG)
# env: FILM_TITLE, FILM_BRAND (required); FILM_SLUG (master file name, default "film"); FILM_DATE;
#      MEDIA_CREATOR_SCRIPTS; CHUNKS="0-1499,1500-2879,..." (default: tools/chunks.mjs, cut at
#      chapter starts, CHUNK_FRAMES per chunk); FILM_BGM (default public/audio/bgm-master.wav);
#      SKIP_RENDER=1 reuses the existing master and only redoes the platform file and QC.
set -euo pipefail
ASPECT=$1
VER=$2
CONC=${3:-6}
DATE=${FILM_DATE:-$(date +%F)}
# QC helpers ship with lov-media-creator (media_probe.py, audio_qc.py)
SKILL=${MEDIA_CREATOR_SCRIPTS:-}   # optional: <lov-media-creator>/scripts adds probe/audio-qc JSON
TITLE=${FILM_TITLE:?set FILM_TITLE}
BRAND=${FILM_BRAND:?set FILM_BRAND}
SLUG=${FILM_SLUG:-film}   # master file name: renders/<slug>-<aspect>-<ver>-master.mp4
WORK=$(cd .. && pwd)
OUTV=$(cd ../.. && pwd)/output/videos
REP=$(cd ../.. && pwd)/output/reports/$VER
mkdir -p "$WORK/renders" "$OUTV" "$REP"
OUTI=$(cd ../.. && pwd)/output/images

# The picture a cover takes, in src/Cover.tsx's order: its own AI picture, then (4:3, 3:4) the 16:9 one, else the
# chapter-spectrum fallback.
cover_source() {
  local r=$1 c f
  for c in "ai-$r.png:own" "ai-$r.jpg:own" "ai-16x9.png:16x9 band" "ai-16x9.jpg:16x9 band"; do
    f=${c%%:*}; [ "$r" = 16x9 ] && [ "${c#*:}" != own ] && continue
    [ -f "public/assets/cover/$f" ] && { echo "$f (${c#*:})"; return; }
  done
  echo fallback
}

if [ "$ASPECT" = "covers" ]; then
  # Every film delivers 16:9, 4:3 and 3:4, named by ratio, not by platform: 4:3 is both the Bilibili home cover and
  # the WeChat Channels share card, 3:4 the Channels profile card (2026-10-12: v0.5 shipped 16:9 and 4:3 only, and
  # Channels asked for 3:4 at publish time). See references/covers.md.
  mkdir -p "$OUTI"
  BUNDLE="$WORK/build/covers"
  tools/bundle.sh src/index.ts "$BUNDLE"
  pids=()
  for r in 16x9 4x3 3x4; do
    rm -f "$OUTI/$BRAND-$TITLE-封面$r-$DATE-$VER.png" "$OUTI/$BRAND-$TITLE-封面$r-$DATE-$VER.jpg"
    # stills.mjs writes <prefix><label>.<ext>: the version is the label of frame 0
    FORMATS=png,jpeg JPEG_QUALITY=92 node tools/stills.mjs "$BUNDLE" "Cover-$r" "$OUTI/$BRAND-$TITLE-封面$r-$DATE-" 1 "0:$VER" &
    pids+=("$!")
  done
  fail=0
  for p in "${pids[@]}"; do wait "$p" || fail=1; done
  [ "$fail" = 0 ] || { echo "covers: a render failed" >&2; exit 1; }
  printf 'file\tpixels\tpicture\tsha256\n' > "$REP/covers.tsv"
  for r in 16x9 4x3 3x4; do
    case $r in 16x9) want=1920x1080; thumb=480:270 ;; 4x3) want=1440x1080; thumb=360:270 ;; *) want=1080x1440; thumb=270:360 ;; esac
    base="$OUTI/$BRAND-$TITLE-封面$r-$DATE-$VER"
    for ext in png jpg; do [ -s "$base.$ext" ] || { echo "covers: $base.$ext is missing" >&2; exit 1; }; done
    wh=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$base.png")
    [ "$wh" = "$want" ] || { echo "covers: $r is $wh, expected $want" >&2; exit 1; }
    src=$(cover_source "$r")
    # the sizes the platforms show the covers at
    ffmpeg -v error -y -i "$base.png" -vf "scale=$thumb:flags=lanczos" "$REP/cover-thumb-$r.png"
    # near-black edges: an AI cover keeps dark space for the title on purpose, so a hit asks for a look, not a fix
    crop=$(ffmpeg -hide_banner -nostats -loop 1 -t 0.2 -i "$base.png" -vf cropdetect=limit=24:round=2:reset=0 -f null - 2>&1 | grep -o 'crop=[0-9:]*' | tail -1 || true)
    note=""
    [ -n "$crop" ] && [ "$crop" != "crop=${want/x/:}:0:0" ] && note="; near-black edges ($crop): check that it is the title's dark space, not a padding bar"
    case "$r:$src" in 3x4:*"16x9 band"*) note="$note; no own 3:4 picture (tools/gen_cover_bg.py --ratio 3:4)" ;; esac
    printf '%s\t%s\t%s\t%s\n' "$(basename "$base").png" "$wh" "$src" "$(shasum -a 256 "$base.png" | cut -d' ' -f1)" >> "$REP/covers.tsv"
    echo "cover $r: $base.png + .jpg, $wh, picture $src$note"
  done
  # the three thumbnails side by side on white, for the report and a last look at thumbnail size
  ffmpeg -v error -y -i "$REP/cover-thumb-16x9.png" -i "$REP/cover-thumb-4x3.png" -i "$REP/cover-thumb-3x4.png" \
    -filter_complex "[0]pad=490:370:5:50:white[a];[1]pad=370:370:5:50:white[b];[2]pad=280:370:5:5:white[c];[a][b][c]hstack=inputs=3" \
    "$REP/cover-thumbs.png"
  echo "covers: $REP/covers.tsv, $REP/cover-thumbs.png; look at every cover at full size and as a thumbnail"
  exit 0
fi

MASTER="$WORK/renders/$SLUG-$ASPECT-$VER-master.mp4"

start=$(date +%s)
if [ "${SKIP_RENDER:-0}" = "1" ]; then
  [ -f "$MASTER" ] || { echo "SKIP_RENDER=1 but there is no master at $MASTER" >&2; exit 1; }
  echo "render ${ASPECT}: reusing $MASTER"
else
  # Render in chunks, each with a fresh `npx remotion render` (a fresh browser): after thousands of
  # frames in one tab Chrome's V8 can hit an internal fatal check ("Page crashed!"), while every
  # chunk alone is fine. Video is concatenated losslessly; the audio is the master WAV encoded once,
  # which assumes Main's only sound is that file mounted at frame 0 (music, voice-over and effects are
  # premixed into it by tools/voice_mix.py).
  BGM=${FILM_BGM:-public/audio/bgm-master.wav}
  if [ -z "${CHUNKS:-}" ]; then
    CHUNKS=$(node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON tools/chunks.mjs) \
      || { echo "chunk plan failed (Node 24 imports src/timeline.ts directly); set CHUNKS=a-b,c-d,... by hand" >&2; exit 1; }
  fi
  CH="$WORK/renders/chunks-$ASPECT-$VER"
  rm -rf "$CH"; mkdir -p "$CH"
  : > "$CH/list.txt"
  # bundle once for every chunk (public/ goes in as clones, see tools/bundle.sh)
  BUNDLE="$WORK/build/main-$ASPECT"
  tools/bundle.sh src/index.ts "$BUNDLE"
  k=0
  for r in ${CHUNKS//,/ }; do
    k=$((k + 1))
    f="$CH/part-$(printf %02d $k).mp4"
    npx remotion render "$BUNDLE" "Main-$ASPECT" "$f" --frames="$r" --muted \
      --codec=h264 --crf=16 --x264-preset=slow --pixel-format=yuv420p --color-space=bt709 \
      --concurrency="$CONC" --log=error
    echo "file '$f'" >> "$CH/list.txt"
  done
  ffmpeg -v error -y -f concat -safe 0 -i "$CH/list.txt" -c copy "$CH/video.mp4"
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$CH/video.mp4")
  # bitexact: otherwise the AAC encoder writes its "Lavc..." version string into the bitstream
  ffmpeg -v error -y -i "$CH/video.mp4" -i "$BGM" -map 0:v -map 1:a \
    -c:v copy -c:a aac -b:a 320k -flags:a +bitexact -fflags +bitexact -t "$DUR" "$MASTER"
  echo "render ${ASPECT}: $(( $(date +%s) - start ))s in $k chunks (video ${DUR}s)"
fi

META=(-map_metadata -1 -metadata "title=$TITLE" -metadata "artist=$BRAND" -metadata comment=)
# no tool names anywhere in the file: drop the encoder's SEI version string (NAL type 6) and the
# muxer's encoder=Lavf... stamp
CLEAN=(-bsf:v filter_units=remove_types=6 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact)
if [ "$ASPECT" = "9x16" ]; then
  # WeChat Channels: <= 10 Mbps advised; one pass with a rate cap, colour tags written explicitly
  PLAT="$OUTV/$BRAND-$TITLE-视频号9x16-$DATE-$VER.mp4"
  ffmpeg -v error -y -i "$MASTER" -c:v libx264 -preset slow -crf 20 -maxrate 9M -bufsize 18M \
    -profile:v high -level 4.1 -g 60 -pix_fmt yuv420p \
    -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
    -c:a copy -movflags +faststart "$PLAT.enc.mp4"
  # re-mux by stream copy: written straight from the encoder, the sample entry (stsd
  # compressorname) keeps "Lavc... libx264"
  ffmpeg -v error -y -i "$PLAT.enc.mp4" -map 0 -c copy "${META[@]}" "${CLEAN[@]}" -movflags +faststart "$PLAT"
  rm -f "$PLAT.enc.mp4"
else
  # Bilibili / general 16:9: the master as rendered, moov atom moved to the front
  PLAT="$OUTV/$BRAND-$TITLE-横版16x9-$DATE-$VER.mp4"
  ffmpeg -v error -y -i "$MASTER" -map 0 -c copy "${META[@]}" "${CLEAN[@]}" -movflags +faststart "$PLAT"
fi
# the renderer stamps its name into the container comment; delivery files carry only title and producer
if ffprobe -v error -show_entries format_tags:stream_tags -of default=nw=1 "$PLAT" | grep -qi remotion; then
  echo "metadata still names the renderer" >&2; exit 1
fi
# long, case-sensitive signatures only: a 4-byte case-insensitive match such as "lavf" occurs by
# chance in compressed data
if grep -a -q -E "x264 - core|libx264|Lavf[0-9]|Lavc[0-9]|Lavc libx|[Rr]emotion" "$PLAT"; then
  echo "a tool name is still embedded in $PLAT" >&2; exit 1
fi

[ -n "$SKILL" ] && python3 "$SKILL/media_probe.py" --input "$PLAT" --output "$REP/probe-$ASPECT.json" --pretty >/dev/null || true
[ -n "$SKILL" ] && python3 "$SKILL/audio_qc.py" --input "$PLAT" --target-i -16 --peak-ceiling -1 --output "$REP/audio-qc-$ASPECT.json" --pretty >/dev/null || true
ffmpeg -v error -xerror -i "$PLAT" -f null - && echo "decode ${ASPECT}: ok"
ffmpeg -hide_banner -nostats -i "$PLAT" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tee "$REP/ebur128-$ASPECT.txt"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,bit_rate,color_space,color_primaries,color_transfer,profile,level,pix_fmt -show_entries format=duration,bit_rate,size -of default=nw=1 "$PLAT" | tee "$REP/stream-$ASPECT.txt"

# contact sheet from the encoded file, one frame every 2 s
if [ "$ASPECT" = "9x16" ]; then TILE="12x8"; SC="scale=180:-1"; else TILE="8x11"; SC="scale=320:-1"; fi
ffmpeg -v error -y -i "$PLAT" -vf "fps=1/2,$SC,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=11:fontcolor=white:box=1:boxcolor=black@0.5,tile=$TILE:padding=3:color=white" -frames:v 1 "$REP/sheet-$ASPECT.jpg"
ffmpeg -v error -y -i "$PLAT" -vframes 1 "$REP/first-frame-$ASPECT.png"
shasum -a 256 "$PLAT" | tee "$REP/sha256-$ASPECT.txt"
echo "$PLAT"
[ -f "$OUTI/$BRAND-$TITLE-封面3x4-$DATE-$VER.png" ] || echo "covers for $VER not delivered yet: tools/deliver.sh covers $VER"
