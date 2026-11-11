#!/usr/bin/env python3
"""Validate a local WeChat article package and write its quality report."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from statistics import median

from PIL import Image


ARTICLE_SCHEMA = "lovstudio/wechat-article-package/v2"
COVER_SCHEMA = "lovstudio/wechat-cover-package/v2"
LEGACY_ARTICLE_SCHEMA = "lovstudio/wechat-article-package/v1"
LEGACY_COVER_SCHEMA = "lovstudio/wechat-cover-package/v1"
REQUIRED_BASE = [
    "article.md",
    "article-manifest.json",
    "sources.md",
    "cover/art-master.png",
    "cover/wechat-cover-wide.png",
    "cover/wechat-cover-wide.jpg",
    "cover/cover-manifest.json",
]

BENCHMARK_REQUIRED_SECTIONS = [
    "测试方法",
    "Prompt",
    "评价指标",
    "评分方法",
    "评分示例",
    "复现方法",
    "测试结果",
    "局限性",
]

SESSION_CONTEXT_LEAK = re.compile(
    r"(?:我|我们)?(?:前一版|上一版|前一稿|上一稿)|"
    r"(?:按你的要求|你之前说|我们(?:刚才|之前)讨论过)"
)

DUPLICATE_SENTENCE_MIN_CHARS = 10
MEDIA_GAP_MEDIAN_MIN = 60
MEDIA_GAP_SHORT = 40
MEDIA_GAP_SHORT_RUN = 3
MEDIA_LINE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
EMBED_LINE = re.compile(r"::(?!:)[A-Za-z]")
WECHAT_ACCOUNT_ID = re.compile(r"(?<![A-Za-z0-9_])wxid_[A-Za-z0-9_-]{4,}")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(path_value: object) -> bool:
    if not isinstance(path_value, str) or not path_value:
        return False
    pure = PurePosixPath(path_value)
    return not pure.is_absolute() and ".." not in pure.parts and "\\" not in path_value


def local_markdown_image_paths(article: str) -> list[str]:
    paths: set[str] = set()
    for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", article):
        raw = match.group(1).strip()
        quoted = re.match(r"(.+?)\s+(['\"]).*\2\s*$", raw)
        target = (quoted.group(1) if quoted else raw).strip("<>")
        if target.startswith(("http://", "https://", "data:", "//")):
            continue
        paths.add(target)
    return sorted(paths)


def opening_context_leaks(article: str) -> list[str]:
    """Return session-dependent phrases from the title plus opening 300 chars."""
    without_fence = re.sub(r"```[\s\S]*?```", " ", article)
    visible = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", without_fence)
    visible = re.sub(r"(?m)^#\s+.*$", " ", visible, count=1)
    opening = re.sub(r"\s+", " ", visible).strip()[:300]
    return [match.group(0) for match in SESSION_CONTEXT_LEAK.finditer(opening)]


def body_lines(article: str) -> list[str]:
    """Return stripped Markdown lines without fenced code or HTML comments."""
    without_fence = re.sub(r"```[\s\S]*?```", "\n", article)
    return [line.strip() for line in re.sub(r"<!--[\s\S]*?-->", "\n", without_fence).splitlines()]


def visible_text(line: str) -> str:
    """Return the reader-visible characters of one Markdown line."""
    text = MEDIA_LINE.sub("", line)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"^(?:#{1,6}|>|[-+*]|\d+\.)\s+", "", text)
    return re.sub(r"[\s*_`~]", "", text)


def duplicate_sentences(article: str) -> list[str]:
    """Return prose sentences of 10+ characters that appear more than once."""
    counts: dict[str, int] = {}
    for line in body_lines(article):
        if not line or line.startswith(("#", "::", "|")) or MEDIA_LINE.fullmatch(line):
            continue
        for sentence in re.findall(r"[^。！？!?；]+[。！？!?；]?", visible_text(line)):
            if len(sentence) >= DUPLICATE_SENTENCE_MIN_CHARS:
                counts[sentence] = counts.get(sentence, 0) + 1
    return [sentence for sentence, count in counts.items() if count > 1]


def emphasis_markup_errors(article: str) -> list[str]:
    """Reject highlight markup; the WeChat theme renders emphasis as bold only."""
    body = re.sub(r"```[\s\S]*?```", " ", article)
    body = re.sub(r"`[^`\n]*`", " ", body)
    errors = []
    if re.search(r"(?<!=)==(?!=)[^=\n]+?(?<!=)==(?!=)", body):
        errors.append("==highlight== is not rendered by the WeChat theme; emphasize with **bold** only")
    if re.search(r"<mark\b|background(?:-color)?\s*:", body, re.IGNORECASE):
        errors.append("background highlight is not allowed in the article; emphasize with **bold** only")
    return errors


def media_gaps(article: str) -> list[int]:
    """Return visible characters between consecutive images or embeds."""
    gaps: list[int] = []
    current, seen = 0, False
    for line in body_lines(article):
        if MEDIA_LINE.fullmatch(line) or EMBED_LINE.match(line):
            if seen:
                gaps.append(current)
            seen, current = True, 0
        elif seen and not re.match(r"#\s", line) and not line.startswith(":::"):
            current += len(visible_text(line))
    return gaps


def media_density_warnings(gaps: list[int]) -> list[str]:
    """Warn when images arrive every few lines, the way a video script reads."""
    if len(gaps) < MEDIA_GAP_SHORT_RUN:
        return []
    run = longest = 0
    for gap in gaps:
        run = run + 1 if gap < MEDIA_GAP_SHORT else 0
        longest = max(longest, run)
    middle = median(gaps)
    if middle >= MEDIA_GAP_MEDIAN_MIN and longest < MEDIA_GAP_SHORT_RUN:
        return []
    return [
        f"body media are dense: median {middle:g} visible characters between images or embeds, "
        f"{longest} consecutive gaps under {MEDIA_GAP_SHORT}; confirm each cluster is intentional "
        "or regroup the images around the paragraphs that name them"
    ]


def benchmark_errors(article: str) -> list[str]:
    """Return reproducibility failures for articles that present a benchmark."""
    h1 = re.search(r"(?m)^#\s+(.+)$", article)
    title = h1.group(1) if h1 else ""
    quantified_claim = bool(re.search(r"排名|排行榜|第一名|总分|雷达图", article)) and bool(
        re.search(r"评分|得分|分数|权重", article)
    )
    # 「调研」既可能是打分排名的 benchmark，也可能是纯数据统计。
    # 只有标题信号叠加真实评测证据时才要求论文式方法章节，
    # 否则纯数据调研会被迫编造并不存在的评分 Prompt 与算分示例。
    title_signal = bool(re.search(r"调研|评测|benchmark", title, re.IGNORECASE))
    benchmark_evidence = bool(
        re.search(r"排名|排行榜|第一名|总分|雷达图|评分|得分|分数|权重", article)
    ) or ("## 测试结果" in article)
    is_benchmark = (
        (title_signal and benchmark_evidence)
        or ("## 测试方法" in article and "## 测试结果" in article)
        or quantified_claim
    )
    if not is_benchmark:
        return []

    headings = [match.group(1).strip() for match in re.finditer(r"(?m)^##\s+(.+?)\s*$", article)]
    missing = [heading for heading in BENCHMARK_REQUIRED_SECTIONS if heading not in headings]
    errors = [f"benchmark article missing required section: {heading}" for heading in missing]
    if missing:
        return errors

    positions = [headings.index(heading) for heading in BENCHMARK_REQUIRED_SECTIONS]
    if positions != sorted(positions):
        errors.append("benchmark methodology, prompt, rubric, reproduction, results, and limitations are out of order")

    prompt_match = re.search(
        r"(?ms)^##\s+Prompt\s*$\n(.*?)(?=^##\s+)",
        article,
    )
    prompt_body = prompt_match.group(1) if prompt_match else ""
    fenced_prompts = re.findall(r"```[^\n]*\n(.*?)```", prompt_body, re.DOTALL)
    if not any(len(re.sub(r"\s+", " ", block).strip()) >= 40 for block in fenced_prompts):
        errors.append("benchmark Prompt section must expose at least one substantive verbatim prompt in a fenced block")
    return errors


def research_disclosure_errors(article: str) -> list[str]:
    """Return disclosure failures for data-research articles that are not benchmarks."""
    h1 = re.search(r"(?m)^#\s+(.+)$", article)
    title = h1.group(1) if h1 else ""
    if not re.search(r"调研|调查|统计|抓取", title):
        return []
    errors = []
    if not re.search(r"口径|样本|范围|定义", article):
        errors.append("research article must disclose its sample scope or definition")
    if not re.search(r"局限|不足|边界|无法|不代表", article):
        errors.append("research article must disclose limitations")
    if not re.search(r"复现|开源|数据集|仓库|github", article, re.IGNORECASE):
        errors.append("research article must expose a reproduction or data entry point")
    return errors


def writing_review_errors(article: bytes, report: object) -> list[str]:
    """Validate the portable receipt; semantic decisions belong to human-writing.

    This verifies evidence integrity, not reviewer identity or editorial taste.
    """
    if not isinstance(report, dict):
        return ["missing or invalid writing-review.json; complete prose review first"]
    errors = []
    expected_hash = hashlib.sha256(article).hexdigest()
    if report.get("schema") != "lov-human-writing/discourse-gate/v1":
        errors.append("writing review schema mismatch")
    if report.get("status") != "accepted" or report.get("errors") != []:
        errors.append("writing review has not completed")
    if report.get("input_sha256") != expected_hash:
        errors.append("writing review is stale: article SHA-256 mismatch")
    review = report.get("review")
    if not isinstance(review, dict):
        return errors + ["writing review lacks semantic review evidence"]
    if (review.get("schema") != "lov-human-writing/discourse-review/v1"
            or review.get("input_sha256") != expected_hash
            or not isinstance(review.get("reviewer"), str)
            or not review.get("reviewer", "").strip()):
        errors.append("writing review evidence metadata mismatch")
    units, decisions = report.get("units"), review.get("units")
    if not isinstance(units, list) or not units or not isinstance(decisions, list):
        return errors + ["writing review lacks paragraph coverage"]
    ids = [u.get("id") for u in units if isinstance(u, dict)]
    seen = []
    for item in decisions:
        if not isinstance(item, dict):
            errors.append("malformed writing review decision"); continue
        seen.append(item.get("id"))
        if (item.get("decision") not in {"accept", "protected"}
                or not isinstance(item.get("reason"), str)
                or not item.get("reason", "").strip()):
            errors.append("writing review contains unresolved or unexplained decisions")
    if (len(ids) != len(units) or not all(isinstance(i, str) for i in ids + seen)
            or sorted(ids) != sorted(seen) or len(set(ids)) != len(ids)):
        errors.append("writing review paragraph coverage mismatch")
    return errors


def self_test() -> int:
    bad = "# 我调研了市面上所有的去 AI 味 Prompt\n\n我前一版 benchmark 做错了。"
    good = "# 我调研了市面上所有的去 AI 味 Prompt\n\n我把 5 套公开 Skill 和两个对照放到同一组输入上，跑了 63 次。"
    if not opening_context_leaks(bad):
        raise AssertionError("cold-reader regression was not detected")
    if opening_context_leaks(good):
        raise AssertionError("valid cold-reader opening was rejected")
    incomplete_benchmark = "# 我调研了去 AI 味 Prompt\n\n## 测试结果\n\n第一名。\n"
    if not benchmark_errors(incomplete_benchmark):
        raise AssertionError("incomplete benchmark article was not detected")
    complete_benchmark = """# 我调研了去 AI 味 Prompt

