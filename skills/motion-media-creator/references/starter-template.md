# 起步模板 `assets/starter/`

来自第一条动态图志（编年轴）《字里中国》的工程，保留了可复用的骨架；`timeline.ts` 和 `glyphs.ts` 里是那条片子的
示例数据，新片要替换。`public/` 不随模板分发，由 `tools/bootstrap.sh` 生成。

| 路径 | 作用 | 新片要改什么 |
| --- | --- | --- |
| `src/timeline.ts` | 片名 `TITLE` / `SUBTITLE`（片头、片尾卡、封面共用）；字幕语言 `SUBTITLE_LANGS`（默认 `'zh'`，用户要中英双语时改 `'zh+en'`）；章节表：起点帧、章名、短名、轴范围、`axisKeys`、配色、字体、转场、内容关键词 `motif`、`CUES`；`AXIS` 决定进度轴读数格式；`CARD_OUT` 是标题卡离场、HUD 小章名进场的章内帧（默认 50） | 全部换成新题材；按轴改 `AXIS.format`；`motif` 只写内容；示例时长早于「每章 ≥ 11 秒」，`chapters.mjs` 在示例上退出 1，新片每章（含片头、片尾）按 ≥ 330 帧重排 |
| `src/components/HUD.tsx` | 章节头（章内第 `CARD_OUT` 帧起淡入）、底部分段进度轴、当前读数（`axisAt` 按 `axisKeys` 插值，`AXIS.format` 显示）；`hudInkAt` 给出当前墨色与底色，字幕与标题卡共用 | 一般不改 |
| `src/components/ChapterCard.tsx` | 章节标题卡：转场过半时在 HUD 章名头的位置出大号「序号 / 总章数」、章名（120 px，过长按宽度缩小）与轴上位置，`CARD_OUT` 时淡出、HUD 小章名接上；底下垫一层本章底色的径向渐变 | 一般不改；场景前约 2 秒别往左上放字 |
| `src/components/Subtitles.tsx` | 旁白字幕：中文，或中文在上、英文在下（46 / 27 px，取自 `TYPE_FLOOR`）；居中在进度轴上方（16:9 底边 H−128，9:16 在舞台带底部）；亮画面用 HUD 墨色，暗画面浅色加投影。导出 `NARRATED`：有旁白时场景左下的正文说明写成 `if (!NARRATED)` 让位 | 一般不改 |
| `src/narration.ts` | 字幕表（绝对帧），由 `tools/narration.py` 生成；空表即无旁白片 | 不手改 |
| `src/components/Reveal.tsx` | 转场：ink / bloom / slats / flash / wipe / wipeRight / shards / iris / wave / dipBlack / white | 按需增删 |
| `src/components/Paper.tsx` | 纸纹、颗粒、暗角背景 | 换题材时换质感 |
| `src/components/Type.tsx` | `StaggerText`、`Line` 等排版动画；`Callout`（引线标注：标签 22 px、引线 1.5 px）、`BigNumber`（大数字 120–160 px，等宽数字，计数只变数字）、`thousands` | 一般不改 |
| `src/lib/fonts.ts` | 字体注册（先 add 再 load）、`fontsReady`、`useFontsReady()`、加载失败 `cancelRender`；字幕字体 `SUBTITLE_FONT` | 换字体族名 |
| `src/lib/layout.ts` | 横竖共享布局常量（安全区、舞台带）；`LayoutOverride` 让父组件按另一种画幅渲染子场景（例如在竖版里放 16:9 缩略图）；字号下限 `TYPE_FLOOR`（1920×1080 的 px）与 `useLayout().ts`（短边 ÷ 1080，9:16 再 ×1.15）、引线宽 `LEADER_W` | 按平台安全区调；场景尺寸一律从 `useLayout()` 取，不直接读 `useVideoConfig()`；场景字号写成 `TYPE_FLOOR.x * ts` 或更大 |
| `src/lib/anim.ts` | 缓动、`prog`、`lerp`、`rng(seed)` 确定性随机 | 不改 |
| `src/lib/brush.ts` | 毛笔笔触路径（片头落笔） | 不改 |
| `src/lib/bitmap.ts` / `glyphs.ts` | 字体栅格化与手绘古文字路径示例 | 按题材替换字形 |
| `src/Main.tsx` / `Root.tsx` | `Main.tsx` 的 `Film` 按传入的章节表拼接整片（章节 Sequence + 转场重叠 + 字幕 + HUD + 根层单次挂载母带），不引用 `src/scenes`；`Root.tsx` 用 `SCENES` 注册整片、单章与封面 Composition（Covers 文件夹依次 `Cover-16x9`、`Cover-4x3`、`Cover-3x4`） | 换章节组件 |
| `src/Cover.tsx` | 三比例封面，通用、不含示例片内容：片名取 `TITLE`，Logo 取 `public/brand/logo.png`，印章取 `src/brand`；每张先找自己比例的 AI 底图 `public/assets/cover/ai-<比例>.png\|.jpg`，4:3、3:4 找不到时用 16:9 的那张（4:3 全宽放底部、片名在上方空带；3:4 取下方 62%），都没有时退回纸纹上的章节色谱；不放章节名与步骤轴。渲染日志里缺图的 404 是它在探测，不是错误 | 设顶部的 `COVER`：`titleEn`（英文名，空则不显示）、`lines`（手动断行，空则自动）、`font`（片名字体族，字体前缀改名时一起改）、`bandGlyph`（只在退回色谱时用）、`tone`（`dark` 近黑底浅色片名，`paper` 纸色底墨色片名，与 `cover/brief.json` 的 `tone` 一致；纸色改 `TONES.paper`） |
| `cover/brief.json` | 封面底图简报：`subject`、`style` 是 `<…>` 占位（不替换脚本拒绝真跑），`tone` 选片名空位的底色（`dark` 或 `paper`，与 `Cover.tsx` 的 `COVER.tone` 一致）；`layouts.dark` 三个比例的留白版式与 `forbid` 是《如何打造一款特斯拉》验证过的写法，`layouts.paper` 是纸色版（未发布验证），`_example` 是该片 v0.5 的提示词 | 写 `subject` 与 `style`，按片子选 `tone`；`layouts`、`forbid` 一般不动（纸色改 `layouts.paper` 里的十六进制） |
| `tools/gen_cover_bg.py` | 封面底图（OpenRouter `openai/gpt-5.4-image-2`，只用标准库）：`--dry-run` 打印提示词、请求体与估价，不联网、不读密钥；`--ratio`（可重复，默认 16:9 与 3:4）、`--size 1K\|2K`（默认 2K）、`--force`、`--attempts`（默认 2）、`--no-balance-check`；真跑前查余额（低于 1.00 美元加估价不开始），`brief.json` 的 `tone` 与 `Cover.tsx` 的 `COVER.tone` 不一致时拒绝，402 与其他请求错误直接停，429 等待重试，断线重试并警告可能已计费；写 `public/assets/cover/ai-<比例>.png` 与同名 `.json`，每张另存 `cover/takes/`（带时间戳，不覆盖）；每次付费尝试在账本记一行 | 不改；`OPENROUTER_API_KEY` 只从环境变量读 |
| `src/credits.ts` | 素材署名表（通用，不含示例片内容）：`CREDITS`（`{author, title, license, url, changed}`，按片中出现顺序，每份一次；空数组即没有第三方素材）、`CREDITS_CHANGED`、`licenseUrl()`（许可名 → 短链接）、`needsCredit()`（CC0、公有领域、Pexels 不要求署名）、`otherLine()`；片尾署名卡与 `tools/credits.mjs` 都读它。不 import 别的文件，Node 直接读 | 取材时逐条填；不移出 `src` |
| `src/scenes/S14Outro.tsx` | 示例片的片尾片名卡；带通用的署名块：读 `src/credits.ts`，需要署名的逐条「作者 · 标题 · 许可」，再接改动说明、许可短链接行与免署名素材一行，字号随条目数在留白内缩小 | 新片照着改说明文字，保留读 `credits.ts` 的署名块；不写「见简介」 |
| `src/dev/harness.tsx` | 单章预览的根：整片时间线上只挂一章，带字幕与 HUD，横竖各一个 Composition（`H-16x9` / `H-9x16`）；入口 `src/dev/entry-<id>.tsx` 由 `tools/preview.sh` 生成 | 不改 |
| `tools/bootstrap.sh` | 新目录一键补齐 `public/`：纹理、字体抽取与子集、品牌 logo、占位配乐；可重复运行 | 不改 |
| `tools/textures.py` | 程序化纸纹、颗粒（固定种子，可复现）与中性占位 logo | 换质感时改参数 |
| `tools/fonts.py` | 从系统字体抽取并子集化，扫描 src 用字，缺字即失败；抽取时缺 OS/2 表即失败，子集后逐个过 OpenType Sanitizer（`validate` 可单独跑） | 换字体源与家族映射；Courier 用 `Supplemental/Courier New.ttf`，不用 `Courier.ttc` |
| `tools/sheet.sh` | 渲染帧区间并拼联系表 | 不改 |
| `tools/stills.sh` | 打包一次，再从 bundle 并行出抽查静帧（`STILLS_DIR`、`BUNDLE_DIR` 默认 `../build/stills`、`REBUNDLE=0` 可选）；`tools/stills.sh covers [缩放]` 出三张封面到 `../qc/stills/cover-<比例>.jpg`，并打印每张用的是哪张底图 | 不改 |
| `tools/bundle.sh` | 打包一次供多次渲染：对空 public 目录打包，再 `cp -Rc` 把 `public/` 克隆进 bundle（APFS 克隆不占空间，其他文件系统退回普通复制）；`preview.sh`、`stills.sh`、`deliver.sh` 都用它 | 不改 |
| `tools/preview.sh` | 单章预览：`<id> bundle｜stills <16x9｜9x16｜both> <章内帧…>｜sheet <画幅> <间隔> [起 止]｜clip <画幅> <起> <止>`，输出 `../qc/preview/<id>/`；从 `scenes/index.ts` 的 `  <id>: <组件>,` 行找组件（文件名同组件名），`MODULE` 可换模块试版 | 不改 |
| `tools/stills.mjs` | 一个浏览器连续出多张静帧（每张新开标签页）：`node tools/stills.mjs <bundle> <comp> <前缀> <缩放> <帧[:标签]>…`；`GL=angle` 给 WebGL 场景；`FORMATS=png,jpeg` 每张按所列格式各出一份（默认只出 JPG），`JPEG_QUALITY` 默认 88 | 不改 |
| `tools/narration.py` | 旁白：逐句用户录音优先、其余 TTS（缓存），去首尾静音、量时长，写 `audio/narration/timing.json` 与 `src/narration.ts`；越界、挤句、离章、落在片名卡或片尾卡上即失败；每次 TTS 请求在账本记一行（字符数，无价格）；`--dry-run` 不联网、不读密钥，报真跑要合成的句数与字符数（扣除缓存与录音） | 换音色用 `TTS_SPEAKER`、语速 `TTS_RATE` |
| `tools/ledger.py` | 费用账本（标准库）：`ledger/costs.jsonl` 一行一次付费调用 `{ts, kind, provider, model, qty, unit, cost_usd, ok, ref}`，`LEDGER_PATH` 可改；`add` 只补记脚本之外的调用（`--failed` 记失败；`gen_chapter_music.py`、`gen_bgm_openrouter.py`、`narration.py`、`gen_cover_bg.py` 自己记，不再补），`summary [--since ISO] [--json]` 出交付报告「费用」节的表，类型不对的行逐行报出并跳过（按类型、服务商、模型分组，附失败但计费、失败且费用未知的次数）；脚本用 `record()` 写，写不进只警告、不抛错，免得触发重试再付一次钱 | 不改 |
| `tools/chapters.mjs` | 章节时间轴：从 `timeline.ts` 打印 `MM:SS 章名`（过一小时用 `HH:MM:SS`，第一条 `00:00`），写 `--out`（默认 `../manifest/chapters.txt`）；时间码向下取整，少于 3 章、起点乱序或任一章显示时长不足 10 秒即退出 1 且不写文件，不足 11 秒警告；`--names era\|short\|<字段>` | 不改 |
| `tools/voice_mix.py` | 母带：`public/audio/bgm-music.wav` + 旁白（+ 可选 `audio/sfx/sfx-stem.wav`）→ `public/audio/bgm-master.wav`；旁白约 −17 LUFS，音乐压低约 9 dB、音效约 4 dB；−16 LUFS、真峰值 ≤ −1 dBTP；无旁白时只处理配乐 | 不改 |
| `tools/deliver.sh` | 默认只跑 `16x9`，用户点名时才跑 `9x16`；打包一次，按章节分块渲染母版（每块新起一次渲染，静音）→ 无损拼接 → 混入配乐母带 → 平台文件 → 质检 → 报告素材；元数据只留片名与出品方，文件里任何位置不含工具名。`deliver.sh covers vX.Y`：三张封面 `output/images/<品牌>-<片名>-封面<比例>-<日期>-vX.Y.png\|.jpg`，核对像素尺寸，写 `reports/vX.Y/covers.tsv`（文件、像素、底图、SHA-256）、`cover-thumb-<比例>.png` 与 `cover-thumbs.png`，黑边扫描只提示；交了成片而这一版缺封面时提醒 | 设 `FILM_TITLE`、`FILM_BRAND`、`FILM_SLUG`（母版文件名，默认 `film`）；可选 `CHUNKS`、`CHUNK_FRAMES`、`FILM_BGM`、`SKIP_RENDER=1` |
| `tools/credits.mjs` | 简介署名块：从 `src/credits.ts` 写 `credits-full.txt`（逐条带许可链接与来源链接）与 `credits-compact.txt`（许可链接合成一行、免署名素材指回片尾）到 `--out-dir`（默认 `../manifest`），打印两版长度（Python 字符数口径）并标出 `<` `>`；缺作者、许可或来源链接，许可推不出链接，或重复条目时退出 1 且不写文件；素材表为空时不写 | 不改 |
| `tools/chunks.mjs` | 读 `timeline.ts` 给出分块：只在章节起点切，每块 ≤ `CHUNK_FRAMES`（默认 1500），片尾单独一块 | 不改 |
| `tools/manifest.mjs` | 导出时间线清单给时间线检查 | 不改 |
| `audio/gen_chapter_music.py` + `audio/chapters/briefs.json` | 分章配乐（默认）：按简报每章生成两条 30 秒 Lyria 3 Clip 候选（OpenRouter，`google/lyria-3-clip-preview`，0.04 美元一条）→ `audio/chapters/<id>-a.mp3`、`<id>-b.mp3` 与同名 `.json`（提示词、费用）；`--dry-run` 只报数量与费用；简报里还有 `<…>` 占位就拒绝运行；空流、断连、5xx、408、429 重试，每次请求（含重试与失败）在账本记一行，费用取 `usage.cost`；其他 4xx 立即停下、不重试、不记账，401、402、403 之后未开始的条目跳过 | 写简报：`common` 补题材与配器风格，`chapters` 按本片章节 id 每章一句情绪 |
| `audio/chapters/analyze.py` | 候选的节拍分析（librosa，用 `uv run --python 3.12 --with librosa` 临时拉起）→ `audio/chapters/analysis.json`：选条用的首拍、`clarity`、`ibi_cv`；定位用的节拍网格（1 秒之后的稳定拍点最小二乘拟合的 `period` / `bpm`、残差 `resid_ms`、小节强拍 `downbeats`） | 不改 |
| `tools/music_bed.py` | 拼分章配乐 → `public/audio/bgm-music.wav`：每段按拟合速度变速到正好 120 BPM（有 rubberband 用它，否则 atempo；`MUSIC_STRETCH` 可指定），拟合网格上离 4 秒最近、前有 1 秒引子的小节强拍对准章节第一帧，换段提前 1 秒等功率叠入，按章节本体调响度；没有候选的章放 `public/audio/bgm-full.wav`，并按它在 `analysis.json` 的拟合网格平移到分章网格上（每处衔接的偏差对一拍取余、折到 ±半拍内取最小平移；缺网格时实跑报错；`--full-shift <毫秒>` 手动指定，`0` 不平移；`--dry-run` 打印平移量与衔接偏差）；选择与响度写 `audio/chapters/picks.json`，没写的自动选拍子最清楚的稳定候选，网格残差超过 15 毫秒的候选跳过；章节起点不在同一 15 帧网格上时警告 | 写 `picks.json` |
| `audio/*.py` | 单曲配乐（备选）：生成候选配乐（`gen_bgm_openrouter.py`）、起音/段落分析（`analyze.py` → `audio/structure.json`）、章节吸附（`snap.py`，默认读 `public/audio/bgm-music.wav`（没有时读 `bgm-master.wav`）、±0.5 秒窗口、速度与相位由 `analyze.py` 估计，均可用参数覆盖 → `audio/snaps.json`）；人声扫描（`vocal_scan.py`，`--out` 指定输出，`listen` 列出不像幻觉、要人耳听的片段）；`gen_bgm_openrouter.py` 每次请求在账本记一行（成功、5xx、408、429、断流都记；其他 4xx 在出音乐前被拒，不记） | 换简报 |
| `qc/transition_sheet.py` | 按章节起点拼转场窗口 | 不改 |
| `qc/beat_phase.py` | 分章配乐的节拍相位质检（librosa，经 uv）：每章按（t − 网格相位）对一拍取余叠起音强度，报各章相位；用自己配乐的各章距网格与彼此都在 ±25 毫秒内才通过，否则非零退出；整片配乐的章只报告（`--all` 才判）；整片配乐与分章配乐的每处衔接默认就判：两侧各测紧挨叠入区、最多 8 秒的相位，相差超过 `--tol`（默认 25 毫秒）即失败；`--json` 存结果（含 `joins`、`worst_join_ms`） | 不改 |

