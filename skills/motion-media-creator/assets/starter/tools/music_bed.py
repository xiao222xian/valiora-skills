#!/usr/bin/env python3
"""Chapter-by-chapter music bed: one 120 BPM cue per chapter, a bar downbeat of it on the chapter's first frame.

  python3 tools/music_bed.py             # -> public/audio/bgm-music.wav (the music input of tools/voice_mix.py)
  python3 tools/music_bed.py --dry-run   # print the plan only (with the full-length track's shift)
  python3 tools/music_bed.py --full-shift 0   # keep the full-length track at its own time (see below)
  uv run --quiet --python 3.12 --with librosa python qc/beat_phase.py   # then check every chapter's beat phase

Inputs
  audio/chapters/<id>-<a|b>.mp3   takes from audio/gen_chapter_music.py (Lyria 3 Clip, about 30 s each)
  audio/chapters/analysis.json    per take: clarity, steadiness and first beat (for the pick), the fitted beat grid
                                  (period, fit residual, bar downbeats; for the placement), from audio/chapters/analyze.py
  audio/chapters/picks.json       optional: {"<id>": {"take": "a", "lufs": -18}}; "take": "full" keeps the full track.
                                  A chapter with takes but no pick gets the take with the clearest beat among the
                                  steady ones (about 120 BPM, ibi_cv <= 0.05, first beat within 1 s) at -18 LUFS; a take
                                  whose grid fit is loose (resid_ms > MAX_RESID_MS) is passed over for the other one.
  public/audio/bgm-full.wav       optional full-length track at film time (the opening was cut to its accents):
                                  chapters without takes (usually the opening and the outro) play it, so the
                                  opening keeps its hits and the outro its real ending. Its beat grid goes into
                                  analysis.json too (key bgm-full.wav): run audio/chapters/analyze.py on it.

Placement. Each cue is time-stretched (pitch kept) from its fitted tempo to exactly the film's beat (tempo factor =
period / beat), and the bar downbeat nearest LEAD s (about the third bar) that leaves at least PRE s of music before
it lands on the chapter's first frame. The downbeat comes from the fitted grid, not from the first detected beat:
librosa's first beats are unstable while the tracker settles (2026-10-12, 《如何打造一款特斯拉》 v0.5: first beat
+ 4 s put 6 of 13 cues 94-244 ms off the picture's beat grid, two by half a beat). The stretch uses ffmpeg's
rubberband filter when the build has it, else atempo (MUSIC_STRETCH=rubberband|atempo overrides): atempo moves
transients as it stretches (2026-10-12, 13 cues re-timed by +-2.5 %: beat phases spread 26 ms with atempo, 9 ms with
rubberband; on takes within 0.15 % of 120 BPM, 13 and 12 ms).

Joins are pre-laps, not splices. The incoming cue fades in (equal power, sine) over the PRE seconds before the
chapter's first frame, under the outgoing cue, which fades out (equal power, cosine) from 0.25 s before to 0.75 s
after it. Both sit on the same beat grid, so the overlap stays in time. Joins into and out of the full-length track
work the same way; consecutive chapters on it play as one stretch. Each cue is levelled to its chapter's loudness
target on the chapter body only (not its lead-in or tail).

Chapter starts must sit on one 120 BPM grid (every BEAT frames) so the hits the picture was cut to stay on
beats: the script warns when they do not. A take too short for a full lead-in uses the latest downbeat that still
fits (a shorter lead-in, warned); a take shorter than its chapter from its first downbeat is an error. A cue on the
last chapter fades out over the film's last second.

The full-length track is shifted onto the cues' beat grid. A cue's fitted grid is placed on its chapter's first
frame; the full track used to play at its own time, so its beats sat wherever its grid fell. Now each stretch of it
that joins a cue moves by minus its grid offset at the join(s): the offset of its fitted beat (analysis.json
`bgm-full.wav`, the same fit as the cues') nearest the join from the beat grid of the cue on the other side, taken
modulo one beat and folded to -beat/2..+beat/2 (a stretch with a join at each end takes the circular mean of the
two). So the shift is the smallest one that lines the beats up, never more than half a beat either way (+ = later,
- = earlier); the other choice, a delay of nearly a beat, would put the opening's accents almost a beat late. The
opening's accents move with it: they were cut on the same frame grid as the chapter starts, so they land on the
beats the cues sit on. --dry-run prints the shift and each join's offset before and after; --full-shift MS sets it
by hand (0 = the track at its own time). Warned: a shift over a quarter beat (the chapter starts are then not on
this track's beats: snap them with audio/snap.py) and a join still more than MAX_JOIN_MS off after the shift (the
track's tempo drifts from the film's between its joins). A delayed track on the last chapter loses its last
milliseconds past the film's end and fades out over the last second.
(2026-10-12, 《如何打造一款特斯拉》 v0.5: unshifted, the track's grid sat +90 ms off the cues' at the join into
chapter 01 and +87 ms at the join out of chapter 13; qc/beat_phase.py read the opening +82 and the outro +81 ms
against -5 to -15 ms for the 13 cues, so both pre-laps overlapped beats about 90 ms apart. Rebuilt from the same
takes with the opening shifted -90.4 ms and the outro -86.7 ms, it read -7.8 and -6.4 ms, the two joins -3.3 and
+3.1 ms apart; nothing between the two pre-laps changed.)
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "audio" / "chapters"
FULL = ROOT / "public" / "audio" / "bgm-full.wav"
DST = ROOT / "public" / "audio" / "bgm-music.wav"
SR = 48000
# Joins (2026-10-12, 《如何打造一款特斯拉》 v0.4: hard 0.35 s splices between different cues sounded abrupt)
PRE = 1.0  # s the incoming cue fades in (equal power) before the chapter's first frame, under the outgoing one
OUT_FROM = -0.25  # s, relative to the chapter's first frame, where the outgoing cue starts fading
OUT_LEN = 1.0  # s of equal-power fade-out of the outgoing cue
TAIL = OUT_FROM + OUT_LEN  # s the outgoing cue runs past the next chapter's first frame
LEAD = 4.0  # s: about two bars at 120 BPM; the downbeat on the chapter's first frame is the bar nearest this
END_FADE = 1.0  # s: a cue on the last chapter fades out over the film's last second (a clip has no real ending there)
DEFAULT_LUFS = -18.0
# Grid (2026-10-12, 《如何打造一款特斯拉》 v0.5): good takes fit their beat grid to about 3 ms (at most 7 ms on 24 of
# 26 takes); the two that wandered read 31 and 45 ms and would drift off the picture's beats within a chapter
MAX_RESID_MS = 15.0
MAX_STRETCH = 0.03  # warn when a cue's tempo changes by more than this (3 % = 116.5-123.7 BPM)
ATEMPO_OK = 0.01  # with atempo, beyond this the stretch itself moves the beats by several ms: run qc/beat_phase.py
# Full-length track: after its shift each join should be this close to the cue's grid (the Tesla track drifted
# 3.7 ms between its two joins, 152 s apart: fitted period 0.499988 s)
MAX_JOIN_MS = 10.0


def stretcher():
    """rubberband keeps transients in place; atempo is in every ffmpeg build."""
    want = os.environ.get("MUSIC_STRETCH")
    if want:
        if want not in ("rubberband", "atempo"):
            sys.exit(f"MUSIC_STRETCH={want}: use rubberband or atempo")
        return want
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return "rubberband" if re.search(r"^\s*\S+\s+rubberband\s", out, re.M) else "atempo"


STRETCH = stretcher()


def timeline():
    js = ("import('./src/timeline.ts').then(m=>console.log(JSON.stringify({fps:m.FPS,beat:m.BEAT,total:m.TOTAL_FRAMES,"
          "ch:m.CHAPTERS.map((c,i)=>({id:c.id,start:c.start,dur:m.chapterDur(i)}))})))")
    out = subprocess.run(["node", "--disable-warning=MODULE_TYPELESS_PACKAGE_JSON", "-e", js],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def decode(path, start=0.0, dur=None, tempo=1.0):
    """start/dur in output seconds; tempo != 1 time-stretches (pitch kept) before cutting."""
    af = []
    if abs(tempo - 1) > 1e-5:
        af.append(f"rubberband=tempo={tempo:.6f}:transients=crisp" if STRETCH == "rubberband" else f"atempo={tempo:.6f}")
    af.append(f"atrim=start={start:.4f}" + (f":duration={dur:.4f}" if dur else "") + ",asetpts=PTS-STARTPTS")
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-af", ",".join(af), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()


def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def lufs(x):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=x.astype("<f4").tobytes(), capture_output=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr.decode())[-1])


def loose(a):
    """A take whose beats wander off its fitted grid (or that has no grid at all)."""
    return a.get("resid_ms") is None or a["resid_ms"] > MAX_RESID_MS


def wrap(x, period):
    """x folded into -period/2 .. +period/2."""
    return (x + period / 2) % period - period / 2


def full_shift(grid, joins, beat_s):
    """The shift (s, + = later) that puts the full track's fitted beats on the cues' grid at its joins, and each
    join's offset before it. joins: (film time of the join, a beat of the cue on the other side, that chapter)."""
    errs = []
    for t, ref, cid in joins:
        k = round((t - grid["phase"]) / grid["period"])  # the track's grid beat nearest the join, at its own time
        errs.append((cid, wrap(grid["phase"] + k * grid["period"] - ref, beat_s)))
    ang = np.array([2 * np.pi * e / beat_s for _, e in errs])
    mean = float(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())) * beat_s / (2 * np.pi)
    return -mean, errs


