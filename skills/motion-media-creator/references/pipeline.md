# 流水线：产物与门禁

每一阶段都有一个可回读的产物；没有产物或门禁未过，不进入下一阶段。

| 阶段 | 产物 | 门禁 |
| --- | --- | --- |
| 1 结构方案 | `chapter-plan.md`：轴的选择；章节表（章名、轴上位置、内容关键词、主画面、配色、字体、内部技法、`axisKeys`、时长）；缺席名单（未成章的有名成员与理由）；用到第三方素材时的素材表（作者、标题、许可、来源链接） | 用户看过方案与 1–2 版品牌元素；章节数 8–15；每章（含片头、片尾）≥ 11 秒；总长 2–4 分钟；方案写明画幅（默认只做 16:9）、旁白方式（TTS / 真人原声）、字幕语言（默认中文）与要发的平台 |
| 2 事实台账 | `facts.json`：每条上屏事实的原文、来源、结论（成立 / 部分成立 / 不成立）、改写；旁白稿 `audio/narration/lines.json` | 无「不成立」残留；旁白每句的事实都在台账里；示意画面均有标注；缺席名单每项都写定上屏位置与文案（片尾选样说明，无名形象另加就近标名） |
| 3 配乐与旁白 | 分章配乐：`audio/chapters/briefs.json`、每章两条候选、`analysis.json`（含拟合的节拍网格）、`picks.json`（可选）、`bgm-music.wav`；单曲时：候选音频、`structure.json`、`snaps.json`、`bgm-music.wav`；旁白 `clips/`、`timing.json`、`src/narration.ts`、`voice-stem.wav`；`bgm-master.wav` | 配乐无人声（人声扫描的幻觉已人工判读）；分章时每章拟合网格上的小节强拍落在章节第一帧、换段提前 1 秒叠入、章节起点同在 15 帧网格上、`music_bed.py` 无报错、`qc/beat_phase.py` 通过（各章节拍相位距网格与彼此都在 ±25 毫秒内；用整片配乐时它进出的每处衔接两侧相差 ≤ 25 毫秒）；付费调用都在 `ledger/costs.jsonl` 有一行；`narration.py` 无 PROBLEM；旁白整轨约 −17 LUFS，旁白处音乐压低约 9 dB；母带 −16 LUFS ±1、真峰值 ≤ −1 dBTP；整片单次挂载 |
| 4 场景 | Remotion 工程：`timeline.ts`、每章 `Sxx*.tsx`、HUD 与章节标题卡、转场、片头片尾（片尾署名卡 `CREDITS`） | `tsc --noEmit` 通过；字体子集无缺字；上屏文字不低于字号下限 |
| 5 检查 | 每章联系表、全片抽帧、转场窗口拼图（每个交付画幅一套，默认只有 16:9）；`tools/chapters.mjs` 的章节时间轴；片尾静帧 | 无溢出、字幕与 HUD 不碰撞、标题卡与场景文字不碰撞、字号不低于下限、无制作技术文字、（做竖版时）竖版在安全区内；缺席名单每项在画面上有交代；`chapters.mjs` 通过（第一条 `00:00`、≥ 3 章、每章显示时长 ≥ 10 秒）；片尾署名卡条目齐全、带许可短链接、不指向简介 |
| 6 封面 | `封面16x9`、`封面4x3`、`封面3x4` 各一份 PNG + JPG（按比例命名，不论是否做竖版）；`cover/brief.json`、`cover/takes/`；`reports/vX.Y/covers.tsv` 与缩略拼图 | 480×270、360×270、270×360 下片名一眼可读；片名、印章与 Logo 不压主体关键部位；AI 底图里没有字、标志、徽章；封面上没有章节名与步骤轴；黑边扫描的命中已看图确认 |
| 7 交付 | 平台成片、`reports/vX.Y/`（probe、audio-qc、ebur128、联系表、首帧、sha256、交付报告）；交付报告含 AI 生成内容清单、版本历史与费用汇总；`publish-handoff.md` 与 `publish-copy/` | 从编码文件回读：解码无错、响度达标、元数据只含片名与出品方；各平台文案长度为实测且不超限；AI 标注留给用户决定 |

