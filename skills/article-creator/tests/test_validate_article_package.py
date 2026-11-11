from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_article_package.py"
SPEC = importlib.util.spec_from_file_location("validate_article_package", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RepeatedSentenceTests(unittest.TestCase):
    def test_reports_a_sentence_written_twice(self) -> None:
        article = (
            "# 标题\n\n一人，一车，两个月，三千公里。\n\n中间一段。\n\n"
            "- **一人，一车，两个月，三千公里。**\n"
        )
        self.assertEqual(MODULE.duplicate_sentences(article), ["一人，一车，两个月，三千公里。"])

    def test_ignores_headings_code_tables_and_short_refrains(self) -> None:
        article = (
            "# 车轮不息\n\n## 车轮不息\n\n车轮不息，生命不止，激情永不灭。\n\n"
            "```text\n同一段代码里的同一行内容。\n同一段代码里的同一行内容。\n```\n\n"
            "| 时段 | 内容是一样的十个字 |\n| 时段 | 内容是一样的十个字 |\n\n"
            "杀出去不会死。\n\n杀出去不会死。\n"
        )
        self.assertEqual(MODULE.duplicate_sentences(article), [])


class EmphasisMarkupTests(unittest.TestCase):
    def test_rejects_equals_highlight(self) -> None:
        self.assertTrue(MODULE.emphasis_markup_errors("这一句：==最重要==。"))

    def test_rejects_background_highlight(self) -> None:
        html = '<span style="background-color:#f1e7b9;">**最重要**</span>'
        self.assertTrue(MODULE.emphasis_markup_errors(html))
        self.assertTrue(MODULE.emphasis_markup_errors("<mark>最重要</mark>"))

    def test_accepts_bold_and_code(self) -> None:
        article = "**最重要**。\n\n`a == b` 是代码。\n\n```css\nbackground: red;\n```\n"
        self.assertEqual(MODULE.emphasis_markup_errors(article), [])


class WechatAccountIdTests(unittest.TestCase):
    def test_detects_account_id(self) -> None:
        self.assertIsNotNone(MODULE.WECHAT_ACCOUNT_ID.search("来源：wxid_abc12345"))

    def test_ignores_plain_source_line(self) -> None:
        self.assertIsNone(MODULE.WECHAT_ACCOUNT_ID.search("来源：本人朋友圈"))


class MediaDensityTests(unittest.TestCase):
    def test_warns_when_every_line_has_an_image(self) -> None:
        article = "# 标题\n\n![首图](cover/a.jpg)\n\n" + "".join(
            f"第{i}句。\n\n![图{i}](figures/{i}.jpg)\n\n" for i in range(5)
        )
        self.assertTrue(MODULE.media_density_warnings(MODULE.media_gaps(article)))

    def test_accepts_images_that_follow_full_paragraphs(self) -> None:
        paragraph = "这一段先交代时间、地点和动作，再写一个转折，然后才放图。" * 3
        article = "# 标题\n\n![首图](cover/a.jpg)\n\n" + "".join(
            f"## 第{i}章\n\n{paragraph}\n\n![图{i}](figures/{i}.jpg)\n\n" for i in range(5)
        )
        self.assertEqual(MODULE.media_density_warnings(MODULE.media_gaps(article)), [])

    def test_counts_channel_embeds_but_not_admonition_fences(self) -> None:
        article = (
            "# 标题\n\n![首图](cover/a.jpg)\n\n宣传片：\n\n"
            '::wechat-channels{id="export/demo" nickname="demo"}\n\n'
            ":::tip\n资料注写在这里。\n:::\n\n![图](figures/b.jpg)\n"
        )
        self.assertEqual(MODULE.media_gaps(article), [4, 8])

    def test_self_test_passes(self) -> None:
        self.assertEqual(MODULE.self_test(), 0)


if __name__ == "__main__":
    unittest.main()