def auto_pick(cid, ana):
    """The clearest beat among the steady takes: near 120 BPM, even beats, no intro before the first beat
    (else the clearest of all). A take with a loose grid fit is passed over while another one fits.
    On 《如何打造一款特斯拉》 this gives the 13 takes of its v0.5 (without the grid rule, cell got its loose a take)."""
    takes = [(f.stem.rsplit("-", 1)[1], ana[f.name]) for f in sorted(CH.glob(f"{cid}-*.mp3")) if f.name in ana]
    if not takes:
        sys.exit(f"{cid}: takes on disk but not in analysis.json: run audio/chapters/analyze.py")
    tight = [t for t in takes if not loose(t[1])]
    for t, a in takes:
        if loose(a) and tight:
            print(f"note: {cid}-{t}: beat grid fit {a.get('resid_ms')} ms (> {MAX_RESID_MS:.0f}): passed over", file=sys.stderr)
    pool = tight or takes
    steady = [t for t in pool if abs(t[1].get("bpm", 120) - 120) <= 2 and t[1]["ibi_cv"] <= 0.05 and t[1]["first_beat"] <= 1.0]
    return max(steady or pool, key=lambda t: t[1]["clarity"])[0]


def main():
    ap = argparse.ArgumentParser(description="Chapter-by-chapter music bed -> public/audio/bgm-music.wav")
    ap.add_argument("--dry-run", action="store_true", help="print the plan only")
    ap.add_argument("--full-shift", type=float, metavar="MS",
                    help="shift the full-length track by this many ms (+ = later) instead of onto the cues' beat "
                         "grid; 0 keeps it at its own time")
    args = ap.parse_args()
    dry = args.dry_run
    tl = timeline()
    fps, beat = tl["fps"], tl["beat"]
    beat_s = beat / fps  # the film's beat in seconds (0.5 at 120 BPM)
    n = int(round(tl["total"] / fps * SR))
    ana = json.loads((CH / "analysis.json").read_text()) if (CH / "analysis.json").exists() else {}
    picks = json.loads((CH / "picks.json").read_text()) if (CH / "picks.json").exists() else {}
    chapters = tl["ch"]

    plan = []
    for i, c in enumerate(chapters):
        p = picks.get(c["id"], {})
        has_takes = any(CH.glob(f"{c['id']}-*.mp3"))
        if p.get("take") == "full" or (not has_takes and "take" not in p):
            if not FULL.exists():
                sys.exit(f"{c['id']}: no takes in audio/chapters/ and no full-length track at {FULL.relative_to(ROOT)}")
            plan.append((c, "full", None, None))
        else:
            take = p.get("take") or auto_pick(c["id"], ana)
            f = CH / f"{c['id']}-{take}.mp3"
            if not f.exists() or f.name not in ana:
                sys.exit(f"{c['id']}: {f.name} missing, or not in analysis.json (run audio/chapters/analyze.py)")
            if "period" not in ana[f.name]:
                sys.exit(f"{c['id']}: analysis.json has no beat grid for {f.name}: re-run audio/chapters/analyze.py")
            if loose(ana[f.name]):
                print(f"WARNING: {c['id']}: {f.name} fits its beat grid only to {ana[f.name]['resid_ms']} ms "
                      f"(> {MAX_RESID_MS:.0f}): its beats drift off the picture's; use the other take or a new one",
                      file=sys.stderr)
            plan.append((c, take, f, float(p.get("lufs", DEFAULT_LUFS))))

    # the hits stay on beats only if every cued chapter starts on the same 120 BPM grid
    phases = {c["start"] % beat for c, take, *_ in plan if take != "full"}
    if len(phases) > 1:
        print(f"WARNING: cued chapter starts are on different beat phases (start mod {beat} = {sorted(phases)}); "
              "move them onto one grid or the cut hits drift off the beat", file=sys.stderr)

    # consecutive chapters on the full track play as one stretch: no join between them
    segs = []
    for c, take, f, target in plan:
        if take == "full" and segs and segs[-1]["take"] == "full":
            segs[-1]["ids"].append(c["id"])
            segs[-1]["dur"] += c["dur"]
        else:
            segs.append({"ids": [c["id"]], "start": c["start"], "dur": c["dur"], "take": take, "f": f, "target": target})

    # the full-length track: each stretch of it moves onto the beat grid of the cues it joins (see the docstring)
    full_grid = ana.get(FULL.name)
    for j, g in enumerate(segs):
        if g["take"] != "full":
            continue
        s, d = g["start"] / fps, g["dur"] / fps
        joins = []  # a cue's downbeat sits on its chapter's first frame, so its beats run through its start
        if j > 0:
            joins.append((s, segs[j - 1]["start"] / fps, segs[j - 1]["ids"][0]))
        if j < len(segs) - 1:
            joins.append((s + d, s + d, segs[j + 1]["ids"][0]))
        g["shift"], g["errs"], g["how"] = 0.0, [], ""
        if args.full_shift is not None:
            g["shift"], g["how"] = args.full_shift / 1000, "--full-shift"
            continue
        if not joins:
            continue
        rel = FULL.relative_to(ROOT)
        if full_grid is None:
            msg = (f"{rel} has no beat grid in audio/chapters/analysis.json: run uv run --quiet --python 3.12 "
                   f"--with librosa python audio/chapters/analyze.py {rel} (or --full-shift 0 to keep it unshifted)")
            if not dry:
                sys.exit(msg)
            if not any(x.get("how") == "no grid yet" for x in segs[:j]):
                print(f"WARNING: {msg}", file=sys.stderr)
            g["how"] = "no grid yet"
            continue
        if not full_grid.get("period"):
            if not any(x.get("how") == "no grid fit" for x in segs[:j]):
                print(f"WARNING: {rel}: too few steady beats for a grid fit: played at its own time; listen to its "
                      "joins", file=sys.stderr)
            g["how"] = "no grid fit"
            continue
        g["shift"], g["errs"] = full_shift(full_grid, joins, beat_s)
        name = "+".join(g["ids"])
        if abs(g["shift"]) > beat_s / 4:
            print(f"WARNING: {name}: the full-length track's beats sit {-g['shift'] * 1000:+.0f} ms off the cues' grid, "
                  "over a quarter beat: were the chapter starts snapped to this track (audio/snap.py)? Shifting it "
                  "that far moves the accents the picture was cut to", file=sys.stderr)
        for cid, e in g["errs"]:
            if abs(e + g["shift"]) * 1000 > MAX_JOIN_MS:
                print(f"WARNING: {name}: after the shift the join with {cid} is still {(e + g['shift']) * 1000:+.1f} ms off "
                      f"(> {MAX_JOIN_MS:.0f}): the track's tempo drifts from the film's between its joins; listen",
                      file=sys.stderr)

    bed = np.zeros((n, 2), dtype=np.float32)

    def place(x, start_s, fade_in, fade_out_at):
        """x starts at start_s; its first fade_in seconds fade in (equal power). With fade_out_at (a chapter start),
        x fades out (equal power) from fade_out_at + OUT_FROM over OUT_LEN and stops there."""
        s = int(round(start_s * SR))
        fi = min(len(x), int(fade_in * SR))
        if fi:
            x[:fi] *= np.sin(np.linspace(0, np.pi / 2, fi, dtype=np.float32))[:, None]
        if fade_out_at is not None:
            k = int(round((fade_out_at + OUT_FROM - start_s) * SR))
            if 0 < k < len(x):
                m = min(int(OUT_LEN * SR), len(x) - k)
                x[k:k + m] *= np.cos(np.linspace(0, np.pi / 2, m, dtype=np.float32))[:, None]
                x[k + m:] = 0
        a = max(0, s)
        x = x[a - s:]
        e = min(n, a + len(x))
        bed[a:e] += x[: e - a]

    report = []
    for j, g in enumerate(segs):
        s, d = g["start"] / fps, g["dur"] / fps
        last = j == len(segs) - 1
        name = "+".join(g["ids"])
        if g["take"] == "full":
            # after a cue it leads in PRE early under the outgoing cue; before a cue it fades out like one
            pre, sh = min(PRE, s), g["shift"]
            line = f"{name:12s} full track {s:7.2f}-{s + d:7.2f} s" + (f", lead-in {pre:.2f} s" if pre else "")
            if g["errs"]:
                line += f", shifted {sh * 1000:+.1f} ms onto the cues' grid (" + "; ".join(
                    f"join with {cid} {e * 1000:+.1f} -> {round((e + sh) * 1000, 1) + 0.0:+.1f} ms"  # no -0.0
                    for cid, e in g["errs"]) + ")"
            elif g["how"] == "--full-shift":
                line += f", shifted {sh * 1000:+.1f} ms (--full-shift)"
            elif g["how"]:
                line += f", not shifted ({g['how']})"
            report.append(line)
            if dry:
                continue
            at = s - pre  # film time where this stretch's audio begins
            src = at - sh  # the track's own time heard there
            if src < 0:  # delayed at the film's start: silence until the track begins
                at, src = at - src, 0.0
            x = decode(FULL, src, None if last else s + d + TAIL + 0.05 - at)
            fade = max(s - at, 0.0)  # the lead-in left
            if not fade and src > 0:
                fade = 0.01  # advanced at the film's start: it begins mid-track, so no click
            place(x, at, fade_in=fade, fade_out_at=None if last else s + d)
            continue
        f, target, a = g["f"], g["target"], ana[g["f"].name]
        if not a.get("period"):
            sys.exit(f"{name}: {f.name} has no beat grid (too few steady beats): use the other take")
        tempo = a["period"] / beat_s  # atempo factor: the cue's beat becomes exactly the film's beat
        if abs(tempo - 1) > MAX_STRETCH:
            print(f"WARNING: {name}: {f.name} is at {a['bpm']:.1f} BPM: changing its tempo by {100 * (tempo - 1):+.1f} % "
                  "may be audible; listen, or use a take nearer 120 BPM", file=sys.stderr)
        elif STRETCH == "atempo" and abs(tempo - 1) > ATEMPO_OK:
            print(f"note: {name}: {f.name} is stretched {100 * (tempo - 1):+.1f} % with atempo (no rubberband in this "
                  "ffmpeg), which can move its beats by several ms: check with qc/beat_phase.py", file=sys.stderr)
        clip = (a.get("dur") or probe_dur(f)) / tempo
        tail = 0.0 if last else TAIL
        # bar downbeats in output (stretched) seconds; the chapter's first frame takes one with a full lead-in,
        # nearest LEAD s, else the latest one that still leaves the chapter enough music after it
        downs = [t / tempo for t in a["downbeats"]]
        fits = [t for t in downs if t + d + tail + 0.1 <= clip]
        roomy = [t for t in fits if t >= PRE + 0.05]
        if not fits:
            room = clip - min(downs) if downs else 0.0
            sys.exit(f"{name}: {f.name} has {room:.2f} s from its first downbeat, the chapter needs {d + tail:.2f} s; "
                     "shorten the chapter or use a longer cue")
        down = min(roomy, key=lambda t: abs(t - LEAD)) if roomy else max(fits)
        pre = min(PRE, s, down)  # the first chapter of the film has nothing to lead in under
        line = (f"{name:12s} {f.name:18s} {a['bpm']:6.2f} BPM x{tempo:.4f}  grid {a['resid_ms']:4.1f} ms  "
                f"bar at {down:5.2f} s, lead-in {pre:.2f} s  {d:5.2f} s  clarity {a['clarity']:.2f}")
        if s > 0 and pre < PRE:
            print(f"WARNING: {name}: {f.name} leaves only {pre:.2f} s of lead-in ({clip:.1f} s take, {d:.2f} s chapter); "
                  "the join is closer to a splice: shorten the chapter or use a longer take", file=sys.stderr)
        if dry:
            report.append(f"{line}  -> {target:.0f} LUFS")
            continue
        x = decode(f, down - pre, pre + d + (tail + 0.05 if tail else 0), tempo)
        if len(x) < int((pre + d) * SR):
            sys.exit(f"{name}: {f.name} has {len(x) / SR - pre:.2f} s from its downbeat, the chapter needs {d:.2f} s; "
                     "shorten the chapter or use a longer cue")
        body = x[int(pre * SR): int((pre + d) * SR)]  # level on the chapter itself, not the lead-in or the tail
        gain = target - lufs(body)
        x *= 10 ** (gain / 20)
        place(x, s - pre, fade_in=max(pre, 0.01), fade_out_at=None if last else s + d)
        report.append(f"{line}  gain {gain:+.1f} dB -> {target:.0f} LUFS")

    if segs[-1]["take"] != "full":
        k = min(n, int(END_FADE * SR))
        bed[n - k:] *= np.linspace(1, 0, k, dtype=np.float32)[:, None]
        report.append(f"{segs[-1]['ids'][-1]:12s} fades out over the last {END_FADE:.1f} s")
    elif segs[-1]["shift"] > 0:  # a delayed full track runs past the film's end: no cut-off tail
        k = min(n, int(END_FADE * SR))
        bed[n - k:] *= np.linspace(1, 0, k, dtype=np.float32)[:, None]
        report.append(f"{segs[-1]['ids'][-1]:12s} full track delayed {segs[-1]['shift'] * 1000:.0f} ms: "
                      f"fades out over the last {END_FADE:.1f} s")
    print("\n".join(report))
    print(f"time-stretch: {STRETCH}")
    if dry:
        return
    DST.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_s24le", str(DST)],
                   input=bed.astype("<f4").tobytes(), check=True)
    print(f"wrote {DST.relative_to(ROOT)} ({n / SR:.2f} s); bed {lufs(bed):.1f} LUFS. Next: tools/voice_mix.py")


if __name__ == "__main__":
    main()