## 1 结构方案

- 先选轴（见 [style-grammar.md](style-grammar.md)「选轴」），在 `timeline.ts` 的 `AXIS` 里设读数格式。
- 章节起点用帧号记录，30 fps；章内事件用相对帧 `axisKeys: [[帧, 轴值], ...]`，`10000` 代表章末。
- 编年轴的年份显示：公元前 841 年以前取「约前 N」并取整到 10；不存在公元 0 年。
- 节拍网格：120 BPM 时一拍 15 帧。章节起点都放在同一张网格上（起点帧对 15 取余相同），章内的剪切与冲击也落在拍上；
  分章配乐的候选每条约 30 秒，从约第 3 小节（拟合网格上离 4 秒最近、前面至少有 1 秒音乐的小节强拍）用起：章节长度加约 5 秒
  （约 2 小节引子与 0.75 秒尾巴）不超过候选长度，换段才有完整的提前叠入；不够时退到更早的小节强拍并警告，章节比第一个小节强拍
  之后的部分还长则报错（`music_bed.py` 会检查）。单曲配乐时，章节起点吸附到起音点后再微调章内节奏。
- 章节时长（含片头、片尾）≥ 11 秒，即 120 BPM 时 ≥ 22 拍（330 帧）。简介里的章节时间码向下取整到秒，YouTube 要求每章按显示的
  时间码 ≥ 10 秒；11 秒保证取整后仍有 ≥ 11 秒。《如何打造一款特斯拉》有三章显示时长正好 10 秒，刚够下限（2026-10-12）：涂装、软件各 300 帧；
  片头 322 帧即 10.73 秒，取整后也显示 10 秒。设计下限定在 11 秒而不是 10 秒，就是给取整留余量。
  起步模板的示例时间线早于这条规则，清、片名两章显示 9 秒，`tools/chapters.mjs` 会判失败。
- 每章选一种视觉技法让章与章之间有明显差异（例如柱面投影展开、裂纹生长、动态排版、融球、路径动画、
  碎片重组、等距生长、视差长卷、程序藤蔓、海浪航迹、比例数据、快切排版、像素聚合）。
  技法名只写在方案与内部文档里，不上屏。
- 交付形态：画幅默认只做 16:9（Profile `records.default_aspect`），用户点名时才做 9:16 或两版；旁白默认 TTS，
  用户给了录音的句子用真人原声（`records.narration`）；字幕默认中文，用户要求时中英双语（`timeline.ts` 的 `SUBTITLE_LANGS`）；
  封面固定三比例；写明要发的平台，交接单按它出文案。
- 第三方素材（照片、影像、三维模型、音效）取材时就记进素材表 `src/credits.ts` 的 `CREDITS`：作者、标题、许可、来源链接、改动。
  片尾署名卡（`S14Outro.tsx` 读它）与简介的两版署名块（`tools/credits.mjs` 从它生成）都从它出，不事后回忆，也不另抄一份。

## 2 事实台账

见 [fact-and-disclosure.md](fact-and-disclosure.md)。

## 3 配乐

默认分章配乐：每章一段 120 BPM 的短配乐，强拍对准章节第一帧，各章音乐性格不同；片头和片尾可以保留一条整片长度的配乐
（片头按它的重音剪过，片尾用它真正的结束段）。用户转述的观众反馈（2026-10-12，《如何打造一款特斯拉》v0.2）：
「音乐可以按照章节来配；缺少一些节奏」，v0.3 照此改，作为默认。节奏规则见 [style-grammar.md](style-grammar.md)「节奏」。

