---
name: lov-interview-media-creator
description: >
  采访短片：把一场手机采访录像（可加微信聊天、本人自述、公众号与现场照片）剪成 4 分钟内的视频号竖版短片，原话钩子、5章重排、提问卡、人名条、配乐与封面A/B。
  Use when turning one interview into a vertical short.
license: MIT
compatibility: >
  Portable Agent Skills format. Python 3.9+ with numpy, opencv-python, mlx-whisper (Apple Silicon), opencc and jieba in a persistent venv;
  the first transcription downloads two Whisper models from Hugging Face (about 3.1 GB + 1.6 GB);
  FFmpeg/FFprobe with zscale; macOS avconvert for Dolby Vision (iPhone HDR) sources; Node 20+ and Remotion 4 for the starter project;
  the OpenCV YuNet face model for beauty, punch-in centres and landscape-to-vertical reframing; macOS swiftc for the BGM vocal check. Mixing and audio QC call the lov-media-creator scripts (written against 0.31.0).
  Optional OPENROUTER_API_KEY for Lyria BGM (about $0.08 per track, observed 2026-10).
depends_on:
  - lov-branding-consistency
  - lov-media-creator
dependencies:
  - name: "lov-media-creator（混音、母带、SMR/CER 与音频质检脚本；缺失时停在混音前）"
    check: 'test -f "${MEDIA_CREATOR_DIR:-$HOME/.agents/skills/lov-media-creator}/scripts/score_mix.py"'
    install: "npx -y lovstudio@latest skills add media-creator -y"
  - name: "lov-media-publisher（可选：发视频号 / B 站；只剪辑不需要）"
    check: 'test -f "$HOME/.agents/skills/lov-media-publisher/SKILL.md"'
    install: "npx -y lovstudio@latest skills add media-publisher -y"
  - name: "lov-logo-sting（可选：片尾品牌 Logo 收尾动画与音效；不装或不要时照常收尾）"
    check: 'test -f "$HOME/.agents/skills/lov-logo-sting/SKILL.md"'
    install: "npx -y lovstudio@latest skills add logo-sting -y"
metadata:
  author: lovstudio
  version: "0.6.0"
  card_standard: lovstudio/skill-card/v1
  content_class: microcopy
  suite: lov-film
  tags:
    - video
    - interview
    - wechat-channels
    - remotion
    - film-style
---

# 采访短片 · Interview Short

把一场采访（通常是手机竖拍、领夹麦收音的单人采访）做成一条 2–4 分钟的视频号竖版短片：前 3 秒用被访者自己最反差的原话做冷开场，
接片名卡，再把采访重排成约 5 章；采访者的问题用提问卡、被访者的回答用大字字幕；人名条、地点条、讲解图形、跳切推近、自然美颜、
按内容生成的配乐、合影与官方 Logo 收尾；封面出 A/B 两版。交付审片版、字幕、封面、发布文案与交付报告，批准后交给发布环节。

本 Skill 是 `lov-film` 片型套件成员：片型 Skill 负责「这一类片子怎么剪才对」，共享的混音、母带、双画幅、媒体质检与交付契约由
`lov-media-creator` 承担，发布由 `lov-media-publisher` 承担。范围只有一种：一场采访 → 一条约 4 分钟以内的视频号竖版短片。
横版深度访谈、访谈长片与访谈纪录片留在 `lov-media-creator` narrative-vlog「访谈长片：先写导演阐述，再动刀」。

## Triggers

### Activate when

- 「刚采访了一位创业者，看本文件夹的视频和微信聊天记录『某某』，做一个适合发视频号的采访视频，要尽可能爆」。
- 「把这段嘉宾访谈剪成竖版短片：开头放金句，分几章，问题用字卡，回答上大字幕，加人名条和配乐」。
- 「这位新朋友的采访也剪一条，可以用她的公众号和朋友圈自述补背景」。
- 「这条采访短片从专业导演角度重新策划一版，先给我导演阐述」。
- Turn this founder interview into a vertical WeChat Channels short with a cold open from his own words.
- Edit a guest interview recording into a viral short with chapter cards, question cards and a name tag.

### Do not activate when

- 横版深度访谈、十几分钟的访谈长片、访谈纪录片（含「从专业导演角度策划」这类长片）：交给 `lov-media-creator` narrative-vlog「访谈长片」。
- 多人整场实录或圆桌要切多条：要剪映草稿、选题卡或无人值守批量出片 → `lov-roundtable-clip`；要逐条精包装、可直接发布的独立切片
  → `lov-media-creator` independent-clips。
