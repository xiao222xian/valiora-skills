# Skill Card — lov-3d-motion-media-creator

本卡片与 `skill-card.yaml` 对应，是发布记录，不是实现说明。展示名「三维图志 · 3D Motion Atlas」。

## Description

没有实拍，用实时三维渲染把一道工序、一件产品的构造或一个尺度讲成产品片质感的分章短片，三维画面标「示意」，真实照片与影像标「资料」并置。

本 Skill 只负责三维这一层：叠在 `lov-motion-media-creator` 起步工程上的三维叠加层（PBR 材质表、物理机位与三维标注投影、按帧可复现的抖动、地面与倒角块、机械臂、glTF 模型加载、后期合成修复与示例章节）、三维风格语法、渲染设置与耗时、贴图与模型授权、三维坑表。分章、事实台账、旁白与字幕、分章配乐、HUD 与章节标题卡、封面、片尾署名、费用账本、交付质检与发布交接都由依赖 `lov-motion-media-creator` 完成。

## Owner

Lovstudio.AI，通过官网联系。

## License / Terms

MIT。起步叠加层不含贴图、模型、HDRI 或品牌资产：CC0 贴图由脚本从 ambientCG、Poly Haven 下载，许可以来源站为准；用户自带的 glTF 模型、照片、影像与音效按各自许可署名。

## Use Case

面向做知识类短视频、需要三维质感的创作者与品牌工作室。输入是一个适合三维讲的主题（工序、构造、尺度），可附 glTF 模型、资料照片与影像；产出一条三维图志成片，以及交给基础 Skill 交付环节的工程。典型场景：二维动态图志被嫌「幼稚」，要升级到产品片质感。

## Deployment Geography

全球；在本地开发机上由支持 Agent Skills 的宿主运行。2026-10-12 只在 macOS 上实测（Chrome headless 经 ANGLE 走 Metal）；Linux 与其他 GPU 未实测，先按 `references/render.md` 测出能用的 `--gl` 后端。

## Requirements / Dependencies

- 依赖 `lov-motion-media-creator`（按 0.9.0 编写，提供起步工程底座与全部共享流水线工具）与 `lov-branding-consistency`。
- Node 24+、pnpm、Remotion 4.0.534、React 19.1.0。
- 三维依赖锁定：`three` 0.186.1、`@react-three/fiber` 9.8.1、`@react-three/drei` 10.7.9、`@react-three/postprocessing` 3.2.0、`postprocessing` 6.39.5、`@remotion/three` 4.0.534。`postprocessing` 6.39.5 要求 `three` < 0.187，fiber 9.8.1 要求 React < 19.4，不能单独升级。
- 能跑 WebGL 的 GPU，渲染用 `--gl=angle`；默认后端会静默落到软件渲染，约 5.7 秒一帧，不可用（2026-10-12）。
- Python 3.9+（`bootstrap_3d.py`、`fetch_textures.py`）；ffmpeg / ffprobe。
- 首次下载贴图时联网；渲染时不联网，HDRI、模型与解码器放在 `public/` 自托管。
- 本 Skill 自身不需要密钥；旁白、AI 配乐与封面底图的可选密钥沿用基础 Skill，只从环境变量读取。

## Known Risks and Mitigations

- GPU 渲染耗时长、长时间单次渲染崩溃或静默走软件渲染：`remotion.config.ts` 固定 `--gl=angle` 与并发 4；按章节分块渲染、无损拼接，改哪章只重渲哪块。实测 v0.2 全片 5211 帧分 5 块，横版 969 秒、竖版 940 秒（两版并行），v0.3 横版 426 秒（2026-10-12）。
- 三维渲染伪影（接触阴影拖影、后期合成首帧黑屏、CC0 金属粗糙度贴图均值约 0.06 让拉丝金属成镜面、机械臂肩部共面 z-fighting、动画不确定）：工具库内置已知修复；动画只由 `useCurrentFrame` 推导；每章静帧与转场窗口逐张看。
- 模型、贴图或 HDRI 授权不清、漏署名，示例模型自带标志：只用 CC0、公有领域与 CC BY，CC BY-SA 默认不用（2026-10-12 用户决定）；取材当下登记 `src/credits.ts`；CC BY 模型的改动写进署名；起步叠加层不打包任何模型。
- 以真实品牌产品为题时出现对方标志、被误认为官方：三维用通用、无标志的模型并标示意；品牌标志只出现在纪录性质的资料照片里（Profile `records.brand_marks`）；AI 底图禁止标志；片尾写无隶属声明。
- AI 生成内容未声明或被代为决定：沿用基础 Skill 的 AI 生成内容清单，由用户决定平台标注；三维渲染画面不是 AI 生成画面，清单照实写。
- 依赖漂移：共享流水线按 Skill ID 引用、不复制；基础 Skill 升主版本或改起步工程结构时重跑 bootstrap、类型检查与示例渲染。
- 证据面窄：只在一部片上验证；起步示例换成中性题材的程序化几何，第二部三维片后复评。

