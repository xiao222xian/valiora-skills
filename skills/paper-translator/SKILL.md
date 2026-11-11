---
name: lov-paper-translator
description: >
  Translate English academic PDFs into Simplified Chinese while preserving
  page correspondence, bilingual layouts, figures, and formulas. Use when
  users mention papers, arXiv files, or technical PDFs.
license: MIT
compatibility: >
  Requires Python 3.10+, pypdf, and reportlab. Poppler pdftotext improves text
  extraction; pdf2zh and a translation provider are optional for
  layout-preserving output. Legacy translate-paper-pdf translation JSON files
  remain readable.
depends_on:
  - lov-branding-consistency
metadata:
  author: lovstudio
  version: "0.2.1"
  tags:
    - paper
    - pdf
    - translation
    - academic
    - chinese
    - bilingual
    - layout
---

# 论文翻译官 · Paper Translator

This is a non-interactive workflow. Infer sensible defaults from the request;
ask only when the input PDF or an output decision cannot be recovered from the
conversation.

## Triggers

### Activate when

- 用户说“翻译这篇论文”“把 arXiv PDF 翻译成中文”或“保留图片和公式翻译”。
- The user asks to translate an academic paper, journal article, conference
  paper, or technical PDF into Simplified Chinese.
- The request needs matching pages, facing bilingual pages, paragraph-aligned
  bilingual output, or layout-preserving translation.
- The user mentions the former Skill name `translate-paper-pdf` while asking
  for the same paper-translation workflow.

### Do not activate when

- The user only wants a summary, literature review, citation extraction, OCR,
  or translation of plain text without a PDF deliverable.

## Workflow

1. Confirm the input is a text-based PDF. If it is scanned, run OCR first with
   a separate OCR tool.
2. Choose the output mode:
   - `key-pages-bilingual`: default polished deliverable. Most pages are
     Chinese-only; important front matter is followed by its original page.
   - `target-only`: Chinese-only PDF with the same selected page count.
   - `facing-pages`: each original page followed by its Chinese page.
   - `bilingual-expanded`: English and Chinese paragraphs share one enlarged
     logical page.
3. When layout, figures, tables, formulas, or images matter, use `pdf2zh`
   first. It retains original PDF objects more faithfully.
4. Use `scripts/paper_translator.py` as the fallback for text-reflow output.
   It does not retain original images, vector figures, or exact layout.
5. Verify page correspondence and inspect the rendered PDF before returning
   its path.

## Polished Deliverable Defaults

- Create both `key-pages-bilingual` and `target-only` outputs unless the user
  requests only one mode.
- In `key-pages-bilingual`, place each selected original page immediately
  after its translated counterpart.
- Remap internal links and outlines after inserting or removing pages.
- Regenerated tables of contents must use visible clickable styling: blue
  titles, dotted leaders, page numbers, and link annotations.
- Preserve bibliography fidelity. Keep original reference pages or reflow
  clean entries when machine translation damages citations.

## User Configuration

Resolve the installation without assuming a personal filesystem path:

```bash
SKILL_DIR="${CODEX_SKILLS_DIR:-${SKILLS_DIR:-$HOME/.codex/skills}}/lov-paper-translator"
```

All input and output locations must come from the request or CLI flags.

## Layout-Preserving Route

Use this route for requests such as “排版尽可能保持一致”, “保留图片”, or “保留公式”:

```bash
uv tool install --python 3.12 pdf2zh

ALI_API_KEY="$DASHSCOPE_API_KEY" pdf2zh \
  "/path/to/paper.pdf" \
  -li en -lo zh \
  -s qwen-mt \
  -t 1 \
  -o "/path/to/output-dir"
```

`pdf2zh` writes `<原文件名>-mono.pdf` and `<原文件名>-dual.pdf`. Rename them to:

```text
手工川超级翻译官 - <原文件名> - <YYYY-MM-DD> - vNN.pdf
手工川超级翻译官 - <原文件名> - <YYYY-MM-DD> - vNN-facing-pages.pdf
```

Keep `-t 1` for DashScope/Qwen-MT unless higher concurrency is known to be
accepted. Text embedded inside images generally needs a separate OCR and image
editing pass.

## Fallback CLI

Use the fallback only when exact image and layout preservation is secondary:

```bash
python3 "$SKILL_DIR/scripts/paper_translator.py" \
  "/path/to/paper.pdf" \
  --mode target-only \
  --translator openai \
  --output-dir "/path/to/output"
```

### Current-agent handoff

When no backend API key is available, export a translation handoff:

```bash
python3 "$SKILL_DIR/scripts/paper_translator.py" \
  "/path/to/paper.pdf" \
  --mode target-only \
  --translator agent \
  --output-dir "/path/to/output"
```

Fill every `translation` field in the generated `.translations.json`, then
render it:

```bash
python3 "$SKILL_DIR/scripts/paper_translator.py" \
  "/path/to/paper.pdf" \
  --translation-json "/path/to/file.translations.json" \
  --output-dir "/path/to/output"
```

New handoffs use the schema `lov-paper-translator.translations.v1`; the reader
also accepts files emitted under the former Skill name. Existing legacy caches
can be reused by passing their directory through `--cache-dir`.

## Translation Rules

- Translate into Simplified Chinese unless the selected mode retains English.
- Preserve section numbers, citations, equations, figure and table labels,
  URLs, code, and proper nouns.
- Do not summarize, omit content, or add commentary.
- Keep terminology stable across pages. For terms without a standard Chinese
  rendering, retain the English term or use `中文（English）` on first mention.
- Keep one output page mapped to one input page for `target-only` and each
  translated half of `facing-pages`; shrink text instead of spilling over.

## Layout Notes

Read `references/layout_modes.md` when choosing a mode, checking page counts,
or handling overflow.

## Validation

After creating a PDF, run:

```bash
pdfinfo "/path/to/output.pdf" | sed -n '1,30p'
```

- `target-only`: output count equals the selected source count.
- `facing-pages`: output count is exactly double.
- `bilingual-expanded`: output count is unchanged and page height is larger.

## 通用反馈闭环

用户在 Skill 驱动任务中提出修改意见时，继续当前产物前必须执行：

1. 先判断意见是 `task-specific`（仅本次）还是 `reusable`（可跨任务复用）。
2. `task-specific` 只修改当前任务，不改 Skill。
3. `reusable` 先确定作用域：领域规则先更新对应 canonical Skill；适用于所有 Skill 的规则先更新共享规范。
4. 完成规则更新、版本、lint 与分发核验后，再把修改应用到当前任务。
5. `reusable` 修改会使此前的“确认”“继续”“发吧”失效；完成当前产物修改和回读后必须停下，等待用户下一步指示，不自动进入发布、提交或其他外部写入。