## 起步

脚本都假定 Remotion 工程在 `<project>/work/remotion`：`../manifest`、`../qc`、`../build`、`../renders` 指 `work/` 下的目录，
`../../output` 指 `<project>/output`（`deliver.sh`、`chapters.mjs --out`、交接单都按这个布局写路径）。

```bash
mkdir -p <project>/work && cp -R "$SKILL_DIR/assets/starter" <project>/work/remotion && cd <project>/work/remotion
pnpm install                                  # 带 pnpm-lock.yaml；pnpm-workspace.yaml 已允许 esbuild 构建
FILM_SEAL_DIR=<印章资产目录> FILM_LOGO=<品牌logo.png> tools/bootstrap.sh    # 生成 public/；不设 FILM_LOGO 则放占位 logo
npx tsc --noEmit -p .
npx remotion studio src/index.ts
```

新片开工先把示例片的画面移出 `src`：`src/scenes/S0[1-9]*.tsx`、`src/scenes/S1[0-4]*.tsx`（保留 `S00Opening.tsx` 和
`index.ts`）、`src/lib/glyphs*.ts` 都是《字里中国》的内容，引用旧时间线的章节、`CUES` 和 `ZL-*` 字体族；
`tools/fonts.py subset` 扫描整个 `src` 的用字，留着它们，旧片的字会一起打进子集。把它们移到 `../ref-starter/` 留作参考
（片尾可以照着改：说明文字换成本片的，读 `src/credits.ts` 的署名块原样保留；`credits.ts` 本身是通用的，留在 `src`）；`scenes/index.ts` 先挂占位场景，让 `tsc` 和片头静帧先跑通
（2026-10-11 实测）。`src/Cover.tsx` 已是通用的，不用移出：设顶部的 `COVER`（英文名、断行、片名字体），写 `cover/brief.json`
的 `subject` 与 `style`；没有 AI 底图时它退回章节色谱，照样能出三张。示例时间线早于「每章 ≥ 11 秒」的规则：清、片名两章显示 9 秒，
`node tools/chapters.mjs` 在示例上退出 1（2026-10-12），新片按新规矩排时长。示例章节早于章节标题卡与放大后的字幕：
它们左上角的字会压在标题卡下，底部的字会撞上字幕（2026-10-12 用示例片渲染静帧可见），照着改时按新规矩让出这两块。字体族前缀随片改名时（例：`ZL-` 改为 `GO-`），
`tools/fonts.py` 的 `FACES` 键名（决定 `public/fonts/` 里的文件名）和 `src` 要一起改，用 `rg "ZL-" src tools` 清掉全部残留，
包括 `fonts.ts` 里 `fam()` 的回退字体和 `Cover.tsx` 的 `COVER.font`。

