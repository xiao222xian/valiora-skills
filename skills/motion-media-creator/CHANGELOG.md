# Changelog

## [0.9.1] - 2026-10-13

### Fixed

- register lov-3d-motion-media-creator as the 3D member built on this Skill
- suite.md 成员表与命名记录加入 lov-3d-motion-media-creator（三维图志），写明它复制本 Skill 的起步工程并对少数文件打补丁，改结构时要复测
- SKILL.md「Do not activate」与 skill-composition.md 把三维产品片路由给 lov-3d-motion-media-creator
- pitfalls.md：ContactShadows 放在地面上方时站立物体没有影子（2026-10-13 复测，并确认清屏修法有效）

## [0.9.0] - 2026-10-13

### Added

- BREAKING: rename lov-film-atlas to lov-motion-media-creator; fold in the 《如何打造一款特斯拉》 lessons
- 调用 ID、源目录、Profile 命名空间（skills.lov-motion-media-creator）与偏好命名空间改为 lov-motion-media-creator；展示名「动态图志 · Motion Atlas」不变；suite.md 记录成员 ID 由用户定
- 封面：每片固定交付 16:9 / 4:3 / 3:4 三比例、按比例命名；AI 无字底图（tools/gen_cover_bg.py + cover/brief.json，余额 ≥ 1 美元门禁、dry-run、断连可能已计费）+ Cover.tsx 排版（tone dark/paper、无进度轴）；references/covers.md
- 片尾署名自足：src/credits.ts 单一来源，片尾卡带许可短链；tools/credits.mjs 生成完整版与精简版署名段并报长度
- tools/chapters.mjs：章节时间轴（00:00 起、≥ 3 章、显示时长 ≥ 10 秒，< 11 秒警告）
- 交付报告加 AI 生成内容清单（附 YouTube AI 音乐披露与《标识办法》第十条）、版本历史与费用汇总；references/publish-handoff.md 给出各平台文案变体与可追加的时间轴、署名块
- 费用账本 tools/ledger.py（ledger/costs.jsonl）：配乐、TTS、封面脚本自动记账，校验坏行；narration.py --dry-run 报合成字数；配乐脚本遇 4xx 不重试
- 整片配乐与章节节拍网格对齐（music_bed.py 按相位差平移），beat_phase.py 检查两处衔接
- cases.json 加入《如何打造一款特斯拉》真实案例（v0.1–v0.5，三平台发布记录）

## [0.8.2] - 2026-10-12

来源：《如何打造一款特斯拉》v0.4 → v0.5 的复查：「第 3 小节强拍 = 检测到的首拍 + 4 秒」让 13 章里 6 章的配乐偏离画面的节拍网格
94–244 毫秒，其中两章差半拍。原因是 librosa 开头几拍还没稳住，首拍本身就偏。该片 v0.5 改用拟合的节拍网格；本版把它移进起步模板与文档。
只关乎配乐定位，没有写入 Profile。

### Fixed

- `audio/chapters/analyze.py` 合并了该片的 `grid.py`：选条用的数字（首拍、`clarity`、`ibi_cv`）照旧，另加节拍网格：1 秒之后的稳定拍点
  按最小二乘拟合拍长与相位（`period`、`bpm` = 60 ÷ 拍长）、残差 `resid_ms`（拍点离拟合线的中位距离）、四拍里起音最强的一拍作小节强拍，
  列出全部 `downbeats`。拍号按相邻拍距对中位拍距取整累加，不按 0.5 秒硬除，速度偏离 120 的候选也不会数错拍。
