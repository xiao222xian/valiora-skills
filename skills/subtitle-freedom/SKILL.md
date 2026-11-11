---
name: lov-subtitle-freedom-skill
description: >
  为视频或原字幕生成以学习者所选水平为最低难度线的英文学习字幕：解释该级别及以上会阻碍理解的生僻词、习语谚语、俚语文化表达和复杂句子并保留原时间轴；默认输出干净 SRT 与带文字水印的 ASS，人物艺术卡片显式开启后再生成。触发词包括“人人字幕”“字幕注释”“四级英语字幕”“俚语解释”“复杂句子讲解”“新人物艺术解释”“learner subtitles”。
license: MIT
depends_on:
  - lov-branding-consistency
metadata:
  author: contributors
  version: "1.3.1"
  card_standard: lovstudio/skill-card/v1
  tags:
    - subtitles
    - english-learning
    - srt
    - ass
    - ffmpeg
    - character-cards
    - research
    - evidence-fusion
    - narrative-safe
    - renderer-compatibility
    - watermark-layout
    - bitmap-subtitle
  compatibility: "Python 3.8+, FFmpeg/FFprobe for video input, UTF-8 subtitle files."
  dependencies: []
---

# 人人字幕 · Subtitle Freedom

输入视频或原字幕文件地址，以及学习者的英语水平 Profile，输出保留原时间轴的英文学习字幕。用户选定的 Profile 是最低难度线：例如 CET4 会保留 CET4、B2、CET6 和更高难度条目，而不是只解释恰好标成 CET4 的词。必要解释的对象包括生僻词/术语、固定搭配、习语或谚语、俚语与文化表达，以及确实难以直读的复杂句子。默认交付干净 SRT 与带文字水印的 ASS；人物介绍和场景卡片会改变原有观看节奏，因此人物艺术卡片仍须由用户显式开启。

## User Profile（跨 session）

本 Skill 声明 `user-profile/v1`，每次运行读取共享 `user`、`brand`、`workspace`、`preferences` 以及 `skills.lov-subtitle-freedom-skill` 命名空间。学习级别、语言偏好和品牌事实按 Profile 连接到后续 session；用户直接说出的长期偏好立即写入 Profile，Skill 源码不复制个人路径或品牌值。默认水印使用文字与水平线；品牌 Logo 为可选项，显式开启 Logo 后再使用共享 `brand.logo`。

需要保存用户明确说出的长期偏好时，使用 `scripts/profile_store.py` 并带 `--confirm`；详见 [`references/user-profile.md`](references/user-profile.md)。Logo 开关、字号和水平线偏好都属于 Profile；交付默认使用 `sidecar_only`，只生成外置 PGS/SUP 或 ASS/SRT 字幕文件，不新建视频容器。

## Triggers

### Activate when

- 用户说“用这个视频做四级词汇注释字幕”“只解释必要单词并生成 SRT”。
- 用户要求解释“字幕里中国人不容易理解的表达”，包括生词、习语、谚语、俚语、文化语境或复杂句子。
- 用户提供视频或 `.srt/.vtt/.ass/.ssa` 地址，并要求按 CET4、B1、CET6 或自定义水平制作学习字幕。
- User asks to “create learner-friendly subtitles from this video/SRT” or “make styled ASS subtitles with a scene card”.
- 用户明确要求开启人物艺术字幕，例如“每个新出场人物都显示名字和简单解释”“生成角色艺术字介绍”或 “enable spoiler-safe character cards”。仅要求学习字幕时不要自行添加艺术卡片。
- 用户要求更换水印品牌、视觉方向、Logo 或署名；默认 ASS 已带品牌文字水印，水印仍可单独关闭。

### Do not activate when

- 用户只要求翻译、听写、校对或提取原字幕，不需要学习词汇注释；交给翻译、转录或字幕抽取能力。
- 用户只要求剪辑、压制视频或制作章节条，不需要新字幕文件；交给视频编辑或视频章节能力。
- 用户要求修改原视频中的画面文字、Logo 或电影片头素材；这不是字幕生成任务。

## Workflow (MANDATORY)

**You MUST follow these steps in order.**

### Step 0: Resolve skill root, dependencies, and runtime context

