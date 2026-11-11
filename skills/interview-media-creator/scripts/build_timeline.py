#!/usr/bin/env python3
"""Build an interview cut from an EDL: snapped cut points, per-piece SDR video, per-line dialogue WAVs,
the Remotion timeline and subtitle data, and a concat list for the mezzanine.

usage: build_timeline.py EDL.json [--video] [--audio] [--remotion-data DIR] [--nouns "a,b"] [--maxlen 13]

- Cut points: pieces may carry a third element "a" / "b" / "ab" meaning the in / out point is fixed
  (already verified by probe_cuts.py) and must not be snapped. Unfixed points snap to the quietest
  10 ms frame of the 300-3400 Hz envelope near the ASR word boundary (in: -40 ms, out: +80 ms tail).
- Video: every piece is decoded separately from the source, HDR (HLG/PQ) is tone-mapped to SDR bt709
  (mobius), the playback speed is applied, and exactly N frames are kept. Cache key = source range +
  speed + tonemap + target size, so editing the EDL only renders new pieces. This tone mapping ignores
  Dolby Vision metadata and renders iPhone footage too bright and magenta: a source with a Dolby Vision
  configuration record prints a WARN; point "source.video" at the SDR file from sdr_source.py instead.
- Audio: pieces of one sentence are concatenated at 1.0x with 6 ms de-click fades, then time-stretched
  with atempo (pitch preserved) and padded/trimmed to frames x samples-per-frame.
- Captions: the curated text is split into lines at punctuation, then at word boundaries (jieba). Words
  in the EDL "nouns" list, every chapter title (per clause) and --nouns are never split across lines:
  put every decorate anchor and highlight key into "nouns". Times come from the long-file ASR words and
  are provisional; subs_from_lines.py re-times them from the cut lines.
- Outputs: <data>/timeline.json and an undecorated copy <data>/timeline.base.json (decorate.py starts
  from it), <data>/subs.json, render/subs-<version>.srt, render/concat-<version>.txt,
  audio/voice-<version>.json, audio/lines/<version>/<id>.wav (--audio). The speech-band envelope cache
  is audio/<audio stem>.env10ms.npy next to the EDL, never next to a symlink target.
- Paths inside the EDL are resolved relative to the EDL file.

EDL schema (lovstudio/interview-edl/v1):
  {"version": "v0.1", "source": {"video": "../IMG.MOV", "audio": "audio/source-48k.wav",
   "words": "audio/words.json"}, "target": {"width": 1080, "height": 1920, "fps": 30},
   "speed": 1.1, "chapter_card_seconds": 1.2, "outro_seconds": 5, "nouns": ["被访者名", "负一到零"],
   "chapters": [{"id": "ch1", "title": "...", "basis": "..."}],
   "segments": [{"id": "1a", "part": "ch1", "speaker": "G" | "Q", "pieces": [[115.64, 116.58], [117.1, 118.44, "a"]],
                 "text": "curated subtitle text, exactly what is said"},
                {"id": "T", "part": "title", "speaker": null, "pieces": [[56.0, 58.5]], "text": ""}]}
Parts: "open" (cold open), "title", "ch1".."chN" (a chapter card is inserted before the first segment of
each chapter), "end". The title card lasts exactly as long as the title segment's piece (played at 1.0x).
Optional segment "crop": 0..1, the horizontal centre of a full-height crop at the target aspect (landscape
source -> the framed face, from crop_centers.py); without it a different-aspect source is centred over a blurred copy.
Optional segment "crop_track": [[source_t, centre], ...] (reframe.py) pans that crop with the face: each piece gets a
piecewise-linear crop x expression over its own stretch of the track ("crop" must still be set).
"""
import argparse
import difflib
import hashlib
import json
import pathlib
import re
import subprocess

import numpy as np

SR = 48000
TOK_RE = r"[A-Za-z0-9]+|."
PUNCT_RE = r"[，。？！、,.?!：:；;“”\"' @]"


def run(cmd):
    subprocess.run(cmd, check=True)


def key(*xs):
    return hashlib.sha1(json.dumps(xs).encode()).hexdigest()[:12]


def strip_punct(s):
    return re.sub(PUNCT_RE, "", s)