要进 git 的：`audio/narration/voice/`（用户录音）、`ledger/costs.jsonl`（费用账本，`.gitignore` 已放行，上级忽略 `*.jsonl` 也照样跟踪）、
`cover/brief.json` 与 `cover/takes/`（每张封面底图连同提示词与用量；`public/` 不进 git，这里是底图唯一的留档）。2K 底图一张约 4.5 MB，
出得多时考虑 Git LFS。

`tools/bootstrap.sh` 每步只补缺的，可反复运行：

- `public/tex/`：缺文件时跑 `tools/textures.py`，生成纸纹与 6 张颗粒。
- `fonts-src/` → `public/fonts/`：缺哪个字面就从 macOS 系统字体抽取，每次都按 `src/` 用字重新子集化，缺字即失败；
  每个子集都过 OpenType Sanitizer（Chrome 加载字体前跑的同一套检查），被拒即失败。
- `public/brand/logo.png`：设了 `FILM_LOGO`（PNG）就每次按原样复制；否则只在缺失时写一个灰色占位框。
- `public/audio/bgm-master.wav`：缺失时按 `TOTAL_FRAMES` 写同长静音。选定配乐后放到 `public/audio/bgm-music.wav`，
  再跑 `tools/voice_mix.py` 写出母带（没有旁白时只处理配乐）。

