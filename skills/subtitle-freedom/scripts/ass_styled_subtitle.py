#!/usr/bin/env python3
"""Convert SRT cues to ASS and add optional timed art/scene-card cues.

This keeps the source subtitle wording and timing intact.  The optional JSON
file is deliberately explicit: a model or editor supplies the art-card text
and timing, while this script performs deterministic serialization.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, NoReturn, Optional, Tuple

from subtitle_gloss import Cue, parse_srt, read_utf8


TIME_RE = re.compile(
    r"^(?:(?P<hours>\d+):)?(?P<minutes>\d{1,2}):"
    r"(?P<seconds>\d{1,2})[\.,](?P<fraction>\d{1,3})$"
)
RESOLUTION_RE = re.compile(r"^(?P<width>[1-9]\d*)x(?P<height>[1-9]\d*)$")
SVG_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
SVG_TOKEN_RE = re.compile(rf"[AaCcHhLlMmQqSsTtVvZz]|{SVG_NUMBER}")
SVG_COMMANDS = set("AaCcHhLlMmQqSsTtVvZz")
# Keep the embedded SVG Logo at its source aspect ratio. A renderer-specific
# horizontal compensation can still be requested explicitly through the CLI.
DEFAULT_LOGO_RENDER_SCALE_X = 1.0
DEFAULT_WATERMARK_TEXT = "手工川工作室 Agent 字幕组"
VISUAL_STYLES = ("elegant", "classic")
WATERMARK_STYLES = (
    "minimal",
    "cinematic_serif",
    "soft_glow",
    "glass",
    "signature",
    "gold_title",
)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"error: {message}")


def profile_path_candidates() -> Iterable[Path]:
    """Yield the shared Profile locations used by Skill Runtime."""

    seen: set[Path] = set()
    configured_names = (
        "SKILL_PROFILE_PATH",
        "SKILLS_PROFILE_PATH",
        "LOVSTUDIO_SKILLS_PROFILE",
    )
    for name in configured_names:
        value = os.environ.get(name)
        if value:
            path = Path(os.path.expandvars(os.path.expanduser(value))).resolve()
            if path not in seen:
                seen.add(path)
                yield path
    if any(os.environ.get(name) for name in configured_names):
        return

    home = Path.home()
    for path in (
        home / ".lovstudio" / "skills" / "profile.json",
        home / ".skill-publisher" / "skills" / "profile.json",
        home / ".config" / "agent-skills" / "profile.json",
    ):
        if path not in seen:
            seen.add(path)
            yield path


def profile_logo_value(profile: Dict[str, Any]) -> Any:
    brand = profile.get("brand", {})
    if not isinstance(brand, dict):
        return None
    logo = brand.get("logo")
    if isinstance(logo, dict):
        for key in ("path", "src", "light", "dark", "default"):
            if logo.get(key):
                return logo[key]
        return None
    return logo


def profile_watermark_logo_enabled(profile: Dict[str, Any]) -> Optional[bool]:
    skills = profile.get("skills", {})
    if not isinstance(skills, dict):
        return None
    skill = skills.get("lov-subtitle-freedom-skill", {})
    if not isinstance(skill, dict):
        return None
    records = skill.get("records", {})
    watermark = records.get("watermark", {}) if isinstance(records, dict) else {}
    if not isinstance(watermark, dict) or "logo_enabled" not in watermark:
        return None
    return bool(watermark["logo_enabled"])


def resolve_watermark_logo(explicit: Optional[Path]) -> Optional[Path]:
    """Resolve an explicitly enabled SVG logo from the request or shared Profile."""

    value: Any = explicit
    if value is None:
        value = os.environ.get("SKILL_BRAND_LOGO") or os.environ.get("SKILL_WATERMARK_LOGO")
    if value is None:
        for profile_path in profile_path_candidates():
            if not profile_path.is_file():
                continue
            try:
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(profile, dict):
                logo_enabled = profile_watermark_logo_enabled(profile)
                if logo_enabled is False:
                    return None
                value = profile_logo_value(profile)
            if value:
                break
    if value is None:
        return None
    path = Path(os.path.expandvars(os.path.expanduser(str(value)))).resolve()
    if path.suffix.lower() != ".svg":
        fail(f"watermark logo must be an SVG file: {path}")
    if not path.is_file():
        fail(f"watermark logo does not exist: {path}")
    return path


def svg_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def svg_fill_value(element: ET.Element, inherited: str) -> str:
    value = element.get("fill")
    style = element.get("style", "")
    if value is None:
        style_match = re.search(r"(?:^|;)\s*fill\s*:\s*([^;]+)", style)
        value = style_match.group(1).strip() if style_match else inherited
    return value.strip()


def svg_path_commands(data: str) -> List[Tuple[str, Tuple[float, ...]]]:
    """Parse the SVG path subset used by brand marks into ASS drawing ops."""

    tokens = SVG_TOKEN_RE.findall(data)
    residue = SVG_TOKEN_RE.sub("", data)
    residue = re.sub(r"[\s,]+", "", residue)
    if residue:
        fail(f"unsupported SVG path syntax near {residue[:24]!r}")

    argument_counts = {
        "M": 2,
        "L": 2,
        "H": 1,
        "V": 1,
        "C": 6,
        "S": 4,
        "Q": 4,
        "T": 2,
    }
    commands: List[Tuple[str, Tuple[float, ...]]] = []
    current = (0.0, 0.0)
    subpath_start = current
    previous_cubic: Optional[Tuple[float, float]] = None
    previous_quadratic: Optional[Tuple[float, float]] = None
    command: Optional[str] = None
    index = 0

    def take(count: int) -> List[float]:
        nonlocal index
        if index + count > len(tokens):
            fail(f"incomplete SVG path command {command!r}")
        values: List[float] = []
        for token in tokens[index : index + count]:
            if token in SVG_COMMANDS:
                fail(f"incomplete SVG path command {command!r}")
            values.append(float(token))
        index += count
        return values

    def point(x: float, y: float, relative: bool) -> Tuple[float, float]:
        return (x + current[0], y + current[1]) if relative else (x, y)

    def quadratic_as_cubic(control: Tuple[float, float], end: Tuple[float, float]) -> Tuple[float, ...]:
        first = (
            current[0] + (2.0 / 3.0) * (control[0] - current[0]),
            current[1] + (2.0 / 3.0) * (control[1] - current[1]),
        )
        second = (
            end[0] + (2.0 / 3.0) * (control[0] - end[0]),
            end[1] + (2.0 / 3.0) * (control[1] - end[1]),
        )
        return first + second + end

    while index < len(tokens):
        if tokens[index] in SVG_COMMANDS:
            command = tokens[index]
            index += 1
            if command.upper() == "Z":
                commands.append(("c", ()))
                current = subpath_start
                previous_cubic = None
                previous_quadratic = None
                command = None
                continue
        if command is None:
            fail("SVG path contains coordinates without a command")
        upper = command.upper()
        if upper not in argument_counts:
            fail(f"SVG path command {command!r} is not supported")
        values = take(argument_counts[upper])
        relative = command.islower()

        if upper == "M":
            next_point = point(values[0], values[1], relative)
            commands.append(("m", next_point))
            current = next_point
            subpath_start = current
            previous_cubic = None
            previous_quadratic = None
            command = "l" if relative else "L"
        elif upper == "L":
            next_point = point(values[0], values[1], relative)
            commands.append(("l", next_point))
            current = next_point
            previous_cubic = None
            previous_quadratic = None
        elif upper == "H":
            x = values[0] + current[0] if relative else values[0]
            current = (x, current[1])
            commands.append(("l", current))
            previous_cubic = None
            previous_quadratic = None
        elif upper == "V":
            y = values[0] + current[1] if relative else values[0]
            current = (current[0], y)
            commands.append(("l", current))
            previous_cubic = None
            previous_quadratic = None
        elif upper == "C":
            control_1 = point(values[0], values[1], relative)
            control_2 = point(values[2], values[3], relative)
            end = point(values[4], values[5], relative)
            commands.append(("b", control_1 + control_2 + end))
            current = end
            previous_cubic = control_2
            previous_quadratic = None
        elif upper == "S":
            control_1 = (
                (2 * current[0] - previous_cubic[0], 2 * current[1] - previous_cubic[1])
                if previous_cubic is not None
                else current
            )
            control_2 = point(values[0], values[1], relative)
            end = point(values[2], values[3], relative)
            commands.append(("b", control_1 + control_2 + end))
            current = end
            previous_cubic = control_2
            previous_quadratic = None
        elif upper == "Q":
            control = point(values[0], values[1], relative)
            end = point(values[2], values[3], relative)
            commands.append(("b", quadratic_as_cubic(control, end)))
            current = end
            previous_quadratic = control
            previous_cubic = None
        elif upper == "T":
            control = (
                (2 * current[0] - previous_quadratic[0], 2 * current[1] - previous_quadratic[1])
                if previous_quadratic is not None
                else current
            )
            end = point(values[0], values[1], relative)
            commands.append(("b", quadratic_as_cubic(control, end)))
            current = end
            previous_quadratic = control
            previous_cubic = None

    if not commands:
        fail("SVG path is empty")
    return commands


def load_svg_logo(path: Path) -> Dict[str, Any]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        fail(f"watermark logo is not a readable SVG: {path} ({exc})")

    view_box = root.get("viewBox") or root.get("viewbox")
    if not view_box:
        fail(f"watermark logo SVG requires a viewBox: {path}")
    view_values = [float(value) for value in re.findall(SVG_NUMBER, view_box)]
    if len(view_values) != 4 or view_values[2] <= 0 or view_values[3] <= 0:
        fail(f"watermark logo SVG has an invalid viewBox: {path}")

    paths: List[Dict[str, Any]] = []

    def visit(element: ET.Element, inherited_fill: str = "#FFFFFF") -> None:
        fill = svg_fill_value(element, inherited_fill)
        if svg_local_name(element.tag) == "path" and element.get("d"):
            if fill.lower() != "none":
                paths.append({"fill": fill, "commands": svg_path_commands(element.get("d", ""))})
        for child in element:
            visit(child, fill)

    visit(root)
    if not paths:
        fail(f"watermark logo SVG contains no filled path: {path}")
    return {"path": str(path), "view_box": tuple(view_values), "paths": paths}


def format_drawing_number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".") or "0"


def scaled_ass_drawing(
    commands: Iterable[Tuple[str, Tuple[float, ...]]],
    view_box: Tuple[float, float, float, float],
    target_height: float,
    offset: Tuple[float, float] = (0.0, 0.0),
    scale_x: float = 1.0,
) -> str:
    view_x, view_y, _view_width, view_height = view_box
    scale = target_height / view_height
    offset_x, offset_y = offset
    rendered: List[str] = []
    for operation, values in commands:
        if operation == "c":
            rendered.append("c")
            continue
        mapped: List[str] = []
        for index, value in enumerate(values):
            if index % 2 == 0:
                mapped.append(
                    format_drawing_number(
                        (value - view_x) * scale * scale_x + offset_x
                    )
                )
            else:
                mapped.append(format_drawing_number((value - view_y) * scale + offset_y))
        rendered.append(operation + " " + " ".join(mapped))
    return " ".join(rendered)


def parse_time(value: Any) -> int:
    """Return milliseconds for an SRT-like timestamp or numeric seconds."""

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
    milliseconds = (
        ((hours * 60 + minutes) * 60 + seconds) * 1000 + int(fraction)
    )
    return milliseconds


def ass_time(milliseconds: int) -> str:
    """ASS timestamps use H:MM:SS.cc (centiseconds)."""

    centiseconds = max(0, int(round(milliseconds / 10)))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def ass_color(value: Any, alpha: str = "00") -> str:
    """Convert #RRGGBB to ASS's &HAABBGGRR& representation."""

    text = str(value or "#FFFFFF").strip().lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", text):
        fail(f"invalid color {value!r}; expected #RRGGBB")
    red, green, blue = text[0:2], text[2:4], text[4:6]
    if not re.fullmatch(r"[0-9A-Fa-f]{2}", alpha):
        fail(f"invalid alpha {alpha!r}; expected two hexadecimal digits")
    return f"&H{alpha.upper()}{blue.upper()}{green.upper()}{red.upper()}&"