- Use `SKILL_DIR` if the environment provides it; otherwise infer the installed Skill directory.
- Verify `$SKILL_DIR/scripts/subtitle_gloss.py`, `$SKILL_DIR/scripts/character_evidence.py`, `$SKILL_DIR/scripts/character_cards.py`, `$SKILL_DIR/scripts/ass_styled_subtitle.py`, `$SKILL_DIR/scripts/profile_store.py`, `$SKILL_DIR/scripts/test_watermark_layout.py`, `$SKILL_DIR/references/level-profiles.md`, `$SKILL_DIR/references/character-cards.md`, `$SKILL_DIR/references/ass-art-text.md`, and `$SKILL_DIR/references/user-profile.md` exist.
- For video input, require `ffprobe` and `ffmpeg`. For an existing subtitle file, Python 3.8+ is sufficient unless format conversion is needed.
- Do not write into the source directory until the output path has been resolved and the source file has been checked. Never overwrite the source subtitle or video.

### Step 1: Resolve input and output

1. Accept a video path (`.mkv`, `.mp4`, `.mov`, `.webm`, `.avi`, `.ts`) or subtitle path (`.srt`, `.vtt`, `.ass`, `.ssa`).
2. For a video, inspect subtitle streams with `ffprobe`; select one English text subtitle by explicit request first, then `eng/en` language metadata, then a title containing `English`. A bilingual `zho` track may contain the same English line inside it, but it is not a second independent English dialogue track; do not merge both tracks or create duplicate cues. If no English text track is unambiguous, report the available tracks and ask one focused question.
3. Extract or normalize the selected track to a temporary UTF-8 SRT with `ffmpeg`; bitmap subtitles such as PGS/VobSub are not silently treated as text.
4. Resolve the learner Profile in this order: explicit request, runtime `profile`, then one focused question if it is missing. Read `references/level-profiles.md`. The selected Profile is a minimum difficulty floor; examples are `cet4`, `a2`, `b1`, `b2`, `cet6`, and `custom`.
5. Default output is adjacent to the source: `<source-stem>.<profile>.glossed.srt` and `<source-stem>.<profile>.glossed.watermarked.ass`; an explicit output path always wins for the SRT, with the ASS placed beside it. Keep the SRT clean and text-selectable. Generate the default text-only watermark ASS during the normal handoff; do not create character cards or scene cards unless the user explicitly enables `output.character_cards`. Honor an explicit SRT-only request or `--no-watermark` override.

### Step 2: Select and apply vocabulary

1. Read the complete normalized subtitle before choosing terms. Treat the selected Profile as a minimum difficulty floor, not an exact bucket: select language units from that level and above that materially block comprehension. Include rare words or terms, fixed phrases, idioms/proverbs, slang, culture-bound expressions, and complex sentences whose structure or implied meaning is hard to follow. Do not annotate names, places, common function words, or every word merely because it is above the learner's level.
2. Prefer the first occurrence of a term or expression. Repeat a gloss only when the meaning changes or the expression is central and far apart; keep the default maximum at three glosses per cue. For a complex sentence, match the shortest exact phrase that carries the difficulty and provide a concise sense, not a full-paragraph translation.
3. Create a temporary glossary JSON using the schema in `references/level-profiles.md`. Set `level` on every newly generated item to `a2`, `b1`, `cet4`, `b2`, `cet6`, or `advanced`; the runtime keeps items whose level is at or above the selected Profile and filters lower-level items. Set `kind` to `word`, `phrase`, `idiom`, `proverb`, `slang`, `culture`, `sentence`, or `term`; use `label` only when the output should say “句意” or another short category marker. Meanings are concise Chinese hints unless the user requests another language. Preserve the original English spelling, capitalization, punctuation, line breaks, cue IDs, and timestamps. Legacy glossary items without `level` remain eligible and are reported as ungraded for compatibility.
4. Run:

   ```bash
   python3 "$SKILL_DIR/scripts/subtitle_gloss.py" \
     --input "/path/to/video-or-subtitle" \
     --profile cet4 \
     --glossary "/tmp/subtitle-freedom-glossary.json" \
     --output "/path/to/output.srt"
   ```

5. Do not claim that a missing dialogue track was reconstructed. This Skill annotates supplied text; speech recognition is a separate, explicitly requested task.

### Step 3: Validate the plain subtitle deliverable

- Compare source and output cue count, cue IDs, and every timestamp; they must be identical for SRT output.
- Check UTF-8, non-empty text, balanced annotation brackets, no accidental duplicate glosses in one cue, no source overwrite, and no cue with a dense pile-up of word/phrase/sentence explanations.
- Run `ffmpeg -f srt -i output.srt -map 0:0 -c:s webvtt -f webvtt /dev/null` with overwrite enabled as a parser smoke test.
- For the default ASS sidecar, run the equivalent ASS parser smoke test and verify that its `Watermark` event contains the resolved brand text.
- Report the exact output path, Profile, annotation count, and any unverified subtitle-track or encoding assumptions.
- Include the profile floor, candidate count, eligible count, and any filtered or ungraded glossary count in the run summary.
- Include `glossary_matched`, `glossary_applied`, `glossary_unmatched`, and
  `glossary_suppressed` from the CLI report. Unmatched entries use
  `no_literal_match`; suppressed entries identify deterministic causes such as
  `overlap`, `max_notes_per_cue`, `duplicate_key`, or `repeat_first`.