依赖 python3 + numpy + fonttools + opentype-sanitizer（没装时有 `uv` 也行，临时拉起；`audio/*.py` 另需 scipy）、
Node 24（`tools/*.mjs` 直接 import `src/timeline.ts`）和 ffmpeg。新片先改 `src/timeline.ts` 的
`TITLE` / `SUBTITLE` 和章节表；改过文案后重跑 `tools/bootstrap.sh`（或 `python3 tools/fonts.py subset`）补字。
`fonts-src/` 是整套系统字体，已在 `.gitignore` 里，不要提交。

`audio/vocal_scan.py` 另需 `mlx-whisper`（仅 Apple Silicon），系统 Python 一般没装；用
`WHISPER_MODEL=mlx-community/whisper-large-v3-turbo uv run --quiet --python 3.12 --with mlx-whisper python audio/vocal_scan.py <候选...>`
临时拉起，首次运行要下载模型，放后台跑（2026-10-11 实测）。

## 分章配乐

```bash
python3 audio/gen_chapter_music.py --dry-run                                   # 先报条数与费用（0.04 美元一条）
python3 audio/gen_chapter_music.py                                             # 每章两条，已有的跳过；OPENROUTER_API_KEY 从环境变量读
uv run --quiet --python 3.12 --with librosa python audio/chapters/analyze.py   # -> audio/chapters/analysis.json
WHISPER_MODEL=mlx-community/whisper-large-v3-turbo uv run --quiet --python 3.12 --with mlx-whisper \
  python audio/vocal_scan.py --out audio/chapters/vocal-scan.json audio/chapters/*.mp3   # 判读见 pipeline.md 第 3 节
uv run --quiet --python 3.12 --with librosa python audio/chapters/analyze.py public/audio/bgm-full.wav   # 用整片配乐时：拟合它的网格，并入 analysis.json
python3 tools/music_bed.py --dry-run                                            # 看每章用哪条、裁多少、调到多少，整片配乐平移多少
python3 tools/music_bed.py                                                      # -> public/audio/bgm-music.wav
uv run --quiet --python 3.12 --with librosa python qc/beat_phase.py             # 各章相位距网格与彼此都在 ±25 毫秒内，整片配乐的衔接两侧相差 ≤ 25 毫秒
```