- `tools/music_bed.py`（`picks.json`、警告与提前叠入不变）：
  - 每段先按拟合速度变速到正好 120 BPM（倍率 = 拍长 ÷ 一拍秒数，不变调），再把拟合网格上离 4 秒最近、前面至少有 1 秒音乐的小节强拍
    放在章节第一帧；去掉了强拍前留的 30 毫秒（引子已经带着起音），强拍正好在第一帧上；
  - 变速优先用 ffmpeg 的 rubberband 滤镜，没有时用 atempo，`MUSIC_STRETCH=rubberband|atempo` 可指定；用 atempo 且变速超过 1% 时提示跑相位质检；
  - 自动选择跳过网格残差超过 15 毫秒（`MAX_RESID_MS`）的候选、改用另一条；`picks.json` 指定的候选残差超限、或任何候选变速超过 3% 时警告；
  - 引子不够时退到能放下章节的最晚一个小节强拍并警告；第一个小节强拍之后也放不下章节时报错；`analysis.json` 还是旧格式（没有网格）时
    报错，提示重跑 `analyze.py`；`--dry-run` 报每段的拟合速度、变速倍率、网格残差、所取强拍与引子。
- 文档里的「第 3 小节 = 首拍后 2 小节」改为拟合网格：`pipeline.md` 阶段表与第 1、3 节，`style-grammar.md`「节奏」，SKILL.md 第 3 步与
  依赖，`starter-template.md`，`skill-card.yaml` 与 `skill-card.md`；`pitfalls.md` 新增一行，速度、候选前奏与换段生硬三行同步。

### Added

- `qc/beat_phase.py`：分章配乐的节拍相位质检（librosa，经 uv）。每章去掉两头的叠入部分（章首 0.8 秒、章尾 1.05 秒），把配乐的起音强度
  按（t − 网格相位）对一拍取余叠成直方图，峰值即这一章的相位；用自己配乐的各章距网格与彼此都在 ±25 毫秒（`--tol`）内才通过，否则非零退出。
  整片配乐的章只报告（`--all` 才判）；`--json` 存结果。放对的配乐读数约 −10 毫秒，是测量本身的偏差（选中的 13 条原样在各自的拟合网格上
  读 −5.0 至 −10.5 毫秒）。

### Verified

在起步模板的临时副本里，用该片的 26 条候选与示例时间线（15 章，片头、片尾用该片整片配乐，延后 0.21 秒对齐示例时间线的网格，
`picks.json` 只写该片各章响度、不指定候选）：

- `analyze.py`：24 条残差 1.1–6.8 毫秒，2 条 30.8、45.4 毫秒（该片 `grid.py` 按 0.5 秒硬除读 61.6、50.6）；24 条的小节强拍与该片 `grid.json` 一致（另 2 条即这两条松的）。
  自动选择跳过这 2 条，13 章与该片 v0.5 的选择一致（0.8.1 的规则会选上 30.8 毫秒的那条）。
- `music_bed.py`：13 章变速 −0.12% 至 +0.03%，引子都是 1 秒，无警告。`qc/beat_phase.py` 各章相位（毫秒，rubberband）：
  −4.1、−7.0、−9.4、−7.5、−10.4、−10.8、−8.2、−8.4、−9.2、−7.8、−8.2、−15.9、−8.2，最远 15.9、彼此相差 11.8，通过；
  整片配乐的片头、片尾 −8.2、−8.2。atempo：最远 20.6、相差 13.2，通过。0.8.1 拼的同一组：+24.6、+53.6、−237.2、+7.5、−86.9、
  −146.5、−238.6、+58.0、+30.4、+128.3、+21.1、+108.3、+101.2，10 章超出 ±25 毫秒，未过。
- 把选中的 13 条先改成 117 或 123 BPM 再拼（变速 ±2.5%）：rubberband 最远 11.5、相差 8.9，通过；atempo 最远 21.5、相差 25.9，未过
  （加快的几章读 0 至 +4，放慢的读 −14 至 −22），所以默认用 rubberband。
- 该片 v0.5 的配乐：13 章 −5.1 至 −15.4 毫秒、相差 10.3，通过；片头、片尾的整片配乐读 +82、+81 毫秒（该曲自身的网格在 0.324 秒相位，
  章节网格在 0.233 秒），未判，进出它的两处叠入值得再听。
- 报错与警告：旧格式 `analysis.json`、`picks.json` 指定残差 30.8 毫秒的候选、候选太短、引子不够，各自按上面的提示退出或警告。