### Step 4: Use ASS/SSA for the default watermark and optional character cards

SRT is a plain timed-text format. It cannot reliably express full-screen placement, font, color, outline, animation, or separate scene-card styles. Generate a text-only, watermarked ASS sidecar by default; use ASS/SSA art cues for character cards only after explicit enablement:

1. Generate the annotated SRT first so vocabulary policy and timing remain separate from presentation. Then generate the default text-only watermarked ASS. When the user explicitly asks for SRT only or disables the watermark, stop after the SRT validation stage.
2. Resolve the character-card policy only when cards are requested. Ordinary learning runs use `card_mode=off`; after explicit enablement, default to `card_mode=identity_after` so a name/explanation appears only after the film makes the identity reasonably clear. `name_only` may show only the name at a verified visual entrance. `full_visual` may show the name and explanation at the visual entrance and requires an explicit spoiler/atmosphere choice. Never silently upgrade character cards from `off` to another mode. The default character-card style is `visual_style=elegant`: small warm-white type, restrained contrast, thin outline, light fade, and no decorative box. `classic` is available only when the user explicitly wants the older, stronger title treatment. Keep the watermark choice independent: default `watermark_style=cinematic_serif` (direction B), with `minimal`, `soft_glow`, `glass`, `signature`, and `gold_title` also available.
3. If the user enables new-character explanations, read the complete subtitle and use the film context to identify every named or narratively important character's first meaningful appearance. Make one temporary character JSON card per character, not one per alias or repeated mention. Include aliases, character-specific semantic context groups, a short Profile-calibrated English explanation, a no-future-spoilers policy, and separate `visual_start`/`identity_start` fields when the evidence differs.
4. Run the fast evidence pass before choosing a card time:

   ```bash
   python3 "$SKILL_DIR/scripts/character_evidence.py" \
     --input "/path/to/output.srt" \
     --characters "/tmp/character-cards.json" \
     --output "/tmp/character-evidence.json"
   ```

   Treat literal name/alias hits as identity evidence, not automatically as visual first appearance. Require multiple nearby phrases for generic semantic anchors such as “Who is she?”. Use the web tool only to confirm identity, aliases, relationships, or the spoiler-safe explanation; record source title/URL/access date, and never treat web research as timestamp proof.
5. If literal and semantic evidence leave a gap, run `character_evidence.py` with `--video` and `--video-samples-dir` to generate a small contact sheet around each candidate window. Inspect only those windows; do not scan every frame of the movie. Keep visual first appearance, identity reveal, and literal-name time separate. Under `identity_after`, do not use a video-only visual time as the display time unless the user explicitly selected `name_only` or `full_visual`.
6. Resolve character cards to timed art cues:

   ```bash
   python3 "$SKILL_DIR/scripts/character_cards.py" \
     --input "/path/to/output.srt" \
     --characters "/tmp/character-cards.json" \
     --profile cet4 \
     --output "/tmp/character-art-cues.json" \
     --resolution 1920x1080 \
     --card-mode identity_after \
     --visual-style elegant
   ```