# ---------------------------------------------------------------- envelope / snapping
def load_envelope(wav, cache):
    if cache.exists():
        return np.load(cache)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-af", "highpass=f=300,lowpass=f=3400",
                          "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    hop = SR // 100
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12))
    np.save(cache, db)
    return db


class Snapper:
    def __init__(self, env, words):
        self.env, self.words = env, words

    def _win(self, t0, t1):
        a, b = max(0, int(round(t0 * 100))), min(len(self.env), int(round(t1 * 100)))
        return a, self.env[a:b]

    def snap_in(self, t):
        prev = max([w["e"] for w in self.words if w["e"] <= t + 0.01] or [t - 0.3])
        lo = max(t - 0.25, prev - 0.03)
        a, e = self._win(lo, t + 0.03)
        if not len(e):
            return t
        quiet = np.where(e <= e.min() + 6)[0]
        return max(lo, (a + quiet[-1]) / 100 - 0.04)

    def snap_out(self, t):
        nxt = min([w["s"] for w in self.words if w["s"] >= t - 0.01] or [t + 0.4])
        hi = min(t + 0.35, nxt + 0.02)
        a, e = self._win(t - 0.03, hi)
        if not len(e):
            return t
        quiet = np.where(e <= e.min() + 6)[0]
        return min(hi, (a + quiet[0] + 1) / 100 + 0.08)


# ---------------------------------------------------------------- media
def probe_transfer(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip().strip(",")
    return out


def probe_dovi(video):
    """Dolby Vision configuration record of the first video stream (iPhone HDR video: profile 8.4), or None."""
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream_side_data",
                                   "-of", "json", str(video)], capture_output=True, text=True).stdout or "{}")
    for s in d.get("streams", []):
        for sd in s.get("side_data_list", []) or []:
            if sd.get("side_data_type") == "DOVI configuration record":
                return sd
    return None


def probe_display_size(video):
    """Display width/height after rotation metadata (phones store portrait as rotated landscape)."""
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height:stream_side_data=rotation", "-of", "json", str(video)],
                                  capture_output=True, text=True).stdout)["streams"][0]
    rot = 0
    for sd in d.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    w, h = d["width"], d["height"]
    return (h, w) if abs(rot) % 180 == 90 else (w, h)


def track_expr(track, t0, sw, cw):
    """Piecewise-linear crop x (pixels) over piece-relative t from absolute [[source_t, centre], ...]."""
    pts = sorted((t - t0, min(max(c * sw - cw / 2, 0), sw - cw)) for t, c in track)
    near = [q for q in pts if -1.0 <= q[0]]
    pts = near or pts[-1:]
    if len(pts) == 1:
        return f"{pts[0][1]:.1f}"
    terms = [f"lt(t\\,{pts[0][0]:.3f})*{pts[0][1]:.1f}"]
    for (ta, xa), (tb, xb) in zip(pts, pts[1:]):
        if tb - ta < 1e-3:
            continue
        terms.append(f"gte(t\\,{ta:.3f})*lt(t\\,{tb:.3f})*({xa:.1f}+({xb - xa:.1f})*(t-({ta:.3f}))/{tb - ta:.3f})")
    terms.append(f"gte(t\\,{pts[-1][0]:.3f})*{pts[-1][1]:.1f}")
    return "+".join(terms)


def video_filter(transfer, width, height, fps, speed, src_size=None, crop=None, track=None, t0=0.0):
    if transfer in ("arib-std-b67", "smpte2084"):
        tm = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=mobius:desat=0,"
              "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")
    else:
        tm = "format=yuv420p,"
    if crop is not None and src_size:
        # wider source (landscape two-shot): full-height crop at the target aspect, centred on crop * width
        sw, sh = src_size
        cw = min(sw, int(round(sh * width / height / 2)) * 2)
        x = int(round(min(max(crop * sw - cw / 2, 0), sw - cw)))
        if track:
            # crop runs before setpts, so its t is source seconds from the piece's in point (speed-independent)
            x = track_expr(track, t0, sw, cw)
        sharp =",unsharp=5:5:0.5" if width / cw > 1.3 else ""
        return (f"{tm}crop={cw}:{sh}:{x}:0,scale={width}:{height}:flags=lanczos{sharp},setsar=1,"
                f"setpts=(PTS-STARTPTS)/{speed},fps={fps}")
    if src_size and abs(src_size[0] / src_size[1] - width / height) < 0.01:
        return f"{tm}scale={width}:{height},setsar=1,setpts=(PTS-STARTPTS)/{speed},fps={fps}"
    # different aspect: centre the frame over a blurred copy of itself (no content lost)
    fit = (f"split[a][b];[a]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
           f"gblur=sigma=40,eq=brightness=-0.12[bg];[b]scale={width}:{height}:force_original_aspect_ratio=decrease[fg];"
           f"[bg][fg]overlay=(W-w)/2:(H-h)/2")
    return f"{tm}{fit},setsar=1,setpts=(PTS-STARTPTS)/{speed},fps={fps}"


