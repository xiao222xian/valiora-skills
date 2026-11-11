#!/usr/bin/env python3
"""Time captions from the cut dialogue itself: transcribe every line WAV with each Whisper model, keep per line
the model whose caption starts sit closest to the voice onsets, and align the curated EDL text to it.

usage: subs_from_lines.py EDL.json [--remotion-data remotion/public/data] [--nouns "a,b"] [--maxlen 13]
                          [--models large-v3,turbo] [--min-ratio 0.6] [--max-rate 12] [--snap 0.5] [--flash 0.5]
                          [--report PATH]

Short line files have no long-file timestamp drift, so this replaces the provisional caption times written
by build_timeline.py. Displayed text always comes from the EDL (the corrected spoken words); line breaks
use the same words as build_timeline.py (EDL "nouns" + chapter titles + --nouns). One model alone is not
reliable enough: on a 27-minute interview large-v3 alone left 7 caption lines on provisional times, timed a
0.35 s flash line and started the cold open's first caption 1 s late. Per dialogue line:
1. Every model in --models transcribes the line WAV (again without the prompt when the match is below
   --min-ratio: on short WAVs Whisper may echo the prompt or hallucinate). A model below --min-ratio is not
   used for that line; when every model is below it, the line keeps its provisional captions:
   "WARN <id>: line ASR matched only X, kept provisional times".
2. Choice: a model whose times would show a caption faster than --max-rate units/s (7 characters in
   0.35 s) is passed over unless every model does. The voice onsets of the line WAV (speech-band energy
   above the 95th percentile of all dialogue - 16 dB, after >= 80 ms below it) score the rest by the mean
   distance of their caption starts, the first caption excluded; the first model wins unless another is
   closer by more than 0.02 s.
3. Caption lines the chosen model cannot time (unaligned leading / trailing characters) take the next
   model's time, then the provisional time; unaligned characters between aligned neighbours are interpolated.
4. Piece starts: a caption start within --snap seconds of a later piece start of the line moves onto it
   (each piece start and each caption at most once; --snap 0 turns this off).
5. Flash lines: a caption of at most --flash-units units ("OK", "对", "对吧") that the aligned times keep on
   screen for less than --flash seconds joins its neighbour in the same line: backwards when it is the last
   caption or ends with a sentence-final particle (吧吗呢啊呀嘛啦, trailing ？！，。 ignored: "对吧？" too),
   otherwise forwards.
6. Head: the first caption starts exactly with the line, because every in-point was trial-cut to the first
   word with probe_cuts.py.
Then build_timeline's tidy pass runs over all captions (order, minimum gap, tail, no overlap). Every caption
must start inside its line and end after it starts, and every line's first caption must start with the line;
otherwise the script exits 1 without writing. Low-match lines, captions left on provisional times and
captions shorter than 0.6 s are listed at the end for a listen.
Provisional times are read from the existing subs.json before it is overwritten (recomputed from the
long-file words when that file no longer matches the EDL). --models takes the aliases large-v3 and turbo,
Hugging Face repos or local model directories, transcribed one model at a time; --nouns are also the proper
nouns in the Whisper prompt, the EDL "nouns" only steer line breaks. Writes subs.json,
render/subs-<version>.srt and the per-line choices to qc/subs-timing-<version>.json (--report).
"""
import argparse
import difflib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

import numpy as np

sys.dont_write_bytecode = True  # importing build_timeline must not leave __pycache__ inside the skill
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_timeline", HERE / "build_timeline.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
TOK = r"[A-Za-z0-9]+|."
MODEL_ALIASES = {"large-v3": "mlx-community/whisper-large-v3-mlx", "turbo": "mlx-community/whisper-large-v3-turbo"}
PARTICLES = ("吧", "吗", "呢", "啊", "呀", "嘛", "啦")
LEAD, TAIL = 0.05, 0.05  # caption lead before the first aligned character, tail after the last


