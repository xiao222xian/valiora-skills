# 路由：采访短片 → `lov-interview-media-creator`

以一位创业者或嘉宾为主体的单场采访录像，重排成以被访者原话起钩、分章推进的竖版短片，风格判断归片型 Skill
`lov-interview-media-creator`（展示名「采访短片 · Interview Short」）；本 Skill 只承担共享的音频母带、双画幅、媒体质检与交付契约，
片型 Skill 原地调用本 Skill 的 `media_probe.py`、`bgm_tracks.py`、`validate_cues.py`、`smr_check.py`、`score_mix.py`、`intelligibility.py`、`audio_qc.py`。

- 判别：一场采访 → 一条约 4 分钟以内的竖版视频号短片，走这里；横版深度访谈、15 分钟级访谈长片、访谈纪录片留在本 Skill，
  按 [`narrative-vlog.md`](../narrative-vlog.md)「访谈长片：先写导演阐述，再动刀」处理。
- 多人整场按交付形态分：要剪映草稿、选题卡或无人值守批量出片 → `lov-roundtable-clip`；要逐条精包装、可直接发布的独立切片 →
  本 Skill 的 [`independent-clips.md`](../independent-clips.md)。
- 触发：手机或相机拍的采访录像（可含采访者提问），要做成一条可发布的视频号采访短片——冷开场取被访者原话、约 5 章重排、提问卡与回答字幕、
  人名条、跳切推近、AI 配乐、封面 A/B；作者对这条短片要求「从专业导演角度策划」时同样走这里。
- 输入：采访录像（声音取原始 PCM）；可选微信聊天（`lov-wdb-cli`）、被访者自述、公众号文章与现场照片；Profile 里的官方 Logo、系列名与章节卡时长。
- 输出：9:16 1080×1920 平台成片（作者点名 16:9 时按 [`platform-variants.md`](../platform-variants.md) 派生）、3:4 封面 A/B 与选定后配套的 4:3 分享卡、
  批准字幕、事实台账、交付报告与发布文案；状态按 [`delivery-contract.md`](../delivery-contract.md)。采访有对白，`subtitle_status` 只能经 `awaiting-review` 到 `approved`。
- 必问：作者要求导演视角时阐述先批再剪；身份信息能否公开问一次；付费 AI 配乐与云端转写先说明单价。
- 默认：2–4 分钟、约 5 章（每章 ≥ 10 秒）、30fps、9:16；母带 −16 LUFS / −3 dBTP；出镜人物自然美颜。
- 不适用：横版或长片访谈、访谈纪录片（narrative-vlog「访谈长片」）；多人整场切片（见上方按交付形态分）；
  Vlog、旅行、纪录片（narrative-vlog）；作者第一人称讲解片（explainer-film）；招聘面试题设计（`interview-designer`）。