def render_piece(src, t0, t1, speed, frames, out, vf, fps):
    if out.exists():
        return
    tmp = out.with_suffix(".tmp.mp4")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{(t1 - t0) + 0.5:.3f}",
         "-filter_complex", vf, "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "15",
         "-pix_fmt", "yuv420p", "-r", str(fps), "-video_track_timescale", "15360", str(tmp)])
    n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", str(tmp)], capture_output=True, text=True).stdout
    n = int(n.strip().strip(","))
    if n != frames:
        raise SystemExit(f"{out.name}: rendered {n} frames, expected {frames}")
    tmp.rename(out)


def render_black(frames, out, width, height, fps):
    if out.exists():
        return
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={fps}",
         "-frames:v", str(frames), "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p",
         "-video_track_timescale", "15360", str(out)])


def render_line(wav, pieces, speed, n_samples, out):
    filt, ins = [], []
    for i, (a, b) in enumerate(pieces):
        s0, s1 = int(round(a * SR)), int(round(b * SR))
        d = (s1 - s0) / SR
        filt.append(f"[0:a]atrim=start_sample={s0}:end_sample={s1},asetpts=PTS-STARTPTS,"
                    f"afade=t=in:d=0.006,afade=t=out:st={max(0.0, d - 0.006):.4f}:d=0.006[p{i}]")
        ins.append(f"[p{i}]")
    filt.append(f"{''.join(ins)}concat=n={len(pieces)}:v=0:a=1,atempo={speed},apad,atrim=end_sample={n_samples}[o]")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(wav), "-filter_complex", ";".join(filt), "-map", "[o]",
         "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(out)])


# ---------------------------------------------------------------- subtitles
try:
    import jieba
    jieba.setLogLevel(60)
except ImportError:  # --help works without it; caption splitting refuses to run (see need_jieba)
    jieba = None


def need_jieba():
    """Without jieba, lines split by character count and cut through names and anchors (负一到 / 零)."""
    if jieba is None:
        raise SystemExit("jieba is not installed in this Python; caption line breaks need it. "
                         "Run the skill scripts from the persistent venv, or: pip install jieba")

STICKY = {"也", "都", "就", "还", "很", "又", "才", "在", "把", "给", "对", "比", "这种", "一个", "这个", "那个",
          "任何", "这样", "那样", "一些", "某种", "每个"}
GOOD_NEXT = {"但是", "所以", "然后", "还有", "或者", "就", "因为", "而且", "我", "它", "他们", "我们", "来", "去", "让"}


def add_words(words):
    need_jieba()
    for w in words:
        jieba.add_word(w)


def caption_nouns(edl, extra="", maxlen=13):
    """Words that must stay on one caption line: EDL "nouns" + chapter titles (per clause) + --nouns."""
    out = [n.strip() for n in edl.get("nouns", []) + extra.split(",") if n.strip()]
    for c in edl.get("chapters", []):
        out += [p for p in (strip_punct(x) for x in re.split(r"[，。？！、,.?!：:；;\s]+", c.get("title", "")))
                if p and _units(p) <= maxlen]
    return list(dict.fromkeys(out))


def _units(t):
    return sum(2 if re.match(r"[A-Za-z0-9@]", x) and len(x) > 2 else 1 for x in re.findall(r"[A-Za-z0-9@]+|.", strip_punct(t)))


