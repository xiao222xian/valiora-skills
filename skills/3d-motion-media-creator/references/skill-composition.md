# Skill Group Composition

2026-10-13 按 `lov-skill-creator` 的第 2.5 步检查本机 Skill 源码根与已安装目录，按路由描述与实际输入输出判断，不按名字。

## Nearby Skills Inspected

| Skill | 负责什么 | 与本 Skill 的关系 |
| --- | --- | --- |
| `lov-motion-media-creator`（0.9.0） | 动态图志的整条流水线：选轴分章、事实台账、旁白与字幕、分章配乐与节拍网格、HUD 与章节标题卡、三比例封面（含 AI 底图）、片尾署名、章节时间轴检查、费用账本、交付质检与发布交接；二维起步工程 `assets/starter/` | 声明依赖（共享流水线与起步底座）：本 Skill 的起步工程叠在它的 `assets/starter/` 上，每个共享阶段按它的 references 执行 |
| `lov-media-creator` | 实录与录屏剪辑、母带、双画幅、媒体质检脚本 `media_probe.py`、`audio_qc.py` | 间接共享核心：由基础 Skill 的 `tools/deliver.sh` 经 `MEDIA_CREATOR_SCRIPTS` 可选调用；本 Skill 不直接调用。有实拍素材要剪时路由给它 |
| `lov-media-publisher` | 视频号、B 站、小红书发布，`check_copy.py` 文案预检、终稿确认与列表回读；不含 YouTube | 下游：接收基础 Skill 写的发布交接单，本 Skill 不另写交接 |
| `lov-channels-cover` | 风格锁定的 3:4 / 4:3 封面与九宫格整墙检验 | 下游可选，经基础 Skill：封面默认由基础 Skill 自出 |
| `lov-branding-consistency` | 读者可见文案的品牌与语境门禁 | 依赖：屏幕文字、标注、署名与封面文字都过它 |
| `motion-graphics` | 短的设计型动效：动态字、数字跳动、Logo 演绎、下三分之一字幕条、动画地图等 | 不组合：单个动效或 Logo 演绎交给它；它不做分章三维片与事实门禁 |
| `hyperframes` 系列、`general-video`、`media-use` | HyperFrames 的 HTML 合成、关键帧、媒体检索与生成 | 不组合：技术栈是 HTML 合成，不是 Remotion + WebGL；用户点名 HyperFrames 时路由过去 |
| `lov-algo-viz-creator` | 算法与数据结构的逐步演示，输出单文件 HTML | 不组合：讲算法时路由过去 |
| `lov-skill-creator` | 生成本 Skill 的骨架（2026-10-13） | 不组合：只在创建时用过；它默认不让 Skill 依赖外部 sibling，本 Skill 的例外见 Composition Decision |

## Atomic Handoffs