- 简报 `audio/chapters/briefs.json`：`common` 写所有章共用的要求（纯器乐、120 BPM 4/4、开头就在强拍上进全编制、不要长前奏和淡入、
  拍子清楚、给旁白留出人声频段，加一句片子的题材与配器风格）；`chapters` 按章节 id 每章一句情绪（主奏乐器、质感、能量），
  沿全片情绪曲线走，相邻两章要有区别。模板里的 `<…>` 不替换完，生成脚本拒绝运行。
- 生成：`python3 audio/gen_chapter_music.py --dry-run` 先报数量与费用，再 `python3 audio/gen_chapter_music.py [章节 id…]`。
  经 OpenRouter 调用 Lyria 3 Clip（`google/lyria-3-clip-preview`），每条约 30 秒、0.04 美元（2026-10-12），每章两条候选
  （b 条要求换一种编配），13 章共 26 条约 1.04 美元；付费调用前先向用户说明单价与总价。密钥只从环境变量 `OPENROUTER_API_KEY` 读。
  空流、断连、5xx、408 与 429 自动重试；已有的候选不重复生成。这些请求（含重试与失败）每次在 `ledger/costs.jsonl` 记一行，费用取
  OpenRouter 返回的 `usage.cost`（见第 7 节「费用账本」）。其他 4xx（400、401 密钥错、402 余额不足、403）在出音乐之前就被拒绝：
  这一条立即停下，不重试、不记账；401、402、403 之后还没开始的条目也跳过。旧版把 401 当瞬时故障，4 条候选发出 16 次请求、记 16 行
  「失败且费用未知」；新版 1 次请求、0 行（2026-10-13 无网络模拟）。
- 分析：`uv run --quiet --python 3.12 --with librosa python audio/chapters/analyze.py` → `analysis.json`，两部分：选条用的首拍时间、
  节拍清晰度 `clarity`、拍距离散度 `ibi_cv`；定位用的节拍网格：1 秒之后的稳定拍点按最小二乘拟合出拍长与相位（`period`、`bpm`），
  拟合残差 `resid_ms`（拍点离拟合线的中位距离），四拍里起音最强的一拍作小节强拍，列出 `downbeats`。每章选拍子最清楚、最稳的一条
  （约 120 BPM、`ibi_cv` ≤ 0.05、首拍在 1 秒内，其中 `clarity` 最高）；`resid_ms` 超过 15 毫秒的候选拍子在漂（好的约 3 毫秒），
  自动选择跳过它、改用另一条。能试听就试听，最后以耳朵为准。
- 人声扫描（`audio/vocal_scan.py --out audio/chapters/vocal-scan.json audio/chapters/*.mp3`）：Whisper 在纯音乐上几乎总会转写出
  文字，`no_speech_prob` 也给 0，不能据此判有人声。按连贯性与置信度判：同一句在各窗口重复、一句里自我重复、各语种的播出套话
  （「Thank you.」「music」「Продолжение следует...」、字幕署名）、句与句接不上且 `avg_logprob` 远低于 −1，都是幻觉；
  真人声是前后连贯的歌词或说话，`avg_logprob` 约 −0.6 以上。脚本把不像幻觉的片段列在 `listen` 里，至少听这些；
  能听的话每条选中的都听一遍。交付报告写明哪些是听过的、哪些只经扫描判读。
