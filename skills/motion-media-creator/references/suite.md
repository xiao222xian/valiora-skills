# `lov-film` 片型套件约定

把不同的视频风格各自沉淀成一个片型 Skill，组成一套；思路类似 hyperframes 系列：一个共享核心，
多个各管一件事的成员，成员之间用文件交接，不互相内嵌。成员在 `SKILL.md` 的 `metadata.suite` 写 `lov-film`。

## 分工

| 层 | Skill | 负责 |
| --- | --- | --- |
| 片型（本层） | 各片型 Skill（现有：`lov-motion-media-creator`，动态图志；`lov-3d-motion-media-creator`，三维图志，以前者为底座） | 这一类片子的叙事语法、场景系统、风格门禁、起步模板、示例案例 |
| 共享核心 | `lov-media-creator` | 素材剪辑、音频母带与混音、双画幅派生、媒体质检、交付契约与状态字段 |
| 封面 | `lov-channels-cover` | 风格锁定的封面与缩略图检验（片型 Skill 也可自出封面） |
| 发布 | `lov-media-publisher` | 视频号、B 站、小红书发布、终稿确认与列表回读；YouTube 不在它的范围内 |

## 片型 Skill 必须有

1. `references/style-grammar.md`：这类片子「对」的标准——结构、文字、视觉、节奏、协作节奏。
2. `references/pipeline.md`：阶段、产物、门禁表。
3. 硬门禁清单：写在 `SKILL.md` 的 Hard gates。
4. 起步模板（有代码时）放 `assets/starter/`，不含私人路径与品牌数据。
5. 至少一个真实案例（`cases/cases.json`），来自真的交付过的片子。
6. 交接说明：写进 `references/skill-composition.md`。

## 命名

- 成员 ID 由用户定。2026-10-12 用户把第一个成员从 `lov-film-atlas` 更名为 `lov-motion-media-creator`（源目录
  `motion-media-creator-skill`，展示名「动态图志 · Motion Atlas」不变，`metadata.suite` 仍是 `lov-film`）；更早一次是 0.2.0 由
  `lov-film-chronicle` 改为 `lov-film-atlas`。原先的写法 `lov-film-<英文片型>`（源目录 `film-<英文片型>-skill`）只作为候选，
  不自动套用：新成员的 ID 先给用户 1–2 个候选，用户同意后再建目录与仓库；现有成员改名同样要用户点头。
- 展示名：中文片型名 + 英文名，例「动态图志 · Motion Atlas」。
- 2026-10-13 用户同意新建第二个成员 `lov-3d-motion-media-creator`（三维图志 · 3D Motion Atlas，源目录 `3d-motion-media-creator-skill`）：
  三维产品片质感是另一种风格；它只放三维特有的部分，分章、旁白、配乐、封面与交付流水线在 `depends_on` 里依赖本 Skill，
  初始化时把本 Skill 的 `assets/starter` 复制过去再叠加三维层，并对少数基座文件打补丁。改本 Skill 起步工程的结构时，要复测它的叠加与示例渲染。
- 片型按「风格」划分，不按题材或结构：同一风格的不同结构（编年、地图、图鉴……）是片型内部的参数，不拆成新成员。
- 规划中的成员（尚未创建，ID 未定）：知识口播片、软件演示片、叙事 Vlog、访谈片、圆桌切片、算法可视化片。
  其中有些能力目前分散在 `lov-media-creator` 的 references 与 `lov-roundtable-clip`、`lov-algo-viz-creator`
  里，拆分时先迁移再删除，避免两处规则漂移。

## 跨成员共享的规则

- 画面不展示制作技术；品牌只用官方 Logo。
- AI 生成内容（TTS 旁白、AI 配乐、AI 图像等）在交付报告与发布交接单里逐类列清单，附平台规则与法规原文；平台上怎么标由用户在发布时决定，
  Skill 不代选、不下合规结论；片内不写制作方式。
- 封面按比例命名、不按平台命名，每片交 16:9、4:3、3:4 三张（2026-10-12：只交 16:9 与 4:3，发视频号时缺 3:4）。
- 片子自足：需要署名的素材在片尾署名卡写全作者、标题、许可与许可短链接，不指向简介。
- 章节时间轴由工具从时间线生成，每章按显示的时间码 ≥ 10 秒、按 ≥ 11 秒设计。
- 付费调用一次一行记进工程的费用账本；每版交付报告带版本历史与费用汇总。
- 用户亲手改过的文案、字段是最高优先级来源；第一个平台上用户改过的简介是后续平台的金标准。
- 能并行就并行；关键创意分叉给用户 1–2 版挑选。