| 方向 | 交接物 | 负责方 | 验收边界 |
| --- | --- | --- | --- |
| 用户 → 本 Skill | 主题与轴（工序、构造、尺度）；可选的 glTF 模型及其许可、资料照片与影像 | 用户 | 模型许可可核，示例标志已去除或确认可用；资料素材的授权规则按基础 Skill |
| `lov-motion-media-creator` → 本 Skill（起步时） | 它的 `assets/starter/` 整份复制到 `<project>/work/remotion`，再叠上本 Skill 的 `assets/starter-3d/` 并合并三维依赖，都由 `scripts/bootstrap_3d.py` 完成；底座位置依次取 `--base`、环境变量 `MOTION_MEDIA_CREATOR_DIR`、`~/.agents/skills/lov-motion-media-creator`。复制时改底座的五个文件（`Cover.tsx` 两个值、`tools/fonts.py` 与 `src/lib/fonts.ts` 的字体表、`HUD.tsx` 一行、配乐简报的章节键） | 本 Skill（`bootstrap_3d.py`） | 找不到底座就报错退出，不在本仓库放底座副本；补丁没对上时报 `warning` 并以 1 退出；叠加后工程能装依赖、过类型检查，示例章节逐张看过静帧 |
| 工程内 → 基础 Skill 的工具 | 叠加后的工程里，基础 Skill 的工具原样运行：`tools/bootstrap.sh`（字体子集、Logo、印章）、`tools/narration.py`、`tools/music_bed.py`、`tools/chapters.mjs`、`tools/credits.mjs`、`tools/gen_cover_bg.py`、`tools/ledger.py`、`tools/deliver.sh` 等 | `lov-motion-media-creator`（工具与门禁） | 基础 Skill 的 Hard gates 全部照旧；本 Skill 只加三维门禁（静帧伪影、示意与资料标注、模型与贴图授权） |
| 本 Skill → 基础 Skill 的交付 | 三维场景的渲染设置（`--gl` 后端、并发、超时）与分块渲染要求 | 本 Skill 定渲染设置（`references/render.md`）；渲染、拼接与回读质检由基础 Skill 的 `tools/deliver.sh` 执行 | 成片从编码文件回读的质检按基础 Skill；三维的转场窗口与静帧检查按本 Skill |
| 本 Skill → 署名 | 每份贴图、HDRI、模型的作者、标题、许可、来源与改动（例如「已删除示例标志」） | 本 Skill 登记，写进基础 Skill 的 `src/credits.ts` | 片尾署名卡与简介署名块仍由基础 Skill 的同一张表生成，本 Skill 不另做署名卡 |
| 基础 Skill → 发布 | 成片、三比例封面、发布交接单 `publish-handoff.md` 与 `publish-copy/` | `lov-media-publisher`（视频号、B 站、小红书）；YouTube 由用户上传 | 本 Skill 没有单独的发布交接；规则见基础 Skill 的 `references/publish-handoff.md` |

## Overlap Decisions

- 与 `lov-motion-media-creator` 的重叠：三维图志也是分章、带 HUD、旁白、配乐、封面与交付的动态图志。它的 `references/suite.md` 规定片型按「风格」划分，
  三维产品片在工具链、渲染设置、模型授权与渲染耗时上和二维纸面风格不同，所以单独成为一个片型成员；但共享流水线不复制，本 Skill 的文档按
  Skill ID 与章节名引用它的 `references/pipeline.md`、`style-grammar.md`、`covers.md`、`fact-and-disclosure.md`、`publish-handoff.md`、`pitfalls.md`。
- 起步工程不 fork：本仓库只放三维叠加层，不放底座副本。底座在 2026-10-12 一天内从 0.5.0 升到 0.8.2，2026-10-13 又升到 0.9.0，
  改了旁白、字号下限、章节标题卡、分章配乐与节拍网格、封面、片尾署名、章节检查与费用账本；复制一份很快就会两边不一致。
- 坑表分层：本 Skill 的 `references/pitfalls-3d.md` 只收三维相关的坑（后端、伪影、材质、模型、确定性）；分块渲染崩溃、空 public 目录打包加 `cp -Rc`、
  工具名回读这类不分二维三维的交付坑已在基础 Skill 的 `pitfalls.md` 与 `tools/bundle.sh`、`tools/deliver.sh` 里，本 Skill 只引用。
- 署名与 AI 生成内容清单沿用基础 Skill 的单一来源；本 Skill 只补三维特有的条目（贴图、HDRI、模型及其改动），并在清单里照实写明三维渲染画面不是 AI 生成画面。
- 封面沿用基础 Skill（AI 无字底图 + 合成排字）。三维定帧可以作为底图之外的备选，不另立封面流程（2026-10-12 该片的三维定帧封面被用户评为不够吸引人，换成了 AI 底图）。
- 以真实品牌为题的处理（通用无标志模型、标志只在资料里、无隶属声明）由本 Skill 定，因为它主要出现在三维建模与 AI 生图时；基础 Skill 的「品牌只用官方 Logo」指的是出品方自己的品牌，两条不冲突。
- 起步工程对底座的改动用复制时打补丁，不 fork 文件：底座的字体表、HUD 一行、封面两个值与配乐简报的键在 `bootstrap_3d.py` 里各有一条带说明的补丁，
  其余底座文件原样复制。补丁对不上（底座改了写法）时脚本报出来，不静默。
- 资料组件（`Archival.tsx`、`conform.py`、`media.ts`）放在本 Skill 的起步层：基座的起步模板没有资料呈现组件（它只管资料的署名），「三维与资料并置」是三维片型的承诺。
  基座以后也要资料时，再把它们移到基座、这里改为引用。

