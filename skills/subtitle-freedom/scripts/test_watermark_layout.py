#!/usr/bin/env python3
"""Regression tests for renderer-compatible ASS watermark centering."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


SCRIPT = Path(__file__).resolve().with_name("ass_styled_subtitle.py")
POSITION_RE = re.compile(r"\\pos\(([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?)\)")
ALIGNMENT_RE = re.compile(r"\\an([1-9])")
DRAWING_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)")


def fail(message: str) -> None:
    raise AssertionError(message)


def parse_event_x(line: str) -> tuple[int, float]:
    alignment = ALIGNMENT_RE.search(line)
    position = POSITION_RE.search(line)
    if alignment is None or position is None:
        fail(f"watermark event lacks alignment/position tags: {line}")
    return int(alignment.group(1)), float(position.group(1))


def assert_watermark_layout(
    path: Path,
    expected_text: str,
    expect_logo: bool = True,
    expect_rule: bool = True,
    expected_end: Optional[str] = None,
) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    style_line = next(
        (line for line in lines if line.startswith("Style: Watermark,")),
        None,
    )
    if style_line is None:
        fail("ASS output has no Watermark style")
    fields = style_line[len("Style: ") :].split(",")
    # Name, Fontname, Fontsize, ..., Shadow, Alignment, ...
    if len(fields) < 19 or fields[18] != "2":
        fail(f"Watermark style must use Alignment=2: {style_line}")
    rule = next((line for line in lines if line.startswith("Dialogue: 19,")), None)
    text = next((line for line in lines if line.startswith("Dialogue: 20,")), None)
    if text is None:
        fail("watermark output must contain text layer 20")
    if expect_rule and rule is None:
        fail("cinematic_serif output must contain rule layer 19")
    if not expect_rule and rule is not None:
        fail("watermark output unexpectedly contains a rule layer")
    logo = next((line for line in lines if line.startswith("Dialogue: 18,")), None)
    if expect_logo:
        if logo is not None:
            fail("logo watermark must use the shared text event, not a separate layer")
        if (
            text.count("\\p1") != 1
            or "\\p0" not in text
            or "\\fscx" not in text
        ):
            fail("logo watermark must embed the ASS vector in the shared text event")
        drawing = text.split("\\p1", 1)[1].split("}", 1)[1].split("{\\p0", 1)[0]
        coordinates = [float(value) for value in DRAWING_NUMBER_RE.findall(drawing)]
        if len(coordinates) < 4:
            fail("logo watermark drawing has too few coordinates")
        drawing_width = max(coordinates[0::2]) - min(coordinates[0::2])
        drawing_height = max(coordinates[1::2]) - min(coordinates[1::2])
        if drawing_height <= 0 or abs((drawing_width / drawing_height) - 1.0) > 0.1:
            fail(
                "embedded Logo changed aspect ratio: "
                f"width={drawing_width:g} height={drawing_height:g}"
            )
    elif logo is not None or "\\p1" in text:
        fail("watermark output unexpectedly contains a logo vector")
    if expected_text not in text:
        fail(f"watermark text missing from layer 20: {expected_text!r}")
    if expected_end is not None:
        fields = text.split(",", 3)
        if len(fields) < 3 or fields[2] != expected_end:
            fail(f"watermark end mismatch: expected={expected_end} event={text}")
    text_alignment, text_x = parse_event_x(text)
    if text_alignment != 2:
        fail(f"watermark text event must use \\an2: text={text}")
    if rule is not None:
        rule_alignment, rule_x = parse_event_x(rule)
        if rule_alignment != 2:
            fail(f"watermark rule event must use \\an2: rule={rule}")
        if expect_logo:
            if rule_x <= text_x:
                fail(
                    "watermark rule must align with the text side of a Logo lockup: "
                    f"rule={rule_x} lockup={text_x}"
                )
        elif abs(rule_x - text_x) > 0.001:
            fail(f"text-only watermark rule/text x anchors differ: rule={rule_x} text={text_x}")


def run_case(
    input_srt: Path,
    output_ass: Path,
    watermark_text: str,
    logo_path: Optional[Path] = None,
    profile_path: Optional[Path] = None,
    expect_logo: bool = True,
    expect_rule: bool = True,
    no_watermark_logo: bool = False,
    watermark_end: Optional[str] = None,
    expected_end: Optional[str] = None,
) -> None:
    command = [
        sys.executable,
        str(SCRIPT),
        "--input",
        str(input_srt),
        "--output",
        str(output_ass),
        "--resolution",
        "1920x1080",
        "--watermark-style",
        "cinematic_serif",
        "--watermark-text",
        watermark_text,
    ]
    if logo_path is not None:
        command.extend(["--watermark-logo", str(logo_path)])
    if no_watermark_logo:
        command.append("--no-watermark-logo")
    if watermark_end is not None:
        command.extend(["--watermark-end", watermark_end])
    environment = dict(os.environ)
    if profile_path is not None:
        environment["SKILL_PROFILE_PATH"] = str(profile_path)
    subprocess.run(
        command,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert_watermark_layout(
        output_ass,
        watermark_text,
        expect_logo,
        expect_rule,
        expected_end,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="lov-watermark-test-") as directory:
        root = Path(directory)
        input_srt = root / "input.srt"
        input_srt.write_text(
            "1\n00:00:00,000 --> 00:00:03,000\nA short test cue.\n",
            encoding="utf-8",
        )
        logo_path = root / "logo.svg"
        logo_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<path fill="#D97757" d="M10 10 L90 10 L90 90 L10 90 Z"/>'
            "</svg>\n",
            encoding="utf-8",
        )
        profile_path = root / "profile.json"
        profile_path.write_text(
            json.dumps({"brand": {"logo": str(logo_path)}}, ensure_ascii=False),
            encoding="utf-8",
        )
        profile_logo_disabled_path = root / "profile-logo-disabled.json"
        profile_logo_disabled_path.write_text(
            json.dumps(
                {
                    "brand": {"logo": str(logo_path)},
                    "skills": {
                        "lov-subtitle-freedom-skill": {
                            "records": {"watermark": {"logo_enabled": False}}
                        }
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        text_only_profile_path = root / "text-only-profile.json"
        text_only_profile_path.write_text(
            json.dumps({"brand": {}}, ensure_ascii=False),
            encoding="utf-8",
        )
        run_case(
            input_srt,
            root / "default-brand.ass",
            "手工川工作室 Agent 字幕组",
            profile_path=profile_path,
        )
        run_case(input_srt, root / "short-brand.ass", "手工川", logo_path=logo_path)
        run_case(
            input_srt,
            root / "long-brand.ass",
            "手工川工作室 Agent 字幕组特别版",
            logo_path=logo_path,
        )
        run_case(
            input_srt,
            root / "full-duration-brand.ass",
            "手工川",
            logo_path=logo_path,
            watermark_end="00:00:07.500",
            expected_end="0:00:07.50",
        )
        run_case(
            input_srt,
            root / "text-only-brand.ass",
            "手工川",
            profile_path=text_only_profile_path,
            expect_logo=False,
            expect_rule=True,
        )
        run_case(
            input_srt,
            root / "profile-logo-disabled.ass",
            "手工川",
            profile_path=profile_logo_disabled_path,
            expect_logo=False,
            expect_rule=True,
        )
        run_case(
            input_srt,
            root / "image-lockup-text.ass",
            "手工川",
            profile_path=profile_path,
            expect_logo=False,
            expect_rule=True,
            no_watermark_logo=True,
        )

        no_watermark = root / "no-watermark.ass"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--input",
                str(input_srt),
                "--output",
                str(no_watermark),
                "--resolution",
                "1920x1080",
                "--no-watermark",
                "--watermark-logo",
                str(logo_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        if any(
            line.startswith("Dialogue: 18,") or line.startswith("Dialogue: 19,")
            for line in no_watermark.read_text(encoding="utf-8").splitlines()
        ):
            fail("--no-watermark unexpectedly emitted a logo or rule event")

    print("PASS: watermark alignment regression cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