def model_list(spec_):
    return [MODEL_ALIASES.get(m.strip(), os.path.expanduser(m.strip())) for m in spec_.split(",") if m.strip()]


def short(model):
    return pathlib.Path(model).name if os.path.isdir(model) else model.split("/")[-1]


def provisional(root, edl, data, maxlen):
    """Provisional captions per segment id, in text order: subs.json if it matches the current split,
    else recomputed from the long-file ASR words and the snapped pieces in the timeline."""
    by_seg = {}
    f = data / "subs.json"
    for s in json.loads(f.read_text()) if f.exists() else []:
        by_seg.setdefault(s["seg"], []).append(s)
    tlf = data / "timeline.base.json" if (data / "timeline.base.json").exists() else data / "timeline.json"
    tl = json.loads(tlf.read_text())
    items = {i["id"]: i for i in tl["items"] if i["kind"] == "speech"}
    words = None
    out = {}
    for seg in edl["segments"]:
        if seg["id"] not in items:
            continue
        want = [d for d, _ in B.split_lines(seg["text"], maxlen)]
        have = by_seg.get(seg["id"], [])
        if [s["text"] for s in have] == want:
            out[seg["id"]] = have
            continue
        if words is None:
            words = json.loads((root / edl["source"]["words"]).read_text())
        it = items[seg["id"]]
        snapped = [p["src"] for p in it["pieces"]]
        out[seg["id"]], _ = B.seg_captions(seg, snapped, it["start"] / tl["fps"], edl.get("speed", 1.0), words, maxlen)
    return out, items, tl["fps"]


def transcribe(wav, model, prompt, tgt, min_ratio, conv):
    """-> (ratio, SequenceMatcher, char times, retried without prompt)."""
    import mlx_whisper
    best = None
    for pr in (prompt, None):
        r = mlx_whisper.transcribe(str(wav), path_or_hf_repo=model, language="zh", temperature=0.0,
                                   word_timestamps=True, condition_on_previous_text=False, initial_prompt=pr)
        chars, times = [], []
        for s_ in r["segments"]:
            for w in s_.get("words", []):
                toks = re.findall(TOK, B.strip_punct(conv(w["word"])))
                if not toks:
                    continue
                d = (w["end"] - w["start"]) / len(toks)
                for i, c in enumerate(toks):
                    chars.append(c.lower())
                    times.append((w["start"] + i * d, w["start"] + (i + 1) * d))
        sm = difflib.SequenceMatcher(None, [c.lower() for c in tgt], chars, autojunk=False)
        if best is None or sm.ratio() > best[0]:
            best = (sm.ratio(), sm, times, pr is None)
        if best[0] >= min_ratio:
            break
    return best


def caption_spans(sm, times, ntgt, lines):
    """Line-local (first char start, last char end) per caption line; None where an edge character is unaligned."""
    res = [None] * ntgt
    for x, y, size in sm.get_matching_blocks():
        for k in range(size):
            res[x + k] = times[y + k]
    known = [i for i, v in enumerate(res) if v]
    for i in range(len(res)):  # interior gaps only; leading / trailing stay None
        if res[i] is None and known and known[0] < i < known[-1]:
            lo = max(k for k in known if k < i)
            hi = min(k for k in known if k > i)
            t0 = res[lo][1] + (i - lo) / (hi - lo) * (res[hi][0] - res[lo][1])
            res[i] = (t0, t0)
    spans, idx = [], 0
    for _, n in lines:
        ts = res[idx:idx + n]
        idx += n
        spans.append(None if any(t is None for t in ts) else (ts[0][0], ts[-1][1]))
    return spans


