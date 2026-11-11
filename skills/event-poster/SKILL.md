---
name: lov-event-poster
category: "Image & Design"
tagline: "Generate event posters via HTML + Playwright / 活动海报生成"
description: >
  Create event posters, exhibition posters, flyers, and promotional graphics
  from a brief. Outputs print-ready high-resolution PNG and iterates on
  visual hierarchy, QR placement, typography, and large-format readability.
  Trigger words: 海报, poster, event poster, 展览海报, 展架, 活动海报, 宣传图,
  promotional, banner, flyer
allowed-tools: [Bash, Read, Write, Edit, AskUserQuestion]
version: "0.6.4"
license: Commercial
compatibility: "claude-code >= 1.0"
depends_on:
  - lov-branding-consistency
  - lov-create-qrcode
  - lov-image-creator
metadata:
  version: "0.6.4"
  author: contributors
  tags: event poster exhibition flyer QR print design
  internal: true  # plaintext source — never installed; the encrypted public/SKILL.md is what users get
---

# 专业海报 · Professional Poster

Generate event posters as plain HTML/CSS → PNG.

## Step 1: Collect Event Details

Use `AskUserQuestion` to gather:

| Field | Required | Example |
|-------|----------|---------|
| 活动名称 / Title | Yes | "Claude Code Workshop" |
| 日期时间 / Date | Yes | "2026-04-20 14:00" |
| 地点 / Venue | Yes | "上海·静安嘉里中心" |
| 主题/描述 / Description | Yes | "Learn to build AI agents" |
| 嘉宾/讲者 / Speakers | No | "Mark, Alice" |
| 主办方 / Organizer | No | "Skill Publisher" |
| 联系方式 / Contact | No | QR code path, URL, WeChat ID |
| 风格 / Style | No | See references/themes.md |

Also ask:
- **Aspect ratio**: 9:16 (mobile/story, default), 3:4 (portrait), 1:1 (square), 16:9 (banner)
- **Style/theme**: see references/themes.md
- **Physical size** when relevant: e.g. 100cm × 178cm exhibition poster, roll-up banner, booth backdrop

Pre-fill from conversation context and user memory when possible.

If this is a revision, identify the latest user-approved poster before editing.
Read `references/quality-and-delivery.md` and lock all unaffected geometry,
copy, assets, and visual style as invariants.

## Step 2: Generate Poster HTML

Write a **single self-contained HTML file using only plain HTML + CSS** for a
static poster (no React, Babel, Tailwind CDN, or runtime CDN assets). Embed or
localize required fonts and images because external resources do not render
reliably in headless capture or clipboard export. If the user explicitly asks
for an interactive poster generator, follow the generator export contract in
`references/quality-and-delivery.md`.

### Design Principles

1. **Visual hierarchy**: Title largest → date/venue → description → details → organizer
2. **Whitespace**: generous padding, don't cram
3. **Typography**: bold display font for title, clean sans for body
4. **CJK support**: use a verified local/system CJK stack or embed the required font; do not depend on a runtime font CDN
5. **Color**: use the event's brand palette, max 3-4 colors. For LovStudio/手工川 work, use Warm Academic (`#CC785C`, `#F9F9F7`, `#181818`) and canonical brand assets.
6. **Decorative elements**: subtle geometric shapes, gradients, or patterns — not clipart
7. **Physical scan behavior**: for exhibition posters, roll-up banners, and booth graphics, place QR codes in the top or eye-level third when possible. Bottom-only QR codes are easy to block by tables, crowds, or bags.
8. **QR restraint**: QR codes usually explain themselves. Prefer large QR blocks with concise labels like "官网" and "微信"; avoid redundant "扫码/Scan" instructions unless the brief explicitly asks for them.
9. **Poster, not webpage**: avoid stacking too many cards. For premium exhibition work, make the QR area, portrait/product image, title, and value proposition share one visual system instead of looking like separate UI panels.
10. **Brand legibility**: domain/brand text may be stylized, but inspect whether line breaks hurt recognition. If using split display text (e.g. `SKILL` / `.AI`), make it intentional and visually stronger than an accidental wrap.
11. **Approved-layout stability**: after approval, treat revisions as a local delta. Do not redesign unrelated sections to solve one QR, spacing, portrait, or copy issue.

### File Structure

```
{output_dir}/
├── poster.html       # Editable source (mobile-first, browser-previewable)
└── poster.png        # Rendered output
```

Write to user's current working directory or specified output path.

