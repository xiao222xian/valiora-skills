---
name: lov-oh-my-landingpage
description: >
  从品牌内核出发初始化或重构可运行的 Landing Page，统一定位、叙事、文案、UI、媒体、实现与验收。Use when the user asks to create, optimize, rebrand, or fix a homepage，尤其适用于“产品价值不清”“首页没有品牌感”或“视觉与产品不匹配”。
license: MIT
compatibility: "Agent runtime with repository tools; optional web research, image generation, and browser or headless visual inspection."
depends_on:
  - lov-branding-consistency
metadata:
  author: contributors
  version: "0.4.1"
  tags:
    - landing-page
    - brand-system
    - frontend-design
    - conversion
  dependencies: []
---

# 官网小能手 · Website Whiz

Turn a product truth into a recognizable public brand experience, then implement
it as a usable Landing Page. The page is not a stack of fashionable sections. It
is the brand performing in public: what it believes, what it makes possible, how
it behaves, what proves it, and what the visitor can do next.

## Triggers

### Activate when

- 用户说“从品牌角度重构官网”“首页没有品牌感”“整体优化形象、UI、文案和内容”。
- 用户说“创建 Landing Page”“优化这个首页”“参考优秀品牌官网重做，但不要照抄”。
- The user asks to build a branded landing page, rebrand a homepage, or improve its identity, story, UI, and conversion.

### Do not activate when

- 用户只要后台表格、设置页或与品牌表达和营销转化无关的业务组件。
- 用户只要独立 Logo、海报或视频，不涉及完整页面体验。
- 用户明确只要发布已有 Skill 或处理部署故障，不改变页面产品。

## Product thesis

- **Brand before layout.** Establish the brand truth and expression rules before
  choosing hero styles, section templates, or visual effects.
- **One public idea.** A strong page leaves one recognizable thesis, not twelve
  equally loud features.
- **Content is product design.** What the page omits, stages, proves, and repeats
  matters as much as its CSS.
- **Conversion is a brand behavior.** The primary action must feel like the next
  chapter of the promise, not a button pasted onto a campaign page.
- **Distinctive, not derivative.** Learn structure and interaction grammar from
  references; never import another brand's identity.
- **Style follows product context.** No visual style is universally better.
  Derive it from the product category, audience, use situation, trust and risk,
  existing brand equity, and the evidence available to the page.

## Non-negotiable contract

- Communication context is not automatically public copy. Names, private
  anecdotes, competitor notes, bracketed explanations, and working assumptions
  remain internal unless visitors need them to understand, trust, or act.
- Brand claims come from product, founder, customer, or documented evidence.
  Do not invent values, heritage, customers, quotes, numbers, awards, or traction.
- Existing routes, design primitives, content sources, and working interactions
  take precedence over novelty. Reconcile before replacing.
- Every CTA, form, prompt box, download badge, product tile, case, and media
  control has a real destination or a clearly labeled development state.
- Product value, product mechanism, proof, and distribution are different jobs.
  Apps, web surfaces, CLIs, Skills, package managers, platforms, and download
  variants remain access or distribution modes unless they materially change
  the promise or mechanism. Do not promote them into product protagonists or
  feature claims merely because several choices exist.
- A requested mood is an input, not the visual answer. Resolve it through the
  product, audience, situation, and brand evidence; never reuse the previous
  project's style as a default or force a fashionable aesthetic onto a mismatch.
- Optimization means diagnose, implement, and verify unless the user explicitly
  requests a read-only audit.

## User Configuration

Resolve workspace, brand sources, market, output, media, analytics, and design
preferences through `$KIT_DIR/references/user-config.md`. Explicit task context
and repository truth always win.

## Skill Kit Modules

Load every selected module completely before acting:

- `$SKILL_DIR/skills/landing-brand/SKILL.md` — brand truth, Brand Spine, verbal identity, visual signature, content principles, and interaction character.
- `$SKILL_DIR/skills/landing-strategy/SKILL.md` — audience tension, narrative, headline spine, proof, section architecture, and conversion path.
- `$SKILL_DIR/skills/landing-art-direction/SKILL.md` — visual world, UI grammar, product staging, imagery, motion, and media production.
- `$SKILL_DIR/skills/landing-builder/SKILL.md` — repository-aware implementation, brand tokens, real content, responsive behavior, SEO, and analytics.
- `$SKILL_DIR/skills/landing-review/SKILL.md` — brand-memory review, visitor-path audit, technical gates, fixes, and regression verification.