def _split_clause(p, maxlen):
    """Split a long clause on word boundaries: near the middle, before conjunctions or after 的/了, never inside a word."""
    if _units(p) <= maxlen:
        return [p]
    need_jieba()
    words = [w for w in jieba.cut(p) if w]
    total, acc = _units(p), 0
    best, best_cost = None, 1e9
    for i in range(1, len(words)):
        acc += _units(words[i - 1])
        left, right = acc, total - acc
        if left < 3 or right < 3:
            continue
        cost = abs(left - right)
        if words[i] in GOOD_NEXT:
            cost -= 3
        if words[i - 1].endswith(("的", "了", "吧")):
            cost -= 2
        if words[i].startswith(("的", "了", "吧", "吗", "为")):
            cost += 6
        if words[i - 1] in STICKY or words[i - 1].endswith(("是",)):
            cost += 5
        if max(left, right) > maxlen + 2:
            cost += 6
        if cost < best_cost:
            best, best_cost = i, cost
    if best is None:
        return [p]
    return _split_clause("".join(words[:best]), maxlen) + _split_clause("".join(words[best:]), maxlen)


def split_lines(text, maxlen=13):
    """Split a curated sentence into caption lines: punctuation first, then word boundaries. -> [(display, n_tokens)]"""
    parts = [p for p in re.split(r"(?<=[，。？！、])", text) if strip_punct(p)]
    out = []
    for p in parts:
        for c in _split_clause(p, maxlen):
            disp = re.sub(r"[，。、]$", "", c)
            n = len(re.findall(TOK_RE, strip_punct(c)))
            if n:
                out.append((disp, n))
    return out


def align_chars(text, words, pieces):
    """Align curated text to ASR word times (source clock). Unaligned characters are interpolated."""
    ws = [w for w in words if any(a - 0.05 <= (w["s"] + w["e"]) / 2 <= b + 0.05 for a, b in pieces)]
    chars, times = [], []
    for w in ws:
        t = strip_punct(w["w"])
        toks = re.findall(TOK_RE, t)
        if not toks:
            continue
        d = (w["e"] - w["s"]) / len(toks)
        for i, c in enumerate(toks):
            chars.append(c.lower())
            times.append((w["s"] + i * d, w["s"] + (i + 1) * d))
    tgt = re.findall(TOK_RE, strip_punct(text))
    sm = difflib.SequenceMatcher(None, [c.lower() for c in tgt], chars, autojunk=False)
    res = [None] * len(tgt)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            res[a + k] = times[b + k]
    known = [i for i, r in enumerate(res) if r]
    for i in range(len(res)):
        if res[i] is None:
            lo = max([k for k in known if k < i], default=None)
            hi = min([k for k in known if k > i], default=None)
            if lo is not None and hi is not None:
                f = (i - lo) / (hi - lo)
                s = res[lo][1] + f * (res[hi][0] - res[lo][1])
                res[i] = (s, s)
            elif lo is not None:
                res[i] = (res[lo][1], res[lo][1])
            elif hi is not None:
                res[i] = (res[hi][0], res[hi][0])
            else:
                res[i] = (pieces[0][0], pieces[0][0])
    return res, sm.ratio()


def src_to_out(t, pieces, seg_start_s, speed):
    acc = 0.0
    for a, b in pieces:
        if t <= b:
            return seg_start_s + (acc + max(0.0, t - a)) / speed
        acc += b - a
    return seg_start_s + acc / speed


def tidy_subs(subs, min_gap=0.35, min_dur=0.7, bridge=0.6):
    """Keep text order (input order = output order). Starts strictly increase by at least min_gap (a caption
    that would start too early is pushed later); 0.12 s tail, at least min_dur on screen where the next
    caption allows; gaps under `bridge` are closed; never overlap, always end > start."""
    prev = None
    for s in subs:
        st = max(0.0, s["start"])
        if prev is not None and st < prev + min_gap:
            st = prev + min_gap
        s["start"] = prev = round(st, 3)
    for i, s in enumerate(subs):
        nxt = subs[i + 1]["start"] if i + 1 < len(subs) else None
        end = max(s["end"] + 0.12, s["start"] + min_dur)
        if nxt is not None:
            if nxt - end < bridge:
                end = nxt
            end = min(end, nxt)
        s["end"] = round(end, 3)
        if s["end"] <= s["start"]:
            raise SystemExit(f"caption '{s['text']}' has end {s['end']} <= start {s['start']}")
    return subs