- 录屏、Screen Studio、Vlog、旅行：交给 `lov-media-creator`。
- 设计招聘面试题或面试流程：交给 `interview-designer`。
- 只要上传或发布已经批准的成片：交给 `lov-media-publisher`。
- 无实拍的动态设计片：交给 `lov-motion-media-creator`。

## User Profile (cross-session)

每次运行读取 `skill.yaml` 声明的 `user-profile/v1`：用户语言与时区、品牌名与官方 Logo、工作区，以及 `skills.lov-interview-media-creator.records`
（系列名、章节卡时长、语速、是否美颜、字体、默认平台）。解析顺序：当前请求 → 项目上下文 → 本 Skill 记录 → 共享偏好 → 用户/品牌 Profile → 默认值。
lov-media-creator 记录里的通用剪辑偏好（章节黑卡、竖版安全区、BGM 按内容生成、不做开场静帧）同样适用。

作者直接说出的长期偏好（例：「以后采访片都不要美颜」「系列名叫某某」）立即写回，并报告保存路径：

```bash
python3 "$SKILL_DIR/scripts/profile_store.py" record --skill-id lov-interview-media-creator --path records.beauty --value false --confirm
```

推断出来的值只留在本次。完整契约见 [references/user-profile.md](references/user-profile.md)。

## Skill Group Composition

运行前读 [references/skill-composition.md](references/skill-composition.md)：哪些步骤调用 lov-media-creator 的脚本（原地调用，不拷贝），
哪些上下文来自 `lov-wdb-cli`、公众号或被访者自述，发布交给谁。相邻 Skill 只通过文件交接。

## Hard gates

0. **出镜授权。** 被访者在聊天或现场说过「保密」「别发」「别露脸」这类话时，先停下交作者确认；确认前不做可发布版本、不发布。
1. **只用原话。** 冷开场、字幕、提问卡、讲解图形里的数字只来自录音（专名校正后）；不新增口播里没有的结论。宣传口径保留为引述。
2. **切点经过试切。** 每个句首句尾用 `probe_cuts.py` 回转写确认；`seam_check.py` 没有残词、没有吃字（同音误识除外）。
3. **该删的整段删。** 被访者拒答的问题、「不方便」公开的网址或细节、制作来回与失败演示；画面里没有可读网址、二维码、聊天或证件信息。
4. **事实有出处。** 人名条、地点条、身份、数字都在 `work/facts.md` 里有出处（原声、聊天、本人公开文字或可核实的公开资料）；两个转写模型分歧的专名交作者确认。
5. **主体是被访者。** 采访者只以提问卡和反应出现；不用「对话之后」「先看结果」这类元字卡；画面不展示制作技术与工具署名。
6. **声音过门禁。** 配乐候选做过人声分离检查；`validate_cues` 0 ERROR、`smr_check` 全过、母带 −16 LUFS-I / ≤ −3 dBTP、可懂度差值达标、
   音乐 stem 无 2 秒以上断档（阈值以 lov-media-creator audio-mix 为准）。lov-media-creator 不可用时停在混音前。
7. **编码成片过质检。** 中间轨帧数等于时间线帧数且是 bt709；成片完整解码、视频号 ≤ 10 Mbps、bt709 标记回读正确、5 fps 分页联系表全片看过、
   逐帧二维码扫描的命中逐条人工判、单帧坏帧扫描的命中逐张看三联图（渲染坏帧重渲那一段再扫，已知模式也要在图上核实）。
8. **封面可读。** 3:4 在 270×360 下一眼读完主标题；官方 Logo；标题不压被访者的脸；同一视觉的 4:3 分享卡同样可读。
9. **批准与确认分开记。** `subtitle_status=approved` 只来自作者对 SRT SHA-256 的确认；原创条款、合集、位置在发布前一次问齐。
10. **付费先报价。** AI 配乐、云端转写先说明单价与本次预估，每次调用记进 `ledger/costs.jsonl`。

## Workflow (MANDATORY)

阶段、产物、命令与门禁表见 [references/pipeline.md](references/pipeline.md)；「对」的标准见 [references/style-grammar.md](references/style-grammar.md)。

### Step 0: 解析运行环境

- 使用 `SKILL_DIR`（本 Skill 目录）；`MC` = lov-media-creator 目录（`$MEDIA_CREATOR_DIR`，缺省 `~/.agents/skills/lov-media-creator`）。
  确认 `$MC/scripts/score_mix.py`、`smr_check.py`、`validate_cues.py`、`intelligibility.py`、`audio_qc.py`、`media_probe.py`、`bgm_tracks.py` 存在。
