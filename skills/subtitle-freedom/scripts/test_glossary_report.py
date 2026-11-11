#!/usr/bin/env python3
"""Regression tests for deterministic glossary coverage reporting."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "subtitle_gloss.py"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="subtitle-freedom-report-test-") as temp:
        root = Path(temp)
        input_path = root / "source.srt"
        glossary_path = root / "glossary.json"
        output_path = root / "output.srt"
        input_path.write_text(
            "1\n"
            "00:00:00,000 --> 00:00:03,000\n"
            "A brave sword guards the gate.\n\n"
            "2\n"
            "00:00:03,000 --> 00:00:06,000\n"
            "The first signal reaches the second tower.\n",
            encoding="utf-8",
        )
        glossary_path.write_text(
            json.dumps(
                {
                    "max_notes_per_cue": 1,
                    "items": [
                        {
                            "term": "brave sword",
                            "meaning": "勇敢的剑士",
                            "key": "brave-sword",
                            "level": "cet4",
                        },
                        {
                            "term": "brave",
                            "meaning": "勇敢的",
                            "key": "brave",
                            "level": "cet4",
                        },
                        {
                            "term": "first",
                            "meaning": "第一个",
                            "key": "first",
                            "level": "cet4",
                        },
                        {
                            "term": "second",
                            "meaning": "第二个",
                            "key": "second",
                            "level": "cet4",
                        },
                        {
                            "term": "missing phrase",
                            "meaning": "未出现的短语",
                            "key": "missing-phrase",
                            "level": "cet4",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--input",
                str(input_path),
                "--profile",
                "cet4",
                "--glossary",
                str(glossary_path),
                "--output",
                str(output_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"subtitle_gloss.py failed: {result.stderr.strip()}"
            )

        report = json.loads(result.stdout)
        assert report["glosses"] == 2
        assert report["glossary_matched"] == 4
        assert report["glossary_applied"] == 2
        assert report["glossary_unmatched"] == [
            {"key": "missing-phrase", "term": "missing phrase", "reason": "no_literal_match"}
        ]
        assert report["glossary_suppressed"] == [
            {"key": "brave", "term": "brave", "reason": "overlap"},
            {"key": "second", "term": "second", "reason": "max_notes_per_cue"},
        ]
        rendered = output_path.read_text(encoding="utf-8")
        assert "brave sword【勇敢的剑士】" in rendered
        assert "first【第一个】" in rendered
        assert "brave【勇敢的】" not in rendered
        assert "second【第二个】" not in rendered

    print("PASS: deterministic glossary coverage report cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
