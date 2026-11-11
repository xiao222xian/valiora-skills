---
name: lov-landing-review
description: >
  从品牌记忆、内容叙事、真实证据、转化路径、UI 细节和技术质量审查并修复 Landing Page；适用于“为什么首页没有品牌感”、“评审并优化官网”、"review this landing page" 或 "fix homepage quality"。
license: MIT
compatibility: "Embedded module of lov-oh-my-landingpage; optional browser or headless inspection."
depends_on:
  - lov-branding-consistency
metadata:
  author: contributors
  version: "0.4.1"
  tags:
    - landing-page
    - brand-review
    - conversion-audit
    - quality-assurance
  dependencies: []
---

# 官网审校 · Website Review

Evaluate the page as a public brand and a working product. Diagnose causal
problems, fix them when the selected pipeline allows edits, and verify again.

## Triggers

### Activate when

- 用户问“为什么首页没有品牌感”“为什么一言难尽”，并期待分析后直接修复。
- 用户要评审 Landing Page 的品牌、文案、内容、UI、转化或技术质量。
- The user asks to review a landing page, diagnose weak brand identity, or fix homepage quality.

### Do not activate when

- 用户只要纯后端接口、数据库迁移或与页面体验无关的代码审查。
- 用户只需要一张独立素材的审美反馈，不涉及完整页面。

## User Configuration

Resolve expected brand sources, market, viewport, analytics, and target path
through `references/user-config.md`. Current page and repository are the evidence.

## Workflow

### Step 1: Capture user-visible truth

Inspect the exact live route or local page, repository state, supplied screenshot,
and real action destinations. Record desktop and 320 px evidence when possible.
Do not infer quality from HTTP 200 or compilation alone.

### Step 2: Review in causal order

Read `$KIT_DIR/references/brand-system.md` and
`$KIT_DIR/references/implementation-and-acceptance.md`. Audit these layers:

1. **Brand memory** — recognizable thesis, signature, product/outcome, logo-swap test.
2. **Orientation** — category, relevance, first-viewport hierarchy, and next action.
3. **Product hierarchy** — value, mechanism, proof, and distribution/access roles.
4. **Narrative** — headline spine, protagonist, stage progression, and pacing.
5. **Content** — product truth, useful specificity, omission, and internal-context leakage.
6. **Trust** — claim/proof match, authentic assets, sources, dates, and attribution.
7. **Action** — CTA clarity, real destination, state continuity, and conversion feedback.
8. **Visual system** — product/style fit, silhouette, typography, scale,
   composition, product staging, media continuity, Logo geometry, controls, and
   state design.
9. **Mechanics** — mobile, keyboard, IME, accessibility, performance, SEO,
   analytics, route integrity, auth, and error/recovery paths.

Do not begin by polishing spacing if the page lacks a brand thesis or story.

### Step 3: Run memory tests

- **Five-second recall:** belief/possibility, product/outcome, signature.
- **Logo-swap:** would a competitor Logo still fit without contradiction?
- **Headline spine:** do headings alone form an argument?
- **Silhouette:** does blurred scale/rhythm look intentional and distinctive?
- **Behavior:** do CTA, loading, success, and failure sound like one brand?
- **Distribution inversion:** after hiding platform/install labels, do value and
  mechanism remain clear and dominant?
- **Logo geometry:** do visible artwork bounds—not just the file canvas—look
  optically centered at actual header and compact sizes?
- **Style fit:** can the main visual decisions be traced to this product,
  audience, use situation, trust/risk, and existing equity rather than a generic
  trend or the previous project?

Record observed evidence, not only scores.

### Step 4: Prioritize root causes

For each issue record:

| Severity | Evidence | Root cause | Visitor/brand impact | Fix | Verification |
|----------|----------|------------|----------------------|-----|--------------|

Prioritize in this order: false or broken behavior, missing orientation, generic
or contradictory identity, unsupported claims, narrative/content gaps, action
friction, responsive/accessibility failures, then polish.

### Step 5: Fix through the correct module

When mutations are allowed:

- identity or positioning cause → `landing-brand`;
- narrative, copy, evidence, or CTA cause → `landing-strategy`;
- hierarchy, UI grammar, media, or product staging cause → `landing-art-direction`;
- code, state, route, accessibility, performance, or metadata cause → `landing-builder`.

Do not patch symptoms with isolated slogans, gradients, oversized type, or extra
sections. Re-run the affected downstream modules after changing the Brand Spine.

### Step 6: Re-verify the whole path

Test landing entry → first-viewport understanding → product/proof progression →
primary action/input → next state → feedback → return/recovery. Repeat for real
public/authenticated states, keyboard, IME, 320 px, desktop, and broken media.

## Quality gate

- Findings cite user-visible or repository evidence.
- Brand, narrative, visual, and technical symptoms are traced to root causes.
- Fixes preserve truthful content and working product semantics.
- Memory, meaning, and mechanics all pass after changes.
- No internal context, synthetic proof, dead control, or misleading state ships.
- Audit-only requests return prioritized findings without mutations.

## Dependencies

Uses target page/repository evidence and all relevant Skill Kit handoffs.

## Runtime context (shared)

运行前读取本 Skill 包的 `skill.yaml`，由宿主提供 `skill-runtime/v1` 上下文。字段解析顺序为：当前请求、项目上下文、个人 Preferences、品牌 Profile、通用默认值。

- 只使用 Manifest 声明的字段；Profile 保存公开品牌事实，Preferences 保存个人工作偏好。
- `required: true` 字段缺失时，按 Manifest 的问题配置向用户提出一个聚焦问题；用户明确同意后再保存回答。
- 报错提供可复制的 `context_id`、字段路径与来源，诊断内容避开秘密、完整私人路径和原始配置。
