# Skill Group Composition

## Nearby Skills Inspected

| Skill | 负责什么 | 与本 Skill 的关系 |
| --- | --- | --- |
| `lov-media-creator` | 把实录、录屏、Screen Studio 源工程剪成 Remotion 成片；音频母带、双画幅、媒体质检、交付契约 | 共享核心（core）：本 Skill 复用它的质检脚本与交付状态字段；无素材的纯动态设计片（动态图志）由本 Skill 负责 |
| `lov-media-publisher` | 发布到视频号、B 站、小红书；`check_copy.py` 文案预检、终稿确认与列表回读 | 下游：接收发布交接单 `publish-handoff.md` 与 `publish-copy/`；YouTube 不在它的范围内 |
| `lov-channels-cover` | 风格锁定的 3:4 / 4:3 封面与九宫格检验 | 下游可选：本 Skill 每片自出 16:9、4:3、3:4 三张封面（AI 无字底图 + 合成排字）；要锁定账号风格或检验主页整墙时交给它 |
| `lov-3d-motion-media-creator` | 三维图志：three.js / R3F 实时三维的产品片质感分章短片 | 下游片型（2026-10-13 起）：依赖本 Skill，初始化时复制本 Skill 的 `assets/starter` 并在工程里运行本 Skill 的工具；本 Skill 不反向依赖它。要三维产品片时路由过去；改起步工程结构时它要复测 |
| `lov-algo-viz-creator` | 算法与数据结构的可视化讲解视频 | 相邻片型，不组合；讲算法时路由过去 |
| `hyperframes` 系列 | HTML 动画、关键帧、音频、注册表等动效能力 | 不组合；单个动效或组件交给它 |
| `motion-graphics` / `general-video` | 通用动效与视频生成 | 不组合；不承担编年叙事与史实门禁 |
| `lov-roundtable-clip` / `lov-video-chapter` / `lov-video-moments` | 实录切片、章节、精彩时刻 | 不组合；它们处理已有素材 |
| `lov-branding-consistency` | 读者可见文案的品牌与语境门禁 | 依赖：屏幕文字、封面与简介都过它 |

## Atomic Handoffs

| 方向 | 交接物 | 负责方 | 验收边界 |
| --- | --- | --- | --- |
| 上游 → 本 Skill | 主题、轴与范围、可选资料与品牌素材 | 用户 | 本 Skill 只采用能找到来源的事实 |
| 用户 → 本 Skill（可选） | 逐句真人录音 `audio/narration/voice/<id>.*` | 用户 | 录音只替换同 id 的 TTS；字幕文字仍以 `lines.json` 为准 |
| 本 Skill → 共享核心 | 平台成片调用 `media_probe.py`、`audio_qc.py` 质检 | `lov-media-creator` 脚本 | 质检结果写入本 Skill 的交付报告 |
| 本 Skill → 封面（可选） | 片名、英文名、AI 底图 `public/assets/cover/ai-<比例>.png`、品牌资产路径 | `lov-channels-cover` | 封面声称的内容必须在片中出现过；比例与命名仍按 `封面16x9`、`封面4x3`、`封面3x4` |
| 本 Skill → 发布 | `output/reports/vX.Y/publish-handoff.md`：成片（默认 16:9）与三张封面各进哪个槽位；各平台文案与实测长度；可原样追加的独立块（`publish-copy/chapters.txt` 由 `tools/chapters.mjs` 生成，署名完整版与压缩版由 `tools/credits.mjs` 从片尾署名卡读的同一张素材表 `src/credits.ts` 生成）；AI 生成内容清单与平台事实；「发布时需要你决定」 | `lov-media-publisher`（视频号、B 站、小红书） | 发布、终稿确认与列表回读由发布 Skill 负责；AI 标注在它的 `confirm-final` 平台于终稿确认时问用户，`auto` 平台按偏好不标注、直接提交、发布后才报告，所以交接回复里直接列出 AI 生成内容清单，本 Skill 不代选；第一个平台上用户改过的文本是金标准，发布后原文存 `publish-copy/<平台>-published.txt` |
| 本 Skill → 用户（YouTube） | 交接单里的 YouTube 标题、简介（含章节时间轴）、标签与限制（标题 ≤ 100、简介 ≤ 5000、标签合计 ≤ 500 字符、不含 `<` `>`） | 用户 | `lov-media-publisher` 不覆盖 YouTube，它的 `check_copy.py` 也不查 YouTube；长度由本 Skill 实测。上传不走发布 Skill 的流程，终稿确认与上传后回读要单独做（2026-10-12《如何打造一款特斯拉》的 YouTube 在发布 Skill 流程之外上传并回读） |

## Overlap Decisions

- `lov-media-creator` 的 references 里也有若干片型规则（知识口播、叙事 Vlog、独立切片）。套件约定把片型规则逐步迁到 `lov-film` 套件的片型成员，
  共享的音频、双画幅、质检与交付契约留在 `lov-media-creator`。本 Skill 不复制那些共享规则，只引用。
- 旁白（TTS 调用、逐句替换为真人录音、字幕、人声闪避混音）在本 Skill 的起步模板里完成；共享核心的母带标准（−16 LUFS、
  真峰值 ≤ −1 dBTP）与质检脚本照用。
- 「画面不展示制作技术」同时写入 `lov-media-creator` v0.29.0 与本 Skill 的硬门禁：前者对所有片型生效，后者给出本片型的具体清单。
- 封面由本 Skill 自出，不默认交给 `lov-channels-cover`：底图要按 `Cover.tsx` 的版式留出片名空位，片名、印章与 Logo 要和片尾同一套排版，
  费用要进本片的账本（2026-10-12）。
- 文案长度、话题专用标签等平台规则以 `lov-media-publisher` 为准（`check_copy.py`）。2026-10-12 B 站拒收的「新能源汽车」
  还不在它的话题专用标签表里，本 Skill 的交接单先记下拒绝原文；该表由发布 Skill 维护，本 Skill 不复制一份。

## Composition Decision

Single Skill。编年方案、事实台账、配乐卡点、场景搭建、检查与交付服务于同一个用户可见结果（一条动态图志），
单独拆开没有独立用途，不做 Skill Kit。外部 Skill 都是可选交接，按交接物调用，不内嵌。
