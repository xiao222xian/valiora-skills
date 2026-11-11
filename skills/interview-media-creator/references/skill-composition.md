# Skill Group Composition

本 Skill 是 `lov-film` 片型套件的成员，展示名「采访短片 · Interview Short」。它只管「一场采访 → 一条约 4 分钟以内的视频号竖版短片，
怎么剪才对」；横版深度访谈、访谈长片与访谈纪录片不归本 Skill。共享的音频母带、双画幅、媒体质检与交付契约归 `lov-media-creator`，发布归 `lov-media-publisher`。套件约定的真源是
`lov-motion-media-creator` 的 `references/suite.md`。本文依据 `lov-media-creator` 0.31.0 与 `lov-motion-media-creator` 0.10.0 写成
（2026-10-19，六个读者并行读源码后综合）。

## Nearby Skills Inspected

| Skill | 关系 | 交接制品 | 验收归属 |
| --- | --- | --- | --- |
| `lov-media-creator` | 共享核心（混音与质检必需） | 在原安装位置调用它的脚本，不拷贝：`media_probe.py` → probe JSON；`bgm_tracks.py` → `tracks.json`；`validate_cues.py --preset narrative`（读本 Skill 的 `film`/`cues`）→ `cue-check.json`；`smr_check.py`（`voice.json` 只放对白）→ `smr.json`；`score_mix.py --stems` → `final-mix.wav`、stems；`intelligibility.py --floor [--source]` → `cer.json`；`audio_qc.py` → `audio-qc.json`；可选 `subtitle_gate.py` | 门禁定义、阈值、状态字段语义归核心；本 Skill 负责跑门禁、做采访片的创意判断、写交付报告 |
| `lov-media-creator` narrative-vlog「访谈长片：先写导演阐述，再动刀」 | 重叠，按画幅与时长分界 | 横版、长片与访谈纪录片留在 narrative-vlog（该节恢复原文，首行写明范围，并把竖版采访短片指向 `references/routes/interview-media-creator.md`）；竖版短片的同源规则改写进本 Skill 的 `references/style-grammar.md` | 长片归核心；一场采访 → 一条约 4 分钟以内的竖版短片归本 Skill |
| `lov-media-creator` independent-clips | 重叠，按交付形态分流 | 多人整场实录要逐条精包装、可直接发布的独立切片 → 它 | 各管各的 |
| `lov-media-publisher` | 下游 | `platform-wechat-channels-vN.mp4`、选定封面、`publish-copy-vN.md`、交付报告、AI 生成内容清单；字幕交付方式 `burned-in` | 账号核对、字段回读、终稿确认、提交、列表回读归发布方；本 Skill 只把返回状态写进报告 |
| `lov-channels-cover` | 下游，可选 | 钩子原话、人像底图 → `cover_3x4.png`、`cover_4x3.png`（4:3 是视频号分享卡片） | 账号有锁定整墙风格时用它；A/B 选择与覆盖两张的 `cover_status` 归本 Skill |
| `lov-logo-sting` | 片尾，可选（frontmatter `dependencies:`，不写进 `depends_on`） | 官方 Logo SVG + 本片 fps（收尾曲有拍点网格时一并给）→ `<LogoSting>` Sequence 接在合影之后、替换起步工程的静态 `LogoCard`；`sting.wav` 在起点帧并进母带前的最终混音（Sequence 不传 `audioSrc`） | 动画、音效与时间表归它；做可发布版本定片尾时提一次，审片初版只在作者要求时做，没装或不要时照常用 `LogoCard`；整条母带连同编码成片重测响度与真峰归本 Skill（参考成片因收尾瞬态需 −2.5 dBTP、限制器 0.70） |
| `lov-branding-consistency` | `depends_on` | 片名、章名、人名条、提问卡、讲解图形、封面字、简介 | 品牌与语境门禁 |
| `lov-wdb-cli` | 上游，可选 | 联系人信息、聊天 JSONL、对方发来的照片 | 查询正确性归它；取哪些事实、怎么上屏、隐私处理归本 Skill |
| `lov-voice2srt` | 上游，可选 | 云端转写 SRT/JSON（上传与计费先问作者） | 时间轴合法性归它；剪口核验与字幕批准归本 Skill |
| `lov-fact-check` | 上游，可选 | 地点、机构、头衔的核查结论 → `work/facts.md` | 单条结论归它；是否上屏归本 Skill |
| `lov-media-fetch` / 浏览器 | 上游，可选 | 公众号文章正文与图片 → `work/context/` | 获取归它；取舍与署名归本 Skill |
| `lov-media-preprocessor` | 上游，可选 | 昏暗或逆光素材的增强片段与 handoff | 增强与时间映射归它 |
| `lov-roundtable-clip` | 重叠，按交付形态分流 | 多人或长对谈要剪映草稿、选题卡或无人值守批量出片 → 它；要逐条精包装可发布 → lov-media-creator independent-clips；一场采访做成一条包装好的竖版短片 → 本 Skill | 各管各的 |
| `lov-motion-media-creator`、`lov-3d-motion-media-creator` | 套件兄弟，不组合 | 无；写法模板与依赖声明先例 | 各管各的片型 |
| `lov-video-chapter` | 默认不组合 | 进度条在本 Skill 的 Remotion 层；作者要剪映章节包时再交终版 SRT 与成片 | — |
| `lov-image-creator` | 不组合 | 封面与讲解图形用真实帧与 Remotion 组件，不生成人物或现场 | — |
| `interview-designer` | 不组合（触发词相近） | 它做招聘面试题设计；本 Skill 的触发词用「采访视频 / 访谈短片」 | — |

## Atomic Handoffs