### 与基座 `references/suite.md`「片型 Skill 必须有」的对照

| suite.md 要求 | 本 Skill | 为什么 |
| --- | --- | --- |
| `references/style-grammar.md` | `references/style-grammar-3d.md`，只写与基座的差异 | 三维片仍是动态图志，基座的语法大部分照用；同名会让人以为是整份替换 |
| `references/pipeline.md`（阶段、产物、门禁表） | 不另写，用基座的 `pipeline.md`；三维多出的检查按阶段写在 `SKILL.md` 的 Workflow 各步 | 阶段与产物和基座相同，另写一份就是复制流水线 |
| 硬门禁写在 `SKILL.md` 的 Hard gates | 同 | 基座的门禁照旧，这里只列三维的 |
| 起步模板放 `assets/starter/` | `assets/starter-3d/`，是叠在基座 `assets/starter/` 上的一层，不能单独用 | 同名会让人以为是完整模板；由 `scripts/bootstrap_3d.py` 叠加 |
| 至少一个真实案例 `cases/cases.json` | 同（《如何打造一款特斯拉》v0.1–v0.5） | |
| 交接说明写进 `references/skill-composition.md` | 同（本文件） | |

### 基座待修项

本 Skill 不改基座仓库；下面几处在基座修好、发版后，这里删掉对应的补丁或说明，并把 `compatibility` 的基座版本改上去（2026-10-13 记）：

- 基座 `references/pitfalls.md` 第 35 行（`ContactShadows` 拖影）：修法 `ClearBeforeComposer` 复测有效，但没写放置高度的坑（放在地面上方时站着的物体没有影子）；
  三维片改用 `GroundShadow`，见 [pitfalls-3d.md](pitfalls-3d.md)。
- 基座 HUD 的进度轴从第一章首帧前 2 帧起淡入：`show` 改为 `frame < RULER_START ? 0 : …`（本 Skill 现在在复制时补这一行）。
- 基座 `Reveal` 没有叠化：加一个 `dissolve`，三维片就不用 `DissolveIn`。
- 基座的字体表写死在 `tools/fonts.py` 与 `src/lib/fonts.ts`：给片型留一个替换字体表的入口，本 Skill 就不用打字体补丁。
- 基座 `references/suite.md`「分工」表的现有成员只列了 `lov-motion-media-creator`，待加入本 Skill。

## Composition Decision

Single Skill，在顶层 `depends_on` 声明依赖 `lov-motion-media-creator`（另有 `lov-branding-consistency`）。

`lov-skill-creator` 的默认做法是不依赖外部 sibling Skill：必需的模块放进自包含的 Skill Kit，相关但不必需的 Skill 只写成可选交接。
本 Skill 是有意的例外，2026-10-13 用户同意了这个方案（方案说明对比过把三维做成基础 Skill 的第二套起步模板，并指出复制流水线的漂移风险）：

- 这不是「相关就依赖」：三维叠加层离开底座的起步工程与工具就出不了片，依赖是必需的，所以写在 `depends_on` 与 `compatibility` 里公开声明，
  `bootstrap_3d.py` 找不到底座时报错，不是隐藏依赖。
- 不做 Skill Kit：Kit 要把流水线作为模块内嵌进本仓库，等于复制一份 `lov-motion-media-creator`；它本身是可单独使用、单独发版、在官网单独付费的二维片型，
  内嵌会分叉出第二份真源，漂移风险同上。
- 不复制：同上，流水线在 2026-10-12 与 10-13 两天里发了七个版本（0.5.0 到 0.9.0）。
- 不做第二套起步模板：成本最低、也没有重复，但会让二维 Skill 变臃肿、无法单独定价、名字更含糊（2026-10-13 方案说明）。
- 与套件约定一致：`lov-motion-media-creator` 的 `references/suite.md` 规定成员之间用文件交接、不互相内嵌，本 Skill 用复制起步工程与在工程里运行底座工具交接。

代价：用户要同时装两个 Skill，而 `lov-motion-media-creator` 在官网是付费的，本 Skill 的定价要把这一点算进去（见 `pricing-card.yaml`）；
底座改起步工程结构时，本 Skill 要复测叠加与示例渲染。
