---
name: lov-motion-media-creator
description: >
  动态图志：无实拍，把一个主题按时间、地图、图鉴、工序或尺度分章，做成每章一种视觉的动态设计短片，
  含章节标题卡与进度轴 HUD、旁白与大字幕、分章配乐卡点、事实核查，默认交付 16:9 成片与 16:9、4:3、3:4 三比例封面。Use when the user asks for 动态图志、
  编年/图鉴/地图动画 or a motion atlas.
license: MIT
compatibility: "Portable Agent Skills format. Remotion 4 + Node 24+, pnpm, Python 3.9+ with fontTools, Pillow and opentype-sanitizer (or uv), mlx-whisper for the vocal scan (Apple Silicon only; uv run --python 3.12 --with mlx-whisper), librosa for the per-chapter beat analysis and beat-phase QC (uv run --python 3.12 --with librosa), ffmpeg/ffprobe (its rubberband filter, when built in, for the music time-stretch; atempo otherwise). macOS system CJK fonts or licensed equivalents. Optional: Doubao Seed-TTS 2.0 (VOICENGINE_API_KEY) for the voice-over, or the user's own recordings; OpenRouter (OPENROUTER_API_KEY) for Lyria music and the text-free cover background (openai/gpt-5.4-image-2, image output needs a balance of at least $1.00)."
depends_on:
  - lov-branding-consistency
metadata:
  author: lovstudio
  version: "0.9.1"
  card_standard: lovstudio/skill-card/v1
  content_class: microcopy
  suite: lov-film
  tags:
    - video
    - motion-design
    - remotion
    - atlas
    - film-style
---

# 动态图志 · Motion Atlas

把一个主题做成 2–4 分钟的动态设计短片：没有实拍素材，屏幕文字与旁白一起叙事：旁白默认用 TTS，
也可逐句换成用户的真人原声，字幕随旁白出（默认中文，用户要求时中英双语）；
全片沿一条「轴」分章——时间（编年）、空间（地图巡游）、分类（图鉴）、工序（流程）或尺度（由小到大）；
每章一种视觉手法、一套配色与字体，像作品集一样展示；每章以大号的章节标题卡开场，底部进度轴贯穿全片，告诉观众讲到哪了；
文字按字号下限做大，一眼能读；默认每章一段配乐，强拍对准章节第一帧、换段提前叠入，剪切与冲击都在拍上；
默认只交付 16:9 横版，用户点名时才出 9:16 竖版或两版同出；封面每片都交 16:9、4:3、3:4 三张（AI 无字底图，片名由合成排字）；
交付报告带 AI 生成内容清单、版本历史与费用汇总，另写一份发布交接单。

本 Skill 是 `lov-film` 片型套件的第一个成员（2026-10-12 由用户从 `lov-film-atlas` 更名为 `lov-motion-media-creator`）：
片型 Skill 负责「这一类片子怎么拍才对」，共享的成片能力（音频母带、双画幅、媒体质检、交付契约）由 `lov-media-creator` 承担，
发布由 `lov-media-publisher` 承担。套件约定见 [references/suite.md](references/suite.md)。

## Triggers

### Activate when

- 「用动态设计讲一遍 XX 的历史/演进」「像作品集一样展示 XX」「每章换一种视觉的动画短片」。
- 编年：「中国史/互联网史的动态设计片」；地图：「丝路沿线 12 座城的地图巡游动画」；
  图鉴：「13 种传统色/10 种字体家族的图鉴动画」；工序：「一本书从选纸到装订的流程动画」；
  尺度：「从原子到星系」。
- "Make a motion atlas / motion-design explainer where each chapter has its own look", "a timeline / map / catalogue animation".
- 上一期动态图志的改版：换章节、换印章/品牌、改片尾、去掉某类画面文字、加旁白或换真人原声、加双语字幕、补出竖版、
  重做封面或补封面比例、各平台简介与章节时间轴、「说说这片的版本迭代与消耗」。

### Do not activate when

- 有实拍、录屏或口播素材要剪辑：交给 `lov-media-creator`（或对应片型 Skill）。
- 只讲一个算法/数据结构：交给 `lov-algo-viz-creator`。
- 只要封面、且不是本 Skill 做的片子：交给 `lov-channels-cover`；只要发布：交给 `lov-media-publisher`（YouTube 不在它的范围内）。
- 单个动效、Logo 演绎或 HTML 动画组件：交给 `hyperframes` 系列或 `motion-graphics`。
- 要产品片质感的实时三维画面（three.js / R3F：工序、产品构造、爆炸视图）：交给 `lov-3d-motion-media-creator`，它以本 Skill 为底座。

