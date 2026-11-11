#!/usr/bin/env python3
"""Resolve film-character cards into timed ASS art-cue JSON.

The Skill/agent supplies the character identity, a profile-calibrated
spoiler-safe explanation, and evidence.  This script performs deterministic
timestamp resolution from the source SRT and emits the JSON consumed by
ass_styled_subtitle.py.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Sequence, Tuple

from subtitle_gloss import Cue, parse_srt, read_utf8


TIME_RE = re.compile(
    r"^(?:(?P<hours>\d+):)?(?P<minutes>\d{1,2}):"
    r"(?P<seconds>\d{1,2})[\.,](?P<fraction>\d{1,3})$"
)
RESOLUTION_RE = re.compile(r"^(?P<width>[1-9]\d*)x(?P<height>[1-9]\d*)$")
CARD_MODES = ("off", "identity_after", "name_only", "full_visual")
VISUAL_STYLES = ("elegant", "classic")


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


def format_srt_time(milliseconds: int) -> str:
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def parse_resolution(value: str) -> Tuple[int, int]:
    match = RESOLUTION_RE.fullmatch(value.strip())
    if not match:
        fail(f"invalid resolution {value!r}; expected WIDTHxHEIGHT")
    return int(match.group("width")), int(match.group("height"))


def source_timing(cue: Cue) -> Tuple[int, int]:
    try:
        start_text, end_text = re.split(r"\s+-->\s+", cue.timing, maxsplit=1)
        return parse_time(start_text), parse_time(end_text.split()[0])
    except (RuntimeError, ValueError) as exc:
        fail(f"invalid source timing for cue {cue.cue_id}: {exc}")


def timed_cues(cues: Sequence[Cue]) -> List[Tuple[Cue, int, int]]:
    return [(cue, *source_timing(cue)) for cue in cues]


def load_payload(path: Path) -> Dict[str, Any]:
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
    normalized = dict(payload)
    normalized["characters"] = characters
    return normalized


def string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    fail(f"expected a string or list of strings, got {value!r}")


def slug(value: str, fallback: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return result or fallback


def find_cue(
    cues: Sequence[Tuple[Cue, int, int]],
    cue_id: Optional[str],
    anchors: Sequence[str],
) -> Tuple[Optional[Tuple[Cue, int, int]], Optional[str]]:
    if cue_id is not None:
        for cue, start, end in cues:
            if cue.cue_id == cue_id:
                return (cue, start, end), f"cue_id:{cue_id}"
        return None, None

    compiled = []
    for anchor in anchors:
        if not anchor:
            continue
        compiled.append(
            (
                anchor,
                re.compile(
                    rf"(?<![A-Za-z]){re.escape(anchor)}(?![A-Za-z])",
                    re.IGNORECASE,
                ),
            )
        )
    for cue, start, end in cues:
        for anchor, pattern in compiled:
            if pattern.search(cue.body):
                return (cue, start, end), f"text:{anchor}"
    return None, None


def as_duration_ms(value: Any, default_seconds: float) -> int:
    if value is None:
        seconds = default_seconds
    else:
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            fail(f"duration must be numeric seconds, got {value!r}")
    if seconds <= 0:
        fail("character card duration must be positive")
    return round(seconds * 1000)


def optional_time(raw: Dict[str, Any], key: str, index: int) -> Optional[int]:
    if raw.get(key) is None:
        return None
    try:
        return parse_time(raw[key])
    except RuntimeError as exc:
        fail(f"character #{index} has invalid {key}: {exc}")


def card_mode(raw: Dict[str, Any], default_mode: str, index: int) -> str:
    value = str(raw.get("card_mode", raw.get("mode", default_mode))).strip().casefold()
    if value not in CARD_MODES:
        fail(
            f"character #{index} has unsupported card mode {value!r}; "
            f"choose one of {', '.join(CARD_MODES)}"
        )
    return value


def visual_timing_is_legacy(raw: Dict[str, Any]) -> bool:
    """Return whether legacy start/end likely describe visual first appearance."""
    if raw.get("visual_start") is not None:
        return True
    evidence = " ".join(
        str(raw.get(key, "")).casefold()
        for key in ("evidence", "timing_source")
    )
    return "video" in evidence or "visual" in evidence or "frame" in evidence


def visual_defaults(style: str) -> Dict[str, Any]:
    if style == "elegant":
        return {
            "font_size": 52,
            "font_name": "Avenir Next",
            "color": "#E8DDCA",
            "outline": 1,
            "shadow": 1,
            "spacing": 0.3,
            "fade_in": 650,
            "fade_out": 900,
        }
    return {
        "font_size": 72,
        "font_name": "Arial",
        "color": "#F7D774",
        "outline": 3,
        "shadow": 2,
        "spacing": 0,
        "fade_in": 350,
        "fade_out": 500,
    }


def make_card(
    raw: Dict[str, Any],
    index: int,
    cues: Sequence[Tuple[Cue, int, int]],
    profile: str,
    default_duration: float,
    width: int,
    height: int,
    include_hints: bool,
    default_sources: Any,
    default_mode: str,
    visual_style: str,
) -> Optional[Dict[str, Any]]:
    name = str(raw.get("name", raw.get("character", ""))).strip()
    explanation = str(raw.get("explanation", raw.get("description", ""))).strip()
    if not name:
        fail(f"character #{index} requires name")

    mode = card_mode(raw, default_mode, index)
    if mode == "off":
        return None
    if mode != "name_only" and not explanation:
        fail(f"character #{index} requires a profile-calibrated explanation")
    style_defaults = visual_defaults(visual_style)

    card_id = str(raw.get("id", slug(name, f"character-{index}"))).strip()
    if not card_id:
        fail(f"character #{index} has an empty id")
    aliases = string_list(raw.get("aliases"))
    anchors = string_list(raw.get("anchors", raw.get("anchor")))
    if not anchors:
        anchors = [name] + aliases

    legacy_cue_id = raw.get("cue_id")
    legacy_cue_id = str(legacy_cue_id).strip() if legacy_cue_id is not None else None
    identity_cue_id = raw.get("identity_cue_id")
    identity_cue_id = (
        str(identity_cue_id).strip() if identity_cue_id is not None else None
    )
    visual_cue_id = raw.get("visual_cue_id")
    visual_cue_id = str(visual_cue_id).strip() if visual_cue_id is not None else None

    visual_start_ms = optional_time(raw, "visual_start", index)
    visual_end_ms = optional_time(raw, "visual_end", index)
    identity_start_ms = optional_time(raw, "identity_start", index)
    identity_end_ms = optional_time(raw, "identity_end", index)
    legacy_start_ms = optional_time(raw, "start", index)
    legacy_end_ms = optional_time(raw, "end", index)

    visual_match = None
    visual_matched_by = None
    identity_match = None
    identity_matched_by = None

    if mode in ("name_only", "full_visual"):
        if visual_start_ms is None and legacy_start_ms is not None:
            visual_start_ms = legacy_start_ms
            visual_end_ms = legacy_end_ms
            visual_matched_by = "explicit:start"
        elif visual_start_ms is None:
            visual_match, visual_matched_by = find_cue(
                cues, visual_cue_id or legacy_cue_id, anchors
            )
            if visual_match is not None:
                _cue, visual_start_ms, _source_end_ms = visual_match

    if identity_start_ms is None and mode == "identity_after":
        # A legacy visual-review start is deliberately not reused here.  The
        # first explicit name cue is the conservative fallback that protects
        # a mystery introduction such as Arwen's.
        if visual_timing_is_legacy(raw) and legacy_start_ms is not None:
            visual_start_ms = legacy_start_ms
            visual_end_ms = legacy_end_ms
        if not visual_timing_is_legacy(raw) and legacy_start_ms is not None:
            identity_start_ms = legacy_start_ms
            identity_end_ms = legacy_end_ms
            identity_matched_by = "explicit:start"
        else:
            identity_match, identity_matched_by = find_cue(
                cues, identity_cue_id, anchors
            )
            if identity_match is not None:
                _cue, identity_start_ms, _source_end_ms = identity_match

    if mode == "identity_after":
        start_ms = identity_start_ms
        end_ms = identity_end_ms
        matched = identity_match
        matched_by = identity_matched_by
        selected_timing_source = (
            "identity_reveal"
            if raw.get("identity_start") is not None
            else matched_by or "identity_after"
        )
    else:
        start_ms = visual_start_ms
        end_ms = visual_end_ms
        matched = visual_match
        matched_by = visual_matched_by
        selected_timing_source = (
            "visual_review"
            if raw.get("visual_start") is not None
            else matched_by or "visual_first_appearance"
        )

    if start_ms is None:
        hint = (
            f"identity_cue_id={identity_cue_id!r} or anchors={anchors!r}"
            if mode == "identity_after"
            else f"visual_cue_id={visual_cue_id!r} or anchors={anchors!r}"
        )
        fail(f"character #{index} ({name}) has no resolvable card anchor: {hint}")
    if end_ms is None:
        end_ms = start_ms + as_duration_ms(raw.get("duration"), default_duration)

    offset_ms = raw.get("offset_ms", 0)
    try:
        offset_ms = int(offset_ms)
    except (TypeError, ValueError):
        fail(f"character #{index} offset_ms must be an integer")
    start_ms += offset_ms
    end_ms += offset_ms
    if end_ms <= start_ms:
        fail(f"character #{index} ({name}) must end after it starts")

    hint = str(raw.get("zh_hint", raw.get("hint", ""))).strip()
    show_hint = include_hints or bool(raw.get("include_zh_hint"))
    text_lines = [name]
    if mode != "name_only":
        text_lines.append(explanation)
    if show_hint and hint:
        text_lines.append(hint)

    position = raw.get("position", [width // 2, round(height * 0.42)])
    if not isinstance(position, list) or len(position) != 2:
        fail(f"character #{index} position must be [x, y]")

    sources = raw.get("sources", default_sources or [])
    if sources is None:
        sources = []
    if not isinstance(sources, list):
        fail(f"character #{index} sources must be a list")

    evidence = str(raw.get("evidence", "subtitle_mention"))
    timing_source = str(raw.get("display_timing_source", selected_timing_source))
    confidence_default = (
        "high"
        if raw.get("identity_start") is not None
        or raw.get("visual_start") is not None
        or raw.get("start") is not None
        else "medium"
    )
    card: Dict[str, Any] = {
        "id": card_id,
        "character": name,
        "aliases": aliases,
        "card_mode": mode,
        "start": format_srt_time(start_ms),
        "end": format_srt_time(end_ms),
        "display_start": format_srt_time(start_ms),
        "display_end": format_srt_time(end_ms),
        "text": "\n".join(text_lines),
        "style": str(raw.get("style", "ArtTitle")),
        "position": position,
        "align": raw.get("align", raw.get("alignment", 5)),
        "font_size": raw.get("font_size", style_defaults["font_size"]),
        "font_name": raw.get("font_name", style_defaults["font_name"]),
        "color": raw.get("color", style_defaults["color"]),
        "outline": raw.get("outline", style_defaults["outline"]),
        "shadow": raw.get("shadow", style_defaults["shadow"]),
        "spacing": raw.get("spacing", style_defaults["spacing"]),
        "fade_in": raw.get("fade_in", style_defaults["fade_in"]),
        "fade_out": raw.get("fade_out", style_defaults["fade_out"]),
        "visual_style": visual_style,
        "evidence": evidence,
        "timing_source": timing_source,
        "confidence": str(raw.get("confidence", confidence_default)),
        "evidence_candidates": raw.get("evidence_candidates", {}),
        "matched_by": matched_by,
        "spoiler_policy": str(raw.get("spoiler_policy", "no_future_spoilers")),
        "profile": profile,
        "sources": sources,
    }
    if visual_start_ms is not None:
        card["visual_start"] = format_srt_time(visual_start_ms)
    if visual_end_ms is not None:
        card["visual_end"] = format_srt_time(visual_end_ms)
    if identity_start_ms is not None:
        card["identity_start"] = format_srt_time(identity_start_ms)
    if identity_end_ms is not None:
        card["identity_end"] = format_srt_time(identity_end_ms)
    if matched is not None:
        card["matched_cue_id"] = matched[0].cue_id
    return card


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="normalized English SRT")
    parser.add_argument("--characters", required=True, type=Path, help="agent-generated character JSON")
    parser.add_argument("--output", required=True, type=Path, help="resolved art-cue JSON")
    parser.add_argument("--profile", required=True, help="learner profile, e.g. cet4 or b1")
    parser.add_argument("--resolution", default="1920x1080", help="ASS coordinates, e.g. 1920x1080")
    parser.add_argument("--duration", type=float, default=4.5, help="default card duration in seconds")
    parser.add_argument(
        "--card-mode",
        choices=CARD_MODES,
        default=None,
        help=(
            "display policy; default is identity_after. The Skill invokes "
            "this stage only when character cards are enabled."
        ),
    )
    parser.add_argument(
        "--visual-style",
        choices=VISUAL_STYLES,
        default=None,
        help="art-card visual style; default is elegant",
    )
    parser.add_argument("--include-hints", action="store_true", help="append zh_hint when present")
    parser.add_argument("--skip-unresolved", action="store_true", help="skip cards without a timestamp anchor")
    parser.add_argument("--force", action="store_true", help="replace an existing output")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input.expanduser().resolve()
    characters_path = args.characters.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if not input_path.is_file():
        fail(f"input SRT does not exist: {input_path}")
    if not characters_path.is_file():
        fail(f"character JSON does not exist: {characters_path}")
    if output_path.exists() and not args.force:
        fail(f"output already exists; pass --force or choose another path: {output_path}")

    width, height = parse_resolution(args.resolution)
    cues = timed_cues(parse_srt(read_utf8(input_path)))
    payload = load_payload(characters_path)
    payload_profile = str(payload.get("profile", "")).strip()
    if payload_profile and payload_profile.casefold() != args.profile.casefold():
        fail(
            f"character JSON profile {payload_profile!r} does not match --profile {args.profile!r}"
        )
    profile = args.profile
    default_sources = payload.get("sources", [])
    default_mode = str(
        args.card_mode
        or payload.get("character_card_mode", payload.get("card_mode", "identity_after"))
    ).strip().casefold()
    if default_mode not in CARD_MODES:
        fail(
            f"unsupported character_card_mode {default_mode!r}; "
            f"choose one of {', '.join(CARD_MODES)}"
        )
    visual_style = str(
        args.visual_style or payload.get("visual_style", "elegant")
    ).strip().casefold()
    if visual_style not in VISUAL_STYLES:
        fail(
            f"unsupported visual_style {visual_style!r}; "
            f"choose one of {', '.join(VISUAL_STYLES)}"
        )
    resolved: List[Dict[str, Any]] = []
    unresolved: List[str] = []
    seen_ids = set()
    for index, raw in enumerate(payload["characters"], start=1):
        if not isinstance(raw, dict):
            fail(f"character #{index} must be an object")
        try:
            card = make_card(
                raw,
                index,
                cues,
                profile,
                args.duration,
                width,
                height,
                args.include_hints,
                default_sources,
                default_mode,
                visual_style,
            )
        except RuntimeError as exc:
            if args.skip_unresolved and "anchor" in str(exc):
                unresolved.append(str(exc))
                continue
            raise
        if card is None:
            continue
        if card["id"] in seen_ids:
            fail(f"duplicate character id: {card['id']}")
        seen_ids.add(card["id"])
        resolved.append(card)

    resolved.sort(key=lambda item: (parse_time(item["start"]), item["id"]))
    output_payload = {
        "schema": "lov-subtitle-freedom-skill/character-cards/v1",
        "profile": profile,
        "spoiler_policy": payload.get("spoiler_policy", "no_future_spoilers"),
        "character_cards_enabled": default_mode != "off",
        "character_card_mode": default_mode,
        "visual_style": visual_style,
        "source_subtitle": str(input_path),
        "sources": default_sources,
        "items": resolved,
        "unresolved": unresolved,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output_path),
                "resolved": len(resolved),
                "unresolved": len(unresolved),
                "profile": profile,
                "visual_style": visual_style,
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