- 确认持久虚拟环境里有 mlx-whisper、numpy、opencv、opencc、jieba，所有脚本都用这个环境的 Python（`$PY`）运行。
- Whisper 模型：转写类脚本（`transcribe`、`probe_cuts`、`seam_check`、`subs_from_lines`）的 `--model` / `--models` 接受别名 `large-v3`
  （`mlx-community/whisper-large-v3-mlx`，约 3.1 GB）、`turbo`（`mlx-community/whisper-large-v3-turbo`，约 1.6 GB）、Hugging Face 仓库名或本地模型目录。
  先看 `~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-*` 是否齐全；缺了先报体积与网络再下载，两个都缓存后设 `HF_HUB_OFFLINE=1`。
- 缓存被清理后要重下约 4.7 GB；经代理时 Python 下载器可能一直卡住。改用 `curl -L -C - --retry 5` 断点续传
  `https://huggingface.co/<repo>/resolve/main/<file>`，`shasum -a 256` 对上 `https://huggingface.co/api/models/<repo>/tree/main` 里的 `lfs.oid`，
  再按缓存结构放好：大文件放 `blobs/<sha256>`，`snapshots/<commit>/<file>` 链接过去，`refs/main` 写 commit（`/api/models/<repo>` 的 `sha`）。
  本机已有同一模型的 MLX 权重目录时，把其中文件链接进 `snapshots/<commit>/`，或把目录直接传给 `--models`。
- YuNet 人脸模型：`--yunet` 或 `$YUNET_MODEL`，缺省 `~/models/yunet.onnx`；没有就从 OpenCV model zoo 下载
  `https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx`（约 230 KB）。
- 看磁盘：渲染前至少预留成片体积的 3 倍，另留中间轨与片段缓存（3 分钟成片约 1.5 GB）。
- 素材原件只读；过程文件在 `work/`，交付在 `deliverables/`。

### Step 1: 盘点素材与上下文

- 素材清单连子文件夹一起列（`find . -maxdepth 2`，排除 `work/`、`deliverables/`），不要只列根目录的文件。作者说「加了照片」时先找
  第一次盘点之后新增的目录（`find . -maxdepth 2 -newer work/source-probe.json`），见 [references/pitfalls.md](references/pitfalls.md)「盘点」。
- `media_probe.py` 读每段录像：时长、旋转元数据、HDR 曲线、音频声道；照片转预览逐张看；15 秒一帧的联系表。
- `sdr_source.py SOURCE.MOV` 查杜比视界（`DOVI configuration record`，iPhone HDR 录像是 profile 8.4、HLG 基础层）。有就默认用 macOS
  `avconvert` 转出整条 SDR bt709 源（`work/src/<名>-sdr709.mov`，长素材后台跑），核对帧数、起点、时长与 bt709 后，EDL `source.video`
  指向它；音频仍从原片提取 WAV。ffmpeg 色调映射不读杜比视界元数据，会过亮偏品红；没有 avconvert 时先告诉作者再渲染。
- 上下文按 [references/context-sources.md](references/context-sources.md) 取：微信聊天（`lov-wdb-cli`）、被访者自述、公众号文章、现场照片。
  事实写进 `work/facts.md`，带出处与用途。

### Step 2: 转写

- 两个 Whisper 模型各转一遍（`transcribe.py`，提示词只放风格句与专名）；分歧专名查证或列给作者。量一下句间底噪，决定是否做人声分离。

### Step 3: 导演阐述与剪辑表

- 读完整份逐字稿，按 style-grammar 选钩子、排 5 章，写 `work/director-statement.md` 与 `work/edl-vX.json`（模板在 `assets/templates/`）。
  EDL 顶层 `nouns` 列出人名、专名，以及后面 `package.json` 用到的每个锚点和高亮词，字幕断行不会把它们拆开；片名卡时长 = title 段 piece 的长度。
- 作者要求「从专业导演角度策划」或判一版「不像一部片子」时，阐述先给作者批，批准后再剪；其他情况随第一版一起交。

### Step 4: 切点核验

- `probe_cuts.py intervals/in/out` 逐个确认句首句尾，在 EDL 里标固定；`build_timeline.py --audio` 后跑 `seam_check.py`。

### Step 5: 画面

- 切点定稿后先跑 `setup_starter.py`，把 `assets/starter` 装进 `work/remotion`（字体、官方 Logo、系列名；`public/{media,audio,img,data}` 就此建好，
  没给封面规格时写中性占位封面与深色占位底图）。
