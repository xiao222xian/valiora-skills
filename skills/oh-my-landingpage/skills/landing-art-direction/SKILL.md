---
name: lov-landing-art-direction
description: >
  把 Brand Spine 转译为 Landing Page 的整体视觉世界、UI 语法、产品舞台、图片、视频和动效系统；适用于“重做官网视觉形象”、“统一首页质感”、"create brand-led art direction" 或 "refresh website visuals"。
license: MIT
compatibility: "Embedded module of lov-oh-my-landingpage; optional image and video generation tools."
depends_on:
  - lov-branding-consistency
metadata:
  author: contributors
  version: "0.4.1"
  tags:
    - landing-page
    - brand-expression
    - art-direction
    - media-system
  dependencies: []
---

# 官网视觉 · Website Art Direction

Translate the Brand Spine and content blueprint into one coherent visual world.
UI, media, typography, stage hierarchy, and motion must express the same idea.

## Triggers

### Activate when

- 用户要重做官网视觉形象、首页 UI、图片、视频、动效或产品展示方式。
- 用户认为页面功能正确但通用、廉价、卡片化，缺少品牌辨识度和舞台感。
- The user asks for brand-led art direction, product staging, or a coherent landing-page visual system.

### Do not activate when

- 用户只要脱离页面的独立 Logo 或海报。
- 用户已有批准且可实现的视觉系统，只需要代码集成或技术修复。

## User Configuration

Resolve brand guide, assets, market, media provider, host, and output directory
through `references/user-config.md`. Real brand and product assets take priority.

## Workflow

### Step 1: Consume brand and narrative

Read `$KIT_DIR/references/brand-system.md` and
`$KIT_DIR/references/visual-and-media.md`. Confirm:

- brand thesis, personality behaviors, visual rules, boundary, and signature idea;
- headline spine, protagonist, stage hierarchy, proof, and action system;
- product category, audience, use situation, trust/risk, and accessibility needs;
- existing design equity, product UI, asset quality, and repository constraints.

Do not begin with a style trend or a competitor screenshot.

### Step 2: Define the visual world

Make implementation-ready decisions for:

- display/body typography and scale contrast;
- semantic palette and dominant background/surface relationship;
- container, grid, negative space, density, and vertical rhythm;
- borders, corners, shadows, texture, and material behavior;
- icon family, product-frame treatment, controls, focus, and status states;
- one signature motif with a restraint rule;
- motion character and reduced-motion equivalent.

Each rule must connect to brand meaning and reject alternatives. “Clean, modern,
premium” is not an art direction.

Build a style-fit rationale before choosing the visual world. Weigh product
mechanism, audience readiness, use environment and emotional state, required
trust, risk and accessibility, existing equity, and authentic assets. Treat
requested adjectives as constraints to interpret, not universal prescriptions.
Do not inherit the previous project's palette, material, density, or interaction
grammar. Reject at least two plausible directions and state why they fit less.
Inspect Logo and icon assets by visible ink bounds, transparent padding, and
optical alignment at their actual rendered sizes; a centered SVG viewBox is not
proof that the mark looks centered.

### Step 3: Design stage hierarchy

Assign a visual role to every content stage:

- **Monument:** one or two defining ideas/products with exceptional scale.
- **Workbench:** interactive product or process shown with operational detail.
- **Gallery:** multiple outputs or products with disciplined variation.
- **Evidence:** cases, metrics, quotes, sources, and demos optimized for trust.
- **Bridge:** transitions that reset rhythm and advance the headline spine.
- **Action:** decisive CTA surface that resolves the story.

Do not render every stage as the same rounded card grid. Use contrast in scale,
alignment, density, surface, and media behavior while retaining one system.

### Step 4: Stage the product truthfully

- Prefer real screenshots, outputs, covers, demos, and interface states.
- Show the product at a readable scale; do not bury it inside decorative chrome.
- Use framing and annotation to reveal mechanism without falsifying UI.
- Keep generated product-stage mockups clearly illustrative, never evidence.
- Define desktop/mobile crop and fallback for every major asset.

### Step 5: Plan or create media

Follow `$KIT_DIR/references/visual-and-media.md`:

1. inventory approved authentic assets;
2. identify narrative/media gaps by section job;
3. generate only decorative or explanatory media that may honestly be synthetic;
4. establish continuity across light, material, palette, subject, and crop;
5. inspect, crop, compress, name, and export implementation-ready variants.

Real customers, product UI, metrics, awards, logos, and testimonial evidence must
come from approved sources.

### Step 6: Produce the art handoff

Deliver:

- style-fit rationale, selected direction, and rejected alternatives;
- visual-world statement and design rules;
- token map for color, typography, spacing, radius, shadow, and motion;
- stage-by-stage composition notes for desktop and 320 px;
- signature motif rules and reduced-motion behavior;
- asset manifest with truth status, source, path, crop, alt, loading, and fallback;
- explicit anti-patterns for this brand.
- Logo/wordmark placement notes for header, hero, footer, and compact icon use.

## Quality gate

- A blurred silhouette still has intentional hierarchy and rhythm.
- The signature idea connects meaning and form without becoming wallpaper.
- Copy, product, media, controls, and states inhabit one visual world.
- The visual world is appropriate to this product, audience, situation, and
  trust context; a different product would not receive the same default styling.
- Real product evidence remains legible and honest.
- Mobile is recomposed, not merely compressed.
- Swapping the Logo for a competitor creates a visible mismatch.

## Dependencies

Requires brand and strategy handoffs. Media generation is optional.

## Runtime context (shared)

运行前读取本 Skill 包的 `skill.yaml`，由宿主提供 `skill-runtime/v1` 上下文。字段解析顺序为：当前请求、项目上下文、个人 Preferences、品牌 Profile、通用默认值。

- 只使用 Manifest 声明的字段；Profile 保存公开品牌事实，Preferences 保存个人工作偏好。
- `required: true` 字段缺失时，按 Manifest 的问题配置向用户提出一个聚焦问题；用户明确同意后再保存回答。
- 报错提供可复制的 `context_id`、字段路径与来源，诊断内容避开秘密、完整私人路径和原始配置。