## User Profile (cross-session)

每次运行读取 `skill.yaml` 声明的 `user-profile/v1`：用户、品牌（名称、官方 Logo 路径、印章文字）、
工作区与输出目录、偏好。用户直接说出的长期偏好（例如「片尾署名只放 Logo」「默认勾原创」）用
`scripts/profile_store.py record ... --confirm` 写入 `skills.lov-motion-media-creator.records` 并报告保存路径。
品牌按此顺序取：本 Skill 的 `records.brand_name` / `records.brand_logo` / `records.seal_asset`，再回退共享的 `brand.*`（共享品牌可能是伞形品牌，不一定是这类片子的署名）。
品牌资产只引用 Profile 指向的官方源文件，不重绘、不生成 Logo。完整契约见
[references/user-profile.md](references/user-profile.md)。

## Skill Group Composition

开工前读 [references/skill-composition.md](references/skill-composition.md)：上游（选题、资料）、
共享核心（`lov-media-creator` 的母带、双画幅、质检、交付契约）、下游（`lov-channels-cover`、
`lov-media-publisher`）各自交接什么文件、谁负责最终验收。

## Workflow (MANDATORY)

按顺序执行；每一步的产物与门禁见 [references/pipeline.md](references/pipeline.md)。

### Step 0: 解析环境与资源

- 用 `SKILL_DIR` 或已安装目录定位本 Skill；确认 `assets/starter/`、`references/` 完整。
- 读取 Profile：品牌名、官方 Logo、印章文字、输出目录、交付命名规则，以及画幅与旁白的默认值
  （`records.default_aspect`、`records.narration`）。缺品牌 Logo 时只问一次。
- 新项目从 `assets/starter/` 起步：复制到 `<project>/work/remotion`（脚本的 `../../output` 指 `<project>/output`）后 `pnpm install`，
  再用 Profile 的 `records.brand_logo` 与 `records.seal_asset` 跑
  `FILM_LOGO=… FILM_SEAL_DIR=… tools/bootstrap.sh`（纹理、字体子集、Logo、印章、占位配乐一步到位）；
  片名改 `src/timeline.ts` 的 `TITLE` / `SUBTITLE`。结构与改造点见 [references/starter-template.md](references/starter-template.md)。
- 费用账本从第一笔付费调用记起：配乐、TTS、封面底图脚本每次可能计费的请求（含失败与重试）自己写一行到 `ledger/costs.jsonl`
  （`tools/ledger.py` 的格式）；只有脚本之外的调用（网页上出的图、单独的测试请求）用 `python3 tools/ledger.py add` 补记，
  脚本记过的不再补；账本随工程进 git。每次付费调用前先说明单价与总价；TTS 没有核实过的单价，只报字符数（见 Step 3）。

### Step 1: 结构方案（先给用户看，再开工）

- 先选轴：时间、空间、分类、工序、尺度之一（判据见 [references/style-grammar.md](references/style-grammar.md)「选轴」）。
  轴决定进度轴上显示什么（年份、地名或里程、序号、步骤、数量级）。
- 沿轴切成 8–15 章 + 片头 + 片尾。每章写：章名与轴上位置、一句内容关键词（简介章节时间轴用）、一个主画面、
  配色、字体、一种视觉技法（**仅内部使用**）、轴关键帧 `axisKeys`。
- 每章技法从 [references/techniques.md](references/techniques.md) 挑，章与章不重复。
- 列「缺席名单」：同领域最有名却没成章的成员，各写一句理由；以无名形象出场的（片头的反面、对照组）也算。
  名单上每一项都要在画面上交代，见 [references/fact-and-disclosure.md](references/fact-and-disclosure.md)「选样与未单列」。
- 片长按 120 BPM 的节拍网格分配（30 fps 一拍 15 帧，章节起点都在同一张网格上），长章 12–15 秒、短章不短于 11 秒
  （片头、片尾也算章）；总长 2–4 分钟。YouTube 章节按显示的时间码要求每章 ≥ 10 秒，11 秒留出取整的余量。
  每章写一句配乐情绪（主奏乐器、质感、能量），沿全片情绪曲线走，相邻两章不同。
- 交付形态写进方案：画幅默认只做 16:9，用户点名时才做 9:16 或两版；旁白默认 TTS，用户给了录音的句子用真人原声；
  字幕默认中文，用户要求时中英双语；封面三比例；要发哪些平台（决定交接单里出哪几份文案）。
