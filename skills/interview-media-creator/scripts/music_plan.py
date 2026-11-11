#!/usr/bin/env python3
"""Turn a music spec into the cue sheet, film map and processed voice list that lov-media-creator's
narrative scoring scripts (validate_cues.py, smr_check.py, score_mix.py, intelligibility.py) consume.

usage: music_plan.py EDL.json MUSIC.json [--remotion-data remotion/public/data] [--skip-voice-chain]
                     [--media-creator DIR]

MUSIC.json:
  {"duck_db": -10, "level_ref": "track",
   "voice_chain": "highpass=f=80:p=2,...",            # optional; default is a light lav-mic chain
   "cues": [{"id": "A-main", "track": "A", "track_in": 17.0, "from": {"t": 0}, "to": {"chapter": "ch5", "plus": 1.5},
             "level_db": 2, "fade_in": 0.25, "fade_out": 2.0, "dips": [["3i", "3i", -4]], "rationale": "..."},
            {"id": "C-end", "track": "C", "align_end": 120.1, "from": {"chapter": "ch5"}, "to": {"film_end": true},
             "level_db": 2, "fade_in": 2.5, "fade_out": 0.4, "dips": [["6c", "6d", -4]], "rationale": "..."}],
   "intents": [{"from": {"t": 0}, "to": {"title_end": true}, "intent": "blend", "reason": "..."}],
   "throughline": ["...", "..."]}

Time references: {"t": s}, {"chapter": id, "plus": s}, {"segment_start": id}, {"segment_end": id},
{"title_end": true}, {"outro_start": true}, {"film_end": true}.
- "align_end" puts the track's audible end (the second after which it is digital silence, measure it) on
  the cue end, so the music resolves on the logo card instead of stopping early.
- "dips" lower the cue under the listed segment span (first id .. last id, inclusive) with 0.5 s ramps;
  use them when smr_check.py fails a line whose pauses sit under a loud passage.
Writes music/cues-<v>.json, music/film-<v>.json and audio/voice-proc-<v>.json, then prints the gate commands
with the absolute lov-media-creator path (--media-creator, else $MEDIA_CREATOR_DIR, else
~/.agents/skills/lov-media-creator), each prefixed by `cd <EDL dir> &&` so they run from anywhere.
"""
import argparse
import json
import os
import pathlib
import shlex
import subprocess