- 拼接：`python3 tools/music_bed.py` → `public/audio/bgm-music.wav`。每条选中的配乐先按拟合速度变速到正好 120 BPM（不变调，
  倍率 = 拍长 ÷ 0.5 秒；ffmpeg 有 rubberband 滤镜时用它，没有时用 atempo），再把拟合网格上离 4 秒最近、前面至少有 1 秒音乐的
  小节强拍放在章节第一帧。不再用「检测到的首拍 + 4 秒」推算：librosa 开头几拍还没稳住，《如何打造一款特斯拉》v0.4 这样推算，
  13 章里 6 章偏离画面的节拍网格 94–244 毫秒，其中两章差半拍；v0.5 改用拟合网格后 13 章落在同一相位（2026-10-12）。
  换段是提前叠入，不是硬接：进来的一段在章节第一帧前 1 秒从它前面的音乐等功率淡入（正弦），叠在出去的一段下面；出去的一段从章节第一帧前 0.25 秒到后 0.75 秒等功率淡出（余弦）。两段同在
  120 BPM 网格上，叠的这一秒拍子对得上。响度只按章节本体调平（不算引子与尾巴）。没有候选的章（通常是片头、片尾）放整片配乐
  `public/audio/bgm-full.wav` 的同一时段，进出整片配乐同样提前叠入，相邻几章都用整片配乐时连成一段。
  整片配乐要平移到分章配乐的网格上：先 `uv run --quiet --python 3.12 --with librosa python audio/chapters/analyze.py public/audio/bgm-full.wav`
  （结果并入 `analysis.json` 的 `bgm-full.wav` 项），`music_bed.py` 再按每处衔接的网格偏差平移它：对一拍取余、折到 ±半拍内，取最小的
  有符号平移（负值是提前），两头都有衔接时取两处偏差的圆周平均。画面不动，片头里画面所卡的重音随音乐一起移动：片头的剪切点与章节起点
  在同一张 15 帧网格上，平移后重音也落到这张网格上。缺网格时实跑报错退出；`--full-shift <毫秒>` 手动指定，`0` 即不平移。平移超过 1/4 拍、平移后衔接仍偏
  10 毫秒以上时警告。2026-10-12《如何打造一款特斯拉》v0.5：整片配乐在进 01 章与出 13 章两处偏 +90.4、+86.7 毫秒，叠入的那一秒两段拍子
  错开约 90 毫秒；平移 −90.4、−86.7 毫秒后重拼，两处衔接两侧相差 −3.3、+3.1 毫秒，两处叠入之间的音频不变。平移只经测量验证，下次渲染
  要听一遍片头与两处衔接。
  用户反馈（2026-10-12，《如何打造一款特斯拉》v0.3）：「片段之间的音乐衔接有些生硬」，原因是新的一段在章节第一帧从首拍硬进、
  上一段只有 0.35 秒淡出；该片 v0.4 改为提前叠入，作为默认。章节起点不在同一张 15 帧网格上时报警告；候选不够完整引子时
  退到更早的小节强拍并警告（衔接接近硬接）；候选在第一个小节强拍后比章节短时报错；选中的候选（含 `picks.json` 指定的）
  `resid_ms` 超过 15 毫秒、或变速超过 3% 时警告。
  选择与响度写在 `audio/chapters/picks.json`（`{"<id>": {"take": "a", "lufs": -18}}`，`"take": "full"` 指定用整片配乐），
  没写的章按上面的规则自动选、−18 LUFS。
- 节拍相位质检：`uv run --quiet --python 3.12 --with librosa python qc/beat_phase.py`（读 `public/audio/bgm-music.wav`，不用带旁白的
  母带）。每章去掉两头的叠入部分，把配乐的起音强度按（t − 网格相位）对一拍取余叠起来，峰值就是这一章的节拍相位。门禁：用自己配乐的
  各章距网格都在 ±25 毫秒内、彼此相差不超过 25 毫秒，否则非零退出；放对的配乐读数约 −10 毫秒（测量本身的偏差），差半拍读约 ±250。
  整片配乐的章只报告（加 `--all` 才判），但它与分章配乐的每处衔接默认就判：两侧各取紧挨叠入区、最多 8 秒的一段测相位，相差超过 `--tol`
  即失败；JSON 里有 `joins` 与 `worst_join_ms`。旧版只在 `--all` 时看整片配乐，衔接错拍也照样通过：该片已发布的 v0.5 配乐床旧质检判过，
  新质检判失败（两处衔接相差 +86.9、+94.0 毫秒）。2026-10-12 在起步模板的示例时间线上用该片 26 条候选实测：13 章 −4.1 至 −15.9 毫秒、
  彼此相差 11.8 毫秒；按旧推算拼的同一组配乐 10 章超出 ±25 毫秒，最远 −238.6 毫秒。