- 用到第三方素材（照片、影像、三维模型、音效）时，取材当下逐条记进 `src/credits.ts` 的 `CREDITS`（作者、标题、许可、来源链接、改动），
  按片中出现顺序、每份一次；片尾署名卡与简介的两版署名块都从这张表出，不另写一份
  （《如何打造一款特斯拉》只用了 CC0、公有领域、Pexels 与 CC BY 2.0/3.0/4.0）。
- 关键品牌元素（印章、署名、Logo 位置）给 1–2 版让用户挑，不自行跑多轮评审——见
  [references/style-grammar.md](references/style-grammar.md)「协作节奏」。宿主有提问工具（如 AskUserQuestion）时，
  方案、片名和品牌元素一次问完，推荐项放第一个。

### Step 2: 事实台账与对抗核查

- 列出每一条将上屏的事实（年份、数字、引文、地名、人物、归属、工艺参数），逐条带来源核对；能用多 Agent
  时让独立核查者「试图驳倒」每一条。不成立的改写或删除，部分成立的按建议改写。
- 示意性画面（地图、建筑、纹样、古文字、比例、流程图）必须在画面上标「示意」；字体只代表风格时也要说明。
- 细则与常见坑见 [references/fact-and-disclosure.md](references/fact-and-disclosure.md)。
- 旁白稿 `audio/narration/lines.json` 逐句只用台账里的事实；英文字幕里的人名、地名、机构名全片一种写法。
  写法与时长见 [references/style-grammar.md](references/style-grammar.md)「旁白与字幕」。

### Step 3: 配乐、旁白与卡点

- 默认分章配乐：每章一段 120 BPM 配乐，按拟合的节拍网格变速到正好 120 BPM、约第 3 小节的强拍落在章节第一帧，
  换段提前 1 秒等功率叠入（不硬接），按章设响度目标；片头、片尾可保留一条整片配乐（片头按它的重音剪过）。
  简报 `audio/chapters/briefs.json` → `audio/gen_chapter_music.py`（Lyria 3 Clip，
  `google/lyria-3-clip-preview`，经 OpenRouter，0.04 美元一条 30 秒，每章两条候选；调用前先说明单价与总价）→
  `audio/chapters/analyze.py`（librosa，经 uv）按节拍清晰度选、拟合节拍网格 → `tools/music_bed.py` 拼成 `public/audio/bgm-music.wav`
  → `qc/beat_phase.py` 验各章节拍相位（距网格与彼此都在 ±25 毫秒内）。
  不用程序合成音乐。细则见 [references/pipeline.md](references/pipeline.md) 第 3 节。
- 片头、片尾用整片配乐 `public/audio/bgm-full.wav` 时，先 `analyze.py public/audio/bgm-full.wav` 拟合它的网格，`music_bed.py`
  再把它平移到分章配乐的网格上（±半拍内取最小平移，`--dry-run` 先看平移量与衔接偏差）；`beat_phase.py` 默认就判整片配乐进出的
  两处衔接（两侧相位相差 ≤ 25 毫秒）。2026-10-12《如何打造一款特斯拉》v0.5 未平移的整片配乐在两处衔接偏约 90 毫秒，旧质检照样通过。
- 单曲配乐是备选（片子短，或用户点名一条完整配乐）：生成 2–3 条候选，分析起音点与段落，把章节起点吸附到最近的强拍/起音点。
- 人声扫描：Whisper 在纯音乐上会幻觉出文字（`no_speech_prob` 也是 0），按连贯性与 `avg_logprob` 判读，`listen` 列出的片段
  要人耳听；能听就听，没听过的写进交付报告。
- 节奏：剪切与冲击在拍上，章节换音乐在章节强拍上，旁白在它说的画面出现后 0.2–0.5 秒开口
  （[references/style-grammar.md](references/style-grammar.md)「节奏」）。
- 旁白：`tools/narration.py` 逐句出声（`audio/narration/voice/<id>.*` 有用户录音就用录音，否则用豆包 Seed-TTS 2.0，
  密钥只从环境变量 `VOICENGINE_API_KEY` 读），量出每句时长并写出字幕表 `src/narration.ts`；超出 `until`、挤到下一句、
  离开本章或落在片名卡与片尾卡上即失败。TTS 是付费服务：先跑 `python3 tools/narration.py --dry-run`（不联网、不读密钥），
  把要合成的句数、字符数（已扣除缓存命中与用户录音）和音色告诉用户；接口不返回价格，本 Skill 也没有实测单价，单价按火山引擎控制台说，不估。
