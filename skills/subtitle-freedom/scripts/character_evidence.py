#!/usr/bin/env python3
"""Collect fast, auditable evidence for first character appearances.

The script scans the subtitle once for literal names/aliases and agent-supplied
semantic phrases.  When requested, it creates small contact sheets only around
those candidate windows; it never scans every video frame by default.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, NoReturn, Optional, Sequence, Tuple

from subtitle_gloss import Cue, parse_srt, read_utf8


TIME_RE = re.compile(
    r"^(?:(?P<hours>\d+):)?(?P<minutes>\d{1,2}):"
    r"(?P<seconds>\d{1,2})[\.,](?P<fraction>\d{1,3})$"
)


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def parse_time(value: Any) -> int:
    if isinstance(value, bool):
        fail(f"invalid time value: {value!r}")
    if isinstance(value, (int, float)):
        milliseconds = round(float(value) * 1000)
        if milliseconds < 0:
            fail(f"time must not be negative: {value!r}")
        return milliseconds
    text = str(value).strip().replace(",", ".")
    match = TIME_RE.fullmatch(text)
    if not match:
        fail(f"invalid time value: {value!r}; expected HH:MM:SS.mmm")
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    fraction = match.group("fraction").ljust(3, "0")[:3]
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + int(fraction)


def format_time(milliseconds: int) -> str:
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def load_characters(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(read_utf8(path))
    except json.JSONDecodeError as exc:
        fail(f"character JSON is invalid: {exc}")
    if isinstance(payload, list):
        return {"characters": payload}
    if not isinstance(payload, dict):
        fail("character JSON must be a list or an object containing characters")
    characters = payload.get("characters", payload.get("items"))
    if not isinstance(characters, list):
        fail("character JSON must contain a characters/items list")
    result = dict(payload)
    result["characters"] = characters
    return result


def string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    fail(f"expected a string or list of strings, got {value!r}")


def cue_timing(cue: Cue) -> Tuple[int, int]:
    try:
        start_text, end_text = re.split(r"\s+-->\s+", cue.timing, maxsplit=1)
        return parse_time(start_text), parse_time(end_text.split()[0])
    except (RuntimeError, ValueError) as exc:
        fail(f"invalid timing in cue {cue.cue_id}: {exc}")


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    parts = phrase.strip().split()
    if not parts:
        return re.compile(r"(?!)")
    body = r"\s+".join(re.escape(part) for part in parts)
    return re.compile(rf"(?<![A-Za-z]){body}(?![A-Za-z])", re.IGNORECASE)


def find_hits(
    cues: Sequence[Tuple[Cue, int, int]],
    phrases: Sequence[str],
    kind: str,
) -> List[Dict[str, Any]]:
    compiled = [(phrase, phrase_pattern(phrase)) for phrase in phrases if phrase]
    hits: List[Dict[str, Any]] = []
    for cue, start, end in cues:
        for phrase, pattern in compiled:
            if pattern.search(cue.body):
                hits.append(
                    {
                        "cue_id": cue.cue_id,
                        "start": format_time(start),
                        "end": format_time(end),
                        "phrase": phrase,
                        "kind": kind,
                        "text": cue.body,
                    }
                )
    return hits


def find_semantic_groups(
    cues: Sequence[Tuple[Cue, int, int]],
    groups: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for group_index, group in enumerate(groups, start=1):
        if not isinstance(group, dict):
            fail(f"semantic group #{group_index} must be an object")
        phrases = string_list(group.get("phrases", group.get("anchors")))
        if not phrases:
            fail(f"semantic group #{group_index} requires phrases")
        try:
            window_seconds = float(group.get("within_seconds", 20))
            minimum = int(group.get("min_matches", 2))
        except (TypeError, ValueError):
            fail(f"semantic group #{group_index} has invalid window or min_matches")
        if window_seconds <= 0 or minimum < 1:
            fail(f"semantic group #{group_index} needs a positive window and min_matches")

        hits = find_hits(cues, phrases, "semantic_phrase")
        ordered = sorted(hits, key=lambda hit: parse_time(hit["start"]))
        window_ms = round(window_seconds * 1000)
        for anchor in ordered:
            anchor_start = parse_time(anchor["start"])
            nearby = [
                hit
                for hit in ordered
                if anchor_start <= parse_time(hit["start"]) <= anchor_start + window_ms
            ]
            distinct_phrases = {hit["phrase"] for hit in nearby}
            if len(distinct_phrases) < minimum:
                continue
            results.append(
                {
                    "group": str(group.get("label", f"group-{group_index}")),
                    "start": anchor["start"],
                    "end": nearby[-1]["end"],
                    "kind": "semantic_context_group",
                    "matches": nearby,
                    "within_seconds": window_seconds,
                }
            )
            break
    return results


def run_contact_sheet(
    video: Path,
    output: Path,
    start_ms: int,
    end_ms: int,
    max_samples: int,
) -> Dict[str, Any]:
    if shutil.which("ffmpeg") is None:
        fail("video sampling requires ffmpeg")
    if end_ms <= start_ms:
        fail("video sampling window must end after it starts")

    duration_ms = end_ms - start_ms
    sample_count = max(2, min(max_samples, math.ceil(duration_ms / 1000) + 1))
    interval = max(1.0, duration_ms / 1000 / max(sample_count - 1, 1))
    columns = 4
    rows = max(1, math.ceil(sample_count / columns))
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start_ms / 1000:.3f}",
        "-i",
        str(video),
        "-t",
        f"{duration_ms / 1000:.3f}",
        "-vf",
        f"fps=1/{interval:.3f},scale=480:-2,tile={columns}x{rows}:padding=4:margin=4",
        "-frames:v",
        "1",
        str(output),
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        fail("video sampling requires ffmpeg")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        fail(f"video contact-sheet generation failed{suffix}")
    return {
        "path": str(output),
        "start": format_time(start_ms),
        "end": format_time(end_ms),
        "sample_count": sample_count,
        "interval_seconds": round(interval, 3),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="English SRT to scan")
    parser.add_argument("--characters", required=True, type=Path, help="character JSON with aliases/semantic_anchors")
    parser.add_argument("--output", required=True, type=Path, help="evidence report JSON")
    parser.add_argument("--video", type=Path, help="optional video for narrow contact-sheet checks")
    parser.add_argument("--video-samples-dir", type=Path, help="generate contact sheets here when --video is supplied")
    parser.add_argument("--lookback", type=float, default=45.0, help="seconds before the earliest text candidate")
    parser.add_argument("--lookahead", type=float, default=15.0, help="seconds after the earliest text candidate")
    parser.add_argument("--max-samples", type=int, default=12, help="maximum frames per character contact sheet")
    parser.add_argument("--force", action="store_true", help="replace an existing report")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input.expanduser().resolve()
    characters_path = args.characters.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if not input_path.is_file():
        fail(f"subtitle does not exist: {input_path}")
    if not characters_path.is_file():
        fail(f"character JSON does not exist: {characters_path}")
    if args.video and not args.video.expanduser().resolve().is_file():
        fail(f"video does not exist: {args.video.expanduser().resolve()}")
    if args.video_samples_dir and not args.video:
        fail("--video-samples-dir requires --video")
    if output_path.exists() and not args.force:
        fail(f"output already exists; pass --force or choose another path: {output_path}")
    if args.lookback < 0 or args.lookahead < 0:
        fail("lookback and lookahead must not be negative")
    if args.max_samples < 2:
        fail("max-samples must be at least 2")

    started = time.monotonic()
    cues = [(cue, *cue_timing(cue)) for cue in parse_srt(read_utf8(input_path))]
    payload = load_characters(characters_path)
    reports: List[Dict[str, Any]] = []
    for index, raw in enumerate(payload["characters"], start=1):
        if not isinstance(raw, dict):
            fail(f"character #{index} must be an object")
        name = str(raw.get("name", raw.get("character", ""))).strip()
        if not name:
            fail(f"character #{index} requires name")
        aliases = string_list(raw.get("aliases"))
        literals = string_list(raw.get("anchors", raw.get("anchor")))
        literals = literals or [name] + aliases
        semantics = string_list(raw.get("semantic_anchors", raw.get("semantic")))
        semantic_groups = raw.get("semantic_groups", [])
        if semantic_groups and not isinstance(semantic_groups, list):
            fail(f"character #{index} semantic_groups must be a list")
        exact_hits = find_hits(cues, literals, "literal_name_or_alias")
        semantic_hits = find_hits(cues, semantics, "semantic_phrase")
        group_hits = find_semantic_groups(cues, semantic_groups)
        first_exact = exact_hits[0] if exact_hits else None
        first_semantic_candidates = (
            group_hits
            if semantic_groups
            else semantic_hits
        )
        first_semantic = (
            min(first_semantic_candidates, key=lambda candidate: parse_time(candidate["start"]))
            if first_semantic_candidates
            else None
        )
        candidates = [candidate for candidate in (first_exact, first_semantic) if candidate]
        first_candidate = min(candidates, key=lambda candidate: parse_time(candidate["start"])) if candidates else None
        report: Dict[str, Any] = {
            "id": str(raw.get("id", name.casefold().replace(" ", "-"))),
            "character": name,
            "literals": literals,
            "semantic_anchors": semantics,
            "semantic_groups": semantic_groups,
            "first_literal": first_exact,
            "first_semantic": first_semantic,
            "literal_hits": exact_hits,
            "semantic_hits": semantic_hits,
            "semantic_group_hits": group_hits,
            "recommended_text_candidate": first_candidate,
            "timing_guidance": (
                "video_review_or_explicit_start_required"
                if first_semantic and first_exact and first_semantic["start"] != first_exact["start"]
                else "literal_subtitle_candidate"
            ),
        }
        if args.video and args.video_samples_dir and first_candidate:
            center = parse_time(first_candidate["start"])
            window_start = max(0, center - round(args.lookback * 1000))
            window_end = center + round(args.lookahead * 1000)
            sample_path = args.video_samples_dir.expanduser().resolve() / f"{report['id']}.jpg"
            report["video_contact_sheet"] = run_contact_sheet(
                args.video.expanduser().resolve(),
                sample_path,
                window_start,
                window_end,
                args.max_samples,
            )
        reports.append(report)

    output = {
        "schema": "lov-subtitle-freedom-skill/character-evidence/v1",
        "source_subtitle": str(input_path),
        "source_video": str(args.video.expanduser().resolve()) if args.video else None,
        "characters": reports,
        "search_seconds": round(time.monotonic() - started, 4),
        "notes": [
            "literal name timing is not necessarily visual first appearance",
            "semantic and web evidence identify a character but do not prove shot timing",
            "video contact sheets are narrow candidate checks, not a full-frame scan",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "characters": len(reports),
                "literal_hits": sum(len(item["literal_hits"]) for item in reports),
                "semantic_hits": sum(len(item["semantic_hits"]) for item in reports),
                "search_seconds": output["search_seconds"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(1)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