- 分章响度：安静的章 −21 至 −19 LUFS，一般 −18 至 −17，重击与高潮 −16 至 −15（《如何打造一款特斯拉》v0.3 用 −21 至 −15）；
  之后 `tools/voice_mix.py` 只做整体增益与限幅，章与章的相对响度保留。
- 没有整片配乐时，把片头、片尾也写进 `briefs.json` 各配一段（片尾那段在片子最后 1 秒淡出）。
- 能试听就把拼好的整片听一遍章与章的衔接，再进旁白与混音；不能试听时在交付报告里写明。

单曲配乐（备选，片子短、章与章不需要换音乐，或用户点名一条完整配乐时）：

- 简报写清：纯器乐、时长、BPM、段落时间点与情绪（例：开场留白 → 渐进 → 重击 → 行进 → 高潮 →
  轻盈 → 宽阔 → 紧张 → 断裂 → 收束）。段落时间点直接对应章节方案。`audio/gen_bgm_openrouter.py` 生成 2–3 条候选（Lyria 3 Pro）。
- 候选生成后做起音与段落分析（`audio/analyze.py`），选与章节结构最贴的一条；再扫一遍是否混入人声（判读同上）。
- 章节起点吸附（`audio/snap.py`）：在 ±0.5 秒内找最近的强起音点；最强的一击留给全片的转折章（例如「断裂」）。
- 选定的一条直接放 `public/audio/bgm-music.wav`。

两种做法的母带都只做线性增益 + 限幅，不做响度归一化重塑动态。

### 旁白

- 旁白稿 `audio/narration/lines.json`，帧号是章内相对帧：

  ```json
  [{"id": "n03", "chapter": "qin", "at": 40, "until": 300,
    "zh": "前 221 年，秦统一六国。", "tts": "公元前二百二十一年，秦统一六国。",
    "en": "In 221 BCE, Qin unified the six states."}]
  ```

  `zh` 是中文字幕，`tts` 是读法（数字、单位写成读音；留空按 `zh` 读），`en` 是英文字幕（只出中文时可留空）。
  `at` 写在这句说的镜头起点之后 6–15 帧（0.2–0.5 秒）。
  写法见 [style-grammar.md](style-grammar.md)「旁白与字幕」。
- `python3 tools/narration.py`：有 `audio/narration/voice/<id>.*`（用户录音，任何 ffmpeg 读得了的格式）就用录音，
  否则调豆包 Seed-TTS 2.0（`POST https://openspeech.bytedance.com/api/v3/tts/unidirectional`，请求头 `X-Api-Key` 取自
  环境变量 `VOICENGINE_API_KEY`、`X-Api-Resource-Id: seed-tts-2.0`；返回逐行 JSON，音频是 base64 分片；默认音色
  `zh_male_ruyayichen_uranus_bigtts`、`speech_rate` 10，约每秒 4.0 字含停顿，2026-10-12 实测），按读法、音色、语速缓存。
  逐句去掉首尾静音、量时长，写 `timing.json` 与字幕表 `src/narration.ts`；超出 `until`、与下一句间隔不足 0.25 秒、
  离开本章、落在片名卡或片尾卡上，都报 PROBLEM 并非零退出。`--check` 只复查时长。`--dry-run` 不联网、不读密钥，列出真跑要合成的句子、
  句数与字符数（扣除缓存命中与用户录音）和音色：调用前把字符数告诉用户，单价按火山引擎控制台说（本 Skill 没有实测单价，2026-10-13）。每次 TTS 请求在账本记一行：用量是字符数，
  `cost_usd` 为 null（接口不返回价格），缓存命中与用户录音不记。
- `python3 tools/voice_mix.py`：配乐 `public/audio/bgm-music.wav` + 旁白（+ 可选音效轨 `audio/sfx/sfx-stem.wav`）→
  `public/audio/bgm-master.wav`。旁白整轨调到约 −17 LUFS；旁白期间音乐压低约 9 dB、音效约 4 dB（0.2 秒压下、0.6 秒恢复）；
  母带同上，−16 LUFS、真峰值 ≤ −1 dBTP。改过旁白稿后依次重跑 `narration.py`、`fonts.py subset`（字幕的字进子集）、`voice_mix.py`。