- 混音：选定的配乐放 `public/audio/bgm-music.wav`，`tools/voice_mix.py` 把旁白整轨调到约 −17 LUFS，旁白期间音乐压低约 9 dB、
  音效约 4 dB（0.2 秒压下、0.6 秒恢复）。
- 母带（`tools/voice_mix.py`，没有旁白时只处理配乐）：线性增益 + 限幅到 −16 LUFS、真峰值 ≤ −1 dBTP；整片只在根层挂载一次。

### Step 4: 搭建场景

- 每章一个独立 Composition；`tools/preview.sh <id>` 从只挂本章的入口预览，别的章坏了也不影响。场景代码横竖共用，
  做竖版时内容限制在共享布局常量的舞台带内。
- HUD：左上「序号 / 章名 / 轴上位置」，底部进度轴与当前读数；读数按 `axisKeys` 分段插值，
  格式由 `timeline.ts` 的 `AXIS` 决定，与画面事件同步。
- 章节标题卡（`ChapterCard`）：每章开场在 HUD 章名头的位置出大号序号与章名，约 1.7 秒后淡出，小章名接上；
  场景在本章前约 2 秒不往左上放字，也不另做同名大标题。
- 字号按 [references/style-grammar.md](references/style-grammar.md)「字号下限」（1920×1080：字幕中文 46 / 英文 27 px、
  引线标注 22 px 配 1.5 px 引线、数据块与清单 ≥ 26 px、HUD 读数 16 / 段名 15 px、大数字 120–160 px），其他画幅按
  `useLayout().ts` 缩放；角落的示意与出处标注保持 14 px 小字（Profile `records.annotation`）。
- 有旁白时，场景左下的正文说明让位给字幕（`if (!NARRATED)`）：同样的事实已经说出来了。大标题、主画面里的字、HUD
  与「示意」、出处等小字标注照常。字幕居中在进度轴上方，中文在上、英文在下；亮画面用 HUD 的墨色。
- 片头：一笔成轴落到底部进度轴；片尾只有片名卡（印章 + 官方 Logo 署名 + 说明）：收束章之后直接接，不做章节回顾，
  也不做片名卡之前的过渡动画（如进度轴收回成一笔）。
- 片尾署名卡自足：需要署名的素材逐条写「作者 · 标题 · 许可」，用到的每种许可写「许可名 + 短链接」
  （`creativecommons.org/licenses/by/2.0`），改动过的素材写一句；不写「许可链接见视频简介」。起步模板 `S14Outro.tsx` 读
  `src/credits.ts`，见 [references/fact-and-disclosure.md](references/fact-and-disclosure.md)「片尾署名」。
- 用到的字先跑字体子集；缺字立即报错，不静默回退；每个子集过 OpenType Sanitizer，被拒即失败（Chrome 会拒载）。
- 场景尺寸一律从 `useLayout()` 取；要在竖版里放 16:9 缩略图时用 `LayoutOverride` 包住冻结的场景，冻结帧取整数。

### Step 5: 逐章与全片检查

- 每章渲染联系表，检查文字溢出、HUD 与字幕碰撞、标题卡与场景文字碰撞、字号是否低于下限、（做竖版时）竖版安全区；全片每 10 帧抽帧，按章节边界拼转场窗口检查。
  有旁白时抽查字幕与声音同句、旁白说到的事物此刻在画面上。
- 章节时间轴：`node tools/chapters.mjs` 从 `timeline.ts` 打印 `MM:SS 章名`（向下取整，第一条 `00:00`）；少于 3 章或任一章
  按显示的时间码不足 10 秒即非零退出，不足 11 秒警告。不过就回 Step 1 调章节时长，不在简介里手改时间码。
- 片尾静帧看一眼署名卡：条目齐全、许可短链接可读、没有指向简介的话。
- **画面不展示制作技术**：技法名、渲染参数、帧数、工具与模型署名、建模线框都不上屏（硬门禁）。
- **上屏文字与旁白去 AI 味**：逐句查口号、金句、对仗、冒号揭示、替观众总结与跨章重复的同一句式，判据与改法见
  [references/style-grammar.md](references/style-grammar.md)「文字」；能用多 Agent 时让独立评审按全片顺序通读一遍。

### Step 6: 封面

