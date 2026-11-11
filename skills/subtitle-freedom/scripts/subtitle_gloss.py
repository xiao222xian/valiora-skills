#!/usr/bin/env python3
"""Extract/normalize a text subtitle and apply a profile-floor glossary.

This script intentionally does not decide which language units are educationally
necessary. The Skill/agent creates a contextual glossary and labels each new
item with a difficulty level; this CLI keeps the selected learner level and all
higher levels, then performs the repeatable file, timing, and annotation work
without changing the source.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, NoReturn, Optional, Sequence, Set, Tuple


VIDEO_EXTENSIONS = {".mkv", ".mp4", ".mov", ".webm", ".avi", ".ts", ".m2ts"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa"}
TEXT_SUBTITLE_CODECS = {
    "subrip",
    "ass",
    "ssa",
    "webvtt",
    "mov_text",
    "text",
    "srt",
}
TIMING_RE = re.compile(
    r"^\d{1,3}:\d{2}:\d{2}[,.]\d{3}\s+-->\s+"
    r"\d{1,3}:\d{2}:\d{2}[,.]\d{3}(?:\s+.*)?$"
)


# This is a product selection ladder for learner subtitles, not a formal
# conversion between CEFR and Chinese exam scores. A selected profile is the
# minimum difficulty line: CET4 keeps CET4, B2, CET6, and advanced items.
PROFILE_LEVEL_ORDER = {
    "a2": 10,
    "b1": 20,
    "cet4": 30,
    "b2": 40,
    "cet6": 50,
    "advanced": 60,
}
PROFILE_ALIASES = {
    "a2": "a2",
    "cefra2": "a2",
    "b1": "b1",
    "cefrb1": "b1",
    "cet4": "cet4",
    "b2": "b2",
    "cefrb2": "b2",
    "cet6": "cet6",
    "advanced": "advanced",
    "c1": "advanced",
    "c2": "advanced",
    "cet6plus": "advanced",
    "abovecet6": "advanced",
}


@dataclass(frozen=True)
class Cue:
    cue_id: str
    timing: str
    body: str


@dataclass(frozen=True)
class Gloss:
    term: str
    meaning: str
    key: str
    repeat: str
    kind: str
    label: str
    level: str = ""


@dataclass(frozen=True)
class AnnotationCoverage:
    """Deterministic glossary coverage for one subtitle run."""

    matched_keys: Set[str]
    applied_keys: Set[str]
    suppressed_reasons: Dict[str, Set[str]]


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def parse_srt(text: str) -> List[Cue]:
    normalized = text.replace("\ufeff", "").replace("\r\n", "\n").strip()
    if not normalized:
        fail("subtitle is empty")
    blocks = re.split(r"\n\s*\n", normalized)
    cues: List[Cue] = []
    for index, block in enumerate(blocks, 1):
        lines = block.split("\n")
        if len(lines) < 3:
            fail(f"SRT cue {index} has fewer than three lines")
        if not TIMING_RE.match(lines[1]):
            fail(f"SRT cue {index} has invalid timing: {lines[1]}")
        body = "\n".join(lines[2:])
        if not body.strip():
            fail(f"SRT cue {index} has empty text")
        cues.append(Cue(lines[0], lines[1], body))
    return cues


def render_srt(cues: Sequence[Cue]) -> str:
    return "\n\n".join(
        "\n".join((cue.cue_id, cue.timing, cue.body)) for cue in cues
    ) + "\n"


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        fail(f"subtitle is not valid UTF-8: {path} ({exc})")


def compact_level(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold().strip())


def canonical_profile(profile: str) -> str:
    compact = compact_level(profile)
    if compact == "custom":
        return "custom"
    return PROFILE_ALIASES.get(compact, compact)


def canonical_gloss_level(value: Any, index: int) -> str:
    raw = str(value or "").strip()
    if not raw or compact_level(raw) in {"ungraded", "unknown"}:
        return ""
    canonical = PROFILE_ALIASES.get(compact_level(raw))
    if canonical not in PROFILE_LEVEL_ORDER:
        fail(
            f"glossary item {index} has unsupported level {raw!r}; use "
            "a2, b1, cet4, b2, cet6, advanced, or omit it for legacy input"
        )
    return canonical


def load_glossary(path: Path) -> Tuple[List[Gloss], int, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"glossary does not exist: {path}")
    except json.JSONDecodeError as exc:
        fail(f"glossary is not valid JSON: {path} ({exc})")

    if isinstance(data, list):
        raw_items: Any = data
        default_repeat = "first"
        max_notes = 3
    elif isinstance(data, dict):
        raw_items = data.get("items")
        default_repeat = str(data.get("repeat", "first")).strip().lower()
        max_notes = int(data.get("max_notes_per_cue", 3))
    else:
        fail("glossary must be a JSON list or an object containing 'items'")

    if not isinstance(raw_items, list):
        fail("glossary 'items' must be a list")
    if default_repeat not in {"first", "all"}:
        fail("glossary repeat must be 'first' or 'all'")
    if max_notes < 1:
        fail("glossary max_notes_per_cue must be positive")

    items: List[Gloss] = []
    for index, raw in enumerate(raw_items, 1):
        if not isinstance(raw, dict):
            fail(f"glossary item {index} must be an object")
        term = str(raw.get("term", "")).strip()
        meaning = str(raw.get("meaning", "")).strip()
        key = str(raw.get("key", term.casefold())).strip()
        repeat = str(raw.get("repeat", default_repeat)).strip().lower()
        kind = str(raw.get("kind", "word")).strip().lower()
        label = str(raw.get("label", "")).strip()
        level = canonical_gloss_level(raw.get("level", ""), index)
        if not term or not meaning or not key:
            fail(f"glossary item {index} needs term, meaning, and key")
        if repeat not in {"first", "all"}:
            fail(f"glossary item {index} repeat must be 'first' or 'all'")
        if kind not in {"word", "phrase", "idiom", "proverb", "slang", "culture", "sentence", "term"}:
            fail(
                f"glossary item {index} kind must be word, phrase, idiom, proverb, "
                "slang, culture, sentence, or term"
            )
        if "【" in meaning or "】" in meaning:
            fail(f"glossary item {index} meaning cannot contain annotation brackets")
        items.append(Gloss(term, meaning, key, repeat, kind, label, level))
    return items, max_notes, default_repeat


def select_glosses(
    glosses: Sequence[Gloss], profile: str
) -> Tuple[List[Gloss], Dict[str, Any]]:
    """Keep glossary items at or above the selected learner level.

    Items without a level are retained for backwards compatibility. They are
    reported so new glossary generation can add an explicit level next time.
    Custom or unknown profiles keep all supplied items because there is no
    comparable product floor.
    """
    canonical = canonical_profile(profile)
    floor = PROFILE_LEVEL_ORDER.get(canonical)
    if floor is None:
        return list(glosses), {
            "canonical_profile": canonical,
            "profile_floor": None,
            "filtered_below_profile": 0,
            "ungraded_glosses_retained": sum(not gloss.level for gloss in glosses),
        }

    selected: List[Gloss] = []
    filtered = 0
    ungraded = 0
    for gloss in glosses:
        if not gloss.level:
            selected.append(gloss)
            ungraded += 1
        elif PROFILE_LEVEL_ORDER[gloss.level] >= floor:
            selected.append(gloss)
        else:
            filtered += 1
    return selected, {
        "canonical_profile": canonical,
        "profile_floor": canonical,
        "filtered_below_profile": filtered,
        "ungraded_glosses_retained": ungraded,
    }


def annotate_cues_with_report(
    cues: Sequence[Cue],
    glosses: Sequence[Gloss],
    max_notes_per_cue: int,
) -> Tuple[List[Cue], int, AnnotationCoverage]:
    compiled = [
        (
            gloss,
            re.compile(
                rf"(?<![A-Za-z]){re.escape(gloss.term)}(?![A-Za-z])",
                re.IGNORECASE | re.DOTALL,
            ),
        )
        for gloss in glosses
    ]
    seen: Set[str] = set()
    matched_keys: Set[str] = set()
    applied_keys: Set[str] = set()
    suppressed_reasons: Dict[str, Set[str]] = {}
    annotated: List[Cue] = []
    note_count = 0

    for cue in cues:
        matches: List[Tuple[int, int, int, Gloss, Any]] = []
        for order, (gloss, pattern) in enumerate(compiled):
            for match in pattern.finditer(cue.body):
                matched_keys.add(gloss.key)
                matches.append((match.start(), match.end(), order, gloss, match))
        matches.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2]))

        selected: List[Tuple[int, int, Gloss, Any]] = []
        selected_in_cue_keys: Set[str] = set()
        for start, end, _order, gloss, match in matches:
            if gloss.repeat == "first" and gloss.key in seen:
                suppressed_reasons.setdefault(gloss.key, set()).add("repeat_first")
                continue
            if gloss.key in selected_in_cue_keys:
                suppressed_reasons.setdefault(gloss.key, set()).add("duplicate_key")
                continue
            if any(
                start < old_end and end > old_start
                for old_start, old_end, *_ in selected
            ):
                suppressed_reasons.setdefault(gloss.key, set()).add("overlap")
                continue
            if len(selected) >= max_notes_per_cue:
                suppressed_reasons.setdefault(gloss.key, set()).add("max_notes_per_cue")
                continue
            selected.append((start, end, gloss, match))
            selected_in_cue_keys.add(gloss.key)
            applied_keys.add(gloss.key)

        body = cue.body
        for start, end, gloss, match in reversed(selected):
            annotation = f"{gloss.label}：{gloss.meaning}" if gloss.label else gloss.meaning
            body = body[:start] + match.group(0) + f"【{annotation}】" + body[end:]
            if gloss.repeat == "first":
                seen.add(gloss.key)
            note_count += 1
        annotated.append(Cue(cue.cue_id, cue.timing, body))
    return annotated, note_count, AnnotationCoverage(
        matched_keys=matched_keys,
        applied_keys=applied_keys,
        suppressed_reasons=suppressed_reasons,
    )


def annotate_cues(
    cues: Sequence[Cue],
    glosses: Sequence[Gloss],
    max_notes_per_cue: int,
) -> Tuple[List[Cue], int]:
    """Annotate cues while preserving the compact legacy return shape."""

    annotated, note_count, _coverage = annotate_cues_with_report(
        cues, glosses, max_notes_per_cue
    )
    return annotated, note_count


def glossary_report_entries(
    glosses: Sequence[Gloss],
    keys: Set[str],
    reasons: Optional[Dict[str, Set[str]]] = None,
    default_reason: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Return unique glossary entries in input order with stable reasons."""

    entries: List[Dict[str, str]] = []
    emitted: Set[str] = set()
    for gloss in glosses:
        if gloss.key not in keys or gloss.key in emitted:
            continue
        emitted.add(gloss.key)
        entry = {"key": gloss.key, "term": gloss.term}
        reason_values = (reasons or {}).get(gloss.key, set())
        if reason_values:
            entry["reason"] = ",".join(sorted(reason_values))
        elif default_reason:
            entry["reason"] = default_reason
        entries.append(entry)
    return entries