def envelope(wav):
    """Speech-band (200-4000 Hz) 10 ms energy in dBFS."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-af", "highpass=f=200,lowpass=f=4000", "-f", "f32le",
                          "-ac", "1", "-ar", "48000", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    n = len(x) // 480
    return 20 * np.log10(np.sqrt((x[:n * 480].reshape(n, 480) ** 2).mean(1)) + 1e-9) if n else np.zeros(0)


def onsets(e, thr):
    """Line-local voice onsets: energy above thr after >= 80 ms below it."""
    out, quiet = [], 0
    for i, v in enumerate(e > thr):
        if v and quiet >= 8:
            out.append(i / 100)
        quiet = 0 if v else quiet + 1
    return out


def units(text):
    return B._units(text)


def too_fast(spans, lines, max_rate):
    """Caption indexes this model would show faster than max_rate units/s (first caption from the line start)."""
    starts = [0.0] + [s[0] - LEAD if s else None for s in spans[1:]]
    out = []
    for k, (disp, _) in enumerate(lines):
        nxt = starts[k + 1] if k + 1 < len(lines) else (spans[k][1] if spans[k] else None)
        if starts[k] is not None and nxt is not None and units(disp) / max(nxt - starts[k], 0.01) > max_rate:
            out.append(k)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--remotion-data", default="remotion/public/data")
    ap.add_argument("--nouns", default="", help="proper nouns: Whisper prompt + kept on one caption line")
    ap.add_argument("--maxlen", type=int, default=13)
    ap.add_argument("--models", default="large-v3,turbo",
                    help="comma-separated: large-v3, turbo, Hugging Face repos or local model directories; the first wins ties")
    ap.add_argument("--model", help="a single model (same as --models MODEL)")
    ap.add_argument("--min-ratio", type=float, default=0.6, help="below this line match a model is not used for the line")
    ap.add_argument("--max-rate", type=float, default=12.0,
                    help="a model that would show a caption faster than this many units/s is passed over for the line")
    ap.add_argument("--snap", type=float, default=0.5, help="move a caption start within this many seconds onto a piece start")
    ap.add_argument("--flash", type=float, default=0.5, help="captions on screen shorter than this may join a neighbour")
    ap.add_argument("--flash-units", type=int, default=2, help="only captions of at most this many units join a neighbour")
    ap.add_argument("--report", help="per-line choices (default qc/subs-timing-<version>.json next to the EDL)")
    a = ap.parse_args()
    models = model_list(a.model or a.models)
    if not models:
        raise SystemExit("--models is empty")
    try:
        import opencc
        conv = opencc.OpenCC("t2s").convert
    except ImportError:
        conv = lambda s: s  # noqa: E731

    edl_path = pathlib.Path(a.edl).resolve()
    root, edl = edl_path.parent, json.loads(edl_path.read_text())
    ver = edl["version"]
    data = (root / a.remotion_data).resolve()
    voice = json.loads((root / "audio" / f"voice-{ver}.json").read_text())
    segs = {s["id"]: s for s in edl["segments"]}
    B.add_words(B.caption_nouns(edl, a.nouns, a.maxlen))
    prov, items, fps = provisional(root, edl, data, a.maxlen)
    nouns = [n for n in a.nouns.split(",") if n]
    prompt = "以下是普通话访谈，使用简体中文。" + ("专有名词：" + "，".join(nouns) + "。" if nouns else "")

    plan = []
    for ln in voice["lines"]:
        seg = segs[ln["id"]]
        lines = B.split_lines(seg["text"], a.maxlen)
        pv = prov.get(seg["id"], [])
        if len(pv) != len(lines):
            raise SystemExit(f"{seg['id']}: no provisional captions for this line; re-run build_timeline.py first")
        plan.append({"ln": ln, "seg": seg, "lines": lines, "pv": pv, "wav": root / "audio" / ln["file"],
                     "tgt": re.findall(TOK, B.strip_punct(seg["text"]))})
    asr = {}  # (model, line id) -> (ratio, spans, retried); one model at a time, so each loads once
    for m in models:
        print(f"transcribing {len(plan)} lines with {short(m)}", flush=True)
        for p in plan:
            ratio, sm, times, retried = transcribe(p["wav"], m, prompt, p["tgt"], a.min_ratio, conv)
            asr[m, p["ln"]["id"]] = (ratio, caption_spans(sm, times, len(p["tgt"]), p["lines"]), retried)
    for p in plan:
        p["env"] = envelope(p["wav"])
    live = np.concatenate([p["env"][p["env"] > -120] for p in plan] or [np.zeros(0)])
    # onset threshold follows the recording: 95th percentile of all dialogue - 16 dB (-48 dBFS on a lavalier interview)
    thr = float(np.percentile(live, 95)) - 16 if len(live) else -48.0

    subs, firsts, low, kept, report = [], [], [], [], []
    for p in plan:
        ln, seg, lines, pv = p["ln"], p["seg"], p["lines"], p["pv"]
        sid, at, dur = ln["id"], ln["at"], ln["frames"] / fps
        it = items[sid]
        piece_starts = [(q["start"] - it["start"]) / fps for q in it["pieces"][1:]]
        ratios = {short(m): round(asr[m, sid][0], 3) for m in models}
        usable = [m for m in models if asr[m, sid][0] >= a.min_ratio]
        rec = {"id": sid, "at": at, "ratios": ratios, "chosen": None, "scores": {}, "filled": [], "provisional": [],
               "snapped": [], "merged": []}
        if not usable:
            print(f"WARN {sid}: line ASR matched only {max(ratios.values()):.2f}, kept provisional times", flush=True)
            low.append((sid, max(ratios.values())))
            caps = [[c["start"], c["end"]] for c in pv]
            rec["provisional"] = list(range(len(caps)))
        else:
            fast = {m: too_fast(asr[m, sid][1], lines, a.max_rate) for m in usable}
            pool = [m for m in usable if not fast[m]] or usable
            ons = np.array([0.0] + onsets(p["env"], thr))
            common = [k for k in range(1, len(lines)) if all(asr[m, sid][1][k] for m in pool)]
            score = {m: float(np.mean([np.min(np.abs(ons - (asr[m, sid][1][k][0] - LEAD))) for k in common]))
                     if common else 0.0 for m in pool}
            best = min(pool, key=lambda m: score[m])
            chosen = pool[0] if score[pool[0]] - score[best] <= 0.02 else best
            rec["chosen"] = short(chosen)
            rec["scores"] = {short(m): round(v, 3) for m, v in score.items()}
            rec["too_fast"] = {short(m): [lines[k][0] for k in ks] for m, ks in fast.items() if ks}
            caps = []
            for k in range(len(lines)):
                span = next((asr[m, sid][1][k] for m in [chosen] + usable if asr[m, sid][1][k]), None)
                if span is None:
                    caps.append([pv[k]["start"], pv[k]["end"]])
                    rec["provisional"].append(k)
                    continue
                if not asr[chosen, sid][1][k]:
                    rec["filled"].append(k)
                caps.append([at + max(0.0, span[0] - LEAD), at + min(dur, span[1] + TAIL)])
            if rec["provisional"]:
                kept.append((sid, len(rec["provisional"]), len(lines)))
        if a.snap > 0:  # piece starts are trial-cut word onsets
            pairs = sorted((abs(caps[k][0] - (at + b)), k, at + b) for k in range(1, len(caps)) for b in piece_starts)
            used_k, used_b = set(), set()
            for d, k, b in pairs:
                if d <= a.snap and k not in used_k and b not in used_b:
                    caps[k][0] = b
                    used_k.add(k)
                    used_b.add(b)
                    rec["snapped"].append([k, round(b, 3)])
        rows = [{"seg": sid, "speaker": seg["speaker"], "part": seg["part"], "text": disp, "start": st, "end": en}
                for (disp, _), (st, en) in zip(lines, caps)]
        shown = [(rows[k + 1]["start"] if k + 1 < len(rows) else rows[k]["end"]) - rows[k]["start"] for k in range(len(rows))]
        flash = [len(rows) > 1 and units(r["text"]) <= a.flash_units and shown[k] < a.flash for k, r in enumerate(rows)]
        k = 0
        while k < len(rows):
            if not flash[k] or len(rows) == 1:
                k += 1
                continue
            back = k == len(rows) - 1 or (k > 0 and rows[k]["text"].rstrip("？！?!，,。.").endswith(PARTICLES))
            i, j = (k - 1, k) if back else (k, k + 1)
            left, right = rows[i], rows[j]
            rec["merged"].append(rows[k]["text"])
            joiner = "" if re.search(r"[？！?!…]$", left["text"]) else "，"
            rows[i:j + 1] = [dict(left, text=left["text"] + joiner + right["text"], end=right["end"])]
            flash[i:j + 1] = [False]
            k = i + 1
        rows[0]["start"] = at  # in-points are trial-cut to the first word
        prev = at
        for r in rows:  # text order inside the line, never before the line
            r["start"] = round(max(r["start"], prev, at), 3)
            r["end"] = round(max(r["end"], r["start"]), 3)
            prev = r["start"]
        firsts.append(len(subs))
        subs += [dict(r, _at=at) for r in rows]
        report.append(rec)
        print(f"{sid:4s} " + " / ".join(f"{m} {r:.2f}" for m, r in ratios.items())
              + (f" -> {rec['chosen']}" if rec["chosen"] else " -> provisional")
              + "".join(f", {m} too fast on {'/'.join(t)}" for m, t in rec.get("too_fast", {}).items())
              + (f", filled {len(rec['filled'])}" if rec["filled"] else "")
              + (f", provisional {len(rec['provisional'])}/{len(lines)}" if rec["provisional"] and rec["chosen"] else "")
              + (f", snapped {len(rec['snapped'])}" if rec["snapped"] else "")
              + (f", joined {' '.join(rec['merged'])}" if rec["merged"] else ""), flush=True)

    bounds = [s.pop("_at") for s in subs]
    subs = B.tidy_subs(subs)
    for i in firsts:  # the tidy pass may push a first caption after a very short previous one
        if subs[i]["start"] > bounds[i] + 0.001:
            subs[i]["start"] = round(bounds[i], 3)
            if i:
                subs[i - 1]["end"] = min(subs[i - 1]["end"], subs[i]["start"])
    first_set = set(firsts)
    bad = [f"'{s['text']}' {s['start']}-{s['end']} (line starts {b})" for i, (s, b) in enumerate(zip(subs, bounds))
           if s["end"] <= s["start"] or s["start"] < b - 0.001 or (i in first_set and abs(s["start"] - b) > 0.001)]
    if bad:
        raise SystemExit("bad caption times, nothing written:\n  " + "\n  ".join(bad))
    (data / "subs.json").write_text(json.dumps(subs, ensure_ascii=False, indent=1))
    B.write_srt(subs, root / "render" / f"subs-{ver}.srt")
    rep = pathlib.Path(a.report) if a.report else root / "qc" / f"subs-timing-{ver}.json"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(json.dumps({"version": ver, "models": [short(m) for m in models], "onset_db": round(thr, 1),
                               "lines": report}, ensure_ascii=False, indent=1))
    if low:
        print("low-match lines (provisional times kept, check by ear): " + ", ".join(f"{i} {r:.2f}" for i, r in low))
    if kept:
        print("caption lines left on provisional times: " + ", ".join(f"{i} {k}/{n}" for i, k, n in kept))
    short_caps = [f"{s['seg']} '{s['text']}' {s['end'] - s['start']:.2f}s" for s in subs if s["end"] - s["start"] < 0.6]
    if short_caps:
        print("captions shorter than 0.6 s (check by ear): " + ", ".join(short_caps))
    print(f"subtitles {len(subs)} -> {data / 'subs.json'}; choices -> {rep}")


if __name__ == "__main__":
    main()
