#!/usr/bin/env python3
"""Regression tests for infographic title modes and scaffold output."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Optional
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "infographic_cli",
    ROOT / "scripts" / "infographic_cli.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load infographic_cli.py")
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


def scaffold_args(
    output_dir: Path,
    *,
    title_mode: str,
    recommendation: Optional[str],
    figure_label: Optional[str] = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        title="开源 MaaS 网关选型指南",
        title_mode=title_mode,
        recommendation=recommendation,
        figure_label=figure_label,
        source=None,
        aspect="16:9",
        template="comparison-matrix",
        mode="qualitative",
        output_dir=str(output_dir),
        brand_profile=str(ROOT / "assets" / "brand-profile.template.json"),
    )


class ScaffoldTitleModeTests(unittest.TestCase):
    def test_topic_mode_adds_evidence_linked_tail_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "topic"
            CLI.scaffold(
                scaffold_args(
                    output,
                    title_mode="topic",
                    recommendation="默认选择 LiteLLM；已有 Kubernetes 时评估 Higress。",
                )
            )

            poster = (output / "poster.html").read_text(encoding="utf-8")
            project = json.loads((output / "project.json").read_text(encoding="utf-8"))
            brief = (output / "brief.md").read_text(encoding="utf-8")

            self.assertIn('data-title-mode="topic"', poster)
            self.assertIn('data-region="recommendation"', poster)
            self.assertIn('data-audit="recommendation"', poster)
            self.assertIn('data-source-ref="S1"', poster)
            self.assertLess(
                poster.index('data-region="visual"'),
                poster.index('data-region="recommendation"'),
            )
            self.assertLess(
                poster.index('data-region="recommendation"'),
                poster.index('data-region="footer"'),
            )
            self.assertEqual(project["schema_version"], 3)
            self.assertEqual(project["title_mode"], "topic")
            self.assertIn("Title mode: topic", brief)

    def test_action_mode_omits_tail_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "action"
            CLI.scaffold(
                scaffold_args(
                    output,
                    title_mode="action",
                    recommendation=None,
                )
            )

            poster = (output / "poster.html").read_text(encoding="utf-8")
            project = json.loads((output / "project.json").read_text(encoding="utf-8"))

            self.assertIn('data-title-mode="action"', poster)
            self.assertNotIn('data-region="recommendation"', poster)
            self.assertEqual(project["title_mode"], "action")
            self.assertEqual(project["recommendation"], "")

    def test_action_mode_rejects_duplicate_tail_advice(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                CLI.CliError,
                "--recommendation is only valid",
            ):
                CLI.scaffold(
                    scaffold_args(
                        Path(temporary) / "invalid",
                        title_mode="action",
                        recommendation="重复建议",
                    )
                )

    def test_recommendation_copy_is_html_escaped(self) -> None:
        block = CLI.recommendation_block("<b>选择 A</b>")
        self.assertIn("&lt;b&gt;选择 A&lt;/b&gt;", block)
        self.assertNotIn("<b>选择 A</b>", block)

    def test_attribution_omits_separator_when_site_is_empty(self) -> None:
        self.assertEqual(CLI.attribution_html("Powered by Example", ""), "Powered by Example")
        self.assertEqual(
            CLI.attribution_html("Powered by", "https://example.com"),
            'Powered by · <span class="site">https://example.com</span>',
        )

    def test_standalone_scaffold_omits_automatic_figure_label(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "standalone"
            CLI.scaffold(
                scaffold_args(
                    output,
                    title_mode="topic",
                    recommendation="先看约束，再看方案。",
                )
            )

            poster = (output / "poster.html").read_text(encoding="utf-8")
            project = json.loads((output / "project.json").read_text(encoding="utf-8"))
            self.assertNotIn('<p class="figure-label">', poster)
            self.assertIn('class="topline topline--brand-only"', poster)
            self.assertIn("Powered by", poster)
            self.assertIn("lovstudio.ai/skills/professional-infographic", poster)
            self.assertIn('src="data:image/png;base64,', poster)
            self.assertEqual(project["figure_label"], "")

    def test_explicit_figure_label_is_rendered_and_escaped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "series"
            CLI.scaffold(
                scaffold_args(
                    output,
                    title_mode="action",
                    recommendation=None,
                    figure_label="Figure <3> · Growth bridge",
                )
            )

            poster = (output / "poster.html").read_text(encoding="utf-8")
            self.assertIn(
                '<p class="figure-label">Figure &lt;3&gt; · Growth bridge</p>',
                poster,
            )
            self.assertNotIn("Exhibit 01", poster)


class BrandResolutionTests(unittest.TestCase):
    def test_legacy_copyright_profile_normalizes_to_attribution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = root / "brand.json"
            profile.write_text(
                json.dumps(
                    {
                        "name": "Legacy Brand",
                        "logo": str(ROOT / "assets" / "shougongchuan-logo.png"),
                        "primary": "#182033",
                        "accent": "#EB6637",
                        "ink": "#172033",
                        "muted": "#566175",
                        "paper": "#F7F4EF",
                        "font_family": "sans-serif",
                        "copyright": "Legacy attribution",
                    }
                ),
                encoding="utf-8",
            )
            _, brand, _ = CLI.load_brand(str(profile))
            self.assertEqual(brand["attribution"], "Legacy attribution")

    def test_shared_profile_is_not_parsed_as_the_brand_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            brand_path = root / "brand.json"
            brand_path.write_text("{}\n", encoding="utf-8")
            shared_path = root / "profile.json"
            shared_path.write_text(
                json.dumps({"brand": {"profile": "brand.json"}}),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {"SKILL_PROFILE_PATH": str(shared_path)},
                clear=False,
            ):
                os.environ.pop("SKILL_PROFESSIONAL_INFOGRAPHIC_BRAND_PROFILE", None)
                self.assertEqual(CLI.configured_brand_path(None), brand_path.resolve())

    def test_default_config_path_expands_without_literal_environment_tokens(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                CLI.shared_profile_path(),
                (Path.home() / ".skill-publisher" / "skills" / "profile.json").resolve(),
            )


if __name__ == "__main__":
    unittest.main()