def run_command(command: Sequence[str], label: str) -> None:
    try:
        subprocess.run(
            list(command),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        fail(f"{label} requires an installed command: {command[0]}")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        fail(f"{label} failed{suffix}")


def probe_video(path: Path) -> List[Dict[str, Any]]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=index,codec_type,codec_name:stream_disposition=default,forced:stream_tags=language,title,handler_name",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        fail("video input requires ffprobe")
    except subprocess.CalledProcessError as exc:
        fail(f"ffprobe failed: {(exc.stderr or '').strip()}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"ffprobe returned invalid JSON: {exc}")
    return [stream for stream in data.get("streams", []) if stream.get("codec_type") == "subtitle"]


def describe_stream(stream: Dict[str, Any]) -> str:
    tags = stream.get("tags") or {}
    language = tags.get("language", "unknown")
    title = tags.get("title") or tags.get("handler_name") or "untitled"
    codec = stream.get("codec_name", "unknown")
    return f"index={stream.get('index')} language={language} codec={codec} title={title}"


def choose_stream(streams: Sequence[Dict[str, Any]], requested: Optional[int]) -> Dict[str, Any]:
    if not streams:
        fail("video has no subtitle streams")
    if requested is not None:
        for stream in streams:
            if int(stream.get("index", -1)) == requested:
                return stream
        fail(
            "requested subtitle stream was not found; available: "
            + "; ".join(describe_stream(stream) for stream in streams)
        )

    def is_english(stream: Dict[str, Any]) -> bool:
        tags = stream.get("tags") or {}
        language = str(tags.get("language", "")).lower()
        title = str(tags.get("title", "")).lower()
        return language in {"en", "eng", "英语", "英文"} or "english" in title

    def is_text(stream: Dict[str, Any]) -> bool:
        return str(stream.get("codec_name", "")).lower() in TEXT_SUBTITLE_CODECS

    english_text = [stream for stream in streams if is_english(stream) and is_text(stream)]
    if english_text:
        return english_text[0]
    text_streams = [stream for stream in streams if is_text(stream)]
    if len(text_streams) == 1:
        return text_streams[0]
    if not text_streams:
        fail(
            "no text subtitle stream is available; bitmap subtitles need OCR, "
            "which is outside this Skill. Available: "
            + "; ".join(describe_stream(stream) for stream in streams)
        )
    fail(
        "English subtitle stream is ambiguous; pass --subtitle-stream with one of: "
        + "; ".join(describe_stream(stream) for stream in text_streams)
    )


def normalize_to_srt(input_path: Path, work_dir: Path, subtitle_stream: Optional[int]) -> Tuple[Path, str]:
    suffix = input_path.suffix.lower()
    if suffix in {".srt"}:
        return input_path, "subtitle"

    target = work_dir / "source.srt"
    if suffix in VIDEO_EXTENSIONS:
        stream = choose_stream(probe_video(input_path), subtitle_stream)
        map_spec = f"0:{int(stream['index'])}"
        label = f"extract subtitle stream {stream['index']}"
        run_command(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_path),
                "-map",
                map_spec,
                "-c:s",
                "srt",
                str(target),
            ],
            label,
        )
        return target, "video"

    if suffix in SUBTITLE_EXTENSIONS:
        run_command(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_path),
                "-map",
                "0:0",
                "-c:s",
                "srt",
                str(target),
            ],
            "normalize subtitle format",
        )
        return target, "subtitle"

    fail(
        "unsupported input extension; use a video or .srt/.vtt/.ass/.ssa subtitle file"
    )


