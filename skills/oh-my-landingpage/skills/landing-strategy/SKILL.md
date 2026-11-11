---
name: lov-landing-strategy
description: >
  在既定 Brand Spine 下为 Landing Page 设计叙事、标题主线、内容取舍、真实证据和转化路径；适用于“重写品牌首页文案”、“规划官网内容”、"compose the landing story" 或 "clarify the value proposition"。
license: MIT
compatibility: "Embedded module of lov-oh-my-landingpage."
depends_on:
  - lov-branding-consistency
metadata:
  author: contributors
  version: "0.4.1"
  tags:
    - landing-page
    - brand-narrative
    - content-strategy
    - conversion-copy
  dependencies: []
---

# 官网叙事 · Website Story

Turn a Brand Spine and product truth into a visitor-facing story. The blueprint
must feel authored for this brand, not assembled from a standard section list.

## Triggers

### Activate when

- 用户要重写品牌首页文案、规划 Landing Page 内容、叙事、章节或转化路径。
- 用户觉得首页信息很多，但访客看不懂主张、记不住重点或不知道下一步。
- The user asks to compose a landing story, plan homepage content, or clarify a value proposition.

### Do not activate when

- 用户已有批准的 Brand Spine 和完整内容蓝图，只需要视觉或代码实现。
- 用户只要脱离产品证据的广告口号，不涉及完整页面决策路径。

## User Configuration

Resolve market, audience, locale, offer, brand sources, and conversion defaults
through `references/user-config.md`. The current task and product evidence win.

## Workflow

### Step 1: Consume the brand handoff

Read `$KIT_DIR/references/brand-system.md` and
`$KIT_DIR/references/landing-system.md`. Confirm:

- brand thesis, belief, promise, mechanism, difference, and boundary;
- verbal identity, content identity, signature idea, and proof behavior;
- audience tension, primary conversion, next state, and acquisition context;
- preserve/strengthen/retire decisions for an existing page.

If the Brand Spine is absent or generic, return to the brand module before copy.
Do not smuggle unapproved brand strategy into headlines.

### Step 2: Define the visitor movement

Write the page's transformation in four lines:

1. what the visitor arrives believing, feeling, or trying to do;
2. which brand point of view reframes that situation;
3. which product experience and proof make the reframe credible;
4. what action advances the visitor into the promised state.

This is the story logic. It is not public copy.

### Step 3: Compose the headline spine

Draft the H1 and section headlines as one continuous argument. When read alone,
they should reveal:

- a memorable belief or possibility;
- what the brand actually makes or enables;
- how it works through concrete product behavior;
- why it is credible and meaningfully different;
- the natural next step.

Avoid headings that are only taxonomy: “功能”“解决方案”“客户评价”“常见问题”.
Use body copy for mechanism, constraints, and evidence—not internal reasoning.

### Step 4: Select the content stages

Choose the smallest number of stages that gives the story rhythm. A stage may be:

- brand idea and product orientation;
- immediate creation/action entry;
- flagship product or artifact on a large stage;
- product constellation or journey;
- direct demonstration or before/after transformation;
- creator/customer outcome with verified attribution;
- craft, principle, or founder perspective when it earns trust;
- evidence, availability, pricing, objection, or closing action.

Do not give every product, feature, or proof equal weight. Define one protagonist,
supporting cast, and transitions. Alternate scale and density intentionally.
Treat App, web, CLI, Skill, platform, chip, package, and download choices as an
availability/action stage unless a choice materially changes product value or
mechanism. The existence of two delivery modes does not justify a two-product
story, comparison grid, or hero fork.

### Step 5: Design the copy system

Produce:

- one hero route: eyebrow if useful, H1, support, primary CTA, optional proof cue;
- section headlines and one-sentence purpose;
- product names, captions, labels, and CTA vocabulary;
- microcopy for loading, success, error, authentication, and unavailable states;
- prohibited phrases that violate voice, evidence, or category clarity.

Run a distribution-inversion check: remove platform and install labels from the
headline spine. The remaining story must still make category, value, mechanism,
proof, and primary action clear.

The hero may be belief-led, outcome-led, or action-led. Across the first viewport,
visitors must still locate category, relevance, proof cue, and next action.

### Step 6: Map claims to proof

For every public claim, identify its proof level:

1. direct working product experience;
2. real product artifact, screenshot, or demo;
3. attributable case or customer outcome;
4. sourced metric with definition and date;
5. specific mechanism explanation;
6. unsupported assertion, which must be removed or held internally.

Generated visuals can explain or evoke; they do not upgrade evidence.

### Step 7: Design the action system

- Define one primary conversion as a user goal and a real destination.
- Use secondary actions only for a distinct readiness level.
- Repeated CTAs keep the same language, mental model, and next state.
- Use a prompt box only when the entered intent reaches a real result.
- Specify loading, success, error, login, and return/recovery behavior.

### Step 8: Produce the blueprint

Return an internal handoff:

| Order | Stage and visitor question | Headline | Core content | Proof/media | Action | Brand role |
|------:|----------------------------|----------|--------------|-------------|--------|------------|

Add hero copy, headline spine, copy rules, CTA/state copy, evidence gaps, and a
`keep internal` list. Pass it to art direction and builder; never render the
planning table in the final page.

## Quality gate

- The headline spine forms a distinct, coherent story.
- Brand belief and product reality appear together; neither becomes empty poetry.
- One protagonist and one primary action are clear.
- Each stage changes the visitor's understanding, trust, or readiness.
- Claims and proof match; context and planning notes remain internal.
- The copy is difficult to transplant unchanged onto a competitor page.

## Dependencies

Requires a completed brand handoff from `lov-landing-brand`.

## Runtime context (shared)

运行前读取本 Skill 包的 `skill.yaml`，由宿主提供 `skill-runtime/v1` 上下文。字段解析顺序为：当前请求、项目上下文、个人 Preferences、品牌 Profile、通用默认值。

- 只使用 Manifest 声明的字段；Profile 保存公开品牌事实，Preferences 保存个人工作偏好。
- `required: true` 字段缺失时，按 Manifest 的问题配置向用户提出一个聚焦问题；用户明确同意后再保存回答。
- 报错提供可复制的 `context_id`、字段路径与来源，诊断内容避开秘密、完整私人路径和原始配置。
