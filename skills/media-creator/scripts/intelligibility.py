#!/usr/bin/env python3
"""Objective proxy for "the music masks the voice": Whisper CER of a mix vs a voice-only floor.

Every SRT cue is cut out on its own (cue +- 0.3 s) and transcribed separately, then scored by
character error rate (CER, capped at 1.0); the mean is compared with the same score on the voice-only
stem (the floor: Whisper's own error without music). Gate: mean CER of the mix - floor <= --max-delta
over the cues scored in both. Per-cue clips matter: transcribing the whole film lets audio elsewhere in
Whisper's 30 s window flip a cue whose own audio did not change. Decoding is deterministic
(temperature 0) so a rerun gives the same verdict.
Whisper repetition loops ("icangoicango...") are an ASR failure, not masking evidence: such cues are
listed under asr_loops for listening and left out of both means. Per-cue CER is noisy, so the largest
per-cue regressions are only listed for listening, never gated.

--source checks the voice processing itself (isolation, denoise, generative enhancement): the same
dialogue built from the unprocessed source on the same timeline is scored too, and the floor's mean CER
may exceed it by at most --max-processing-delta. The masking gate cannot see this, because a processing
stage that garbles speech lowers the floor and the mix together. A processing regression fails the run
unless --processing-accepted records the author's words after they heard an A/B of the worst cues.

--floor and --source accept an audio file (transcribed now; save it with --floor-output /
--source-output to reuse) or a JSON written earlier by this script. Backends: mlx-whisper (Apple Silicon) or openai-whisper. Run with a
Python that already has one installed; set HF_HUB_OFFLINE=1 when the model is cached locally.
"""
import argparse
import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

MODELS = {"mlx": "mlx-community/whisper-large-v3-mlx", "openai": "large-v3"}
MODE = "per-cue"
SR = 16000
# Short clips have no context, so Whisper may switch to Traditional characters at random; a prompt in
# Simplified Chinese keeps the script stable (both sides get the same prompt).
PROMPTS = {"zh": "以下是普通话的句子，使用简体中文。"}


def norm(s):
    return re.sub(r"[^一-鿿0-9a-zA-Z]", "", s)


def cer(ref, hyp):
    r, h = norm(ref), norm(hyp)
    if not r:
        return 0.0
    d = list(range(len(h) + 1))
    for i, rc in enumerate(r, 1):
        prev, d[0] = d[0], i
        for j, hc in enumerate(h, 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (rc != hc))
            prev, d[j] = d[j], cur
    return d[len(h)] / len(r)


def asr_loop(ref, hyp):
    r, h = norm(ref), norm(hyp)
    return len(h) > 2 * len(r) + 4 and re.search(r"(.{2,8})\1{3,}", h) is not None


def parse_srt(path):
    def sec(t):
        h, m, s = t.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    cues = []
    text = Path(path).read_text(encoding="utf-8-sig")
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        lines = block.strip().split("\n")
        for k, ln in enumerate(lines):
            m = re.match(r"(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)", ln)
            if m:
                cues.append((sec(m.group(1)), sec(m.group(2)), "".join(lines[k + 1:])))
                break
    return cues


def backend_name(choice):
    if choice != "auto":
        return choice
    try:
        import mlx_whisper  # noqa: F401
        return "mlx"
    except ImportError:
        pass
    try:
        import whisper  # noqa: F401
        return "openai"
    except ImportError:
        sys.exit("no Whisper backend: install mlx-whisper or openai-whisper in this Python, "
                 "or run the script with an existing venv that has one")


def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-map", "0:a:0", "-ac", "1",
                          "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


@lru_cache(maxsize=1)
def openai_model(name):
    import whisper
    return whisper.load_model(name)


def transcribe(clip, backend, model, language):
    kw = {"language": language, "condition_on_previous_text": False, "temperature": 0.0,
          "initial_prompt": PROMPTS.get(language)}
    if backend == "mlx":
        import mlx_whisper
        r = mlx_whisper.transcribe(clip, path_or_hf_repo=model, **kw)
    else:
        r = openai_model(model).transcribe(clip, **kw)
    return "".join(s["text"].strip() for s in r["segments"])


def score(audio, cues, backend, model, language):
    x = load_audio(audio)
    rows = []
    for a, b, text in cues:
        clip = np.ascontiguousarray(x[max(0, int((a - 0.3) * SR)):int((b + 0.3) * SR)])
        heard = transcribe(clip, backend, model, language) if len(clip) > SR // 10 else ""
        rows.append({"t": round(a, 2), "sub": text, "asr": heard, "cer": round(min(1.0, cer(text, heard)), 3),
                     "asr_loop": asr_loop(text, heard)})
    return {"mix": str(audio), "mode": MODE, "mean_cer": round(mean_cer(rows), 4), "rows": rows}


def mean_cer(rows):
    kept = [min(1.0, r["cer"]) for r in rows if not asr_loop(r["sub"], r["asr"])]
    return sum(kept) / max(1, len(kept))