- 横拍素材裁竖版：`crop_centers.py --write` 按画面里最大的人脸给每段定固定取景（两人同框加 `--guest-side`）；`reframe.py --write` 给固定框会切脸的段
  写 `crop_track`，裁切框跟脸平移（边距默认画宽 0.07，单段参数写进该段 `reframe`）。被访者靠在画面最边上的提问段写 `"crop_on": "none"`，用横幅全景
  加虚化底。渲完在联系表里找贴边的脸，见 [references/pitfalls.md](references/pitfalls.md)「画面与包装」。
- 会议录像（飞书 / 腾讯会议说话人视图）：先做「只有被访者」的中间源（采访者在主画面的帧换成被访者小窗的放大虚焦版）；被访者坐得偏低时
  用顶部 3:4 画框加虚化底。做法见 [references/pipeline.md](references/pipeline.md)「5 画面」。
- `build_timeline.py --video --audio` 渲染逐片段 SDR（无杜比视界的 HLG/PQ 自动色调映射，源是杜比视界时打印 WARN；保音高变速）；`fx_pieces.py --copy-to work/remotion/public/media`
  美颜、人脸、拼 bt709 中间轨，并克隆进 Remotion（中间轨帧数与时间线不符时退出 1）。
- 美颜前后近景对比交作者看；作者说不要就 `--no-beauty`（参数变了会自动重算缓存），并记进 Profile。被访者要求更明显的美颜（「要修！」）时
  加 `--level strong`（更强的保边磨皮、强度 1.0、整帧提亮），封面与照片同一档；两档都不改脸型，改脸型要被访者明确同意。

### Step 6: 字幕与包装

- `subs_from_lines.py` 从剪好的对白取字幕时间：large-v3 与 turbo 各转一遍，按对白 WAV 的语音起点逐句择优（显示过快的一方不选），
  缺字的边缘行用另一模型补；每句首行从句首开始，行首吸附到片段起点，「OK」「对」「对吧」这类闪行并入邻行；两个模型都对不上的句子保留
  临时时间并列给作者，选择记录写在 `qc/subs-timing-vX.json`。要中英双语时，译文按段写进 `work/subs-en.json`，`subs_en.py` 按行对回字幕
  并把 SRT 改成每条两行。`decorate.py` 从未装饰的
  `timeline.base.json` 起，按 `work/package.json` 加片名、人名条、地点条、讲解图形、照片、重点词与推近中心。
- 被访者本人的生活照放在自我介绍那几句上，做成竖版相册（`inserts[].album`：一张张落下叠成白边卡片堆，字幕在上层）；人名条、地点条在相册开始前收掉。
  规则见 style-grammar 第 6 节，写法见 pipeline「6 字幕与包装」。
- `check_timeline.py --public … --mezz …` 通过后再进 Studio：引用的文件（含相册每一张）都在、中间轨帧数与 bt709 对得上、人名条不和讲解图形撞时间、
  人名条与地点条不和相册撞时间。
- 片尾 Logo 卡可选交 `lov-logo-sting` 换成收尾动画与音效：做可发布版本、定片尾时提一次，审片初版只在作者要求时做；宿主没装或作者不要，照常用起步工程的静态 `LogoCard`。
  交给它的是品牌上下文里的官方 Logo SVG、本片 fps，收尾曲有拍点网格时一并给（三笔落在拍上）；取回 `<LogoSting>` Sequence 接在合影之后、替换 `LogoCard`。
  `sting.wav` 在起点帧并进母带前的最终混音、`<LogoSting>` 不传 `audioSrc`：`finalize_platform.py` 只封装最终混音（`-shortest`），只挂在 Remotion 里的音效会丢，混音短于画面会截掉片尾。
  加入后整条母带连同编码成片重测，混音与真峰门禁仍归本 Skill（≤ −3 dBTP）；观测实例：参考成片加入后 AAC 编码一度超过 0 dBFS，母带目标降到 −2.5 dBTP、限制器 0.70 才过。

### Step 7: 配乐与混音

- 写一句音乐简报，`gen_bgm.py` 生成 2–3 个候选（先报单价）；`bgm_check.py candidates` 判人声与可闻尾音；`$MC/scripts/bgm_tracks.py` 登记。
- `music_plan.py --media-creator "$MC"` 生成 cue、film 与处理后的 voice 清单，并打印带绝对路径、以 `cd <EDL 目录> &&` 开头的门禁命令；
  照它跑核心门禁，`bgm_check.py stem` 扫音乐断档。
- 最终混音转成 `work/remotion/public/audio/mix-vX.m4a`（`ffmpeg -c:a aac -b:a 256k`），与 `package.json` 的 `media.audio` 一致。

### Step 8: Studio 主预览与金丝雀