## [0.8.1] - 2026-10-12

来源：用户看《如何打造一款特斯拉》v0.3 的反馈：「片段之间的音乐衔接有些生硬」。原因是每章的新配乐在章节第一帧从首拍硬进，
上一段只有 0.35 秒淡出。该片 v0.4 改为提前叠入；本版把它移进起步模板与文档，作为分章配乐的默认。只关乎配乐拼接，没有写入 Profile。

### Fixed

- `tools/music_bed.py` 换段改为提前叠入（移植自该片 v0.4；`picks.json`、自动选择、警告与最后一章在片尾 1 秒淡出不变）：
  - 每段从第 3 小节用起（首拍后 2 小节，`LEAD` = 4 秒），这一小节的强拍落在章节第一帧，前面有真正的音乐可以叠；
  - 进来的一段在章节第一帧前 1 秒（`PRE`）等功率淡入（正弦），叠在出去的一段下面；出去的一段从章节第一帧前 0.25 秒到后
    0.75 秒等功率淡出（余弦，`OUT_FROM`、`OUT_LEN`）；
  - 响度只按章节本体调平，不算引子与尾巴；
  - 进出整片配乐 `public/audio/bgm-full.wav` 同样提前叠入；相邻几章都用整片配乐时连成一段，中间不再淡出淡入；
  - 候选不够 2 小节引子时退到 1 小节、再退到首拍，并警告衔接接近硬接；候选在首拍后比章节短仍报错；`--dry-run` 报每段用第几小节、
    引子多长。
- 文档里的「0.35 秒交叉淡化」「首拍落在章节第一帧」改成上面的做法：`pipeline.md` 阶段表与第 1、3 节，`style-grammar.md`
  开头与「节奏」，SKILL.md 开头与第 3 步，`starter-template.md`，`skill-card.yaml` 与 `skill-card.md`。
- `pitfalls.md` 新增一行：不同的两段配乐 0.35 秒硬接听着生硬，改为在同一张 120 BPM 网格上提前 1 秒叠入；候选前奏一行改为从首拍起算。

### Verified

- 在起步模板的示例时间线（15 章，片头、片尾用整片配乐）上用该片 26 条候选跑通：13 章自动选择，都用上第 3 小节、引子 1 秒，无警告。
- 14 处衔接，0.25 秒窗口电平：成片与两段各自（不淡化）在同一窗口相比，衔接处没有凹陷（始终比较轻的一段高 2.4 dB 以上），
  强拍前约半秒两段都接近满音量，最多高出较响的一段 5.7 dB。与前后各一秒同拍位的窗口相比，4 处超出「凹陷 ≤ 6 dB、凸起 ≤ 4 dB」
  （最大凹陷 7.2 dB、凸起 5.2 dB；0.35 秒硬接时 6 处，最大凹陷 15.7 dB），与该片 v0.4 成片（5 处）同一水平；超出的凹陷来自
  进来那段自己的弱拍，章内同样测法也有 29/169 处超出。
- 第 3 小节的强拍按 120 BPM 从首拍推算（与该片 v0.4 相同）：13 条里 8 条在章节第一帧后 10–57 毫秒有起音，5 条最近的起音在
  83–126 毫秒外（可能是切分），未试听。

## [0.8.0] - 2026-10-12

来源：用户转述的观众对《如何打造一款特斯拉》v0.2 的反馈：「像这种带素材、强动画的视频，文字部分应该尽量大一些，
目前文字部分太小导致不够一眼 get 信息；因为比较长，所以可以分章节讲述；音乐可以按照章节来配；缺少一些节奏」。
该片 v0.3 已照此修改；本版把它变成这类片子的默认。是转述的反馈，没有写入 Profile。

### Changed