## References

- [Machine-readable card](skill-card.yaml)
- [Primary Skill instructions](SKILL.md)
- [与相邻 Skill 的组合](references/skill-composition.md)
- [User Profile 契约](references/user-profile.md)
- 三维风格语法 `references/style-grammar-3d.md`、场景工具库 `references/scene-kit.md`、渲染设置与耗时 `references/render.md`、授权 `references/assets-and-licensing.md`、三维坑表 `references/pitfalls-3d.md`
- 共享流水线：`lov-motion-media-creator` 的 `references/pipeline.md`、`style-grammar.md`、`covers.md`、`fact-and-disclosure.md`、`publish-handoff.md`、`pitfalls.md`

## Skill Output

三维图志成片（默认 16:9；画幅、三比例封面、交付报告与发布交接单的形态同基础 Skill）、带三维叠加层的 Remotion 工程、每章三维静帧与转场窗口检查图、贴图 / HDRI / 模型的来源与许可登记及片尾署名条目。格式：MP4（H.264 + AAC）、PNG / JPG、TypeScript / TSX、Markdown / JSON。参数：主题与轴、主角模型（程序化几何或用户的 glTF 及其许可）、材质种类、渲染后端与并发。

校验：每章静帧无黑帧、无未打光、无缺失贴图、无 z-fighting，分块交界无阴影拖影；同一帧重复渲染结果一致；三维都标「示意」、资料都标「资料」，真实品牌标志不出现在三维、AI 图与封面里；每份贴图、HDRI 与模型都有来源与许可登记；基础 Skill 的全部 Hard gates 照旧。

## Skill Version

0.1.1

## Ethical Considerations

以真实品牌或产品为题时只做独立科普：三维模型用通用、无标志的造型并标示意，品牌标志只出现在纪录性质的资料里，片尾写无隶属声明；不让生成模型画出标志；三维模型、贴图与资料按许可署名并写明改动；AI 生成内容按基础 Skill 列清单，平台上怎么标由用户决定；不展示与题材无关的个人信息。

## LovStudio Evidence

### User Cases

见 [`cases/cases.json`](cases/cases.json)：《如何打造一款特斯拉》从二维首版被评「过于幼稚」到三维重制 v0.2，再到 v0.5（173.7 秒、15 章），Input → Prompt → Output 完整。2026-10-12 回读：YouTube 已公开（`hyjEEXHXV2M`），B 站 `BV1DopR6wEHw` 与视频号在平台审核中。这是目前唯一的真实案例。

### Dimension Map

机器可读卡片有五个维度及其证据：三维画面与标注、质感升级、渲染耗时、素材授权、可迁移性（证据缺口：只有一部片）。评分待更多案例后给出。

### Pricing Basis

见 [`pricing-card.yaml`](pricing-card.yaml)：本 Skill 与依赖 `lov-motion-media-creator`、`lov-branding-consistency` 均包含在 Lovstudio.AI VIP Membership 全套权益中，不单独定价、不兑换 Credits（用户于 2026-10-14 确认）。会员金额以实际会员方案为准；会员权益不包含 GPU、渲染时间、第三方服务费用或人工代制作。交付包不附带贴图、HDRI 与模型文件。

### Distribution

已选择 Lovstudio.AI 官网会员分发（2026-10-14）；本次官网目录登记与下载权益待发布流程验证。源码仓库保持私有，不进入免费镜像；未选择 WorkBuddy、SkillPay 等其他平台渠道。