片头按整片配乐的重音剪过时，把那条配乐放 `public/audio/bgm-full.wav`（例：在第一次跑 `music_bed.py` 之前
`cp public/audio/bgm-music.wav public/audio/bgm-full.wav`），片头、片尾就用它；没有整片配乐时把 `opening`、`outro` 也写进简报。
`music_bed.py` 把整片配乐平移到分章配乐的网格上（±半拍内的最小平移），所以先要有它的网格；`--full-shift 0` 保持原时间，
输出与平移前的版本逐字节相同。2026-10-12 用《如何打造一款特斯拉》v0.5 的配乐在工程副本上实测：整片配乐网格残差 4.1 毫秒，
两处衔接偏 +90.4、+86.7 毫秒，平移后重拼，`beat_phase.py` 默认判定通过（片头 −7.8、片尾 −6.4 毫秒，衔接两侧相差 −3.3、+3.1 毫秒）；
已发布的 v0.5 配乐床在新质检下失败（+86.9、+94.0 毫秒）。
2026-10-12 在起步模板的示例时间线上用《如何打造一款特斯拉》的 26 条候选实测：自动选择与人工选的 13 条一致，
各章起点后 10–50 毫秒内都有起音。0.8.1 改为提前叠入后再跑：13 章都用上第 3 小节、引子 1 秒，无警告。0.8.2 改用拟合的节拍网格后再跑
（片头、片尾的整片配乐手动延后 0.21 秒，对齐这条示例时间线的网格；现在由 `music_bed.py` 自动算）：自动选择与该片 v0.5 的 13 条一致（两条网格残差 31、45 毫秒的候选被跳过），
13 章引子都是 1 秒、无警告；`qc/beat_phase.py` 通过，13 章 −4.1 至 −15.9 毫秒、彼此相差 11.8 毫秒，按 0.8.1 推算拼的同一组配乐
10 章超出 ±25 毫秒、最远 −238.6 毫秒。把这 13 条先改成 117 或 123 BPM 再拼：rubberband 相差 8.9 毫秒，atempo 相差 25.9 毫秒（未过）。