DEFAULT_CHAIN = ("highpass=f=80:p=2,equalizer=f=250:t=q:w=1:g=-1.5,equalizer=f=3500:t=q:w=1:g=2,"
                 "deesser=i=0.25,acompressor=threshold=-26dB:ratio=3:attack=6:release=120:makeup=2")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("music")
    ap.add_argument("--remotion-data", default="remotion/public/data")
    ap.add_argument("--skip-voice-chain", action="store_true", help="reuse audio/lines-proc if already rendered")
    ap.add_argument("--media-creator", metavar="DIR",
                    help="lov-media-creator skill directory (default $MEDIA_CREATOR_DIR, else ~/.agents/skills/lov-media-creator)")
    a = ap.parse_args()
    mc = pathlib.Path(a.media_creator or os.environ.get("MEDIA_CREATOR_DIR")
                      or pathlib.Path.home() / ".agents" / "skills" / "lov-media-creator").expanduser().absolute()
    edl_path = pathlib.Path(a.edl).resolve()
    root = edl_path.parent
    edl = json.loads(edl_path.read_text())
    ver = edl["version"]
    spec = json.loads(pathlib.Path(a.music).read_text())
    tl = json.loads(((root / a.remotion_data) / "timeline.json").read_text())
    voice = json.loads((root / "audio" / f"voice-{ver}.json").read_text())
    fps = tl["fps"]
    dur = tl["frames"] / fps
    items = tl["items"]
    sp = {i["id"]: i for i in items if i["kind"] == "speech"}
    ch = {i["chapter"]: i for i in items if i["kind"] == "chapter"}
    title = next((i for i in items if i["kind"] == "title"), None)
    outro = next(i for i in items if i["kind"] == "outro")

    def t(ref):
        if "t" in ref:
            return float(ref["t"])
        if "chapter" in ref:
            return ch[ref["chapter"]]["start"] / fps + ref.get("plus", 0.0)
        if "segment_start" in ref:
            return sp[ref["segment_start"]]["start"] / fps + ref.get("plus", 0.0)
        if "segment_end" in ref:
            s = sp[ref["segment_end"]]
            return (s["start"] + s["frames"]) / fps + ref.get("plus", 0.0)
        if ref.get("title_end"):
            return (title["start"] + title["frames"]) / fps
        if ref.get("outro_start"):
            return outro["start"] / fps
        if ref.get("film_end"):
            return dur
        raise SystemExit(f"unknown time reference {ref}")

    def dips(cue_at, spans, ramp=0.5):
        env = []
        for first, last, db in sorted(spans, key=lambda x: sp[x[0]]["start"]):
            t0 = sp[first]["start"] / fps - cue_at
            t1 = (sp[last]["start"] + sp[last]["frames"]) / fps - cue_at
            env += [[round(max(0.0, t0 - ramp), 2), 0], [round(t0, 2), db], [round(t1, 2), db], [round(t1 + ramp, 2), 0]]
        return env

    # 1. voice chain on every line (light EQ + 3:1 compression; loudness matching stays in score_mix.py)
    chain = spec.get("voice_chain", DEFAULT_CHAIN)
    proc = root / "audio" / "lines-proc" / ver
    proc.mkdir(parents=True, exist_ok=True)
    for ln in voice["lines"]:
        src = root / "audio" / ln["file"]
        dst = proc / src.name
        if not (a.skip_voice_chain and dst.exists()):
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-af", chain, "-ar", "48000", "-ac", "1",
                            "-c:a", "pcm_s16le", str(dst)], check=True)
        ln["file"] = str(dst.relative_to(root / "audio"))
    (root / "audio" / f"voice-proc-{ver}.json").write_text(json.dumps(voice, ensure_ascii=False, indent=1))

    # 2. cue sheet
    cues = []
    for c in spec["cues"]:
        at, end = t(c["from"]), t(c["to"])
        d = round(end - at, 3)
        track_in = c["track_in"] if "track_in" in c else round(c["align_end"] - d, 3)
        if track_in < 0:
            raise SystemExit(f"cue {c['id']}: track too short for {d}s ending at {c.get('align_end')}")
        cue = {"id": c["id"], "track": c["track"], "track_in": track_in, "at": round(at, 3), "dur": d,
               "level_db": c.get("level_db", 0), "fade_in": c.get("fade_in", 1.0), "fade_out": c.get("fade_out", 1.0),
               "rationale": c["rationale"]}
        if c.get("dips"):
            cue["env"] = dips(at, c["dips"])
        cues.append(cue)
    intents = [{"t0": round(t(i["from"]), 3), "t1": round(t(i["to"]), 3), "intent": i["intent"], "reason": i["reason"]}
               for i in spec.get("intents", [])]
    sheet = {"level_ref": spec.get("level_ref", "track"), "cues": cues, "silences": spec.get("silences", []), "mix_intents": intents}
    if "duck_db" in spec:
        sheet["duck_db"] = spec["duck_db"]
    (root / "music").mkdir(exist_ok=True)
    (root / "music" / f"cues-{ver}.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1))

    # 3. film map for validate_cues.py / cut_metrics.py
    voice_spans = [{"t0": ln["at"], "t1": round(ln["at"] + ln["frames"] / fps, 3)} for ln in voice["lines"]]
    text_spans = []
    if title:
        text_spans.append({"t0": title["start"] / fps, "t1": (title["start"] + title["frames"]) / fps,
                           "text": "".join(tl.get("title", {}).get("lines", ["片名"]))})
    for c in ch.values():
        text_spans.append({"t0": c["start"] / fps, "t1": (c["start"] + c["frames"]) / fps, "text": f"第{c['index']}章 {c['title']}"})
    bounds = [0.0] + [c["start"] / fps for c in ch.values()] + [outro["start"] / fps, dur]
    shots = []
    for it in items:
        if it["kind"] == "speech":
            shots += [{"t0": round(p["start"] / fps, 3), "t1": round((p["start"] + p["frames"]) / fps, 3), "source": "interview"}
                      for p in it["pieces"]]
        else:
            shots.append({"t0": round(it["start"] / fps, 3), "t1": round((it["start"] + it["frames"]) / fps, 3),
                          "source": "card" if it["kind"] != "title" else "interview", "black": it["kind"] in ("chapter", "outro")})
    film = {"duration": round(dur, 3), "dialogue_language": "zh", "voice_spans": voice_spans, "text_spans": text_spans,
            "chapters": [{"t": c["start"] / fps} for c in ch.values()],
            "scenes": [{"t0": round(x, 3), "t1": round(y, 3)} for x, y in zip(bounds, bounds[1:])],
            "shots": shots, "throughline": spec.get("throughline", [])}
    (root / "music" / f"film-{ver}.json").write_text(json.dumps(film, ensure_ascii=False, indent=1))

    for c in cues:
        print(f"{c['id']}: track {c['track']} in {c['track_in']}s, at {c['at']}s for {c['dur']}s, env points {len(c.get('env', []))}")
    if not (mc / "scripts" / "score_mix.py").exists():
        print(f"WARN {mc}/scripts/score_mix.py not found: pass --media-creator or set MEDIA_CREATOR_DIR")
    cd, py = f"cd {shlex.quote(str(root))} &&", f"python3 {shlex.quote(str(mc / 'scripts'))}"
    print(f"""
Next (lov-media-creator at {mc}):
  {cd} {py}/validate_cues.py --preset narrative --cues music/cues-{ver}.json --tracks music/tracks.json --film music/film-{ver}.json --json music/cue-check-{ver}.json
  {cd} {py}/smr_check.py --voice audio/voice-proc-{ver}.json --cues music/cues-{ver}.json --tracks music/tracks.json --output music/smr-{ver}.json
  {cd} {py}/score_mix.py --voice audio/voice-proc-{ver}.json --cues music/cues-{ver}.json --tracks music/tracks.json --out-dir audio/mix-{ver} --stems
  {cd} {py}/intelligibility.py --mix audio/mix-{ver}/final-mix.wav --srt render/subs-{ver}.srt --floor audio/mix-{ver}/stem-voice.wav --floor-output music/cer-floor-{ver}.json --output music/cer-{ver}.json""")


if __name__ == "__main__":
    main()