`kit.yaml` is the executable module and pipeline contract.

## Workflow (MANDATORY)

### Step 0: Resolve the real surface

- Verify `kit.yaml`, selected modules, and referenced documents.
- Inspect the exact repository, route, URL, screenshots, files, and brand assets
  provided by the user before broad exploration.
- Read project instructions and current git state. Preserve unrelated work.
- Identify whether the target is a corporate brand homepage, product Landing
  Page, campaign, portfolio, creator platform, or authenticated product entry.
- Ask one focused question through the host's user-input capability (for example
  `AskUserQuestion` where available) only when an unresolved choice would
  materially change the public result; otherwise proceed from repository truth.

### Step 1: Select the pipeline

| Situation | Pipeline |
|-----------|----------|
| New page or product launch | `initialize` |
| Existing page should become substantially better | `optimize` |
| Identity, positioning, copy, and UI all need a new direction | `rebrand` |
| Brand is stable; narrative and copy need a new edition | `refresh-copy` |
| Brand is stable; visual media need renewal | `refresh-assets` |
| Explicit read-only assessment | `audit` |

If the user asks why the page is weak, select `optimize`: explain the root cause,
then fix it. Select `audit` only when edits are explicitly excluded.

### Step 2: Establish the source hierarchy

Create an internal truth ledger before writing public copy:

1. approved brand guide, founder/product truth, and existing design system;
2. actual product behavior, repository content, live routes, and real assets;
3. verified customer evidence, metrics, cases, and current public statements;
4. inferred opportunity, clearly marked internal;
5. evidence gaps that must not become production claims.

Separate every useful input into `internal context`, `publishable claim`,
`verified proof`, or `open evidence`. Never paste the raw brief into the page.

### Step 3: Build the brand foundation

Run the brand module before downstream design. Produce a compact Brand Spine:

- category and audience tension;
- belief, promise, mechanism, and meaningful difference;
- personality expressed as observable behavior;
- one brand thesis the page should leave in memory;
- verbal rules, visual signature, content principles, interaction character;
- proof anchors, boundaries, and the action that completes the promise.

Classify the offer's product value, mechanism, proof, and distribution/access
modes before composing the page. A local architecture may be a meaningful
mechanism; a macOS download button is still a delivery control.

For an existing brand, distinguish what is equity to preserve, inconsistency to
repair, and generic residue to retire. Read
`$KIT_DIR/references/brand-system.md` for the full decision model.

### Step 4: Compose the public story

Use the strategy module to turn the Brand Spine into a narrative rather than a
feature inventory. Define:

- the visitor's initial state and desired movement;
- a headline spine that tells the story when only headings are scanned;
- the smallest section sequence needed to reveal belief, product, proof, and action;
- one primary conversion with a real next state;
- proof paired to every meaningful claim;
- copy that sounds like this brand and does not expose planning context.

Keep installation, platform, package, pricing, and access-mode choices in an
availability or action stage unless one of them changes the actual product
promise. Run a distribution-inversion check: after removing platform labels,
the hero and headline spine must still explain why the product matters.

The first viewport may lead with a brand belief, an outcome, or an action, but it
must still make category, relevance, and next step discoverable without guesswork.

### Step 5: Create one visual world

Use the art-direction module to translate the same Brand Spine into UI and media:

- typographic roles, palette, surfaces, spacing, composition, icon and control grammar;
- one ownable visual motif repeated with restraint;
- stage hierarchy that gives major ideas different visual weight;
- real product imagery and product-specific media treatment;
- motion that expresses character and has a reduced-motion equivalent.