- 字号下限（1920×1080，其他画幅按短边 ÷ 1080 缩放，9:16 再 ×1.15）：字幕中文 46 px、英文 27 px；引线标注 22 px、引线 1.5 px；
  数据块与清单 ≥ 26 px；HUD 读数 16 px、段名 15 px；大数字 120–160 px。角落的示意与出处标注保持 14 px 小字（用户长期偏好，
  Profile `records.annotation`）。
  - `style-grammar.md`「文字」新增「字号下限」，HUD 一节写明读数与段名下限；SKILL.md 第 4、5 步与 Hard gates、`pipeline.md`
    第 4、5 阶段同步。
  - 起步模板：`src/lib/layout.ts` 新增 `TYPE_FLOOR`、`LEADER_W` 与 `useLayout().ts`；`Subtitles.tsx` 从 34 / 21 px 放大到
    46 / 27 px（9:16 按 `ts` 缩放）。
- 章节标题卡：每章转场过半时，在 HUD 章名头的位置出大号「序号 / 总章数」、章名（120 px，过长按宽度缩小）与轴上位置，
  约 1.7 秒（章内第 50 帧）后淡出，HUD 小章名同时淡入；场景前约 2 秒不往左上放字，不另做同名大标题。
  - 起步模板新增 `src/components/ChapterCard.tsx`（移植自该片，改用模板的 `hudInkAt` 墨色与底色、章节字体、`ERA_CHAPTERS`），
    `timeline.ts` 新增 `CARD_OUT`，`Main.tsx` 在字幕下面挂载标题卡。
  - `HUD.tsx`：章名头从 `CARD_OUT` 起淡入（此前章节开头就出现，带上移动画）；总章数取 `ERA_CHAPTERS.length`，不再写死 13。
  - `style-grammar.md`「结构」「HUD」、`pipeline.md` 第 4 节、SKILL.md 第 4 步同步。
- 配乐默认改为分章配乐：每章一段 120 BPM 配乐（Lyria 3 Clip，`google/lyria-3-clip-preview`，经 OpenRouter，0.04 美元一条
  30 秒，每章两条候选，按节拍清晰度选），首拍落在章节第一帧，按章设响度目标（安静 −21 至 −19 LUFS、一般 −18 至 −17、
  重击与高潮 −16 至 −15），章与章 0.35 秒交叉淡化；片头、片尾可保留片头剪辑所依据的整片配乐。单曲配乐保留为备选。
  - `pipeline.md` 第 3 节重写，第 1 节节拍网格一条改为「章节起点都在同一张 15 帧网格上」；SKILL.md 第 1、3 步同步。
- 节奏默认（`style-grammar.md` 新增「节奏」）：剪切与冲击在拍上；章节换音乐在章节强拍上；旁白在它说的画面出现后 0.2–0.5 秒开口
  （`lines.json` 的 `at` 写成镜头起点加 6–15 帧）。
- 人声扫描的判读写清：Whisper 在纯音乐上几乎总会转写出文字，`no_speech_prob` 也是 0；按连贯性与 `avg_logprob` 判，能听就听。
  `audio/vocal_scan.py` 新增 `--out` 与每个文件的 `listen` 列表（排除重复、一句内自我重复、多语种播出套话后剩下、置信度高于 −1 的片段）；
  用该片 13 条分章配乐与一条整片配乐的扫描结果核对过。
- `pitfalls.md`：人声扫描一行改写；Lyria 空流一行补上 Lyria 3 Clip 的实测。

### Added