## 4 场景

- 每章一个 Composition（横版 `chNN-id`、竖版 `vNN-id`），时长 = 本章 + 下一章转场重叠。
- 转场：墨晕、光晕、百叶、闪白、擦除（带边线）、碎片、圆孔、波浪、黑场；重叠帧由下一章的 `transitionFrames` 决定。
- HUD 在转场中点切换配色；深色章节用 `hudAlt` 换墨色与底板。
- 章节标题卡（`src/components/ChapterCard.tsx`）：每章转场过半时在 HUD 章名头的位置出大号序号与章名，章内第 `CARD_OUT`（50）帧
  淡出，HUD 小章名同时淡入。场景在本章前约 2 秒不往左上放文字，也不另做同名大标题。
- 字号按 [style-grammar.md](style-grammar.md)「字号下限」：字幕、引线标注（`Callout`）、大数字（`BigNumber`）用起步模板的共享组件，
  尺寸从 `TYPE_FLOOR` × `useLayout().ts` 取；数据块与清单 ≥ 26 px；角落标注保持 14 px。
- 做竖版时：内容放在共享布局常量的舞台带（例：y 330–1540），HUD 进度轴放在 H−300。
- 片尾署名卡：`S14Outro.tsx` 读 `src/credits.ts`：`CREDITS`（`{author, title, license, url, changed}`，按片中出现顺序，每份一次）里
  需要署名的逐条「作者 · 标题 · 许可」，再接 `CREDITS_CHANGED`（改动说明）、许可行（`licenseUrl()` 从许可名推出短链接）和不要求署名的素材
  一行（`otherLine()`，按许可归组）；字号随条目数在留白内缩小（16:9 最小 14 px）。
  缩到最小仍放不下时另做一张署名卡，不删条目。写法见 [fact-and-disclosure.md](fact-and-disclosure.md)「片尾署名」。
- 字幕层在章节之上、HUD 之下（`src/components/Subtitles.tsx`）：16:9 底边在 H−128，避开移动的读数；9:16 在舞台带底部。
  有旁白时（`NARRATED`），场景左下的正文说明不再上屏，由字幕承担。
- 单章预览：`tools/preview.sh <id> stills 16x9 <章内帧…>`、`sheet 16x9 <间隔>`、`clip 16x9 <起> <止>`。每章生成只挂本章的
  入口（`src/dev/entry-<id>.tsx`），带 HUD 与字幕、按整片时间线；多 Agent 并行搭章时各自用它预览，章节代码与预览随做随写盘，
  断线后可从盘上续做（见 [pitfalls.md](pitfalls.md)）。

## 5 检查

- 每章：`tools/sheet.sh <comp> <from> <to> <every> <out.jpg>`，或 `tools/preview.sh <id> sheet 16x9 <every>`（带 HUD、标题卡与字幕）。
- 字号：在 1920×1080 原尺寸静帧上看字幕、标注、数据块是否一眼可读；源码里 `fontSize` 低于下限的逐个说明理由（只有角落标注例外）。
- 抽查静帧：`tools/stills.sh <前缀> <comp> <scale> <帧…>`，先 `remotion bundle` 一次再从 bundle 并行出图，
  不要每张都从 `src/index.ts` 重新打包。
- 全片：每 10 帧低分辨率抽帧，用 `qc/transition_sheet.py` 按章节起点拼「起点前 20 帧到后 60 帧」窗口。
- 用多 Agent 时：一路按源码列出所有上屏字符串，一路按渲染帧逐帧找文字，合并后对抗核查遗漏。
- 章节时间轴：`node tools/chapters.mjs`（默认写 `../manifest/chapters.txt`，`--names short` 换短章名）。时间码向下取整，每章时长按
  相邻两条显示的时间码算，最后一章算到取整后的片长；少于 3 章、起点乱序或任一章不足 10 秒时非零退出且不写文件，不足 11 秒警告。
  不过就改 `timeline.ts` 的章节时长，不在简介里改时间码。
