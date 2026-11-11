---
name: lov-landing-brand
description: >
  为 Landing Page 提炼真实品牌内核并建立 Brand Spine、语言人格、视觉签名、内容原则与交互性格；适用于“从品牌角度重构官网”、"define the brand system" 或 "make this homepage recognizable"。
license: MIT
compatibility: "Embedded module of lov-oh-my-landingpage."
depends_on:
  - lov-branding-consistency
metadata:
  author: contributors
  version: "0.4.1"
  tags:
    - landing-page
    - brand-strategy
    - verbal-identity
    - design-system
  dependencies: []
---

# 官网品牌 · Website Brand

Establish the public identity system that every later page decision must express.
Do not invent a brand from adjectives. Extract it from product truth, founder
intent, audience tension, behavior, evidence, and the strongest existing equity.

## Triggers

### Activate when

- 用户要从品牌角度重构官网、统一整体形象、语言、内容和 UI。
- 用户觉得首页“什么都有但没有品牌感”，或换掉 Logo 后像任何竞品。
- The user asks to define a brand system or make a landing page distinctive and recognizable.

### Do not activate when

- 用户已有批准且足够具体的 Brand Spine，只需按它实现页面。
- 用户只要注册商标、公司命名或独立 Logo 文件，不涉及 Landing Page 表达系统。

## User Configuration

Resolve persistent identity sources, brand guide, asset directory, market, and
locale through `references/user-config.md`. Current product evidence wins over a
stale profile or generic brand adjectives.

## Workflow

### Step 1: Audit brand truth and equity

Read `$KIT_DIR/references/brand-system.md`. Inspect, in order:

1. approved brand/product documents and founder statements;
2. real product behavior and shipped user experience;
3. existing visual system, assets, domains, routes, and public language;
4. real customer use, proof, support patterns, and community vocabulary;
5. references and competitors, treated only as category context.

For existing pages, sort observations into:

- `preserve` — recognizable, truthful equity;
- `strengthen` — promising but inconsistent expression;
- `retire` — generic, contradictory, or obsolete residue;
- `unknown` — evidence needed before a public claim.

### Step 2: Define the Brand Spine

Produce one evidence-backed sentence for each:

| Element | Decision |
|---------|----------|
| Category | The frame visitors already understand |
| Audience tension | The unresolved struggle or aspiration |
| Belief | The point of view the brand acts on |
| Promise | The change it commits to enable |
| Mechanism | How the product makes that change real |
| Difference | A meaningful choice, not a comparative adjective |
| Personality | Observable behavior under real constraints |
| Proof | The strongest current reasons to believe |
| Boundary | What the brand deliberately does not become |
| Action | The next step that completes the promise |

Compress these into one **brand thesis** that can guide the page and survive a
five-second exposure. It may be visitor-facing or remain the internal standard;
do not force a strategy sentence into the hero verbatim.

Separate product value and mechanism from distribution. App, web, CLI, Skill,
package, platform, and download variants are usually ways to acquire or operate
the product, not meaningful differences by themselves. Promote one only when
evidence shows it changes the promise, audience job, capability, or boundary.

### Step 3: Define the expression systems

Specify five connected systems:

1. **Verbal identity** — vocabulary, sentence rhythm, confidence level, naming,
   CTA verbs, proof language, and phrases this brand avoids.
2. **Visual identity** — typographic character, palette logic, material/surface
   language, composition, image treatment, icon family, signature motif, and the
   product-specific evidence that makes this direction appropriate.
3. **Content identity** — which stories deserve the largest stage, how products
   and people are framed, and what content is intentionally omitted.
4. **Interaction character** — how the brand invites, responds, confirms,
   handles failure, and moves; include reduced-motion behavior.
5. **Evidence behavior** — how claims, demos, sources, dates, and uncertainty are
   shown without turning the page into compliance prose.

Rules must be concrete enough to reject plausible alternatives. Replace “modern”
or “premium” with observable choices such as editorial scale contrast, direct
verbs, paper-like surfaces, restrained motion, or exposed product artifacts.
No style is globally preferred: record how category, audience, use situation,
trust/risk, existing equity, and real assets support the selected direction and
why at least two attractive alternatives are less suitable here.

### Step 4: Choose a signature idea

Select one ownable page-level device that joins meaning and form. It may be a
recurring material, transformation, frame, gesture, spatial rule, or product
artifact. It must:

- express the brand thesis rather than decorate it;
- work in hero, transitions, product stages, and sharing media;
- remain legible at 320 px and with reduced motion;
- avoid another brand's recognizable trade dress;
- coexist with real product evidence.

### Step 5: Write the brand handoff

Deliver a compact handoff containing:

- source ledger and evidence gaps;
- preserve/strengthen/retire decisions;
- Brand Spine and one-sentence thesis;
- verbal, visual, content, interaction, and evidence rules;
- signature idea with desktop/mobile behavior;
- three `must feel like` and three `must never feel like` tests;
- implications for hero, section hierarchy, CTA, product staging, and proof.
- a product/mechanism/distribution classification that prevents delivery choices
  from displacing the brand thesis.

Pass the handoff to strategy, art direction, builder, and review. It is an
internal design contract, not a block of copy to paste into the page.

## Quality gate

- The brand thesis is specific, truthful, and traceable to evidence.
- Personality is described through behavior, not a bag of adjectives.
- Copy, content, visuals, and interaction express the same point of view.
- Visual style is justified by this product's context rather than inherited from
  a trend, reference, or previous project.
- One signature is memorable without overwhelming product proof.
- Swapping in a competitor's Logo would create visible contradictions.
- Private context and unsupported aspiration remain outside public copy.

## Dependencies

None beyond the containing Skill Kit and target brand/product evidence.

## Runtime context (shared)

运行前读取本 Skill 包的 `skill.yaml`，由宿主提供 `skill-runtime/v1` 上下文。字段解析顺序为：当前请求、项目上下文、个人 Preferences、品牌 Profile、通用默认值。

- 只使用 Manifest 声明的字段；Profile 保存公开品牌事实，Preferences 保存个人工作偏好。
- `required: true` 字段缺失时，按 Manifest 的问题配置向用户提出一个聚焦问题；用户明确同意后再保存回答。
- 报错提供可复制的 `context_id`、字段路径与来源，诊断内容避开秘密、完整私人路径和原始配置。
