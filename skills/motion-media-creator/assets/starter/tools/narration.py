#!/usr/bin/env python3
"""Voice-over: one audio file per line, the user's own recording first, TTS otherwise; then the subtitle table.

  python3 tools/narration.py --dry-run  # what TTS would bill: lines and characters to synthesize; no network, no key
  python3 tools/narration.py            # synthesize what is missing or changed, check timing, write src/narration.ts
  python3 tools/narration.py --check    # timing check only (no synthesis; needs a previous run's timing.json)

Input  audio/narration/lines.json   [{id, chapter, at, until, zh, tts, en}]  (at/until: frames local to the chapter)
         zh   the Chinese subtitle; tts  the spoken form (digits and units spelled out; empty = zh);
         en   the English subtitle (shown only when src/timeline.ts SUBTITLE_LANGS is 'zh+en'; may be empty)
Voice  audio/narration/voice/<id>.*   a real recording of that line wins over TTS (any format ffmpeg reads)
TTS    audio/narration/tts/<id>.wav   Doubao Seed-TTS 2.0 (env VOICENGINE_API_KEY), cached by text+speaker+rate;
                                      every request adds a line to the cost ledger (tools/ledger.py: characters
                                      sent, no price: the API returns none)
Output audio/narration/clips/<id>.wav  48 kHz mono, leading/trailing silence trimmed (what tools/voice_mix.py places)
       audio/narration/timing.json     per line: absolute start, spoken length, slack against `until`
       src/narration.ts                subtitle table read by src/components/Subtitles.tsx
Exits non-zero when a line overruns its `until`, crowds the next line, leaves its chapter, or sits on the
opening title card or the end card (first and last chapter: no voice there).
Planning rate: speaker zh_male_ruyayichen_uranus_bigtts at speech_rate 10 says about 4.0 Chinese characters
a second including pauses (measured 2026-10-12), so a 10-14 s chapter takes about 25-45 characters.
Cost: the API returns no price and none has been measured here. Before a run, report the --dry-run character
count (what the ledger records as qty) and give the unit price as the Volcengine console states it, not a guess.
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ledger import record  # tools/ledger.py: one line per paid call

ROOT = Path(__file__).resolve().parent.parent
NAR = ROOT / "audio" / "narration"
URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
SPEAKER = os.environ.get("TTS_SPEAKER", "zh_male_ruyayichen_uranus_bigtts")
RATE = int(os.environ.get("TTS_RATE", "10"))
UID = os.environ.get("TTS_UID", "motion-media-creator")
HOLD = 0.35  # seconds a subtitle stays after the voice ends
MIN_SUB = 1.2  # shortest time a subtitle is on screen
GAP = 0.25  # least silence between two lines, seconds


def timeline():
    """FPS and the chapters (id, start, duration) in film order, read from src/timeline.ts (Node 24)."""
    js = ("import('./src/timeline.ts').then(m=>console.log(JSON.stringify({fps:m.FPS,"
          "chapters:m.CHAPTERS.map((c,i)=>({id:c.id,start:c.start,dur:m.chapterDur(i)}))})))")
    out = subprocess.run(["node", "--disable-warning=MODULE_TYPELESS_PACKAGE_JSON", "-e", js],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    t = json.loads(out)
    return t["fps"], t["chapters"]


def spoken(ln) -> str:
    # an empty `tts` means "say the subtitle as written": `or`, not a None check ('' is not None)
    return ln.get("tts") or ln["zh"]


def tts_key(ln) -> str:
    return hashlib.sha1(f"{SPEAKER}|{RATE}|{spoken(ln)}".encode()).hexdigest()[:12]


def recording(ln):
    found = sorted((NAR / "voice").glob(f"{ln['id']}.*"))
    return found[0] if found else None


def tts_cached(ln) -> bool:
    wav, stamp = NAR / "tts" / f"{ln['id']}.wav", NAR / "tts" / f"{ln['id']}.key"
    return wav.exists() and stamp.exists() and stamp.read_text() == tts_key(ln)


def synth(text: str, rid: str) -> bytes:
    """One request; the response is JSON lines, each carrying a base64 chunk of the audio."""
    body = json.dumps({"user": {"uid": UID}, "req_params": {"text": text, "speaker": SPEAKER,
                       "audio_params": {"format": "mp3", "sample_rate": 24000, "speech_rate": RATE}}}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "X-Api-Key": os.environ["VOICENGINE_API_KEY"], "X-Api-Resource-Id": "seed-tts-2.0",
        "X-Api-Request-Id": rid, "Content-Type": "application/json"})
    raw = urllib.request.urlopen(req, timeout=120).read().decode()
    audio = b""
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("code") not in (0, 20000000, None):
            raise RuntimeError(line[:200])
        if d.get("data"):
            audio += base64.b64decode(d["data"])
    if not audio:
        raise RuntimeError("empty audio: " + raw[:200])
    return audio


def synth_logged(ln, rid: str) -> bytes:
    """synth() plus one cost-ledger line for the request, failed ones included."""
    ok = False
    try:
        audio = synth(spoken(ln), rid)
        ok = True
        return audio
    finally:
        record(kind="tts", provider="volcengine", model="seed-tts-2.0", qty=len(spoken(ln)), unit="chars",
               cost_usd=None, ok=ok, ref=f"audio/narration/tts/{ln['id']}.wav")


def tts_line(ln) -> Path:
    wav, stamp = NAR / "tts" / f"{ln['id']}.wav", NAR / "tts" / f"{ln['id']}.key"
    if tts_cached(ln):
        return wav
    for attempt in range(4):
        try:
            mp3 = NAR / "tts" / f"{ln['id']}.mp3"
            mp3.write_bytes(synth_logged(ln, f"film-{ln['id']}-{attempt}-{int(time.time() * 1000)}"))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-ac", "1", "-ar", "48000", str(wav)], check=True)
            stamp.write_text(tts_key(ln))
            return wav
        except Exception as e:  # transient network errors and empty streams: retry
            print(f"retry {ln['id']}: {e}", flush=True)
            time.sleep(2 + attempt * 2)
    raise SystemExit(f"TTS failed for {ln['id']}")


def clip(ln):
    rec = recording(ln)
    src, kind = (rec, "voice") if rec else (tts_line(ln), "tts")
    out = NAR / "clips" / f"{ln['id']}.wav"
    # trim silence at both ends (-45 dB), keep 40-60 ms of air
    af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04,"
          "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "48000", "-af", af, str(out)], check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True, check=True).stdout.strip()
    # a silent or broken source trims down to nothing (ffprobe then reports N/A)
    dur = float(probe) if probe not in ("", "N/A") else 0.0
    if dur < 0.3:
        raise SystemExit(f"{ln['id']}: the {kind} audio ({src.name}) is silent or empty after trimming; check the source")
    return ln["id"], dur, kind


def dry_run(lines):
    """The characters a real run would send: lines without a recording and without a matching cached take."""
    rec = [ln for ln in lines if recording(ln)]
    cached = [ln for ln in lines if not recording(ln) and tts_cached(ln)]
    need = [ln for ln in lines if not recording(ln) and not tts_cached(ln)]
    chars = sum(len(spoken(ln)) for ln in need)
    print(f"{len(lines)} lines: {len(rec)} recorded, {len(cached)} cached, {len(need)} to synthesize "
          f"= {chars} characters (speaker {SPEAKER}, speech_rate {RATE})")
    for ln in need:
        print(f"  {ln['id']:>6} {len(spoken(ln)):>4}  {spoken(ln)}")
    print(f"if the voice or rate changes (cache no longer matches): {sum(len(spoken(ln)) for ln in lines if not recording(ln))} "
          "characters; price per character: see the Volcengine console (the API returns none)")


def main():
    ap = argparse.ArgumentParser(description="Voice-over clips (recordings first, TTS otherwise) and the subtitle table.")
    ap.add_argument("--check", action="store_true", help="timing check only, from the previous run's timing.json")
    ap.add_argument("--dry-run", action="store_true", help="count the lines and characters TTS would bill; no network, no key")
    args = ap.parse_args()
    if not (NAR / "lines.json").exists():
        sys.exit("no script at audio/narration/lines.json: write it first ([{id, chapter, at, until, zh, tts, en}], "
                 "see the docstring); a film without voice-over keeps src/narration.ts empty")
    lines = json.loads((NAR / "lines.json").read_text(encoding="utf-8"))
    if args.dry_run:
        dry_run(lines)
        return
    fps, chs = timeline()
    ch = {c["id"]: c for c in chs}
    cards = {chs[0]["id"], chs[-1]["id"]}  # opening title card, end card
    unknown = sorted({ln["chapter"] for ln in lines} - set(ch))
    if unknown:
        sys.exit(f"lines.json names chapters that are not in src/timeline.ts: {', '.join(unknown)}")
    lines.sort(key=lambda ln: ch[ln["chapter"]]["start"] + ln["at"])
    for d in ("tts", "clips", "voice"):
        (NAR / d).mkdir(parents=True, exist_ok=True)
    if args.check:
        tim = json.loads((NAR / "timing.json").read_text(encoding="utf-8"))
        durs = {t["id"]: t["dur"] for t in tim}
        kinds = {t["id"]: t["kind"] for t in tim}
        missing = [ln["id"] for ln in lines if ln["id"] not in durs]
        if missing:
            sys.exit(f"--check: no measured clip for {', '.join(missing)}; run without --check first")
    else:
        need = [ln["id"] for ln in lines if not recording(ln) and not tts_cached(ln)]
        if need and not os.environ.get("VOICENGINE_API_KEY"):
            sys.exit(f"{len(need)} lines need TTS ({', '.join(need[:6])}...): set VOICENGINE_API_KEY, "
                     "or put the recordings at audio/narration/voice/<id>.*")
        with ThreadPoolExecutor(6) as ex:
            res = list(ex.map(clip, lines))
        durs = {i: d for i, d, _ in res}
        kinds = {i: k for i, _, k in res}
    rows, problems = [], []
    for k, ln in enumerate(lines):
        c = ch[ln["chapter"]]
        start = c["start"] + ln["at"]
        end_f = start + durs[ln["id"]] * fps
        slack = (c["start"] + ln["until"]) - end_f
        nxt = lines[k + 1] if k + 1 < len(lines) else None
        nxt_start = ch[nxt["chapter"]]["start"] + nxt["at"] if nxt else None
        if ln["chapter"] in cards:
            problems.append(f"{ln['id']}: voice over the title card or the end card ({ln['chapter']})")
        if slack < 0:
            problems.append(f"{ln['id']}: runs {-slack / fps:.2f} s past its until")
        if nxt_start is not None and end_f + GAP * fps > nxt_start:
            problems.append(f"{ln['id']}: ends {((end_f - nxt_start) / fps):+.2f} s against the next line")
        if end_f > c["start"] + c["dur"] + 0.5 * fps:
            problems.append(f"{ln['id']}: leaves chapter {ln['chapter']}")
        sub_end = max(end_f + HOLD * fps, start + MIN_SUB * fps)
        if nxt_start is not None:
            sub_end = min(sub_end, nxt_start - 2)
        rows.append({"id": ln["id"], "chapter": ln["chapter"], "from": int(round(start)), "to": int(round(sub_end)),
                     "voiceFrom": int(round(start)), "dur": round(durs[ln["id"]], 3), "slack": round(slack / fps, 2),
                     "kind": kinds[ln["id"]], "zh": ln["zh"], "en": ln.get("en") or ""})
    (NAR / "timing.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    subs = [{"from": r["from"], "to": r["to"], "zh": r["zh"], "en": r["en"]} for r in rows]
    (ROOT / "src" / "narration.ts").write_text(
        "// Generated by tools/narration.py from audio/narration/lines.json and the measured voice clips.\n"
        "// Absolute frames. The voice itself is premixed into public/audio/bgm-master.wav by tools/voice_mix.py.\n"
        "// Empty = a film without voice-over: no subtitles, and the scenes keep their lower-left captions.\n"
        "export type SubtitleLine = {from: number; to: number; zh: string; en: string};\n\n"
        f"export const SUBTITLES: SubtitleLine[] = {json.dumps(subs, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    total = sum(durs.values())
    tight = f"; tightest slack {min(r['slack'] for r in rows):.2f} s" if rows else ""
    print(f"{len(rows)} lines, {total:.1f} s of voice ({sum(1 for r in rows if r['kind'] == 'voice')} recorded, "
          f"{sum(1 for r in rows if r['kind'] == 'tts')} TTS){tight}")
    print("next: python3 tools/voice_mix.py (master), python3 tools/fonts.py subset (subtitle glyphs)")
    for p in problems:
        print("PROBLEM", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
