---
name: lov-landing-builder
description: >
  在目标仓库中把 Brand Spine、内容蓝图和视觉系统实现为真实可用的 Landing Page；适用于“直接重构首页代码”、“实现品牌官网”、"implement the branded landing page" 或 "build the real conversion path"。
license: MIT
compatibility: "Embedded module of lov-oh-my-landingpage; uses the target repository's native stack."
depends_on:
  - lov-branding-consistency
metadata:
  author: contributors
  version: "0.4.1"
  tags:
    - landing-page
    - frontend-implementation
    - design-system
    - accessibility
  dependencies: []
---

# 官网搭建 · Website Builder

Implement the approved brand, narrative, and art direction inside the real
repository. Preserve product semantics while making the identity systematic.

## Triggers

### Activate when

- 用户要直接实现或重构品牌官网、Landing Page、首页内容与真实转化路径。
- 用户要求把批准的 Brand Spine、文案、视觉和媒体落到现有项目。
- The user asks to implement a branded landing page or build its real conversion path.

### Do not activate when

- 用户明确只要只读评审、策略草案或视觉方向，不允许改代码。
- 用户未提供仓库且只需要可交接的品牌/内容蓝图。

## User Configuration

Resolve workspace, output, brand sources, locale, analytics, and asset paths
through `references/user-config.md`. Project-native conventions always win.

## Workflow

### Step 1: Inspect before editing

Read `$KIT_DIR/references/implementation-and-acceptance.md`. Identify:

- project instructions, git state, homepage route, rendering, and auth state;
- tokens, fonts, components, icons, layout, localization, and content sources;
- metadata, analytics, consent, sitemap, media pipeline, and legal patterns;
- native package manager, lint, typecheck, tests, build, and screenshot tooling.

Preserve unrelated changes. Extend coherent primitives instead of creating a
parallel one-page design system.

### Step 2: Map the Brand Spine into code

Create or extend reusable tokens for the approved semantic jobs:

- canvas, surface, text, accent, evidence, status, border, and focus colors;
- display/body type roles and responsive scale;
- layout width, grid, spacing rhythm, radii, shadows, and material treatment;
- motion duration/easing and reduced-motion states;
- product frames, buttons, links, cards only where structurally justified.

Token names express roles, not page-section accidents. Do not scatter one-off
values that make the signature impossible to maintain.

### Step 3: Implement the headline spine and stages

- Preserve one clear H1 and logical heading hierarchy.
- Let each section perform its narrative and brand role.
- Use stage-specific compositions instead of repeating a generic section wrapper.
- Keep the protagonist and flagship products visually dominant.
- Place proof beside the claim it supports.
- Use real content sources and preserve localization conventions.

### Step 4: Implement real actions

- Primary and repeated CTAs share a destination and mental model.
- Links navigate; buttons act; status indicators are not fake controls.
- Prompt inputs use a form, visible/programmatic label, loading/error/success,
  and a real handler.
- While IME composition is active, Enter accepts the candidate rather than
  submitting. Submit only after composition ends.
- Public/authenticated states reflect actual product behavior without flicker.

### Step 5: Integrate media as content

- Use real product screenshots, covers, outputs, and approved people/cases.
- Give hero/LCP media dimensions and correct priority.
- Provide mobile crop, responsive sources, alt/empty alt, poster, and fallback.
- Lazy-load below-the-fold assets and heavy third-party embeds.
- Keep meaningful HTML copy out of generated images.

### Step 6: Complete identity surfaces

Align with the same brand system:

- title, description, canonical, locale, and share media;
- header, favicon/Logo, footer, contact, legal, and resource links;
- empty, loading, success, error, unavailable, and reduced-motion states;
- analytics naming for meaningful intent and conversion success.

Do not treat metadata and error states as generic leftovers.

For Logo assets, compare intrinsic canvas/viewBox with visible artwork bounds,
then verify optical centering in the real header, hero, footer, and compact icon
sizes. Prefer correcting the canonical asset or a purposeful wrapper over
scattered negative margins. On a product Landing Page, keep the product identity
primary and the maker/parent-brand mark secondary unless the Brand Spine says
otherwise.

### Step 7: Verify natively

Run focused formatting/lint, typecheck, tests, production build, route checks,
headless interactions, and screenshots as available. Inspect 320 px, tablet, and
desktop. Test the full path from landing entry to result and return/recovery.

## Quality gate

- Brand decisions are encoded in reusable primitives, not isolated CSS tricks.
- The page expresses one narrative and visual world across all states.
- Primary actions and prompt inputs reach real results and are IME-safe.
- Responsive layouts preserve hierarchy, focus, and product legibility.
- Metadata, analytics, accessibility, performance, and evidence are accurate.
- Repository-native validation passes or remaining failures are reported precisely.

## Dependencies

Requires approved brand, strategy, and art-direction handoffs plus a target repository.

## Runtime context (shared)

运行前读取本 Skill 包的 `skill.yaml`，由宿主提供 `skill-runtime/v1` 上下文。字段解析顺序为：当前请求、项目上下文、个人 Preferences、品牌 Profile、通用默认值。

- 只使用 Manifest 声明的字段；Profile 保存公开品牌事实，Preferences 保存个人工作偏好。
- `required: true` 字段缺失时，按 Manifest 的问题配置向用户提出一个聚焦问题；用户明确同意后再保存回答。
- 报错提供可复制的 `context_id`、字段路径与来源，诊断内容避开秘密、完整私人路径和原始配置。