- 起步模板，移植自该片并按模板结构改写：
  - `audio/gen_chapter_music.py`：每章两条候选，已有的跳过，空流与断连重试；新增 `--dry-run`（只报条数与费用）、简报占位检查、
    缺密钥时明确报错、有失败时非零退出。
  - `audio/chapters/briefs.json`：简报模板，片子专属的章节情绪与题材句换成 `<…>` 占位，`_example` 里留了三句写法示例。
  - `audio/chapters/analyze.py`：librosa 节拍分析（PEP 723 头，`uv run --python 3.12 --with librosa` 运行）；新增按全部拍点拟合的
    `bpm`（librosa 自身的速度估计把 120 BPM 量化成 117.45 或 123.05），可只分析指定文件并合并进已有的 `analysis.json`。
  - `tools/music_bed.py`：路径改为模板内的 `audio/chapters/`；选择与响度从代码常量改为可选的 `audio/chapters/picks.json`，
    没写的章自动选（约 120 BPM、`ibi_cv` ≤ 0.05、首拍在 1 秒内的候选里 `clarity` 最高；在该片的 26 条候选上与人工选的 13 条一致）；
    没有候选的章放可选的整片配乐 `public/audio/bgm-full.wav`（不再自动把 `bgm-music.wav` 另存一份）；章节起点不在同一 15 帧网格上
    时警告；候选比章节短时报错；最后一章是分章配乐时在片尾 1 秒淡出；`--dry-run`。
  - `src/components/Type.tsx` 新增 `Callout`（引线标注）、`BigNumber`（大数字）与 `thousands`，移植自该片的 `Overlay.tsx`，
    尺寸取自 `TYPE_FLOOR`。
  - `.gitignore` 忽略 `audio/chapters/*.mp3`（同名 `.json` 记着提示词与费用，保留）。
- `pitfalls.md` 新增 2 行：librosa 速度量化；候选带前奏或提前收尾。
- `starter-template.md`：新文件与新常量的说明、「分章配乐」一节，以及示例章节与标题卡、放大字幕会相撞的提醒。

## [0.7.0] - 2026-10-12

来源：用户审《如何打造一款特斯拉》样片时的三条反馈：「感觉不错，但请默认先出 16:9视频（而非同时做两版），除非用户指定」
「应支持基于 tts 或者真人原声的音频，目前缺少，不够有代入感」「本片还应使用中英双语的字幕」。前两条存入 Profile
`skills.lov-film-atlas.records.default_aspect` 与 `records.narration`；双语字幕只对这一片生效，默认仍是中文字幕。

### Changed

- 默认只交付 16:9 横版；9:16 竖版或两版同出只在用户点名时做。
  - SKILL.md 第 1、4、5、6、7 步与 Hard gates，`pipeline.md` 阶段表、第 4 与第 7 节，`starter-template.md`，
    `skill-composition.md`，README 与卡片同步。
  - 封面默认 16:9 与 4:3 两张，做了竖版才加 3:4。
  - `deliver.sh` 的用法说明写明默认只跑 `16x9`。
- 旁白成为片型的一部分，「无旁白」的说法全部改掉：屏幕文字与旁白一起叙事，字幕承载说出的话。
  - 旁白默认用 TTS（豆包 Seed-TTS 2.0），也可以逐句换成用户的真人录音（`audio/narration/voice/<id>.*`）。
  - 旁白稿 `lines.json` 每句有 `zh`（中文字幕）、`tts`（读法）、`en`（英文字幕）三份文字。
  - 写法：只用事实台账里的事实，去 AI 味规则与上屏文字相同；一章 10–14 秒配 25–45 字；片名卡与片尾卡上不配旁白。
  - 混音：旁白整轨约 −17 LUFS，旁白期间音乐压低约 9 dB、音效约 4 dB（0.2 秒压下、0.6 秒恢复）；母带标准不变。
  - 有旁白时，场景左下的正文说明让位给字幕。
  - 写进 SKILL.md 第 2、3、4、5 步与 Hard gates，`style-grammar.md` 新增「旁白与字幕」一节，`pipeline.md` 第 3 节新增「旁白」，
    `fact-and-disclosure.md` 把旁白与字幕纳入台账。
- 字幕默认只有中文；用户要求时中英双语：中文在上、英文在下，居中在进度轴上方，亮画面跟随 HUD 墨色；英文专名全片一种写法。
- 起步模板 `Main.tsx` 改为导出 `Film`（按传入的章节表拼接，不再引用 `src/scenes`），`Root.tsx` 用 `SCENES` 组装整片；
  `HUD.tsx` 抽出 `hudInkAt` 供字幕共用，HUD 自身行为不变。
