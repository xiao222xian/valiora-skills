# Layout Modes

## `target-only`

Use for "仅输出目标语言". The generated PDF has the same number of pages and page sizes as the selected source pages. Each Chinese page is rendered from the matching English page text. This is the safest mode for reading and downstream sharing when the user does not need the source text visible.

Check:

- Output page count equals selected source page count.
- No English source paragraphs remain, except preserved proper nouns, citations, formulas, URLs, or technical names.
- Dense pages may use smaller type or two columns to avoid spillover.

## `facing-pages`

Use for "一页原文，一页目标". The generated PDF interleaves pages:

```text
source page 1
Chinese page 1
source page 2
Chinese page 2
...
```

Check:

- Output page count is exactly two times the selected source page count.
- Every odd page is an original source page.
- Every even page is the translation of the immediately previous source page.

## `bilingual-expanded`

Use for "一段段的翻译（保留中文和英文），页面高度扩充为接近 2 倍，但页数保持不变". The generated PDF keeps the same number of logical pages but scales page height, defaulting to `--height-scale 1.9`. Each page alternates source paragraph and Chinese paragraph.

This mode is feasible for text-based PDFs, but very dense pages may require smaller type. It is less faithful to the original visual layout than the first two modes because the page geometry changes.

Check:

- Output page count equals selected source page count.
- Page height is larger than the original, usually close to 2x.
- Paragraph order is preserved.

## Dependencies

The script expects:

- `python3`
- `pypdf`
- `reportlab`
- `pdftotext` from Poppler for best text extraction. If unavailable, the script falls back to `pypdf` extraction.

For live translation with `--translator openai`, set:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4.1-mini"
```

`OPENAI_BASE_URL` is optional and defaults to `https://api.openai.com/v1`. Any OpenAI-compatible `/chat/completions` endpoint can be used.

## Current-Agent Translation

Use `--translator agent` when the user wants to avoid a backend API key and let the current Codex session do the translation. This mode exports a `.translations.json` template and exits. The agent must fill the JSON translation fields, then rerun the script with `--translation-json`.

This is slower for long papers because the translation happens through the current conversation, but it avoids storing or requiring API credentials. Keep page boundaries intact while filling the JSON so the rendered PDF preserves page correspondence.