- 片尾：`tools/stills.sh` 出片尾片名卡的静帧，看署名卡条目齐全、许可短链接可读、没有「见简介」一类的话。

## 6 封面

每片交 `封面16x9`、`封面4x3`、`封面3x4` 三张，按比例命名，各出 PNG 与 JPG；4:3 同时是 B 站首页卡片与视频号分享卡片，3:4 是视频号主页卡片。
AI 只出没有文字的底图，片名、英文名、印章与 Logo 由 `src/Cover.tsx` 排版。

1. 写 `cover/brief.json` 的 `subject`（片中出现过的主体画成一张图）与 `style`（渲染方式、光线、一个取自片中配色的强调色）；
   `tone` 选片名空位的底色（`dark` 近黑，`paper` 纸色，与 `Cover.tsx` 的 `COVER.tone` 一致），`layouts` 按它给片名留空位，`forbid` 禁止标志与文字，一般不动。
2. `python3 tools/gen_cover_bg.py --dry-run` 打印提示词、请求体与估价（不联网），告诉用户后再真跑；默认 16:9 与 3:4、2K。
   余额低于 1.00 美元加估价时脚本不开始；断线照样可能计费，重试前先核用量。
3. `src/Cover.tsx` 的 `COVER` 设英文名、断行与字体；`tools/stills.sh covers` 出三张静帧，逐张看原尺寸与缩略尺寸。
4. 定稿后 `tools/deliver.sh covers vX.Y`。

版式、提示词、费用、1K/2K 与 4:3 专图的取舍、黑边扫描的误报，见 [covers.md](covers.md)。

## 7 交付

- `deliver.sh 16x9 <版本> [并发]`（默认只跑这一条；用户点名竖版时再跑 `deliver.sh 9x16`）：环境变量 `FILM_TITLE`、`FILM_BRAND`、`MEDIA_CREATOR_SCRIPTS`、可选 `FILM_DATE`、`FILM_SLUG`。
- 母版分块渲染：先用 `tools/bundle.sh` 打包一次（空 public 打包，再把 `public/` 克隆进去），默认由 `tools/chunks.mjs` 在章节起点切块
  （每块 ≤ 1500 帧，片尾单独一块），每块新起一次渲染且静音，
  concat 无损拼接后把配乐母带编码一次混入；`CHUNKS=a-b,c-d` 手动指定，`SKIP_RENDER=1` 复用已有母版只重做平台文件与质检。
- 视频号：CRF 20、maxrate 9M、High@4.1、bt709 标记、faststart；B 站：母版直出 + faststart。
- 平台文件都清除元数据（Remotion 会写入 `Made with Remotion`），只写片名与出品方；再去掉封装器戳记、x264 SEI 版本串、
  竖版样本描述里的编码器名与 AAC 码流里的版本串，最后用长签名 `grep -a` 回读整个文件确认不含工具名。
- 封面：`deliver.sh covers vX.Y` 写出 `output/images/<品牌>-<片名>-封面<比例>-<日期>-vX.Y.png|.jpg`、`covers.tsv` 与缩略拼图；
  交 16:9 或 9:16 成片后，这一版的封面缺了它会提醒。
- 旧版本整体移入 `output/archive/vX.Y/`，不删除。

### 交付报告

`output/reports/vX.Y/delivery-report.md`：状态字段、文件（成片、三张封面）、质检数字、配乐与旁白来源、事实依据、字体授权提醒，另有三节。

- **AI 生成内容清单**：旁白（TTS 服务商、模型、音色；用户录音替换的句子单列）、配乐（模型、哪几章）、封面底图（模型、哪几个比例）、
  片中画面与音效，每类一行，没有的写「无」；后面照抄平台事实并写核实日期。Skill 不替用户决定标不标，不写「已合规」「无需标注」。
  模板与平台事实见 [fact-and-disclosure.md](fact-and-disclosure.md)「AI 生成内容清单」。