### HTML Template

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --terracotta: #CC785C;
      --terracotta-light: #E8A68E;
      --warm: #F9F9F7;
      --charcoal: #181818;
      --charcoal-light: #4A4A4A;
    }

    body {
      width: 100%; max-width: 480px; margin: 0 auto;
      font-family: 'PingFang SC', 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
      background: var(--warm);
      overflow-x: hidden;
    }

    .content {
      display: flex; flex-direction: column;
      min-height: 100vh;
      padding: 48px 24px 40px;
    }

    /* === POSTER SECTIONS — customize layout below === */
  </style>
</head>
<body>
  <div class="content">
    <!-- Title, date, venue, day cards, speakers, pricing, footer -->
    <!-- All content is plain HTML — easy to edit directly -->
  </div>
</body>
</html>
```

**KEY rules**:
- **No `<script>` tags** — pure HTML + CSS only. CDN scripts fail in headless renderer.
- **Mobile-first sizing** — use `max-width: 480px; margin: 0 auto` on body. Font sizes in px for mobile (e.g. title 36px, body 14px).
- **No `overflow: hidden`** on body — allows scrolling in browser preview.
- **CSS custom properties** for theme colors — easy to swap palettes.

## Step 3: Render to PNG

Use mobile viewport width with high scale factor:

```bash
python3 "$SKILL_IMAGE_CREATOR_DIR/scripts/render_to_png.py" \
  poster.html \
  -o poster.png \
  -W {viewport_width} -H {viewport_height} \
  --scale {scale}
```

Dimension mapping (viewport → rendered at scale):
| Ratio | -W  | -H  | --scale | Output pixels |
|-------|-----|-----|---------|---------------|
| 9:16  | 480 | 852 | 3       | 1440 × 2556  |
| 3:4   | 480 | 640 | 3       | 1440 × 1920  |
| 1:1   | 480 | 480 | 3       | 1440 × 1440  |
| 16:9  | 480 | 270 | 3       | 1440 × 810   |

For physical dimensions or non-standard ratios, preserve the exact ratio with a custom viewport. Example:

| Physical size | -W | -H | --scale | Output pixels |
|---------------|----|----|---------|---------------|
| 100cm × 178cm | 1000 | 1780 | 6 | 6000 × 10680 |

Use larger scale factors for print or large-format display. A 100cm-wide poster at 6000px is about 150 DPI, which is typically acceptable for exhibition viewing distance.

Always use **absolute file paths** when calling render_to_png.py.
Resolve `SKILL_IMAGE_CREATOR_DIR` from the installed `lov-image-creator` Skill;
do not hard-code a user home or one client-specific skills directory.

## Step 4: Display & Iterate

1. Use `Read` to display the PNG to the user
2. Run `open poster.png` to open in Preview
3. Do a visual self-review before reporting done:
   - Is the main title readable from a distance?
   - Are CJK line breaks intentional, with no awkward word splitting?
   - Are QR codes large enough and placed where people can actually scan?
   - Is there redundant explanatory text around QR codes?
   - Does the design feel like a poster system rather than a web layout screenshot?
   - Do portraits, product images, QR blocks, and title typography share a coherent visual language?
   - Does every required image appear in the final PNG, not only in browser preview?
   - If this is a revision, are all locked baseline regions unchanged?
4. If the poster contains QR codes, complete the final-artifact scan checks in
   `references/quality-and-delivery.md`, including representative phone widths.
5. If user wants changes or the self-review finds issues:
   - Content changes → edit the HTML directly
   - Style changes → edit the CSS
   - Re-render with the same command

## Notes

- For QR codes, use `lov-create-qrcode` and follow
  `references/quality-and-delivery.md`. Never report a source-code scan as final-poster verification.
- If user provides a reference image, analyze its layout/colors and replicate the style
- For print-quality output, use `--scale 4`
- The HTML is browser-previewable — open `poster.html` directly to see a mobile-width centered layout

## Runtime context (shared)

运行前读取本 Skill 包的 `skill.yaml`，由宿主提供 `skill-runtime/v1` 上下文。字段解析顺序为：当前请求、项目上下文、个人 Preferences、品牌 Profile、通用默认值。

- 只使用 Manifest 声明的字段；Profile 保存公开品牌事实，Preferences 保存个人工作偏好。
- `required: true` 字段缺失时，按 Manifest 的问题配置向用户提出一个聚焦问题；用户明确同意后再保存回答。
- 报错提供可复制的 `context_id`、字段路径与来源，诊断内容避开秘密、完整私人路径和原始配置。