- `deliver.sh` 只打包一次再分块渲染（此前每块各打一次包）；`stills.sh` 改用 `tools/bundle.sh`，bundle 默认目录改为 `../build/stills`。
- `audio/snap.py` 默认分析 `public/audio/bgm-music.wav`（没有时退回 `bgm-master.wav`），因为母带里可能已有旁白。

### Added

- 起步模板，移植自《如何打造一款特斯拉》工程并按模板结构改写：
  - `tools/narration.py`：逐句用户录音优先、其余 TTS（按读法、音色、语速缓存），去首尾静音、量时长；写 `timing.json` 与
    `src/narration.ts`。超出 `until`、挤到下一句、离开本章、落在片名卡或片尾卡上即失败。缺旁白稿、缺密钥、录音为静音、`--check` 遇到未量过的句子时给出明确报错。
  - `tools/voice_mix.py`：模板没有音效预混，新增这一步。`bgm-music.wav` + 旁白（+ 可选音效轨）→ `bgm-master.wav`，
    旁白调平、音乐与音效闪避，母带到 −16 LUFS、真峰值 ≤ −1 dBTP；没有旁白时只处理配乐。
  - `src/components/Subtitles.tsx`、`src/narration.ts`（空表即无旁白片）、`timeline.ts` 的 `SUBTITLE_LANGS`、`fonts.ts` 的 `SUBTITLE_FONT`。
  - `tools/preview.sh` + `src/dev/harness.tsx`：单章预览，入口只挂本章，一章坏了不挡别的章。
  - `tools/bundle.sh`：对空 public 目录打包，再 `cp -Rc` 克隆 `public/` 进 bundle。
  - `tools/stills.mjs`：一个浏览器连续出多张静帧。
  - `.gitignore` 忽略 TTS 缓存、裁好的片段、人声轨与生成的预览入口；`voice/` 里的用户录音保留。
- `pitfalls.md` 新增 8 行（2026-10-12）：
  - drei `ContactShadows` 在连续渲染里留拖影（`autoClear` 在优先级 -1 打开、0.5 关回）。
  - ambientCG `Metal050A` 粗糙度贴图均值约 0.06，拉丝金属成镜面（贴图重映射到约 0.24–0.40）。
  - `''` 不是 null，「空即默认」用 `||`。
  - Remotion 静态服务器不跟随软链接的 public 目录。
  - 每次打包都复制 `public/`（约 1 GB）：改为空 public 打包再克隆。
  - zsh 通配无匹配即中止：循环放进 bash 并 `shopt -s nullglob`。
  - 并行搭章的 Agent 各自从单章入口预览。
  - 断网会让长时间运行的 Agent 失败：章节随做随写盘，可从盘上续做。
- `skill.yaml` 的 Profile 字段加入 `records.default_aspect` 与 `records.narration`（非必填）。

## [0.6.0] - 2026-10-12

来源：用户审《背包九讲》v0.1 时的三条反馈。

### Changed

- 片尾只保留片名卡（印章 + 出品 + 官方 Logo + 说明），收束章之后直接接上。不做章节回顾网格，也不做回顾之后、
  片名卡之前的过渡动画（进度轴收回成一笔或收回成片头图形）。
  - 用户原话：「以后都无需章节回顾章节」。
  - 过渡动画在《跳出局部最优》之后已被指出多余，但当时没有写进本 Skill，《背包九讲》v0.1 又出现一次。
  - 这条规则同步写进 SKILL.md 第 4 步与 Hard gates、`style-grammar.md`「结构」和 `techniques.md`，并存入 Profile
    `skills.lov-film-atlas.records.outro`。
  - 起步模板的 `S14Outro.tsx` 改为只有片名卡；`timeline.ts` 的 `outroDecay` 改为片尾起点，片名卡出现时 HUD 淡出。