def load_or_score(path, cues, backend, model, language, save=None):
    if path.endswith(".json"):
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        if d.get("mode") != MODE:
            sys.exit(f"{path} was scored in another mode; pass the audio to re-score it")
        return d
    d = score(path, cues, backend, model, language)
    if save:
        Path(save).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def compare(top, base):
    """Pair the cues scored in both runs, drop ASR loops on either side, and return each side's mean
    CER, their difference (top - base) and the cues where top lost the most."""
    by_t = {r["t"]: r for r in base["rows"]}
    loops = [r for r in top["rows"] if asr_loop(r["sub"], r["asr"])
             or (r["t"] in by_t and asr_loop(by_t[r["t"]]["sub"], by_t[r["t"]]["asr"]))]
    paired = [(r, by_t[r["t"]]) for r in top["rows"] if r["t"] in by_t and r not in loops]
    a, b = mean_cer([m for m, _ in paired]), mean_cer([f for _, f in paired])
    worse = sorted(({"t": m["t"], "sub": m["sub"], "asr": m["asr"], "base_asr": f["asr"],
                     "delta": round(min(1.0, m["cer"]) - min(1.0, f["cer"]), 3)} for m, f in paired),
                   key=lambda r: -r["delta"])
    return {"paired": len(paired), "top": a, "base": b, "delta": a - b, "loops": loops,
            "worse": [r for r in worse if r["delta"] > 0]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mix", required=True, help="final mix (WAV or any decodable audio/video)")
    ap.add_argument("--srt", required=True, help="subtitles on the same timeline")
    ap.add_argument("--output", required=True, help="JSON report")
    ap.add_argument("--floor", help="voice-only stem to transcribe, or a JSON from an earlier run")
    ap.add_argument("--floor-output", help="save the floor transcription JSON for reuse")
    ap.add_argument("--max-delta", type=float, default=0.02, help="allowed mean CER above the floor (default 0.02)")
    ap.add_argument("--source", help="the same dialogue built from the unprocessed source on the same timeline "
                    "(audio or JSON); checks that voice processing did not cost intelligibility; needs --floor")
    ap.add_argument("--source-output", help="save the source transcription JSON for reuse")
    ap.add_argument("--max-processing-delta", type=float, default=0.05,
                    help="allowed floor mean CER above the unprocessed source (default 0.05)")
    ap.add_argument("--processing-accepted", metavar="AUTHOR_WORDS",
                    help="the author heard an A/B of the worst cues and kept the processing: their words, "
                         "recorded in the report; a processing regression is then reported, not failed")
    ap.add_argument("--language", default="zh")
    ap.add_argument("--backend", choices=["auto", "mlx", "openai"], default="auto")
    ap.add_argument("--model", help="model id (default per backend: large-v3)")
    args = ap.parse_args()
    backend = backend_name(args.backend)
    model = args.model or MODELS[backend]
    cues = parse_srt(args.srt)
    rep = score(args.mix, cues, backend, model, args.language)
    rep.update({"srt": args.srt, "backend": backend, "model": model, "language": args.language})
    if args.source and not args.floor:
        sys.exit("--source needs --floor (the processed voice-only stem)")
    floor = load_or_score(args.floor, cues, backend, model, args.language, args.floor_output) if args.floor else None
    if floor:
        c = compare(rep, floor)
        rep.update({"floor": {"source": args.floor, "mean_cer": round(mean_cer(floor["rows"]), 4)},
                    "paired_cues": c["paired"], "paired_mix_cer": round(c["top"], 4),
                    "paired_floor_cer": round(c["base"], 4), "delta": round(c["delta"], 4),
                    "max_delta": args.max_delta, "pass": c["delta"] <= args.max_delta,
                    "asr_loops": [{"t": r["t"], "sub": r["sub"], "asr": r["asr"][:60]} for r in c["loops"]],
                    "largest_regressions": [{k: r[k] for k in ("t", "sub", "asr", "delta")} for r in c["worse"][:8]]})
    if args.source:
        src = load_or_score(args.source, cues, backend, model, args.language, args.source_output)
        c = compare(floor, src)
        rep["processing"] = {"source": args.source, "paired_cues": c["paired"], "floor_cer": round(c["top"], 4),
                             "source_cer": round(c["base"], 4), "delta": round(c["delta"], 4),
                             "max_delta": args.max_processing_delta, "pass": c["delta"] <= args.max_processing_delta,
                             "accepted_by_author": args.processing_accepted,
                             "largest_regressions": c["worse"][:12]}
    Path(args.output).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"mix mean CER {rep['mean_cer']:.3f} over {len(rep['rows'])} cues")
    if not floor:
        print("RESULT NO-GATE (pass --floor with the voice-only stem to gate masking)")
        return 0
    print(f"paired {rep['paired_cues']} cues: mix {rep['paired_mix_cer']:.3f}  floor {rep['paired_floor_cer']:.3f}  "
          f"delta {rep['delta']:+.3f}  (max {args.max_delta})")
    for r in rep["asr_loops"]:
        print(f"  asr loop {r['t']:7.2f}s (excluded; listen) | {r['sub']} | {r['asr']}")
    for r in rep["largest_regressions"]:
        print(f"  listen {r['t']:7.2f}s  +{r['delta']:.2f} | {r['sub']} | {r['asr']}")
    proc = rep.get("processing")
    proc_ok = not proc or proc["pass"] or bool(proc["accepted_by_author"])
    if proc:
        print(f"processing: floor {proc['floor_cer']:.3f}  unprocessed source {proc['source_cer']:.3f}  "
              f"delta {proc['delta']:+.3f}  (max {proc['max_delta']})")
        for r in proc["largest_regressions"][:6]:
            print(f"  processing {r['t']:7.2f}s  +{r['delta']:.2f} | {r['sub']} | {r['asr']} (source: {r['base_asr']})")
        if not proc["pass"]:
            print("PROCESSING REGRESSION: play the author an A/B of these cues (processed vs unprocessed) "
                  + (f"- accepted by the author: {proc['accepted_by_author']}" if proc["accepted_by_author"]
                     else "and let them decide; rerun with --processing-accepted to record their choice"))
    ok = rep["pass"] and proc_ok
    print(f"RESULT {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