- 每片交三张，按比例命名、不按平台命名，不论做没做竖版：`封面16x9`（B 站投稿封面、YouTube 缩略图）、`封面4x3`
  （B 站首页卡片，同时是视频号分享卡片）、`封面3x4`（视频号主页卡片），各出 PNG 与 JPG。
- 底图由 AI 生成，不带任何文字：写 `cover/brief.json`（主体只画片中出现过的东西；版式给片名留一块安静的空位，横版左 40%、竖版上 40%，
  空位的底色随片子：`tone` 选 `dark` 近黑或 `paper` 纸色，与 `src/Cover.tsx` 的 `COVER.tone` 一致；禁止标志、徽章、文字与水印）
  → `python3 tools/gen_cover_bg.py --dry-run` 报提示词与估价并告诉用户 → 真跑（默认 16:9 与 3:4、2K，
  2026-10-12 约 0.27–0.36 美元一张；OpenRouter 余额低于 1.00 美元时拒绝出图，脚本先查余额）。
- 片名、英文名、印章与官方 Logo 由 `src/Cover.tsx` 排在底图上（`COVER` 设英文名、断行、字体与 `tone`：近黑底配浅色片名，
  纸色底配墨色片名）。4:3 没有专图时，16:9 图全宽放底部、片名在上方空带里，不把 16:9 裁成 4:3；封面不放章节名、步骤轴或进度轴。
- 检查：`tools/stills.sh covers` 逐张看原尺寸（片名与印章不压主体关键部位，AI 图里没有字、标志与畸形结构）和 480×270、360×270、
  270×360 缩略；定稿后 `tools/deliver.sh covers vX.Y`。近黑底的封面，黑边扫描会把留给片名的暗部报成黑边，命中先看图。
  细则见 [references/covers.md](references/covers.md)；要九宫格整墙检验时可交给 `lov-channels-cover`。

### Step 7: 交付与发布交接

- 用 `assets/starter/tools/deliver.sh`，默认只跑 `16x9`，用户点名时才跑 `9x16`：按章节分块渲染母版（整片一次渲染会在片尾崩溃）→ 平台文件（视频号限码率、
  只留片名与出品方、去掉文件内所有工具名）→ 探测、响度、全片解码、联系表、首帧、SHA-256。
- 写交付报告：状态字段、文件（成片与三张封面）、质检数字、配乐来源、旁白来源（逐句 TTS 或真人原声、音色）、事实依据、字体授权提醒，
  另有三节：
  - AI 生成内容清单：旁白、配乐、封面底图、片中画面与音效逐类一行，没有的写「无」，附平台事实（YouTube 对 AI 音乐的声明要求、
    《人工智能生成合成内容标识办法》第十条、作者偏好及其范围），见 [references/fact-and-disclosure.md](references/fact-and-disclosure.md)「AI 生成内容清单」。
    Skill 不替用户决定平台上标不标，也不写「已合规」。
  - 版本历史：表格「版本 | 改了什么 | 为什么（用户原话或检查发现）」，从 v0.1 累计到本版。
  - 费用：`python3 tools/ledger.py summary --since <上一版交付时间>` 的表贴进来，再给全片累计；失败但计费、失败且费用未知的调用单列。
- 写发布交接单 `output/reports/vX.Y/publish-handoff.md` 与 `publish-copy/`：成片与封面对应哪个槽位；各平台文案与实测长度
  （B 站简介 ≤ 2000、标签 ≤ 10，视频号短标题 6–16 字，YouTube 简介 ≤ 5000）；章节时间轴
  （`node tools/chapters.mjs --out ../../output/reports/vX.Y/publish-copy/chapters.txt`）与署名块（完整版、压缩版：
  `node tools/credits.mjs --out-dir ../../output/reports/vX.Y/publish-copy`，从 `src/credits.ts` 生成并打印长度）是独立文件，
  可原样追加到任何平台的正文末尾；AI 生成内容清单与「发布时需要你决定」。见 [references/publish-handoff.md](references/publish-handoff.md)。
- 发布交给 `lov-media-publisher`（视频号、B 站、小红书；YouTube 不在它的范围内，交接单照样给出 YouTube 的文案）。第一个平台上用户
  手改并发布的文本是金标准，后续平台只做最小适配并追加独立块。片内不写制作方式。
- 交接回复里直接贴出 AI 生成内容清单，不只给交接单路径：发布 Skill 登记为 `auto` 的平台（Profile
  `skills.lov-media-publisher.records.auto_publish`）提交前不再问，按偏好不标注直接提交，B 站「创作声明」投稿后不能改；
  要在这些平台标注，用户需在这次发布请求里说明（[references/fact-and-disclosure.md](references/fact-and-disclosure.md)「AI 生成内容清单」）。