- `style-grammar.md`「文字」新增去 AI 味判据：不写口号、金句、格言式收尾，不替观众总结意义。
  - 用户判为 AI 味的例子：「九讲，从这一行出发」「一切从一个选择开始：装，或不装」「一只包，九种变化」。
  - 同类句式还有对仗、冒号揭示、破折号吊悬念，以及同一句口号在多章重复。
  - 改法：写画面上看得到的事实，换同义词不算改好。
  - SKILL.md 第 5 步与 Hard gates 同步加了这一项。
- `pitfalls.md`：只与回顾缩略图有关的两行注明适用场景；`fact-and-disclosure.md` 把「片尾回顾称『章』」改为
  「HUD 与片尾说明称『章』」；`starter-template.md` 去掉片尾收笔与回顾缩略图的说法。

### Fixed

- 起步模板 `Paper.tsx` 对当前帧取整：`Freeze` 收到小数帧时，颗粒纹理文件名会变成 `grain5.1999.png` 并报 404。
- `pitfalls.md` 新增 Didot 一行：`Didot.ttc` 的字面顺序是 0 常规、1 斜体、2 粗体，常规体默认是旧式数字。

## [0.5.0] - 2026-10-12

来源：《跳出局部最优》发布后观众问「为啥没有包含梯度下降相关的算法」，以及本片制作中的核查、终审与渲染记录。
每条都由独立 Agent 回到会话记录逐条核对证据后才写入。

### Added

- 「选样与未单列」门禁：结构方案阶段列一张缺席名单，写清同领域最有名、却没成章的成员及理由，以无名形象出场的也算在内。
  名单上每一项都写进片尾选样说明；以无名形象出场的，另在出场处就近标名。这条规则写进了 SKILL.md 第 1 步和 Hard gates，
  也加进了 `pipeline.md` 第 2 阶段与第 5 阶段的门禁，以及 `fact-and-disclosure.md`。
- `assets/starter/tools/stills.sh`：打包一次，再从 bundle 并行出抽查静帧。脚本逐个等待子进程，任一张失败即非零退出，
  并先删掉同名旧图。
- `fact-and-disclosure.md` 新增三项：
  - 年份口径：方案里写定一条，破例在片尾点名，改年份后复查相邻章与 `axisKeys`。
  - 格式固定的署名行：这一行暗含「提出者」的意思，不写「首创」，案例按上位词写。
  - 实跑数字：按画面上可数的口径计数，默认值不能当数据上屏，负零要防住，负号用「−」。
- `style-grammar.md` 新增三项：
  - 进度轴短名缩写时不能删掉否定词。
  - 同一概念全片只用一个说法，上屏前过一遍歧义。
  - 外国人名全片统一一种写法，没有通行汉译时用原文。
- `starter-template.md` 新增两项：
  - 开工先把示例场景移出 `src`，`Cover.tsx` 换成空白占位组件；改字体族前缀时，`tools/fonts.py` 的 `FACES` 要一起改。
  - `vocal_scan.py` 依赖 `mlx-whisper`，没装时用 `uv` 临时拉起。

### Changed

- 描述改为「Use when …」触发语；方案阶段注明用宿主的提问工具，把方案、片名和品牌元素一次问完。
- `pitfalls.md`：
  - 「并行渲染缓存报错」改写为「先打包一次」的做法。
  - Lyria 一行补上「请求被服务端断开」的情况。

## [0.4.1] - 2026-10-11

### Fixed

- 卡片定价依据只写 Credits，不出现法币金额（官网详情页会读取 `skill-card.yaml`）。

## [0.4.0] - 2026-10-11

来源：制作动态图志《跳出局部最优》时验证过的修复，只移植通用部分。

### Changed

- `tools/deliver.sh` 分块渲染：整片约 5400 帧一次渲染在片尾反复崩溃（V8 `TrustedCast` 致命检查，Remotion 报
  `Page crashed!`，并发 8 与 4 均复现），分块单独渲染全部正常。现按章节边界分块、每块新起一次静音渲染，
  concat `-c copy` 拼接，配乐母带只编码一次（AAC 320k，bitexact）并按视频时长截断。`CHUNKS` 可手动指定，
  `FILM_BGM` 可换音频，`SKIP_RENDER=1` 复用已有母版（缺母版即失败）。