7. Prepare any additional art-cue JSON with `start`, `end`, `text`, and optional `style`, `position`, `alignment`, `font_name`, `font_size`, `spacing`, `color`, and `outline`. Pass `--art-cues` more than once to merge additional cards with the generated character-art cues when the user requested both.
8. Convert to the default watermarked ASS:

   ```bash
   python3 "$SKILL_DIR/scripts/ass_styled_subtitle.py" \
     --input "/path/to/output.srt" \
     --output "/path/to/output.ass" \
     --resolution 1920x1080 \
     --visual-style elegant \
     --watermark-style cinematic_serif \
     --watermark-text "手工川工作室 Agent 字幕组"
   ```

   Default ASS output adds a brand watermark: `手工川工作室 Agent 字幕组`. The default `cinematic_serif` direction is the selected B style; users may choose another `--watermark-style`, turn it off with `--no-watermark`, or change the brand with `--watermark-text "..."`. Never add this watermark to the plain SRT. Pass `--art-cues` only when character cards or other explicitly requested art cues are present.
   The generated `Watermark` style is deliberately bottom-center aligned. By
   default the generator emits only the brand text and the cinematic rule.
   Pass `--watermark-logo /path/to/logo.svg` to opt into the Logo; its SVG paths
   are embedded in the same `Watermark` ASS event, tinted to the brand color,
   and placed independently to the left of the text. The Logo preserves its
   source aspect ratio. `--no-watermark-logo` keeps the text and rule while
   explicitly omitting the optional Logo. The default Logo/text gap is 8 ASS
   pixels when Logo is enabled. The default dialogue subtitle size is 58 ASS
   pixels. The cinematic watermark uses 24-pixel text and a 24-pixel Logo
   height. Use `--watermark-logo-scale-x` only for renderer-specific adjustment.
   The horizontal rule aligns with the text center, not the full Logo-and-text
   lockup, so it never crosses the independent Logo. The `--watermark-logo-gap`
   and `--watermark-logo-offset-y` controls remain available.
   When the user asks for the original Logo image without video re-encoding,
   rasterize the shared `brand.logo` to an RGBA PNG and create an external
   PGS/SUP image subtitle with `scripts/raster_pgs_subtitle.py`. Pass the brand
   text to the same command so Logo and text are one visible image-subtitle
   event; use a transparent background, the source Logo colors, and a compact
   position immediately beside the text. Keep the original video path untouched
   and hand off the `.sup` sidecar directly. Do not remux it into a replacement
   MKV. If the learner subtitle remains text-selectable, hand off a clean ASS or
   SRT beside the visual watermark sidecar.
   The
   brand text and any cinematic/signature vector rule must use the same `\\an2`
   and identical `\\pos` x anchor. Do not reintroduce left/right half-width
   compensation: some players apply the style alignment again to vector
   drawings, which causes the line to drift. Run the watermark regression gate
   after changing this layout.
9. Use a scene-card cue only when the video, existing subtitle, or user-provided context supports its timing and wording. Do not invent a character biography merely because a face appears. If `character_cards.py` reports unresolved cards, either resolve them with evidence or report the omitted names; do not claim complete coverage.
10. Explain that players such as mpv, VLC, and libass-based renderers generally support ASS styling; burning into video with FFmpeg makes the appearance more stable but changes the video and depends on installed fonts.

See `references/character-cards.md` for the evidence policy and JSON contract, and `references/ass-art-text.md` for `\pos`, `\an`, `\fs`, `\c`, `\bord`, `\shad`, `\fad`, and examples.

### Step 5: Handoff

- Link the finished SRT and default watermarked ASS unless the user requests SRT only or disables the watermark.
- For an original-raster watermark request, link the external `.sup` sidecar and
  any clean text subtitle; never create a replacement video container unless the
  user explicitly asks for a new video file.
- State that the SRT is the clean portable text layer and the ASS is the positioned/styled watermarked layer. Report watermark enabled/disabled, its exact brand text, and whether the shared brand Logo was embedded. Report character cards separately as disabled by default or explicitly enabled.
- For character-card requests, report the selected mode (`identity_after`, `name_only`, or `full_visual`), character-card style (`elegant` or `classic`), watermark style, number of resolved cards, unresolved names, evidence type, spoiler policy, and whether web sources were used.
- For each card, retain the distinction between literal-name time, semantic-context time, and final visual display time; do not collapse them into one unexplained timestamp.
- Keep temporary glossary and extracted subtitle files out of the user-facing output directory unless explicitly requested.

### Local quality gate

```bash
python3 scripts/validate_skill.py .
python3 scripts/subtitle_gloss.py --help
python3 scripts/character_evidence.py --help
python3 scripts/character_cards.py --help
python3 scripts/ass_styled_subtitle.py --help
python3 scripts/profile_store.py read --skill-id lov-subtitle-freedom-skill
python3 scripts/test_profile_floor.py
python3 scripts/test_glossary_report.py
python3 scripts/test_watermark_layout.py
python3 scripts/raster_pgs_subtitle.py --help
```

## Dependencies

- Python 3.8+ and Pillow for raster Logo palettes; standard library only for the
  remaining bundled scripts.
- FFmpeg and FFprobe when the input is a video or when converting subtitle formats.
- An ASS-capable player or libass/FFmpeg for rendering styled subtitle events.

## 通用反馈闭环

用户在 Skill 驱动任务中提出修改意见时，继续当前产物前必须执行：

1. 先判断意见是 `task-specific`（仅本次）还是 `reusable`（可跨任务复用）。
2. `task-specific` 只修改当前任务，不改 Skill。
3. `reusable` 先确定作用域：领域规则先更新对应 canonical Skill；适用于所有 Skill 的规则先更新共享规范。
4. 完成规则更新、版本、lint 与分发核验后，再把修改应用到当前任务。
5. `reusable` 修改会使此前的“确认”“继续”“发吧”失效；完成当前产物修改和回读后必须停下，等待用户下一步指示，不自动进入发布、提交或其他外部写入。
