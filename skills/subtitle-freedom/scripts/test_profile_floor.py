#!/usr/bin/env python3
"""Regression tests for minimum-level glossary selection."""

from __future__ import annotations

import sys
import json
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from subtitle_gloss import (  # noqa: E402
    Cue,
    Gloss,
    annotate_cues,
    canonical_profile,
    load_glossary,
    select_glosses,
)


def gloss(term: str, level: str = "") -> Gloss:
    return Gloss(term, term, term, "first", "word", "", level)


def terms(items):
    return [item.term for item in items]


def main() -> int:
    items = [
        gloss("a2-item", "a2"),
        gloss("b1-item", "b1"),
        gloss("cet4-item", "cet4"),
        gloss("b2-item", "b2"),
        gloss("cet6-item", "cet6"),
        gloss("advanced-item", "advanced"),
        gloss("legacy-item"),
    ]

    assert canonical_profile("CET-4") == "cet4"
    assert canonical_profile("CET 6") == "cet6"

    cet4, cet4_report = select_glosses(items, "cet4")
    assert terms(cet4) == [
        "cet4-item",
        "b2-item",
        "cet6-item",
        "advanced-item",
        "legacy-item",
    ]
    assert cet4_report == {
        "canonical_profile": "cet4",
        "profile_floor": "cet4",
        "filtered_below_profile": 2,
        "ungraded_glosses_retained": 1,
    }

    cet6, cet6_report = select_glosses(items, "cet6")
    assert terms(cet6) == ["cet6-item", "advanced-item", "legacy-item"]
    assert cet6_report["filtered_below_profile"] == 4

    custom, custom_report = select_glosses(items, "custom")
    assert terms(custom) == terms(items)
    assert custom_report["profile_floor"] is None

    with tempfile.TemporaryDirectory(prefix="subtitle-freedom-profile-test-") as temp:
        glossary_path = Path(temp) / "glossary.json"
        glossary_path.write_text(
            json.dumps(
                {
                    "profile": "cet4",
                    "items": [
                        {
                            "kind": "word",
                            "term": "basic",
                            "meaning": "基础",
                            "level": "a2",
                            "key": "basic",
                        },
                        {
                            "kind": "word",
                            "term": "hard",
                            "meaning": "困难",
                            "level": "cet6",
                            "key": "hard",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        loaded, _limit, _repeat = load_glossary(glossary_path)
        eligible, _report = select_glosses(loaded, "cet4")
        annotated, count = annotate_cues(
            [Cue("1", "00:00:00,000 --> 00:00:03,000", "basic and hard")],
            eligible,
            3,
        )
        assert count == 1
        assert "basic【" not in annotated[0].body
        assert "hard【困难】" in annotated[0].body

    print("PASS: profile floor selection regression cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