def plain_ass_text(value: Any) -> str:
    """Escape text and map line breaks to ASS's explicit line-break marker."""

    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    # Art-cue JSON is often hand-written with a literal backslash-n.
    text = text.replace("\\N", "\n").replace("\\n", "\n")
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{").replace("}", "\\}")
    return text.replace("\n", r"\N")


def srt_ass_text(value: Any) -> str:
    """Preserve the common italic/bold tags found in SRT files."""

    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    replacements = (
        (r"<i>", r"{\i1}"),
        (r"</i>", r"{\i0}"),
        (r"<b>", r"{\b1}"),
        (r"</b>", r"{\b0}"),
        (r"<u>", r"{\u1}"),
        (r"</u>", r"{\u0}"),
    )
    for source, target in replacements:
        text = re.sub(
            source,
            lambda _match, replacement=target: replacement,
            text,
            flags=re.IGNORECASE,
        )

    # Protect the ASS tags we inserted, then escape literal braces/backslashes.
    placeholders: Dict[str, str] = {}

    def hold(match: re.Match[str]) -> str:
        token = f"\x00ASS{len(placeholders)}\x00"
        placeholders[token] = match.group(0)
        return token

    text = re.sub(r"\{\\[ibu][01]\}", hold, text)
    text = plain_ass_text(text)
    for token, replacement in placeholders.items():
        text = text.replace(plain_ass_text(token), replacement)
    return text