- **版本历史**：从 v0.1 累计到本版，每版一行。

  | 版本 | 改了什么 | 为什么 |
  | --- | --- | --- |
  | v0.4 | 去掉副题；分章配乐换段改为提前 1 秒叠入 | 用户看 v0.3：「副题『十三道工序』孱弱」；「片段之间的音乐衔接有些生硬」 |

  「为什么」写用户原话或检查发现，不写「优化体验」一类的话。
- **费用**：贴 `python3 tools/ledger.py summary --since <上一版交付时间>` 的表（按类型、服务商、模型分组：调用、失败、用量、美元），
  再给全片累计（不带 `--since`）；失败但计费、失败且费用未知的调用单列，后者到服务商的用量页核对。旁白的 TTS 接口不返回价格，只列字符数。

用户问「这片的版本迭代与消耗」时，直接从版本历史与费用两节回答。2026-10-12《如何打造一款特斯拉》v0.5 交付后用户这样问，答案要翻
v0.1–v0.5 的报告与会话记录才凑齐。

### 费用账本

`ledger/costs.jsonl`（Remotion 工程根目录，`LEDGER_PATH` 可改），每次付费调用一行：
`{ts, kind, provider, model, qty, unit, cost_usd, ok, ref}`。`audio/gen_chapter_music.py`、`audio/gen_bgm_openrouter.py`、
`tools/narration.py`、`tools/gen_cover_bg.py` 自己写，不要再补；只有脚本之外的调用（试一条请求、在网页上生成的图）用
`python3 tools/ledger.py add` 补记。失败的调用也记（`ok: false`），费用未知时 `cost_usd` 为 null；在出结果之前就被拒绝的 4xx 不记。
`summary` 跳过类型不对的行（数量写成字符串、`ok` 写成 `"false"`、费用为 `Infinity`）并逐行报出，手改坏一行不会让整张表出错。账本进 git（`.gitignore` 已放行），是这部片子的开支记录。

### 发布交接

交付之后写 `output/reports/vX.Y/publish-handoff.md` 与 `publish-copy/`，交给 `lov-media-publisher`（视频号、B 站、小红书）；
YouTube 不在发布 Skill 的范围内，交接单照样给出它的文案与限制。

- 章节时间轴：`node tools/chapters.mjs --out ../../output/reports/vX.Y/publish-copy/chapters.txt`，不手写。
- 署名块：`node tools/credits.mjs --out-dir ../../output/reports/vX.Y/publish-copy` 从 `src/credits.ts` 写完整版（逐条带许可链接与来源链接）
  与压缩版（许可链接合成一行），并打印两版长度；与片尾署名卡同出一张表，条目和顺序自然一致，不手写。缺作者、许可、来源链接，许可推不出链接，
  或同一份素材列了两次，都非零退出、不写文件。
- 各平台正文分开存，拼好的变体按组成部分命名（`bilibili+chapters+credits-compact.txt`），长度用同一段脚本实测；
  视频号、B 站、小红书再跑 `check_copy.py`。2026-10-12《如何打造一款特斯拉》：带完整署名的 B 站简介 2646 字，超过 2000；
  压缩版署名后 1938 字。
- 第一个平台上用户手改并发布的文本是金标准，后续平台只做最小适配，再在末尾原样追加章节时间轴（与署名块）。
- 「发布时需要你决定」：各平台的 AI 标注、是否追加署名段、原创声明、合集、话题与标签。这一节和 AI 生成内容清单直接贴进交接回复：
  发布 Skill 设为 `auto` 的平台提交前不再问，按偏好不标注（[fact-and-disclosure.md](fact-and-disclosure.md)「AI 生成内容清单」）。

目录、平台限制表、拼接脚本与交接单模板见 [publish-handoff.md](publish-handoff.md)。
