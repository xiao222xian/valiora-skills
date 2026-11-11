"""ASR scan of music candidates: instrumental beds must not contain sung or spoken words.

  WHISPER_MODEL=mlx-community/whisper-large-v3-turbo uv run --quiet --python 3.12 --with mlx-whisper \\
    python audio/vocal_scan.py [--out audio/vocal-scan.json] <audio ...>

Whisper hallucinates on instrumental music: it nearly always returns text, and no_speech_prob is no help
(0.0 on pure music, 2026-10-12). Judge by the text and its log-probability instead. Hallucination looks like the
same line repeated across windows or within one line, broadcast stock phrases in any language ("Thank you.",
"music", "For more information, visit ...", "Продолжение следует...", a subtitle credit), a line at the very end
of the clip, or sentences that do not follow from each other at avg_logprob well below -1. Real vocals read as
lyrics or speech that continue each other at avg_logprob around -0.6 or higher. The `listen` list per file keeps
the segments that are not obviously hallucinated: listen to those (and, when you can, to every pick) before
calling a take clean.
"""
import json
import os
import sys
from collections import Counter

import mlx_whisper

MODEL = os.environ.get("WHISPER_MODEL", "mlx-community/whisper-large-v3-mlx")
STOCK = {"thank you", "you", "music"}  # whole lines
STOCK_IN = ("for more information", "subtitle", "subscribe", "thanks for watching", "thank you for watching", "to be continued",
            "right back", "субтитр", "продолжение следует", "заставка", "字幕", "谢谢观看", "订阅")


def hallucinated(text, seen):
    t = text.lower().strip(" .!")
    words = t.split()
    looped = len(words) >= 8 and len(set(words)) < len(words) / 2
    return seen[text.lower()] > 1 or t in STOCK or any(k in t for k in STOCK_IN) or looped


args = sys.argv[1:]
out_path = "audio/vocal-scan.json"
if args[:1] == ["--out"]:
    out_path, args = args[1], args[2:]
out = {}
for p in args:
    r = mlx_whisper.transcribe(p, path_or_hf_repo=MODEL, condition_on_previous_text=False, word_timestamps=False)
    segs = [{"start": round(s["start"], 1), "end": round(s["end"], 1), "text": s["text"].strip(),
             "no_speech_prob": round(s.get("no_speech_prob", 0), 3), "avg_logprob": round(s.get("avg_logprob", 0), 2)}
            for s in r["segments"] if s["text"].strip()]
    seen = Counter(s["text"].lower() for s in segs)
    listen = [s for s in segs if s["avg_logprob"] > -1.0 and not hallucinated(s["text"], seen)]
    out[p] = {"language": r.get("language"), "segments": segs, "listen": [[s["start"], s["end"], s["text"]] for s in listen]}
    print(p, r.get("language"), len(segs), "segments;", f"listen at {[(s['start'], s['end']) for s in listen]}" if listen else "all look hallucinated")
    for s in segs[:20]:
        print("  ", s)
os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)
print(out_path)