- 中间轨与混音是 `public/` 里的实体文件（APFS 克隆），不用软链接。
- 开 Studio 前给 `src` 存快照；关键帧金丝雀（冷开场、片名、每种卡、讲解图形、照片、Logo）看过再整片渲染。

### Step 9: 渲染、封装与质检

- 在子 shell 里 `(cd work/remotion && zsh render-chunks.sh …)` 分段渲染；`finalize_platform.py` 封装最终混音、补 bt709 标记、5 fps 分页联系表与
  3 秒总览、逐帧二维码扫描、按片长算码率的手机预览（< 30 MB）；再跑 `$MC/scripts/audio_qc.py`。
- 同一遍逐帧解码里跑单帧坏帧扫描（`glitch_scan.py`）：渲染偶发的花屏、错位只有一帧，5 fps 联系表抽不到。`--timeline` 给这一版的
  `timeline.json`，片尾闪白、照片快门闪白打标签，运动模糊按画面打标签，但都不自动放行；每处命中看 `qc/glitch-<stem>/` 的三联图，
  读法与重渲那一段的做法见 [references/pipeline.md](references/pipeline.md)「9–10」。不走 finalize 的文件（横版、重渲后的渲染件）单独跑它。

### Step 10: 封面

- 选一帧被访者看镜头、头顶留白够的画面，`fx_pieces.py --photo` 美颜（档位与成片一致）后做 3:4 A/B（`InterviewCover34-a/b`）；270×360 缩略检查。
- 作者选定后，用同一份 `cover.json` 出同一视觉的 4:3 分享卡（`InterviewCover43-<v>`）；要 B 站等 16:9 时再出 `InterviewCover169-<v>`。
- 视频号封面槽数以发布页现场读到的为准（观测：一个 3:4 槽，有时是 3:4 + 4:3 两个槽），所以选定的 3:4 与 4:3 一起交，`cover_status` 覆盖两张。

### Step 11: 交付与发布交接

- 交付报告的状态字段与最低内容按 lov-media-creator `references/delivery-contract.md`；本片型另写冷开场原话与源时间、每章命名依据、讲解图形清单、
  事实核对（出处）、待确认事实、AI 生成内容清单与费用汇总。
- 字幕在作者确认 SHA-256 前保持 `awaiting-review`。发布交接与「一次确认收齐」见 [references/publish-handoff.md](references/publish-handoff.md)。
- B 站 16:9 横版按 [references/pipeline.md](references/pipeline.md)「13 横版派生」从同一条时间线派生（起步工程只有竖版成片）。要不要先问作者，
  看 lov-media-publisher Profile 的 `records.auto_publish.bilibili`：`auto` 时视频号发完直接派生、质检，交给发布方，不再问；没有这条记录、
  值是 `confirm-final`，或作者当次说了「做好先给我看」，先问或先交审片。

踩过的坑见 [references/pitfalls.md](references/pitfalls.md)。

## Dependencies

- Python 3.9+：numpy、opencv-python、mlx-whisper、opencc（繁转简）、jieba（字幕断行）；放在一个持久虚拟环境里。
  首次转写下载 `mlx-community/whisper-large-v3-mlx`（约 3.1 GB）与 `mlx-community/whisper-large-v3-turbo`（约 1.6 GB）；缓存后可设 `HF_HUB_OFFLINE=1`；缓存被清理后的重建办法见 Step 0。
- FFmpeg / FFprobe（带 zscale，用于无杜比视界的 HDR 色调映射）；macOS `avconvert`（杜比视界素材转 SDR 源）；Node 20+ 与 Remotion 4（`assets/starter`）。
- OpenCV YuNet 人脸模型 `face_detection_yunet_2023mar.onnx`（OpenCV model zoo，地址见 Step 0）；macOS `swiftc`（编译 `assets/tools/isolate.swift`，配乐人声检查）。
- lov-media-creator 的混音与质检脚本（必需，见 frontmatter `dependencies`；装在别处时设 `MEDIA_CREATOR_DIR`）；lov-media-publisher（可选，发布时）；lov-logo-sting（可选，片尾 Logo 收尾动画与音效）。
- 可选：`OPENROUTER_API_KEY`（Lyria 配乐），只从环境变量读。

## Validation

```bash
python3 scripts/validate_skill.py .
for s in sdr_source build_timeline crop_centers reframe transcribe probe_cuts seam_check subs_from_lines subs_en fx_pieces decorate music_plan gen_bgm bgm_check finalize_platform glitch_scan check_timeline setup_starter; do
  python3 scripts/$s.py --help >/dev/null || echo "FAIL $s"
done
```

同时检查 `skill-card.yaml`、`skill-card.md`、`cases/cases.json` 与 `pricing-card.yaml`。