def default_output(input_path: Path, profile: str) -> Path:
    safe_profile = re.sub(r"[^A-Za-z0-9_-]+", "-", profile.strip().lower()).strip("-")
    safe_profile = safe_profile or "learner"
    return input_path.with_name(f"{input_path.stem}.{safe_profile}.glossed.srt")


def validate_output(source: Sequence[Cue], output: Sequence[Cue]) -> None:
    if len(source) != len(output):
        fail(f"output cue count changed: {len(source)} -> {len(output)}")
    for index, (before, after) in enumerate(zip(source, output), 1):
        if before.cue_id != after.cue_id or before.timing != after.timing:
            fail(f"output changed cue id or timestamp at cue {index}")
        if not after.body.strip():
            fail(f"output cue {index} is empty")
    if "【" not in "".join(cue.body for cue in output):
        print("warning=no glossary match was applied", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Video or subtitle path")
    parser.add_argument(
        "--profile",
        required=True,
        help="Minimum learner level; keeps this level and higher, e.g. cet4, b1, or custom",
    )
    parser.add_argument("--glossary", required=True, type=Path, help="Contextual glossary JSON")
    parser.add_argument("--output", type=Path, help="Output SRT; defaults beside the input")
    parser.add_argument(
        "--subtitle-stream",
        type=int,
        help="Video stream index from ffprobe when English subtitle selection is ambiguous",
    )
    parser.add_argument(
        "--max-notes-per-cue",
        type=int,
        help="Override the glossary's annotation density limit",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    if not input_path.is_file():
        print(f"ERROR: input does not exist: {input_path}", file=sys.stderr)
        return 2
    if args.output and args.output.expanduser().resolve() == input_path:
        print("ERROR: output must not overwrite the input", file=sys.stderr)
        return 2

    output_path = (
        args.output.expanduser().resolve()
        if args.output
        else default_output(input_path, args.profile).resolve()
    )
    if output_path.exists() and output_path != input_path:
        print(f"ERROR: output already exists: {output_path}", file=sys.stderr)
        return 2

    try:
        glosses, glossary_limit, _default_repeat = load_glossary(args.glossary.expanduser().resolve())
        eligible_glosses, selection = select_glosses(glosses, args.profile)
        if selection["ungraded_glosses_retained"]:
            print(
                "warning=glossary items without level were retained for compatibility; "
                "label new items with level to enforce the profile floor",
                file=sys.stderr,
            )
        max_notes = (
            args.max_notes_per_cue
            if args.max_notes_per_cue is not None
            else glossary_limit
        )
        if max_notes < 1:
            fail("max notes per cue must be positive")
        with tempfile.TemporaryDirectory(prefix="subtitle-freedom-") as temp:
            source_srt, input_kind = normalize_to_srt(
                input_path, Path(temp), args.subtitle_stream
            )
            source_cues = parse_srt(read_utf8(source_srt))
            output_cues, note_count, coverage = annotate_cues_with_report(
                source_cues, eligible_glosses, max_notes
            )
            validate_output(source_cues, output_cues)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(render_srt(output_cues), encoding="utf-8")
        eligible_keys = {gloss.key for gloss in eligible_glosses}
        unmatched_keys = eligible_keys - coverage.matched_keys
        suppressed_keys = coverage.matched_keys - coverage.applied_keys
        print(
            json.dumps(
                {
                    "input": str(input_path),
                    "input_kind": input_kind,
                    "profile": args.profile,
                    "profile_floor": selection["profile_floor"],
                    "cues": len(source_cues),
                    "glosses": note_count,
                    "glossary_candidates": len(glosses),
                    "eligible_glosses": len(eligible_glosses),
                    "glossary_matched": len(coverage.matched_keys),
                    "glossary_applied": len(coverage.applied_keys),
                    "glossary_unmatched": glossary_report_entries(
                        eligible_glosses,
                        unmatched_keys,
                        default_reason="no_literal_match",
                    ),
                    "glossary_suppressed": glossary_report_entries(
                        eligible_glosses,
                        suppressed_keys,
                        reasons=coverage.suppressed_reasons,
                    ),
                    "filtered_below_profile": selection["filtered_below_profile"],
                    "ungraded_glosses_retained": selection["ungraded_glosses_retained"],
                    "output": str(output_path),
                },
                ensure_ascii=False,
            )
        )
        return 0
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