## 旁白与字幕

```bash
python3 tools/narration.py --dry-run    # 要合成几句、多少字符（扣除缓存与录音）；不联网，先把字符数告诉用户
python3 tools/narration.py              # 录音优先、其余 TTS（需 VOICENGINE_API_KEY），量时长，写 src/narration.ts
python3 tools/fonts.py subset           # 字幕用到的字进子集（缺字即失败）
python3 tools/voice_mix.py              # bgm-music + 旁白 -> public/audio/bgm-master.wav
tools/preview.sh <id> stills 16x9 120   # 单章看字幕与 HUD
```

旁白稿放 `audio/narration/lines.json`，用户录音放 `audio/narration/voice/<id>.*`（录了哪句就替换哪句）。TTS 缓存
`audio/narration/tts/`、裁好的 `clips/` 与人声轨都在 `.gitignore` 里；`voice/` 是用户的录音，要保留。2026-10-12 用
macOS `say` 生成的录音实测：静音录音（未安装的音色）会在裁静音后变空，脚本报「silent or empty」并停下。

## 封面

```bash
python3 tools/gen_cover_bg.py --dry-run          # 提示词、请求体、估价；不联网、不读密钥（先把估价告诉用户）
python3 tools/gen_cover_bg.py                    # 16:9 与 3:4、2K；已有的比例跳过，--force 重出（再花一次钱）
tools/stills.sh covers                           # -> ../qc/stills/cover-<比例>.jpg，打印每张用的底图
FILM_TITLE=<片名> FILM_BRAND=<品牌> tools/deliver.sh covers vX.Y   # -> output/images/…-封面16x9|4x3|3x4-…png/jpg，reports/vX.Y/covers.tsv
```

流程、版式与费用见 [covers.md](covers.md)。

## 章节时间轴、费用与交接

```bash
node tools/chapters.mjs --out ../../output/reports/vX.Y/publish-copy/chapters.txt   # MM:SS 章名；不足 10 秒的章即失败
node tools/credits.mjs --out-dir ../../output/reports/vX.Y/publish-copy            # 署名完整版、压缩版，打印长度；素材表在 src/credits.ts
python3 tools/ledger.py summary --since <上一版交付时间>                           # 交付报告「费用」节
python3 tools/ledger.py summary                                                    # 全片累计
python3 tools/ledger.py add --kind image --provider openrouter --model <模型> --qty 1 --unit image --cost-usd <美元> --ref cover/takes/web-16x9.png   # 只补脚本之外的调用（网页上出的图）；封面、配乐、TTS 脚本自己记
```

交付报告与交接单的写法见 [pipeline.md](pipeline.md) 第 7 节与 [publish-handoff.md](publish-handoff.md)。