- 交付文件只留 title 与 artist，并去掉文件内所有工具名：重封装加 `CLEAN`（去 x264 SEI、封装器 `encoder=Lavf…`）；
  竖版先编码到临时文件再流复制重封装（否则 stsd compressorname 留 `Lavc… libx264`）；AAC 编码时即 bitexact。
  新增长签名、区分大小写的 `grep -a` 门禁（短的大小写不敏感匹配会在压缩数据里偶然命中）。
- `tools/fonts.py`：抽取时缺 OS/2 表即失败（苹果 `Courier.ttc` 没有 OS/2，Chrome 的 OTS 拒收，`FontFace.load()` 报
  `NetworkError`、渲染被取消；改用 `Supplemental/Courier New.ttf`）；子集后逐个过 OpenType Sanitizer，任一被拒即失败；
  新增 `validate` 子命令。`bootstrap.sh` 预检 `opentype-sanitizer` 或 `uv`。
- 依赖说明改为 Node 24+（`tools/*.mjs` 直接 import `src/timeline.ts`）。

### Pricing

- 官网付费上架：一次性购买 1,394 Credits。

### Added

- `tools/chunks.mjs`：从 `timeline.ts` 给出分块，只在章节起点切，每块 ≤ `CHUNK_FRAMES`（默认 1500），片尾单独一块。
- `src/lib/layout.ts` 的 `LayoutOverride` context：竖版片尾可按 16:9 渲染冻结的场景缩略图。
- `references/pitfalls.md`：以上各项，以及 Lyria 3 Pro（OpenRouter）单条约 3 分钟上限与偶发空流、Whisper 在纯器乐上的
  「Thank you.」幻觉、片内算法实跑数字同样需要对抗核查；`fact-and-disclosure.md` 台账纳入算法实跑数字与指向性标注。

## [0.3.0] - 2026-10-11

### Added

- 起步模板可在全新目录一步跑通：`tools/bootstrap.sh` 生成纹理、抽取并子集化字体、注入官方 Logo（`FILM_LOGO`）
  与品牌印章（`FILM_SEAL_DIR`）、写入占位静音配乐；`tools/textures.py` 移植；`pnpm-workspace.yaml` 与 lockfile。
- Profile 记录 `records.brand_name` / `records.brand_logo` / `records.seal_asset`，优先于共享 `brand.*`（共享品牌可能是伞形品牌）。

### Changed

- 片名与副题参数化为 `TITLE` / `SUBTITLE`；`snap.py`、`analyze.py` 改为命令行参数（吸附窗口默认 ±0.5 s，与文档一致），
  修复音频长度恰为整拍时的越界崩溃；`vocal_scan.py` 输出到 `audio/`；交付脚本母版名用 `FILM_SLUG`。

## [0.2.0] - 2026-10-11

### Changed

- 由 `lov-film-chronicle`（动态编年片）更名为 `lov-film-atlas`（动态图志）：片型按风格定义，编年只是其中一种轴；
  新增空间（地图巡游）、分类（图鉴）、工序、尺度四种轴的选轴判据与读数格式。来源：用户 2026-10-11「编年方案是不是让这个类型受限了？」
- 流程第一步由「编年方案」改为「结构方案」：先选轴再切章。
- 起步模板：`yearKeys` / `yearAt` 泛化为 `axisKeys` / `axisAt`，新增 `AXIS` 读数格式配置。

## [0.1.0] - 2026-10-11

### Added

- 首个 `lov-film-*` 片型 Skill：动态编年片。片型语法、流水线与门禁、事实台账与示意说明、套件约定。
- 起步模板 `assets/starter/`：HUD、转场、纸纹、排版、布局常量、字体子集、联系表、交付与质检脚本、配乐卡点脚本。
- 真实案例：《字里中国》v0.3。
- 硬门禁来自该案例的用户纠正：画面不展示制作技术；印章与署名用品牌与官方 Logo；协作上关键创意给 1–2 版选项并并行推进。