def seg_captions(seg, snapped, seg_start_s, speed, words, maxlen):
    """Provisional captions of one speech segment from long-file ASR words -> ([sub], match ratio)."""
    times, ratio = align_chars(seg["text"], words, snapped)
    out, idx = [], 0
    for disp, n in split_lines(seg["text"], maxlen):
        ts_ = times[idx:idx + n]
        idx += n
        out.append({"seg": seg["id"], "speaker": seg["speaker"], "part": seg["part"], "text": disp,
                    "start": round(src_to_out(ts_[0][0], snapped, seg_start_s, speed), 3),
                    "end": round(src_to_out(ts_[-1][1], snapped, seg_start_s, speed), 3)})
    return out, ratio


def write_srt(subs, path):
    def ts(t):
        h, r = divmod(t, 3600)
        m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round(t * 1000)) % 1000:03d}"
    path.write_text("".join(f"{i + 1}\n{ts(s['start'])} --> {ts(s['end'])}\n{s['text']}\n\n" for i, s in enumerate(subs)))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--video", action="store_true", help="render missing video pieces")
    ap.add_argument("--audio", action="store_true", help="render dialogue line WAVs")
    ap.add_argument("--remotion-data", default="remotion/public/data", help="where timeline.json / subs.json go (relative to EDL)")
    ap.add_argument("--nouns", default="", help="extra comma-separated words kept on one caption line (added to EDL \"nouns\")")
    ap.add_argument("--maxlen", type=int, default=13, help="caption line length in CJK units")
    a = ap.parse_args()

    edl_path = pathlib.Path(a.edl).resolve()
    root = edl_path.parent
    edl = json.loads(edl_path.read_text())
    ver = edl["version"]
    src = (root / edl["source"]["video"]).resolve()
    wav = (root / edl["source"]["audio"]).resolve()
    words = json.loads((root / edl["source"]["words"]).read_text())
    W, H, FPS = edl["target"]["width"], edl["target"]["height"], edl["target"]["fps"]
    SPF = SR // FPS
    speed = edl.get("speed", 1.0)
    add_words(caption_nouns(edl, a.nouns, a.maxlen))

    (root / "audio").mkdir(parents=True, exist_ok=True)
    env = load_envelope(wav, root / "audio" / f"{pathlib.Path(edl['source']['audio']).stem}.env10ms.npy")
    snap = Snapper(env, words)
    transfer = probe_transfer(src)
    dv = probe_dovi(src) if transfer in ("arib-std-b67", "smpte2084") else None
    if dv:
        print(f"WARN {src.name}: Dolby Vision profile {dv.get('dv_profile')}.{dv.get('dv_bl_signal_compatibility_id')}; "
              "ffmpeg tone mapping renders it too bright and magenta. Run sdr_source.py and point EDL "
              "\"source.video\" at the SDR file (audio stays the original WAV)", flush=True)
    src_size = probe_display_size(src)
    segdir = root / "render" / "seg"
    segdir.mkdir(parents=True, exist_ok=True)
    linedir = root / "audio" / "lines" / ver
    linedir.mkdir(parents=True, exist_ok=True)
    data = (root / a.remotion_data).resolve()
    data.mkdir(parents=True, exist_ok=True)
    chap_titles = {c["id"]: c["title"] for c in edl["chapters"]}

    timeline, concat, lines, subs = [], [], [], []
    frame, last_part, prev_piece = 0, None, None
    for seg in edl["segments"]:
        part = seg["part"]
        if part.startswith("ch") and part != last_part:
            n = int(round(edl.get("chapter_card_seconds", 1.2) * FPS))
            f = segdir / f"black-{W}x{H}-{n}.mp4"
            if a.video:
                render_black(n, f, W, H, FPS)
            concat.append(f)
            timeline.append({"kind": "chapter", "chapter": part, "index": int(part[2:]), "title": chap_titles[part],
                             "start": frame, "frames": n})
            frame += n
        last_part = part
        if part == "title":
            t0, t1 = seg["pieces"][0][:2]
            n = int(round((t1 - t0) * FPS))
            vf = video_filter(transfer, W, H, FPS, 1.0, src_size, seg.get("crop"))
            f = segdir / f"v-{key(str(src), t0, t1, 1.0, vf)}.mp4"
            if a.video:
                render_piece(src, t0, t1, 1.0, n, f, vf, FPS)
            concat.append(f)
            timeline.append({"kind": "title", "id": seg["id"], "start": frame, "frames": n, "src": [t0, t1], "file": f.name})
            frame += n
            continue
        snapped = []
        for p in seg["pieces"]:
            flags = p[2] if len(p) > 2 else ""
            snapped.append([round(p[0] if "a" in flags else snap.snap_in(p[0]), 3),
                            round(p[1] if "b" in flags else snap.snap_out(p[1]), 3)])
        seg_start, meta = frame, []
        vf = video_filter(transfer, W, H, FPS, speed, src_size, seg.get("crop"))
        for p0, p1 in snapped:
            if seg.get("crop_track"):
                vf = video_filter(transfer, W, H, FPS, speed, src_size, seg.get("crop"), seg["crop_track"], p0)
            if prev_piece and prev_piece[1] < p1 and p0 < prev_piece[2] - 0.005:
                # adjacent cuts from the same source stretch (question then answer) must share one cut point,
                # otherwise the overlap is heard twice ("介绍一下" -> "绍" repeated)
                print(f"WARN {seg['id']}: piece {p0}-{p1} overlaps the previous piece ({prev_piece[0]} ends at "
                      f"{prev_piece[2]}) by {prev_piece[2] - p0:.2f}s; give both one shared, fixed cut point")
            prev_piece = (seg["id"], p0, p1)
            n = int(round((p1 - p0) / speed * FPS))
            if n < 1:
                raise SystemExit(f"segment {seg['id']}: piece {p0}-{p1} is shorter than one frame")
            f = segdir / f"v-{key(str(src), p0, p1, speed, vf)}.mp4"
            if a.video:
                render_piece(src, p0, p1, speed, n, f, vf, FPS)
            concat.append(f)
            meta.append({"src": [p0, p1], "start": frame, "frames": n, "file": f.name})
            frame += n
        nseg = frame - seg_start
        lf = linedir / f"{seg['id']}.wav"
        if a.audio:
            render_line(wav, snapped, speed, nseg * SPF, lf)
        lines.append({"id": seg["id"], "file": str(lf.relative_to(root / "audio")), "at": round(seg_start / FPS, 4),
                      "frames": nseg, "speaker": seg["speaker"]})
        timeline.append({"kind": "speech", "id": seg["id"], "part": part, "speaker": seg["speaker"], "start": seg_start,
                         "frames": nseg, "pieces": meta, "text": seg["text"]})
        caps, ratio = seg_captions(seg, snapped, seg_start / FPS, speed, words, a.maxlen)
        subs += caps
        if ratio < 0.8:
            print(f"WARN {seg['id']}: curated text matches ASR only {ratio:.2f}; check the text or the pieces")

    outro = int(round(edl.get("outro_seconds", 5) * FPS))
    f = segdir / f"black-{W}x{H}-{outro}.mp4"
    if a.video:
        render_black(outro, f, W, H, FPS)
    concat.append(f)
    timeline.append({"kind": "outro", "start": frame, "frames": outro})
    frame += outro

    tl_json = json.dumps({"version": ver, "fps": FPS, "width": W, "height": H, "frames": frame,
                          "chapters": edl["chapters"], "items": timeline}, ensure_ascii=False, indent=1)
    (data / "timeline.base.json").write_text(tl_json)
    (data / "timeline.json").write_text(tl_json)
    subs = tidy_subs(subs)
    (data / "subs.json").write_text(json.dumps(subs, ensure_ascii=False, indent=1))
    (root / "render" / f"concat-{ver}.txt").write_text("".join(f"file '{p}'\n" for p in concat))
    (root / "audio" / f"voice-{ver}.json").write_text(json.dumps({"duration": round(frame / FPS, 4), "lines": lines},
                                                                ensure_ascii=False, indent=1))
    write_srt(subs, root / "render" / f"subs-{ver}.srt")
    print(f"frames {frame} = {frame / FPS:.2f}s, segments {len(edl['segments'])}, subtitles {len(subs)}, transfer {transfer or 'sdr'}")


if __name__ == "__main__":
    main()
