# 人人字幕 · Subtitle Freedom

![Version](https://img.shields.io/badge/version-1.3.1-CC785C)
![License](https://img.shields.io/badge/license-MIT-green)

从视频或原字幕生成适合学习者英语水平的英文注释字幕：用户选定的 Profile 是最低难度线，输出该级别及以上真正影响理解的词、短语、习语、文化表达和复杂句子；默认同时输出保留原时间轴的干净 SRT 与带文字水印的 ASS。人物卡片和场景卡片会改变原片视觉节奏，仍须由用户显式开启；默认艺术风格采用优雅克制的 `elegant`。

## 本地安装

源目录：

```text
$SKILLS_ROOT/subtitle-freedom-skill
```

本地安装入口：

```text
$AGENT_SKILLS/lov-subtitle-freedom-skill
```

运行时使用 `$SKILL_DIR` 指向安装入口或源目录；Skill Creator 已创建可解析的本地 symlink。

## 使用

### 视频或 SRT → 学习字幕

Agent 先根据用户请求生成一个临时 glossary JSON，再运行：

```bash
python3 scripts/subtitle_gloss.py \
  --input "/path/to/movie.mkv" \
  --profile cet4 \
  --glossary "/tmp/movie-cet4-glossary.json" \
  --output "/path/to/movie.cet4.glossed.srt"
```

也可以直接输入已有字幕：

```bash
python3 scripts/subtitle_gloss.py \
  --input "/path/to/movie.en.srt" \
  --profile b1 \
  --glossary "/tmp/movie-b1-glossary.json" \
  --output "/path/to/movie.b1.glossed.srt"
```

`--profile` 表示最低难度线，而不是“只显示该级别”。例如 `--profile cet6` 会保留 CET6 与 `advanced` 条目；`--profile cet4` 会保留 CET4、B2、CET6 与更高条目。Agent 生成的 glossary 条目应携带 `level`；脚本会在注释前过滤低于该线的条目，并保留未标级别的旧条目以维持兼容性。实际解释条目仍来自本次字幕上下文生成的 glossary。完整契约参见 `references/level-profiles.md`。

运行结果会同时报告 `profile_floor`、候选条数、有效条数、被级别线过滤的条数和未标级别条数，方便检查“选择级别以上”的策略是否真正生效；另外会输出 `glossary_matched`、`glossary_applied`、`glossary_unmatched` 与 `glossary_suppressed`，明确列出词表未在原字幕中出现的条目，以及因短语重叠、单条字幕注释上限、重复键或首次出现规则而未落到输出里的条目。

### SRT → 全屏艺术字 ASS

SRT 本身不能可靠保存位置、字体、颜色和动画。普通学习字幕的默认 ASS 交付无需人物卡片，直接运行 `ass_styled_subtitle.py` 即可得到带文字水印的样式化字幕；需要人物卡片或其他艺术字时，再准备艺术字事件：

```json
[
  {
    "start": "00:00:12.000",
    "end": "00:00:17.000",
    "text": "FRODO BAGGINS\\nThe Ring-bearer",
    "style": "ArtTitle",
    "position": [960, 430],
    "align": 5,
    "font_size": 54,
    "color": "#E8DDCA",
    "outline": 1,
    "shadow": 1
  }
]
```

然后转换：

```bash
python3 scripts/ass_styled_subtitle.py \
  --input "/path/to/movie.cet4.glossed.srt" \
  --art-cues "/path/to/art-cues.json" \
  --output "/path/to/movie.cet4.styled.ass" \
  --resolution 1920x1080 \
  --visual-style elegant \
  --watermark-style cinematic_serif \
  --watermark-text "手工川工作室 Agent 字幕组"
```

ASS 可在 mpv、VLC、libass 和 FFmpeg 烧录流程中使用。需要稳定交付到视频文件时，再用 FFmpeg 烧录；这会生成新视频而不是修改字幕文件。

人物艺术卡片默认关闭。只要求学习字幕时仍生成默认水印 ASS，但不自动创建人物卡片；如果用户明确开启人物艺术字幕，再选择 `identity_after`（默认、身份揭示后显示）、`name_only`（首次画面只显示名字）或 `full_visual`（首次画面显示名字和解释）。后两种会主动改变神秘感，其中 `full_visual` 可能剧透。艺术 ASS 默认使用 `elegant`：暖白低对比度、小字号、细描边、轻淡入淡出、不加装饰框。`classic` 仅在用户明确要求更醒目的旧风格时使用。品牌水印默认开启，默认采用 B / `cinematic_serif` 电影衬线风格，默认文字为“手工川工作室 Agent 字幕组”；用户可从 A–F 选择、改名或关闭。

关闭水印时使用 `--no-watermark`；需要启用 Logo 时使用 `--watermark-logo "/path/to/logo.svg"`；需要显式关闭 Logo 但保留文字和水平线时使用 `--no-watermark-logo`；需要让文字水印覆盖到影片尾部时使用 `--watermark-end HH:MM:SS.mmm`；改名时使用 `--watermark-text "你的品牌名"`；选择其他方向时使用 `--watermark-style minimal|soft_glow|glass|signature|gold_title`。艺术 ASS 默认只输出文字和水平线；启用 Logo 后，SVG 路径与品牌文字合并到同一个 ASS 水印事件，水平线只与文字对齐，不覆盖独立 Logo。水印只写入 ASS，不会进入 SRT。

如果用户要求使用原始 Logo 图像、保持视频原样并避免整片烧录：先将共享 Profile 的 `brand.logo` 栅格化为 RGBA PNG，再生成一个包含 Logo 和品牌文字的外置 PGS/SUP 图像字幕轨：

```bash
python3 scripts/raster_pgs_subtitle.py \
  --input "/path/to/original-logo.png" \
  --output "/tmp/original-logo.sup" \
  --video-size 1920x804 \
  --position 1517:734 \
  --start 00:00:00.000 \
  --end 03:55:32.138 \
  --text "手工川工作室 Agent 字幕组" \
  --font "/System/Library/Fonts/Supplemental/Songti.ttc" \
  --font-size 24 \
  --text-color "#E4C58F" \
  --logo-height 24 \
  --logo-gap 8
```

`.sup` 是外置字幕文件，直接与原片一起加载；不要把它重新封装成新的 MKV。PGS 图像轨保持原 Logo 的透明边缘和源颜色，并保留水印上方的细水平线；位置应以文字水印的实际锚点为准，让 Logo 紧邻文字，不增加厚重底板。需要可选择的学习字幕时，另行提供干净的 ASS 或 SRT。

B / `cinematic_serif` 与 E / `signature` 的装饰横线采用播放器兼容的居中规则：`Watermark` 样式自身为底部居中，文字和矢量横线共享同一 `\\an2` 与 `\\pos` 横向锚点。不要按左右边缘再次补偿线宽；这会在部分播放器中造成横线漂移。修改水印布局后运行 `python3 scripts/test_watermark_layout.py`。

### 新人物首次出场 → 艺术解释卡片

Agent 根据完整英文字幕和电影上下文生成角色 JSON；身份不确定时才联网检索，并把来源保存在临时 JSON 中。卡片默认只使用首次出场时已经能知道的信息，不提前剧透后续剧情。字幕姓名首次出现不等于画面首次出现，因此先做证据候选报告：

```json
{
  "film": "The Lord of the Rings: The Fellowship of the Ring",
  "profile": "cet4",
  "spoiler_policy": "no_future_spoilers",
  "character_card_mode": "identity_after",
  "characters": [
    {
      "id": "aragorn",
      "name": "Aragorn",
      "aliases": ["Strider"],
      "anchor": "Strider",
      "semantic_groups": [
        {
          "phrases": ["Who is he?", "He's a ranger"],
          "within_seconds": 20,
          "min_matches": 2
        }
      ],
      "explanation": "A quiet ranger who protects the travelers.",
      "evidence": "subtitle_and_video_review",
      "visual_start": "01:00:42.000",
      "identity_start": "01:00:47.000",
      "duration": 4.5
    }
  ]
}
```

快速扫描字幕并生成文字证据：

```bash
python3 scripts/character_evidence.py \
  --input "/path/to/movie.en.srt" \
  --characters "/tmp/movie.cet4.characters.json" \
  --output "/tmp/movie.character-evidence.json"
```

如果语义证据和姓名证据不一致，再对候选窗口抽少量帧：

```bash
python3 scripts/character_evidence.py \
  --input "/path/to/movie.en.srt" \
  --characters "/tmp/movie.cet4.characters.json" \
  --video "/path/to/movie.mkv" \
  --video-samples-dir "/tmp/movie-character-frames" \
  --lookback 45 --lookahead 15 --max-samples 12 \
  --output "/tmp/movie.character-evidence.json"
```

这个 contact sheet 只覆盖候选窗口，不逐帧扫描整部电影。确认后再运行人物卡片和 ASS 转换：

```bash
python3 scripts/character_cards.py \
  --input "/path/to/movie.cet4.glossed.srt" \
  --characters "/tmp/movie.cet4.characters.json" \
  --profile cet4 \
  --output "/tmp/movie.cet4.character-art-cues.json" \
  --resolution 1920x1080 \
  --card-mode identity_after \
  --visual-style elegant

python3 scripts/ass_styled_subtitle.py \
  --input "/path/to/movie.cet4.glossed.srt" \
  --art-cues "/tmp/movie.cet4.character-art-cues.json" \
  --output "/path/to/movie.cet4.characters.ass" \
  --resolution 1920x1080 \
  --visual-style elegant \
  --watermark-style cinematic_serif \
  --watermark-text "手工川工作室 Agent 字幕组"
```

若字幕无法定位某个人物，脚本默认停止并报告该人物；只有明确接受部分结果时才使用 `--skip-unresolved`。完整规则见 `references/character-cards.md`。

不需要人物艺术字幕时，直接停在 SRT；也可以在脚本层使用 `--card-mode off` 生成一个 `items: []` 的空艺术层。完整规则见 `references/character-cards.md`。

## 质量门

```bash
python3 scripts/validate_skill.py .
python3 scripts/subtitle_gloss.py --help
python3 scripts/character_evidence.py --help
python3 scripts/character_cards.py --help
python3 scripts/ass_styled_subtitle.py --help
python3 scripts/test_watermark_layout.py
```

脚本质量门会检查 SRT cue 数量、时间轴、UTF-8、注释括号和 ASS 事件格式。Skill 默认不覆盖源视频或源字幕。

## 依赖

- Python 3.8+
- FFmpeg/FFprobe（视频输入或格式转换时）
- 支持 ASS 的播放器或 libass 渲染器（艺术字模式）

## License

MIT
