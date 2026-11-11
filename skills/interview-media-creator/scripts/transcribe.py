#!/usr/bin/env python3
"""Transcribe an interview recording with Whisper (mlx-whisper) and keep word timestamps.

usage: transcribe.py SOURCE.wav --out audio/asr-large-v3.json [--model large-v3|turbo|REPO|DIR]
                     [--nouns "被访者名,English name,地点"] [--words audio/words.json] [--print]

- Use a 16 kHz mono WAV extracted from the source (ffmpeg -ac 1 -ar 16000).
- The prompt carries only a style sentence and proper nouns. Never put expected content in it:
  silent windows then return the prompt itself as "speech".
- Output is converted to Simplified Chinese (opencc t2s) because long files drift back to Traditional.
- Run a second model (for example whisper-large-v3-turbo) on the same file to cross-check uncertain
  proper nouns; disagreements go to the author as a confirmation list, not into captions as guesses.
- Word timestamps from one long pass drift later in the file (observed up to ~0.6 s). They are good for
  planning; every cut point is verified with probe_cuts.py before it is fixed in the EDL.
- --model takes the aliases large-v3 (default) and turbo, a Hugging Face repo or a local model directory.
  The first run downloads the model from Hugging Face (about 3.1 GB / 1.6 GB); once both are cached,
  HF_HUB_OFFLINE=1 skips the online check. Rebuilding a cleared cache without the Python downloader:
  SKILL.md Step 0.
"""
import argparse
import json
import os

MODEL_ALIASES = {"large-v3": "mlx-community/whisper-large-v3-mlx", "turbo": "mlx-community/whisper-large-v3-turbo"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("source")
    ap.add_argument("--out", required=True, help="full Whisper result JSON")
    ap.add_argument("--model", default="large-v3", help="large-v3, turbo, a Hugging Face repo or a local model directory")
    ap.add_argument("--nouns", default="", help="comma-separated proper nouns for the prompt")
    ap.add_argument("--language", default="zh")
    ap.add_argument("--words", help="also write a flat word list [{w,s,e,p}]")
    ap.add_argument("--print", action="store_true", help="print segments with timestamps")
    a = ap.parse_args()

    import mlx_whisper
    try:
        import opencc
        conv = opencc.OpenCC("t2s").convert
    except ImportError:
        conv = lambda s: s  # noqa: E731

    prompt = "以下是一段普通话访谈对话，使用简体中文。"
    if a.nouns:
        prompt += "专有名词：" + "，".join(n for n in a.nouns.split(",") if n) + "。"
    model = MODEL_ALIASES.get(a.model, os.path.expanduser(a.model))
    r = mlx_whisper.transcribe(a.source, path_or_hf_repo=model, language=a.language, word_timestamps=True,
                               temperature=0.0, condition_on_previous_text=False, initial_prompt=prompt)
    with open(a.out, "w") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    if a.words:
        words = [{"w": conv(w["word"]).strip(), "s": round(w["start"], 3), "e": round(w["end"], 3),
                  "p": round(w.get("probability", 0), 2)} for s in r["segments"] for w in s.get("words", [])]
        with open(a.words, "w") as f:
            json.dump(words, f, ensure_ascii=False)
    if a.print:
        for s in r["segments"]:
            print(f"[{s['start']:7.2f}-{s['end']:7.2f}] {conv(s['text'].strip())}")
    print(f"segments {len(r['segments'])} -> {a.out}")


if __name__ == "__main__":
    main()