1. 素材可读：录像（声音一律从原始 PCM 读；杜比视界录像先用 `sdr_source.py` 转出 SDR 视频源，EDL `source.video` 指向它）、现场照片，
   以及可选的聊天 JSONL、自述、公众号摘录。
2. 转写与剪口（本 Skill）：`transcribe.py` 两模型 → EDL（含 `nouns`）→ `probe_cuts.py` 固定切点 → `build_timeline.py --audio` → `seam_check.py`。
3. 画面与包装（本 Skill）：`setup_starter.py`（Remotion 起步工程 `assets/starter`，建好 `public/` 各目录）→ 横拍素材 `crop_centers.py` → `reframe.py`
   → `build_timeline.py --video --audio`（同时写 `timeline.base.json`）→ `fx_pieces.py --copy-to work/remotion/public/media`（bt709 中间轨，帧数不符退出 1）
   → `subs_from_lines.py` →（双语）`subs_en.py` → `decorate.py`（从 `timeline.base.json` 起）→ `check_timeline.py --public --mezz`。
4. 配乐生成（本 Skill，核心收录前的过渡）：`gen_bgm.py`（Lyria 经 OpenRouter，先报单价、记账本）→ `bgm_check.py`（人声分离判定、可闻尾音）。
5. 配乐登记与混音（核心脚本）：`bgm_tracks.py --instrumental` → `music_plan.py --media-creator` 生成 `cues`/`film`/`voice-proc` 并打印门禁命令
   → `validate_cues.py` → `smr_check.py` → `score_mix.py --stems` → `intelligibility.py`；最终混音转 `remotion/public/audio/mix-vN.m4a` 供 Studio 预览。
6. 编码与质检（本 Skill + 核心）：`finalize_platform.py`（视频号参数、bt709 码流标记、5 fps 分页联系表、逐帧二维码扫描、手机预览）→ `audio_qc.py`、`media_probe.py`。
7. 字幕批准：审片版 SRT 的 SHA-256 → 作者确认 → `subs-approved-vN.srt`；状态字段按核心 delivery-contract。
8. 发布：`subtitle_status=approved`、`delivery_status=platform-ready`、`cover_status=approved`（覆盖选定的 3:4 与 4:3）后交 `lov-media-publisher`（见 publish-handoff.md）。

## Overlap Decisions

- **与 lov-media-creator：新建片型 Skill，不扩展核心，只拿走竖版短片。** 套件规划里的「访谈片」按画幅与时长拆开：一场采访 → 一条约 4 分钟
  以内的视频号竖版短片归本 Skill，它有自己的叙事语法（原话钩子、重排约 5 章、提问卡与回答字幕两套文字、人名条、跳切推近、封面 A/B）和只服务
  这种剪法的切点核验脚本；横版深度访谈、访谈长片与访谈纪录片仍是 narrative-vlog 的「访谈长片」。本 Skill 不是第二个剪辑引擎：混音、母带、
  SMR/CER、状态字段、编码与隐私规则全部调用核心。
- **两边写同一个判别条件。** 本 Skill 的 Activate / Do-not、核心的 narrative-vlog「访谈长片」首行与 `references/routes/interview-media-creator.md`
  都写「单场采访 → 约 4 分钟以内竖版视频号短片 → 本 Skill；横版、长片或访谈纪录片 → narrative-vlog」。导演阐述的通用清单在两边都有，
  本 Skill 的版本只多了竖版短片专属项。
- **多人实录按交付形态分流。** 要剪映草稿、选题卡或无人值守批量出片 → `lov-roundtable-clip`；要逐条精包装、可直接发布的独立切片 →
  lov-media-creator independent-clips；一场采访要一条包装好的竖版短片 → 本 Skill。
- **过渡期自带的脚本**：`gen_bgm.py`、`bgm_check.py`、`finalize_platform.py` 里的二维码扫描，核心目前只有文档没有脚本。二维码检测按核心
  delivery-contract「发布前隐私扫描」逐帧跑，人工联系表按 5 fps 分页。核心收录后本 Skill 改为引用、删除本地副本。
- **封面比例**：套件约定每片交三比例；视频号封面槽数以发布页现场读到为准（观测：一个 3:4 槽，有时 3:4 + 4:3 两个槽）。做法：3:4 出 A/B 让作者选，
  选定后同一视觉出 4:3 分享卡，两张一起交给发布方；16:9 只在要发 B 站等横版平台时出。报告写明每张用在哪个槽、哪张没用上。
- **横版成片不在起步工程里**：起步工程只有竖版成片与 3:4 / 4:3 / 16:9 封面合成；横版成片按 lov-media-creator `references/platform-variants.md` 派生，
  横拍采访的具体做法与「首发之后不再问」的判断见 `references/pipeline.md`「13 横版派生」。

## Composition Decision

**Single Skill，不做 Kit。** 一种输入对应一种成片；脚本只服务这一条剪辑管线，单独拆出来没有用处；共享能力已在核心里，没有需要内嵌的独立模块。

依赖写法：`depends_on: [lov-branding-consistency, lov-media-creator]`。`lov-media-creator` 是混音与质检门禁的运行时，作者 2026-10-21 决定
把它写进 `depends_on`，安装时随本 Skill 进入安装闭包（0.2.1 起）；frontmatter `dependencies:` 仍保留运行时检查（check 按 `$MEDIA_CREATOR_DIR` 查找，
缺省 `~/.agents/skills/lov-media-creator`，与 Step 0 的解析顺序一致；带安装命令），并在 `compatibility` 里声明；找不到时在混音前停下，`audio_status`
不得记 `passed`。其余相邻 Skill 都是可选的文件交接。