def load_art_cues(path: Path) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(read_utf8(path))
    except json.JSONDecodeError as exc:
        fail(f"art cue JSON is invalid: {exc}")

    if isinstance(payload, dict):
        payload = payload.get("items", payload.get("cues", []))
    if not isinstance(payload, list):
        fail("art cue JSON must be a list or an object with an items/cues list")

    result: List[Dict[str, Any]] = []
    for index, raw in enumerate(payload, start=1):
        if not isinstance(raw, dict):
            fail(f"art cue #{index} must be an object")
        if "start" not in raw or "end" not in raw or "text" not in raw:
            fail(f"art cue #{index} requires start, end and text")
        start = parse_time(raw["start"])
        end = parse_time(raw["end"])
        if end <= start:
            fail(f"art cue #{index} must end after it starts")
        item = dict(raw)
        item["_start_ms"] = start
        item["_end_ms"] = end
        result.append(item)
    return result


def parse_resolution(value: str) -> Tuple[int, int]:
    match = RESOLUTION_RE.fullmatch(value.strip())
    if not match:
        fail(f"invalid resolution {value!r}; expected WIDTHxHEIGHT")
    return int(match.group("width")), int(match.group("height"))


def as_number(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        fail(f"expected a number, got {value!r}")


def estimate_text_width(value: Any, font_size: float, spacing: float) -> float:
    """Estimate a mixed CJK/Latin ASS text width for shared centering anchors."""
    text = str(value).replace("\r", "").replace("\n", "")
    width = 0.0
    for char in text:
        if char.isspace():
            ratio = 0.35
        elif unicodedata.east_asian_width(char) in {"W", "F"}:
            ratio = 1.0
        elif char.isupper():
            ratio = 0.68
        elif char.islower():
            ratio = 0.52
        elif char.isdigit():
            ratio = 0.56
        else:
            ratio = 0.45
        width += font_size * ratio
    if text:
        width += max(0, len(text) - 1) * spacing
    return max(1.0, width)


def override_tags(item: Dict[str, Any]) -> str:
    tags: List[str] = []
    position = item.get("position", item.get("pos"))
    if isinstance(position, (list, tuple)) and len(position) == 2:
        x = as_number(position[0], 0)
        y = as_number(position[1], 0)
        tags.append(f"\\pos({x:g},{y:g})")

    alignment_value = item.get("align", item.get("alignment"))
    if alignment_value is not None:
        try:
            align = int(alignment_value)
        except (TypeError, ValueError):
            fail(f"invalid art alignment: {alignment_value!r}")
        if align not in range(1, 10):
            fail("art alignment must be an ASS value from 1 to 9")
        tags.append(f"\\an{align}")

    if item.get("font_size") is not None:
        tags.append(f"\\fs{as_number(item['font_size'], 64):g}")
    if item.get("font_name"):
        tags.append(f"\\fn{item['font_name']}")
    if item.get("spacing") is not None:
        tags.append(f"\\fsp{as_number(item['spacing'], 0):g}")
    if item.get("color") or item.get("primary_color"):
        tags.append(
            "\\c"
            + ass_color(item.get("color", item.get("primary_color")), str(item.get("alpha", "00")))
        )
    if item.get("outline_color"):
        tags.append("\\3c" + ass_color(item["outline_color"], str(item.get("outline_alpha", "00"))))
    if item.get("outline") is not None:
        tags.append(f"\\bord{as_number(item['outline'], 2):g}")
    if item.get("shadow") is not None:
        tags.append(f"\\shad{as_number(item['shadow'], 1):g}")
    if item.get("bold") is not None:
        tags.append("\\b1" if bool(item["bold"]) else "\\b0")
    if item.get("italic") is not None:
        tags.append("\\i1" if bool(item["italic"]) else "\\i0")
    if item.get("scale_x") is not None:
        tags.append(f"\\fscx{as_number(item['scale_x'], 100):g}")
    if item.get("scale_y") is not None:
        tags.append(f"\\fscy{as_number(item['scale_y'], 100):g}")
    if item.get("rotation") is not None:
        tags.append(f"\\frz{as_number(item['rotation'], 0):g}")
    if item.get("blur") is not None:
        tags.append(f"\\blur{as_number(item['blur'], 0):g}")

    move = item.get("move")
    if isinstance(move, (list, tuple)) and len(move) in (4, 6):
        values = [as_number(part, 0) for part in move]
        rendered = ",".join(f"{part:g}" for part in values)
        tags.append(f"\\move({rendered})")

    fade = item.get("fade")
    if isinstance(fade, (list, tuple)) and len(fade) == 2:
        fade_in, fade_out = fade
    else:
        fade_in = item.get("fade_in")
        fade_out = item.get("fade_out")
    if fade_in is not None or fade_out is not None:
        tags.append(f"\\fad({int(as_number(fade_in, 0))},{int(as_number(fade_out, 0))})")

    transform = item.get("transform")
    if transform:
        # Advanced ASS transform tags remain opt-in and are passed through
        # after the simple, validated tags above.
        tags.append(f"\\t({transform})")

    return "{" + "".join(tags) + "}" if tags else ""


def style_line(
    name: str,
    font: str,
    size: int,
    primary: str,
    outline: str,
    back: str,
    bold: int,
    alignment: int,
    border: int,
    shadow: int,
    border_style: int = 1,
) -> str:
    return (
        f"Style: {name},{font},{size},{primary},&H000000FF,{outline},{back},"
        f"{bold},0,0,0,100,100,0,0,{border_style},{border},{shadow},{alignment},60,60,42,1"
    )


def visual_style_defaults(style: str) -> Dict[str, Any]:
    if style == "elegant":
        return {
            "art_font": "Avenir Next",
            "watermark_font": "Avenir Next",
            "art_size": 54,
            "art_primary": ("#E8DDCA", "00"),
            "art_outline": ("#2A2724", "00"),
            "art_back": ("#000000", "FF"),
            "art_bold": 0,
            "art_border": 1,
            "art_shadow": 1,
            "card_size": 44,
            "watermark_size": 18,
            "watermark_color": "#E9E3D8",
            "watermark_alpha": "A6",
            "watermark_margin": 48,
            "watermark_spacing": 0.3,
            "watermark_outline": 0,
            "watermark_shadow": 1,
            "watermark_fade_in": 700,
            "watermark_fade_out": 1000,
        }
    return {
        "art_font": "Arial",
        "watermark_font": "Arial",
        "art_size": 72,
        "art_primary": ("#F7D774", "00"),
        "art_outline": ("#111111", "00"),
        "art_back": ("#000000", "A0"),
        "art_bold": 1,
        "art_border": 3,
        "art_shadow": 2,
        "card_size": 58,
        "watermark_size": 24,
        "watermark_color": "#FFFFFF",
        "watermark_alpha": "80",
        "watermark_margin": 36,
        "watermark_spacing": 0,
        "watermark_outline": 1,
        "watermark_shadow": 0,
        "watermark_fade_in": 500,
        "watermark_fade_out": 800,
    }


def watermark_style_defaults(style: str) -> Dict[str, Any]:
    styles: Dict[str, Dict[str, Any]] = {
        "minimal": {
            "font_name": "Avenir Next",
            "font_size": 23,
            "color": "#F6F2EB",
            "alpha": "28",
            "margin": 48,
            "spacing": 0.2,
            "outline": 0,
            "shadow": 2,
            "fade_in": 500,
            "fade_out": 800,
            "back_alpha": "FF",
            "border_style": 1,
            "blur": 0,
            "rule": False,
        },
        "cinematic_serif": {
            "font_name": "Baskerville",
            "font_size": 24,
            "color": "#E4C58F",
            "alpha": "08",
            "margin": 48,
            "spacing": 1.2,
            "outline": 1,
            "shadow": 2,
            "fade_in": 500,
            "fade_out": 800,
            "back_alpha": "FF",
            "border_style": 1,
            "blur": 0,
            "rule": True,
            "rule_color": "#D9B375",
            "rule_alpha": "10",
            "rule_width": 300,
            "rule_height": 2,
            "rule_gap": 36,
        },
        "soft_glow": {
            "font_name": "Avenir Next",
            "font_size": 27,
            "color": "#F4F7FF",
            "alpha": "08",
            "margin": 48,
            "spacing": 0.2,
            "outline": 0,
            "shadow": 1,
            "fade_in": 600,
            "fade_out": 900,
            "back_alpha": "FF",
            "border_style": 1,
            "blur": 2.5,
            "rule": False,
        },
        "glass": {
            "font_name": "Avenir Next",
            "font_size": 23,
            "color": "#F5F2EC",
            "alpha": "00",
            "margin": 48,
            "spacing": 0.1,
            "outline": 0,
            "shadow": 0,
            "fade_in": 300,
            "fade_out": 500,
            "back_alpha": "75",
            "border_style": 3,
            "blur": 0,
            "rule": False,
        },
        "signature": {
            "font_name": "Avenir Next",
            "font_size": 26,
            "color": "#E8EDDA",
            "alpha": "10",
            "margin": 48,
            "spacing": 0.8,
            "outline": 0,
            "shadow": 1,
            "fade_in": 500,
            "fade_out": 800,
            "back_alpha": "FF",
            "border_style": 1,
            "blur": 0,
            "rule": True,
            "rule_color": "#CFDCAD",
            "rule_alpha": "18",
            "rule_width": 300,
            "rule_height": 2,
            "rule_gap": 36,
        },
        "gold_title": {
            "font_name": "Hiragino Mincho Pro",
            "font_size": 34,
            "color": "#F0C675",
            "alpha": "05",
            "margin": 48,
            "spacing": 2,
            "outline": 0,
            "shadow": 2,
            "fade_in": 650,
            "fade_out": 950,
            "back_alpha": "FF",
            "border_style": 1,
            "blur": 0,
            "rule": True,
            "rule_color": "#E0B66D",
            "rule_alpha": "12",
            "rule_width": 260,
            "rule_height": 2,
            "rule_gap": 42,
        },
    }
    try:
        result = dict(styles[style])
        result.setdefault("logo_height", 24)
        result.setdefault("logo_gap", 8)
        result.setdefault("logo_scale_x", DEFAULT_LOGO_RENDER_SCALE_X)
        result.setdefault("logo_vertical_offset", 0)
        return result
    except KeyError:
        fail(
            f"unsupported watermark_style {style!r}; "
            f"choose one of {', '.join(WATERMARK_STYLES)}"
        )


def ass_header(
    width: int,
    height: int,
    font: str,
    visual_style: str,
    art_font: str,
    watermark_font: str,
    watermark_style: str,
) -> List[str]:
    style_defaults = visual_style_defaults(visual_style)
    watermark_defaults = watermark_style_defaults(watermark_style)
    default_primary = ass_color("#FFFFFF")
    default_outline = ass_color("#1E1E1E")
    default_back = ass_color("#000000", "96")
    art_primary = ass_color(*style_defaults["art_primary"])
    art_outline = ass_color(*style_defaults["art_outline"])
    art_back = ass_color(*style_defaults["art_back"])
    card_primary = ass_color("#F1EDE5")
    watermark_primary = ass_color(
        watermark_defaults["color"], watermark_defaults["alpha"]
    )
    watermark_outline = ass_color("#000000", "C0")
    watermark_back = ass_color("#000000", watermark_defaults["back_alpha"])
    return [
        "[Script Info]",
        "; Generated by lov-subtitle-freedom-skill.",
        "ScriptType: v4.00+",
        "Collisions: Normal",
        "PlayDepth: 0",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        style_line("Default", font, 58, default_primary, default_outline, default_back, 0, 2, 2, 1),
        style_line(
            "ArtTitle",
            art_font or style_defaults["art_font"],
            style_defaults["art_size"],
            art_primary,
            art_outline,
            art_back,
            style_defaults["art_bold"],
            5,
            style_defaults["art_border"],
            style_defaults["art_shadow"],
        ),
        style_line(
            "SceneCard",
            art_font or style_defaults["art_font"],
            style_defaults["card_size"],
            card_primary,
            art_outline,
            art_back,
            0,
            5,
            style_defaults["art_border"],
            style_defaults["art_shadow"],
        ),
        style_line(
            "Watermark",
            watermark_font or watermark_defaults["font_name"],
            watermark_defaults["font_size"],
            watermark_primary,
            watermark_outline,
            watermark_back,
            0,
            2,
            watermark_defaults["outline"],
            watermark_defaults["shadow"],
            watermark_defaults["border_style"],
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]


def dialogue_line(layer: int, start: int, end: int, style: str, text: str) -> str:
    return f"Dialogue: {layer},{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{text}"


def write_ass(
    cues: Iterable[Cue],
    art_cues: Iterable[Dict[str, Any]],
    output: Path,
    width: int,
    height: int,
    font: str,
    visual_style: str,
    art_font: str,
    watermark_font: str,
    watermark_style: str,
    watermark: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    events: List[Tuple[int, int, int, str]] = []
    sequence = 0
    cue_count = 0
    movie_end = 0
    for cue in cues:
        sequence += 1
        cue_count += 1
        start_text, end_text = re.split(r"\s+-->\s+", cue.timing, maxsplit=1)
        start = parse_time(start_text)
        end = parse_time(end_text.split()[0])
        movie_end = max(movie_end, end)
        events.append((start, 0, sequence, dialogue_line(0, start, end, "Default", srt_ass_text(cue.body))))

    art_count = 0
    for item in art_cues:
        sequence += 1
        art_count += 1
        style = str(item.get("style", "ArtTitle"))
        if style not in {"Default", "ArtTitle", "SceneCard", "Watermark"}:
            fail(
                f"unsupported art style {style!r}; "
                "use Default, ArtTitle, SceneCard or Watermark"
            )
        tags = override_tags(item)
        text = tags + plain_ass_text(item["text"])
        line = dialogue_line(10, item["_start_ms"], item["_end_ms"], style, text)
        events.append((item["_start_ms"], 10, sequence, line))

    watermark_count = 0
    watermark_logo_count = 0
    watermark_rule_count = 0
    watermark_logo_path: Optional[str] = None
    if watermark is not None:
        watermark_text = str(watermark.get("text", "")).strip()
        if watermark_text:
            watermark_count = 1
            sequence += 1
            watermark_start = int(watermark.get("_start_ms", 0))
            watermark_end = int(watermark.get("_end_ms", movie_end))
            if watermark_end <= watermark_start:
                fail("watermark must end after it starts")
            tags = override_tags(watermark)
            watermark_content = plain_ass_text(watermark_text)
            logo = watermark.get("logo")
            if isinstance(logo, dict):
                watermark_tags = dict(watermark)
                # Some renderers paint the vector before applying inline shadow
                # overrides. Keep the Logo pass shadow-free and restore the
                # text shadow after the transparent spacer.
                watermark_tags["shadow"] = 0
                tags = override_tags(watermark_tags)
                try:
                    view_box = tuple(float(value) for value in logo["view_box"])
                    logo_height = float(watermark["logo_height"])
                    logo_x, logo_y = [
                        float(value) for value in watermark["logo_offset"]
                    ]
                    logo_scale_x = float(watermark.get("logo_scale_x", 1))
                    logo_alpha = str(watermark.get("alpha", "00"))
                except (KeyError, TypeError, ValueError):
                    fail("watermark logo requires a valid viewBox, size and offset")
                if len(view_box) != 4 or logo_height <= 0 or logo_scale_x <= 0:
                    fail("watermark logo dimensions must be positive")
                watermark_logo_path = str(logo.get("path", "")) or None
                content_max_x = max(
                    (
                        value
                        for logo_path in logo.get("paths", [])
                        if isinstance(logo_path, dict)
                        for operation, values in logo_path.get("commands", [])
                        for index, value in enumerate(values)
                        if operation != "c" and index % 2 == 0
                    ),
                    default=view_box[0],
                )
                normalized_max_x = (
                    (content_max_x - view_box[0]) * logo_height / view_box[3]
                )
                # Keep the Logo's right edge stable when an explicit renderer
                # compensation is requested.
                logo_x += normalized_max_x * (1 - logo_scale_x)
                drawing_parts: List[str] = []
                logo_color: Optional[str] = None
                for logo_path in logo.get("paths", []):
                    if not isinstance(logo_path, dict):
                        continue
                    try:
                        drawing = scaled_ass_drawing(
                            logo_path["commands"],
                            view_box,
                            logo_height,
                            offset=(logo_x, logo_y),
                            scale_x=logo_scale_x,
                        )
                        logo_color = ass_color(
                            watermark.get("logo_color", watermark.get("color", logo_path["fill"])),
                            logo_alpha,
                        )
                    except (KeyError, TypeError, ValueError):
                        fail("watermark logo contains an invalid path or fill color")
                    if not drawing:
                        continue
                    drawing_parts.append(drawing)
                    watermark_logo_count += 1
                if drawing_parts:
                    if logo_color is None:
                        fail("watermark logo contains no drawable filled paths")
                    text_color = ass_color(
                        watermark.get("color", "#FFFFFF"),
                        str(watermark.get("alpha", "00")),
                    )
                    text_outline = as_number(watermark.get("outline", 0), 0)
                    text_shadow = as_number(watermark.get("shadow", 0), 0)
                    # The renderer already advances past the vector drawing.
                    # Only reserve the requested visual gap; reserving the
                    # full Logo width here doubles the distance in players
                    # that honor drawing advances.
                    spacer_width = float(watermark.get("logo_gap", 8))
                    spacer_base_width = estimate_text_width(
                        "M",
                        float(watermark.get("font_size", 30)),
                        0,
                    )
                    spacer_content = "{\\p0}"
                    if spacer_width > 0:
                        spacer_scale_x = 100 * spacer_width / max(spacer_base_width, 1.0)
                        spacer_content = (
                            f"{{\\p0\\alpha&HFF&\\fscx{spacer_scale_x:g}}}M"
                        )
                    watermark_content = (
                        f"{{\\p1\\1c{logo_color}\\bord0\\shad0}}"
                        + " ".join(drawing_parts)
                        + spacer_content
                        + f"{{\\alpha&H{watermark.get('alpha', '00')}&\\fscx100"
                        f"\\c{text_color}\\bord{text_outline:g}\\shad{text_shadow:g}}}"
                        + watermark_content
                    )
            line = dialogue_line(
                20,
                watermark_start,
                watermark_end,
                "Watermark",
                tags + watermark_content,
            )
            events.append((watermark_start, 20, sequence, line))
            if watermark.get("rule"):
                try:
                    rule_anchor = watermark.get("rule_position", watermark["position"])
                    x, y = [float(value) for value in rule_anchor]
                    rule_width = float(watermark["rule_width"])
                    rule_height = float(watermark.get("rule_height", 2))
                    rule_gap = float(watermark.get("rule_gap", 36))
                except (KeyError, TypeError, ValueError):
                    fail("watermark rule requires numeric position and dimensions")
                if rule_width <= 0 or rule_height <= 0 or rule_gap < 0:
                    fail("watermark rule dimensions must be positive")
                rule_color = ass_color(
                    watermark.get("rule_color", watermark.get("color", "#FFFFFF")),
                    str(watermark.get("rule_alpha", watermark.get("alpha", "00"))),
                )
                # The Watermark style is bottom-center.  Keep the vector event on
                # the same center anchor as the brand text; this avoids depending
                # on how a player applies per-event alignment to ASS drawings.
                rule_x = x
                rule_y = y - rule_gap
                rule_text = (
                    f"{{\\an2\\pos({rule_x:g},{rule_y:g})\\c{rule_color}"
                    f"\\bord0\\shad0\\p1}}"
                    f"m 0 0 l {rule_width:g} 0 l {rule_width:g} {rule_height:g} "
                    f"l 0 {rule_height:g}{{\\p0}}"
                )
                sequence += 1
                watermark_rule_count = 1
                events.append(
                    (
                        watermark_start,
                        19,
                        sequence,
                        dialogue_line(
                            19,
                            watermark_start,
                            watermark_end,
                            "Watermark",
                            rule_text,
                        ),
                    )
                )

    events.sort(key=lambda event: (event[0], event[1], event[2]))
    lines = ass_header(
        width,
        height,
        font,
        visual_style,
        art_font,
        watermark_font,
        watermark_style,
    )
    lines.extend(event[3] for event in events)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "output": str(output),
        "cues": cue_count,
        "art_cues": art_count,
        "watermark": watermark_count,
        "watermark_logo": watermark_logo_count,
        "watermark_logo_path": watermark_logo_path,
        "watermark_rule": watermark_rule_count,
        "watermark_style": watermark_style,
        "resolution": f"{width}x{height}",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 SRT file")
    parser.add_argument("--output", required=True, type=Path, help="ASS output path")
    parser.add_argument(
        "--art-cues",
        type=Path,
        action="append",
        help="JSON list of timed art/scene-card cues; repeat to merge files",
    )
    parser.add_argument("--resolution", default="1920x1080", help="ASS PlayRes, e.g. 1920x1080")
    parser.add_argument("--font", default="Arial", help="fallback font family")
    parser.add_argument(
        "--visual-style",
        choices=VISUAL_STYLES,
        default="elegant",
        help="artistic visual profile; elegant is restrained, classic is the legacy look",
    )
    parser.add_argument(
        "--art-font",
        default=None,
        help="font for ArtTitle/SceneCard; defaults by --visual-style",
    )
    watermark_group = parser.add_mutually_exclusive_group()
    watermark_group.add_argument(
        "--watermark",
        dest="watermark_enabled",
        action="store_true",
        help=f"add the default/custom brand watermark (default: {DEFAULT_WATERMARK_TEXT})",
    )
    watermark_group.add_argument(
        "--no-watermark",
        dest="watermark_enabled",
        action="store_false",
        help="disable the brand watermark",
    )
    parser.set_defaults(watermark_enabled=True)
    parser.add_argument(
        "--watermark-text",
        default=DEFAULT_WATERMARK_TEXT,
        help="brand text shown in the lower-right corner",
    )
    parser.add_argument(
        "--watermark-logo",
        type=Path,
        default=None,
        help="optional SVG logo for the watermark; explicit path enables the Logo",
    )
    parser.add_argument(
        "--no-watermark-logo",
        action="store_true",
        help="keep the text watermark and rule while omitting its optional Logo",
    )
    parser.add_argument(
        "--watermark-end",
        default=None,
        help="watermark end time as HH:MM:SS.mmm; defaults to the last subtitle cue",
    )
    parser.add_argument(
        "--watermark-logo-height",
        type=int,
        default=None,
        help="watermark logo height in ASS pixels; defaults by watermark style",
    )
    parser.add_argument(
        "--watermark-logo-scale-x",
        type=float,
        default=None,
        help="horizontal scale for the embedded Logo; default preserves source aspect ratio",
    )
    parser.add_argument(
        "--watermark-logo-gap",
        type=float,
        default=None,
        help="gap in ASS pixels between the embedded Logo and brand text; default 8",
    )
    parser.add_argument(
        "--watermark-logo-offset-y",
        type=float,
        default=None,
        help="vertical offset in ASS pixels for the embedded Logo; default 0",
    )
    parser.add_argument(
        "--watermark-font",
        default=None,
        help="watermark font; defaults by --watermark-style",
    )
    parser.add_argument(
        "--watermark-style",
        choices=WATERMARK_STYLES,
        default="cinematic_serif",
        help="watermark visual direction; default is B/cinematic_serif",
    )
    parser.add_argument(
        "--watermark-font-size",
        type=int,
        default=None,
        help="watermark font size; defaults by --watermark-style",
    )
    parser.add_argument(
        "--watermark-alpha",
        default=None,
        help="watermark primary alpha as two hex digits; defaults by --watermark-style",
    )
    parser.add_argument(
        "--watermark-margin",
        type=int,
        default=None,
        help="right/bottom watermark margin; defaults by --watermark-style",
    )
    parser.add_argument(
        "--watermark-spacing",
        type=float,
        default=None,
        help="watermark letter spacing; defaults by --watermark-style",
    )
    parser.add_argument("--force", action="store_true", help="replace an existing output")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if not input_path.is_file():
        fail(f"input file does not exist: {input_path}")
    if input_path == output_path:
        fail("output must differ from input")
    if output_path.exists() and not args.force:
        fail(f"output already exists; choose another path or pass --force: {output_path}")

    width, height = parse_resolution(args.resolution)
    try:
        cues = parse_srt(read_utf8(input_path))
    except ValueError as exc:
        fail(f"cannot parse input SRT: {exc}")
    if not cues:
        fail("input SRT contains no cues")
    art_cues: List[Dict[str, Any]] = []
    for art_path in args.art_cues or []:
        art_cues.extend(load_art_cues(art_path.expanduser().resolve()))
    style_defaults = visual_style_defaults(args.visual_style)
    watermark_defaults = watermark_style_defaults(args.watermark_style)
    art_font = str(args.art_font or style_defaults["art_font"])
    watermark_font = str(args.watermark_font or watermark_defaults["font_name"])
    watermark_logo_path = (
        None
        if not args.watermark_enabled or args.no_watermark_logo
        else resolve_watermark_logo(args.watermark_logo)
    )
    watermark_logo = load_svg_logo(watermark_logo_path) if watermark_logo_path else None
    watermark = None
    if args.watermark_enabled:
        watermark_text = str(args.watermark_text).strip()
        if not watermark_text:
            fail("--watermark-text must not be empty; use --no-watermark to disable it")
        watermark_font_size = args.watermark_font_size or watermark_defaults["font_size"]
        watermark_alpha = args.watermark_alpha or watermark_defaults["alpha"]
        watermark_margin = args.watermark_margin
        if watermark_margin is None:
            watermark_margin = watermark_defaults["margin"]
        watermark_spacing = args.watermark_spacing
        if watermark_spacing is None:
            watermark_spacing = watermark_defaults["spacing"]
        if watermark_font_size <= 0:
            fail("--watermark-font-size must be positive")
        if watermark_margin < 0:
            fail("--watermark-margin must not be negative")
        if not re.fullmatch(r"[0-9A-Fa-f]{2}", str(watermark_alpha)):
            fail("--watermark-alpha must be two hexadecimal digits")
        watermark_logo_height = args.watermark_logo_height
        if watermark_logo_height is None:
            watermark_logo_height = int(watermark_defaults["logo_height"])
        if watermark_logo_height <= 0:
            fail("--watermark-logo-height must be positive")
        watermark_logo_scale_x = args.watermark_logo_scale_x
        if watermark_logo_scale_x is None:
            watermark_logo_scale_x = float(watermark_defaults.get("logo_scale_x", 1))
        if watermark_logo_scale_x <= 0:
            fail("--watermark-logo-scale-x must be positive")
        watermark_logo_gap = args.watermark_logo_gap
        if watermark_logo_gap is None:
            watermark_logo_gap = float(watermark_defaults.get("logo_gap", 8))
        if watermark_logo_gap < 0:
            fail("--watermark-logo-gap must not be negative")
        watermark_logo_offset_y = args.watermark_logo_offset_y
        if watermark_logo_offset_y is None:
            watermark_logo_offset_y = float(
                watermark_defaults.get("logo_vertical_offset", 0)
            )
        watermark_text_width = estimate_text_width(
            watermark_text,
            float(watermark_font_size),
            float(watermark_spacing),
        )
        watermark_text_center_x = width - watermark_margin - (watermark_text_width / 2)
        watermark_center_x = watermark_text_center_x
        logo_width = 0.0
        logo_offset: Optional[List[float]] = None
        if watermark_logo is not None:
            view_x, _view_y, _view_width, view_height = watermark_logo["view_box"]
            content_min_x = min(
                (
                    value
                    for logo_path in watermark_logo.get("paths", [])
                    if isinstance(logo_path, dict)
                    for operation, values in logo_path.get("commands", [])
                    for index, value in enumerate(values)
                    if operation != "c" and index % 2 == 0
                ),
                default=view_x,
            )
            content_max_x = max(
                (
                    value
                    for logo_path in watermark_logo.get("paths", [])
                    if isinstance(logo_path, dict)
                    for operation, values in logo_path.get("commands", [])
                    for index, value in enumerate(values)
                    if operation != "c" and index % 2 == 0
                ),
                default=view_x,
            )
            logo_scale = float(watermark_logo_height) / float(view_height)
            logo_width = (content_max_x - content_min_x) * logo_scale * watermark_logo_scale_x
            watermark_center_x -= (logo_width + watermark_logo_gap) / 2
            logo_offset = [
                -(content_min_x - view_x) * logo_scale * watermark_logo_scale_x,
                watermark_logo_offset_y,
            ]
        watermark = {
            "text": watermark_text,
            "position": [watermark_center_x, height - watermark_margin],
            "rule_position": [watermark_text_center_x, height - watermark_margin],
            "align": 2,
            "font_name": watermark_font,
            "font_size": watermark_font_size,
            "spacing": watermark_spacing,
            "blur": watermark_defaults["blur"],
            "color": watermark_defaults["color"],
            "alpha": str(watermark_alpha),
            "outline": watermark_defaults["outline"],
            "shadow": watermark_defaults["shadow"],
            "fade_in": watermark_defaults["fade_in"],
            "fade_out": watermark_defaults["fade_out"],
            # Keep the cinematic rule above the text side of the lockup. When a
            # Logo is present, its independent left-side position is excluded.
            "rule": (
                watermark_defaults["rule"]
            ),
            "logo": watermark_logo,
            "logo_path": str(watermark_logo_path) if watermark_logo_path else None,
            "logo_color": watermark_defaults["color"],
            "logo_height": watermark_logo_height,
            "logo_gap": watermark_logo_gap,
            "logo_width": logo_width,
            "logo_scale_x": watermark_logo_scale_x,
            "logo_offset": logo_offset,
        }
        if args.watermark_end is not None:
            watermark_end = parse_time(args.watermark_end)
            if watermark_end <= 0:
                fail("--watermark-end must be positive")
            watermark["_end_ms"] = watermark_end
        for key in (
            "rule_color",
            "rule_alpha",
            "rule_width",
            "rule_height",
            "rule_gap",
        ):
            if key in watermark_defaults:
                watermark[key] = watermark_defaults[key]
        if watermark.get("rule") and "rule_width" in watermark_defaults:
            watermark["rule_width"] = min(
                float(watermark_defaults["rule_width"]),
                watermark_text_width * 0.86,
            )
    summary = write_ass(
        cues,
        art_cues,
        output_path,
        width,
        height,
        args.font,
        args.visual_style,
        art_font,
        watermark_font,
        args.watermark_style,
        watermark,
    )
    summary["watermark_text"] = watermark["text"] if watermark else None
    summary["visual_style"] = args.visual_style
    summary["art_font"] = art_font
    summary["watermark_font"] = watermark_font if watermark else None
    summary["watermark_logo_path"] = (
        str(watermark_logo_path) if watermark_logo_path else None
    )
    summary["watermark_estimated_text_width"] = (
        estimate_text_width(
            watermark["text"],
            float(watermark["font_size"]),
            float(watermark["spacing"]),
        )
        if watermark
        else None
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(1)