已知坑与解法见 [references/pitfalls.md](references/pitfalls.md)。

## Hard gates

- 画面上没有任何制作技术信息（技法、工具、模型、代码、渲染、帧数、线框）；元数据只有片名与出品方，
  文件里任何位置（容器、SEI、样本描述、AAC 码流）都不含工具名，交付脚本用长签名回读确认。
- 进度轴读数与画面事件同步；编年轴不出现「前 0」。
- 每个示意画面都有「示意」标注；数字与引文都有来源。
- 缺席名单上每个有名成员都写进片尾选样说明（名字加一句理由）；以无名形象出场的另在出场处就近标名。
- 品牌露出只用官方 Logo 源文件；印章文字来自 Profile。
- 片尾只有片名卡：没有章节回顾，也没有回顾之后、片名卡之前的过渡动画（用户长期偏好，Profile `records.outro`）。
- 上屏文字与旁白都没有口号、金句与替观众总结意义的句子；每句是画面上看得到的事实、操作、数字或有出处的原话。
- 旁白每句只说事实台账里的事实，片名卡与片尾卡上没有旁白；字幕文字就是说出来的话（`tts` 只改读法）；
  有旁白处音乐压低约 9 dB，母带仍是 −16 LUFS、真峰值 ≤ −1 dBTP（Profile `records.narration`）。
- 上屏文字不低于「字号下限」（字幕、引线标注、数据块与清单、HUD、大数字）；只有角落的示意与出处标注保持 14 px 小字。
- 默认只交付 16:9；9:16 只在用户点名时出（Profile `records.default_aspect`）。交付的每个画幅都通过联系表与转场窗口检查；
  成片从编码文件回读质检。
- `qc/beat_phase.py` 通过：分章配乐各章相位，以及整片配乐进出的每处衔接（默认就判，不靠 `--all`）。
- 封面三张（16:9、4:3、3:4）按比例命名、PNG 与 JPG 都有；底图上没有模型画出的字、标志与徽章，片名由合成排字；没有章节名与步骤轴；
  三个缩略尺寸下片名一眼可读。
- `tools/chapters.mjs` 通过：第一条 `00:00`、至少 3 章、每章按显示的时间码 ≥ 10 秒。
- 片尾署名卡自足：每份需要署名的素材都有作者、标题、许可与许可短链接，不指向简介；署名卡与简介署名块出自同一张 `src/credits.ts`，
  `tools/credits.mjs` 通过。
- 交付报告有 AI 生成内容清单（逐类，无则写「无」）、版本历史与来自账本的费用汇总；AI 标注由用户决定，清单在交接回复里直接给用户看
  （`auto` 发布的平台提交前不再问），Skill 不代选、不下合规结论。交接单里的长度都是实测值。

## Dependencies

- Remotion 4、React 19、TypeScript、pnpm；Node 24+（`tools/*.mjs` 直接 import `src/timeline.ts`）。
- Python 3.9+：`fontTools`、`Pillow`、`numpy`（配乐分析）、`opentype-sanitizer`（字体校验；未安装时用 `uv` 临时拉起）、
  `mlx-whisper`（人声扫描，仅 Apple Silicon；未安装时用 `uv` 临时拉起）、`librosa`（分章配乐的节拍分析与相位质检，用 `uv` 临时拉起）。
- ffmpeg / ffprobe（带 rubberband 滤镜时配乐变速用它，没有时用 atempo）。
- 旁白：豆包 Seed-TTS 2.0（`VOICENGINE_API_KEY` 只从环境变量读取，不写入文件），或用户逐句的真人录音。
- 可选：`lov-media-creator`（质检脚本 `media_probe.py`、`audio_qc.py`）、`lov-channels-cover`、
  `lov-media-publisher`（视频号、B 站、小红书，含 `check_copy.py` 文案预检）、AI 音乐模型 API（默认 OpenRouter 上的 Lyria 3 Clip，
  `OPENROUTER_API_KEY` 只从环境变量读取）。
- 封面底图：OpenRouter 的 `openai/gpt-5.4-image-2`（同一个 `OPENROUTER_API_KEY`；出图要求余额 ≥ 1.00 美元，2026-10-12）。
  没有密钥或预算时，`src/Cover.tsx` 退回纸纹上的章节色谱，照样出三张。