Before selecting a style, write a compact style-fit rationale covering product
category and mechanism, audience and readiness, use environment and emotional
state, trust/risk/accessibility needs, existing equity, and authentic assets.
Then choose one visual world and reject at least two plausible but less suitable
directions. Translate any requested adjectives into product-specific materials,
density, typography, composition, imagery, and interaction behavior.
Audit Logo assets by visible ink bounds and optical alignment rather than
trusting the SVG viewBox or transparent canvas to be visually centered.

Do not solve a brand problem with a generic card grid, default gradient, stock
illustration pack, or another company's recognizable visual language.

### Step 6: Implement the brand as a product

Use the builder module to make the approved narrative and visual system real:

- map brand decisions into reusable tokens and components;
- preserve semantic HTML, accessibility, localization, and design-system integrity;
- make primary and repeated actions share one mental model and destination;
- keep prompt inputs IME-safe and connect them to a real result;
- integrate authentic assets with correct crop, loading, alt, and responsive behavior;
- align metadata, sharing, footer, analytics, and legal surfaces with the same identity.

### Step 7: Validate memory, meaning, and mechanics

Use the review module and `$KIT_DIR/references/implementation-and-acceptance.md`.
Verify three layers:

1. **Memory:** after a short exposure, can a visitor recall the brand thesis,
   one signature, and one thing the brand enables?
2. **Meaning:** can they identify category, relevance, proof, and next action?
3. **Mechanics:** do routes, forms, keyboard, IME, responsive states, performance,
   metadata, analytics, and error states work?

Run repository-native quality gates and inspect 320 px, tablet, and desktop.
Include at least one common 1280-1440 px desktop width so hero wrapping and Logo
placement are observed at realistic sizes. Fix causal problems, then re-run the
complete visitor path. When a public page is deployed, read back the production
route rather than treating a local build as online verification.

### Step 8: Report the outcome

Lead in the user's language with what changed. Include:

- page/route and primary visitor path;
- Brand Spine and the signature choices expressed in copy, content, UI, and media;
- authentic versus generated assets and remaining proof gaps;
- commands, viewport/path checks, and observed results;
- production-only follow-up, without presenting it as completed.

## References

- `$KIT_DIR/references/brand-system.md` — brand truth, Brand Spine, expression systems, and memory tests.
- `$KIT_DIR/references/landing-system.md` — narrative, copy, proof, section selection, and conversion.
- `$KIT_DIR/references/visual-and-media.md` — art direction, product staging, imagery, video, and asset quality.
- `$KIT_DIR/references/implementation-and-acceptance.md` — code, accessibility, performance, SEO, analytics, and QA.
- `$KIT_DIR/references/user-config.md` — portable initialization and preference schema.
- `$KIT_DIR/references/research.md` — source-backed principles and freshness notes.

## Dependencies

No fixed frontend framework. Use the target repository's package manager, design
system, build commands, and test stack. Research, media generation, and visual
inspection are optional capabilities selected only when the task needs them.

## Runtime context (shared)

运行前读取本 Skill 包的 `skill.yaml`，由宿主提供 `skill-runtime/v1` 上下文。字段解析顺序为：当前请求、项目上下文、个人 Preferences、品牌 Profile、通用默认值。

- 只使用 Manifest 声明的字段；Profile 保存公开品牌事实，Preferences 保存个人工作偏好。
- `required: true` 字段缺失时，按 Manifest 的问题配置向用户提出一个聚焦问题；用户明确同意后再保存回答。
- 报错提供可复制的 `context_id`、字段路径与来源，诊断内容避开秘密、完整私人路径和原始配置。

## 通用反馈闭环

用户在 Skill 驱动任务中提出修改意见时，继续当前产物前必须执行：

1. 先判断意见是 `task-specific`（仅本次）还是 `reusable`（可跨任务复用）。
2. `task-specific` 只修改当前任务，不改 Skill。
3. `reusable` 先确定作用域：领域规则先更新对应 canonical Skill；适用于所有 Skill 的规则先更新共享规范。
4. 完成规则更新、版本、lint 与分发核验后，再把修改应用到当前任务。
5. `reusable` 修改会使此前的“确认”“继续”“发吧”失效；完成当前产物修改和回读后必须停下，等待用户下一步指示，不自动进入发布、提交或其他外部写入。