## 测试方法
固定模型与输入。
## Prompt
```text
请在保持全部事实、数字、专有名词、链接、引语和作者立场的前提下改写这篇文章，不得补造经历，也不得删除不确定性。
```
## 评价指标
事实保真、声音保留。
## 评分方法
使用离散量表和盲评。
## 评分示例
展示一项原始分和总分计算。
## 复现方法
给出环境、命令、随机种子和产物索引。
## 测试结果
公开原始结果。
## 局限性
说明样本与随机性。
"""
    if benchmark_errors(complete_benchmark):
        raise AssertionError("complete benchmark article was rejected")
    data_research = (
        "# 我调研了平台上 517 个高价活动\n\n"
        "## 调研对象与口径\n样本与口径说明。\n"
        "## 局限\n样本不是全集，无法区分隐藏数据。\n"
        "## 附录\n数据与脚本已开源在 github。\n"
    )
    if benchmark_errors(data_research):
        raise AssertionError("pure data research was misclassified as a benchmark")
    if research_disclosure_errors(data_research):
        raise AssertionError("compliant data research was rejected")
    undisclosed = "# 我调研了平台上 517 个高价活动\n\n直接给结论。\n"
    if not research_disclosure_errors(undisclosed):
        raise AssertionError("undisclosed research article was not detected")
    sample = b"# Installation"
    sample_hash = hashlib.sha256(sample).hexdigest()
    receipt = {
        "schema": "lov-human-writing/discourse-gate/v1", "status": "accepted",
        "errors": [], "input_sha256": sample_hash, "units": [{"id": "u1"}],
        "review": {"schema": "lov-human-writing/discourse-review/v1",
                   "input_sha256": sample_hash, "reviewer": "test-fixture",
                   "units": [{"id": "u1", "decision": "accept", "reason": "Names installation."}]}}
    assert not writing_review_errors(sample, receipt)
    assert writing_review_errors(sample, None)
    assert writing_review_errors(sample + b" changed", receipt)
    receipt["review"]["units"][0]["decision"] = "revise"
    assert writing_review_errors(sample, receipt)
    repeated = "# 标题\n\n一人，一车，两个月，三千公里。\n\n后来又写了一遍：\n\n**一人，一车，两个月，三千公里。**\n"
    if duplicate_sentences(repeated) != ["一人，一车，两个月，三千公里。"]:
        raise AssertionError("repeated sentence was not detected")
    if duplicate_sentences("# 标题\n\n## 杀出去不会死\n\n杀出去不会死，呆在原地才会死。\n"):
        raise AssertionError("a heading echoed once in the body was reported as a repeat")
    assert emphasis_markup_errors("这句很重要：==要记住==。")
    assert emphasis_markup_errors('<span style="background-color:#f1e7b9;">**要记住**</span>')
    assert not emphasis_markup_errors("**要记住**，`a == b` 只是代码。")
    assert WECHAT_ACCOUNT_ID.search("来源：wxid_abc12345 的朋友圈")
    assert not WECHAT_ACCOUNT_ID.search("来源：本人朋友圈")
    script_like = "# 标题\n\n![首图](cover/a.jpg)\n\n" + "".join(
        f"第{i}句很短。\n\n![图{i}](figures/{i}.jpg)\n\n" for i in range(6)
    )
    if not media_density_warnings(media_gaps(script_like)):
        raise AssertionError("script-like image density was not detected")
    paragraph = "这一段交代时间、地点、动作和转折，足够让读者读进去再看图。" * 4
    spaced = "# 标题\n\n![首图](cover/a.jpg)\n\n" + "".join(
        f"{paragraph}\n\n![图{i}](figures/{i}.jpg)\n\n:::tip\n资料注。\n:::\n\n" for i in range(6)
    )
    if media_density_warnings(media_gaps(spaced)):
        raise AssertionError("a well-spaced article was flagged as dense")
    print("SELF-TEST PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.package is None:
        parser.error("provide --package or --self-test")

    package = args.package.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []

    if not package.is_dir():
        parser.error(f"package not found: {package}")
    article_manifest_path = package / "article-manifest.json"
    article_schema = ""
    if article_manifest_path.is_file():
        try:
            article_schema = json.loads(article_manifest_path.read_text(encoding="utf-8")).get("schema", "")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    legacy_package = article_schema == LEGACY_ARTICLE_SCHEMA
    opening_files = (
        ["cover/article-opening-vertical.png", "cover/article-opening-vertical.jpg"]
        if legacy_package
        else ["cover/article-opening-4x3.png", "cover/article-opening-4x3.jpg"]
    )
    for relative in REQUIRED_BASE + opening_files:
        if not (package / relative).is_file():
            errors.append(f"missing required file: {relative}")
    if errors:
        report = {"schema": "lovstudio/wechat-article-quality/v1", "valid": False, "checks": checks, "errors": errors, "warnings": warnings, "checked_at": now_iso()}
        (package / "quality-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else "INVALID")
        return 1

    try:
        article_manifest = json.loads((package / "article-manifest.json").read_text(encoding="utf-8"))
        cover_manifest = json.loads((package / "cover/cover-manifest.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        errors.append(f"manifest parse error: {error}")
        article_manifest = {}
        cover_manifest = {}

    if article_manifest.get("schema") not in {ARTICLE_SCHEMA, LEGACY_ARTICLE_SCHEMA}:
        errors.append("article manifest schema mismatch")
    else:
        checks.append("article manifest schema")
    if cover_manifest.get("schema") not in {COVER_SCHEMA, LEGACY_COVER_SCHEMA}:
        errors.append("cover manifest schema mismatch")
    else:
        checks.append("cover manifest schema")

    title = article_manifest.get("title", "")
    excerpt = article_manifest.get("excerpt", "")
    if not isinstance(title, str) or not title or len(title) > 32:
        errors.append("title must contain 1-32 Unicode characters")
    else:
        checks.append("title length")
    if not isinstance(excerpt, str) or not excerpt or len(excerpt) > 120:
        errors.append("excerpt must contain 1-120 Unicode characters")
    else:
        checks.append("excerpt length")

    expected_opening = (
        "cover/article-opening-vertical.jpg" if legacy_package else "cover/article-opening-4x3.jpg"
    )
    expected_paths = {
        "article_path": "article.md",
        "opening_image_path": expected_opening,
        "wide_cover_path": "cover/wechat-cover-wide.jpg",
    }
    for key, expected in expected_paths.items():
        value = article_manifest.get(key)
        if value != expected or not safe_relative(value):
            errors.append(f"invalid {key}: expected {expected}")
        else:
            checks.append(key)

    brand = article_manifest.get("brand", {})
    if not isinstance(brand, dict) or not brand.get("name") or brand.get("logo_source") != "profile:brand.logo":
        errors.append("article brand must name the publisher and reference profile:brand.logo")
    else:
        checks.append("article brand identity")
    if cover_manifest.get("brand", {}).get("name") != brand.get("name"):
        errors.append("article and cover brand names differ")
    else:
        checks.append("brand agreement")
    publication = article_manifest.get("publication", {})
    cover_publication = cover_manifest.get("publication", {})
    if not publication.get("name") or cover_publication.get("name") != publication.get("name"):
        errors.append("article and cover publication names differ")
    else:
        checks.append("publication identity")
    if (
        cover_publication.get("logo_source")
        != "profile:skills.lov-article-creator.records.cover_logo_path"
        or cover_publication.get("logo_variant") != "horizontal-lockup"
        or cover_publication.get("logo_color") != "white"
        or not isinstance(cover_publication.get("logo_aspect_ratio"), (int, float))
        or cover_publication.get("logo_aspect_ratio", 0) < 1.8
        or not isinstance(cover_publication.get("logo_white_pixel_ratio"), (int, float))
        or cover_publication.get("logo_white_pixel_ratio", 0) < 0.98
    ):
        errors.append("cover must use the configured official white horizontal publication lockup")
    else:
        checks.append("white horizontal publication lockup")

    article = (package / "article.md").read_text(encoding="utf-8")
    review_path = package / "writing-review.json"
    try:
        writing_review = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        writing_review = None
    prose_errors = writing_review_errors((package / "article.md").read_bytes(), writing_review)
    errors.extend(prose_errors)
    if not prose_errors:
        checks.append("text-bound paragraph review receipt")
    h1_matches = list(re.finditer(r"(?m)^#\s+\S.*$", article))
    if len(h1_matches) != 1:
        errors.append(f"article must contain exactly one H1, found {len(h1_matches)}")
    else:
        checks.append("single H1")
    image_index = article.find(expected_opening)
    first_h2 = re.search(r"(?m)^##\s+\S", article)
    if image_index < 0 or (first_h2 and image_index > first_h2.start()) or (h1_matches and image_index < h1_matches[0].end()):
        errors.append("body opening image must appear after H1 and before the first H2")
    else:
        checks.append("opening image placement")
    context_leaks = opening_context_leaks(article)
    if context_leaks:
        errors.append(
            "opening depends on session or draft history: "
            + ", ".join(context_leaks)
        )
    else:
        checks.append("cold-reader opening context")
    duplicates = duplicate_sentences(article)
    if duplicates:
        errors.append("article repeats sentences: " + " | ".join(duplicates[:5]))
    else:
        checks.append("no repeated sentences")
    emphasis_errors = emphasis_markup_errors(article)
    if emphasis_errors:
        errors.extend(emphasis_errors)
    else:
        checks.append("bold-only emphasis")
    gaps = media_gaps(article)
    density_warnings = media_density_warnings(gaps)
    if density_warnings:
        warnings.extend(density_warnings)
    elif gaps:
        checks.append(f"body media spacing (median {median(gaps):g} visible characters)")
    reproducibility_errors = benchmark_errors(article) + research_disclosure_errors(article)
    if reproducibility_errors:
        errors.extend(reproducibility_errors)
    elif re.search(r"调研|评测|benchmark", title, re.IGNORECASE):
        checks.append("benchmark reproducibility contract")

    if not legacy_package:
        local_images = [path for path in local_markdown_image_paths(article) if path != expected_opening]
        manifest_images = article_manifest.get("body_image_paths")
        if manifest_images != local_images:
            errors.append("body_image_paths must list every packaged local body image")
        else:
            checks.append("body image manifest")
        for relative in local_images:
            if not safe_relative(relative) or not (package / relative).is_file():
                errors.append(f"missing packaged body image: {relative}")
            else:
                checks.append(f"packaged body image: {relative}")

        # A package with no body figures is only valid when the illustration
        # stage actually ran and recorded why. `undecided` means it never ran.
        figures = article_manifest.get("body_figures")
        if not isinstance(figures, dict):
            errors.append("article manifest must record a body_figures decision")
        else:
            decision = figures.get("decision")
            if decision not in {"required", "not-required"}:
                errors.append(
                    "body_figures.decision must be 'required' or 'not-required'; "
                    "'undecided' means the illustration stage was skipped"
                )
            elif decision == "not-required" and not str(figures.get("reason", "")).strip():
                errors.append("body_figures.decision 'not-required' must carry a reason")
            elif decision == "required" and not local_images:
                errors.append("body_figures.decision is 'required' but the article embeds no body figure")
            else:
                checks.append("body figure decision")

    public_text = article + (package / "sources.md").read_text(encoding="utf-8") + json.dumps(article_manifest, ensure_ascii=False) + json.dumps(cover_manifest, ensure_ascii=False)
    if re.search(r"(?:/Users/|C:\\Users\\)", public_text):
        errors.append("package leaks a private absolute user path")
    else:
        checks.append("portable public paths")
    if WECHAT_ACCOUNT_ID.search(public_text):
        errors.append("package leaks a WeChat account id (wxid_...)")
    else:
        checks.append("no WeChat account ids")

    image_specs = [
        ("wide", 1880, 800, 2.35, "cover/wechat-cover-wide.png", "cover/wechat-cover-wide.jpg"),
    ]
    if legacy_package:
        image_specs.append(("vertical", 1200, 1600, 0.75, "cover/article-opening-vertical.png", "cover/article-opening-vertical.jpg"))
        warnings.append("legacy v1 package uses a 3:4 opening image; new packages must use the v2 4:3 body hero")
    else:
        image_specs.append(("opening", 1600, 1200, 4 / 3, "cover/article-opening-4x3.png", "cover/article-opening-4x3.jpg"))
    for key, min_width, min_height, expected_ratio, png_rel, jpg_rel in image_specs:
        spec = cover_manifest.get(key, {})
        for format_key, relative in (("png", png_rel), ("jpg", jpg_rel)):
            image_path = package / relative
            with Image.open(image_path) as image:
                width, height = image.size
            if width < min_width or height < min_height or abs(width / height - expected_ratio) > 0.01:
                errors.append(f"{relative} has invalid dimensions {width}x{height}")
            elif spec.get("width") != width or spec.get("height") != height:
                errors.append(f"{key} manifest dimensions do not match {relative}")
            else:
                checks.append(f"{relative} dimensions")
            expected_hash = spec.get("sha256", {}).get(format_key)
            if expected_hash != sha256(image_path):
                errors.append(f"{relative} SHA-256 mismatch")
            else:
                checks.append(f"{relative} SHA-256")

    if not article_manifest.get("read_original_url"):
        warnings.append("read_original_url is empty; acceptable only when no online version exists")

    valid = not errors
    if valid:
        article_manifest["status"] = "prepared"
        publication = article_manifest.setdefault("publication", {})
        publication["status"] = "prepared"
        (package / "article-manifest.json").write_text(json.dumps(article_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        checks.append("publication state promoted to prepared")

    elif article_manifest.get("status") == "prepared":
        article_manifest["status"] = "draft"
        if article_manifest.get("publication", {}).get("status") == "prepared":
            article_manifest["publication"]["status"] = "draft"
        (package / "article-manifest.json").write_text(json.dumps(article_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "lovstudio/wechat-article-quality/v1",
        "valid": valid,
        "status": "prepared" if valid else "failed",
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "checked_at": now_iso(),
    }
    (package / "quality-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else ("VALID" if valid else "INVALID"))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
