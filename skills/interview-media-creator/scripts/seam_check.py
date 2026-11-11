#!/usr/bin/env python3
"""Re-transcribe every cut dialogue line and compare it with the EDL text, character by character.

usage: seam_check.py EDL.json [--out qc/seam-v0.1.json] [--threshold 0.12] [--models large-v3,turbo]

Lines are the per-segment WAVs written by build_timeline.py --audio (already time-stretched). Two Whisper
models transcribe each line; lines whose best match is worse than the threshold are printed as CHECK with
the inserted/deleted characters. Each model loads once and transcribes every line (progress on stderr), so
the table prints after both models finish: mlx-whisper keeps a single model in memory, and switching models
per line reloads the weights (about 3 GB for large-v3) every time.

Reading the result:
- Homophone swaps (骰子→投资, 品质→频率, 创业→穿越) and one model dropping half a line are ASR noise.
- Both models hearing an extra word at the start/end ("然后", "明白明白", "OK 就是") means a filler or
  the other speaker leaked across the cut: move the cut with probe_cuts.py.
- Both models missing the first or last word means the cut clipped it: move the cut outward.
- Captions must follow what is actually said; when both models agree on words the EDL text lacks
  ("调度这个声音啊"), fix the EDL text rather than the audio.
- --models: the aliases large-v3 and turbo (default both), Hugging Face repos or local model directories.
  The first run downloads both (about 3.1 GB + 1.6 GB); once they are cached, HF_HUB_OFFLINE=1 skips the
  online check. Rebuilding a cleared cache without the Python downloader: SKILL.md Step 0.
"""
import argparse
import difflib
import json
import os
import pathlib
import re
import sys

PUNCT = r"[，。？！、,.?!：:；;“”\"' @]"
MODEL_ALIASES = {"large-v3": "mlx-community/whisper-large-v3-mlx", "turbo": "mlx-community/whisper-large-v3-turbo"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--out")
    ap.add_argument("--threshold", type=float, default=0.12)
    ap.add_argument("--nouns", default="", help="comma-separated proper nouns for the prompt")
    ap.add_argument("--models", default="large-v3,turbo",
                    help="comma-separated: large-v3, turbo, Hugging Face repos or local model directories")
    a = ap.parse_args()
    models = [MODEL_ALIASES.get(m.strip(), os.path.expanduser(m.strip())) for m in a.models.split(",") if m.strip()]
    import mlx_whisper
    try:
        import opencc
        conv = opencc.OpenCC("t2s").convert
    except ImportError:
        conv = lambda s: s  # noqa: E731

    edl_path = pathlib.Path(a.edl).resolve()
    root, edl = edl_path.parent, json.loads(edl_path.read_text())
    prompt = "以下是普通话访谈，使用简体中文。" + ("专有名词：" + "，".join(a.nouns.split(",")) + "。" if a.nouns else "")
    norm = lambda s: re.sub(PUNCT, "", s).lower()  # noqa: E731
    segs = [s for s in edl["segments"] if s["part"] != "title"]
    heard = [[] for _ in segs]  # model by model: mlx-whisper caches only the last model it loaded
    for m in models:
        print(f"transcribing {len(segs)} lines with {m.rstrip('/').split('/')[-1]}", file=sys.stderr, flush=True)
        for h, seg in zip(heard, segs):
            f = root / "audio" / "lines" / edl["version"] / f"{seg['id']}.wav"
            h.append(conv(mlx_whisper.transcribe(str(f), path_or_hf_repo=m, language="zh", temperature=0.0,
                                                 condition_on_previous_text=False, initial_prompt=prompt)["text"]).strip())
    res, flagged = [], 0
    for seg, h in zip(segs, heard):
        exp = norm(seg["text"])
        rows = []
        for m, got in zip(models, h):
            sm = difflib.SequenceMatcher(None, exp, norm(got))
            ops = [(t, exp[i1:i2], norm(got)[j1:j2]) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
            rows.append({"model": m.rstrip("/").split("/")[-1], "dist": round(1 - sm.ratio(), 3), "ops": ops, "text": got})
        best = min(r["dist"] for r in rows)
        flag = best > a.threshold
        flagged += flag
        res.append({"id": seg["id"], "expected": seg["text"], "best_dist": best, "check": flag, "asr": rows})
        print(f"{'CHECK' if flag else 'ok':5s} {seg['id']:4s} {best:.2f} | {seg['text']}")
        if flag:
            for r in rows:
                print(f"        {r['model']}: {r['text']}  {r['ops'][:6]}")
    out = pathlib.Path(a.out) if a.out else root / "qc" / f"seam-{edl['version']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"lines {len(res)}, check {flagged} -> {out}")


if __name__ == "__main__":
    main()
