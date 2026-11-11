# 新人物艺术解释契约

人物卡不是对白翻译，而是用户主动开启后，用 ASS/SSA 叠加的一张短小英文角色卡。它会改变导演原本安排的视觉节奏，可能提前暴露身份或破坏神秘感，所以人物卡层默认关闭；普通学习字幕仍默认生成只有品牌文字水印的 ASS。只有用户明确 enable 后才生成角色卡。开启后默认使用 `visual_style=elegant`：小号暖白字、细描边、轻淡入淡出和无装饰框。`classic` 只在用户明确要求更醒目的旧风格时使用。卡片默认包含英文名和一句符合学习者 Profile 的简单英文说明；只有用户要求时才追加中文提示。

## 艺术字幕开关与叙事模式

`output.character_cards` 默认是 `false`。只生成学习字幕时，输出干净 SRT 与默认水印 ASS，不创建人物卡片。用户明确开启后，再用 `card_mode` 选择显示策略：

| 模式 | 行为 | 风险 |
|---|---|---|
| `off` | 不生成任何人物艺术卡片。 | 无额外观感影响；这是 Skill 的总开关关闭时的结果。 |
| `identity_after`（开启后的默认模式） | 等电影通过姓名、对白或明确身份信息揭示人物后，再显示“名字 + 简短解释”。 | 最保守；首次画面可能不显示卡片。 |
| `name_only` | 在已核验的首次画面显示名字，不显示身份、关系或背景解释。 | 会改变神秘感，但比完整解释少剧透。 |
| `full_visual` | 在已核验的首次画面显示名字和解释。 | 必须用户明确选择；可能剧透或破坏导演节奏。 |

不要把“首次看到人物”“字幕首次说出姓名”“对白首次让观众理解身份”强行合并成一个时间。`visual_start`、`literal_name_start`、`identity_start` 和最终 `display_start` 应分别保留；`identity_after` 使用 `identity_start`，没有明确字段时保守回退到字幕首次姓名命中。

## “每个新出场人物”的范围

- 包含有名字、明确身份或对剧情有持续作用的人物；同一人物的别名只生成一张卡。
- 不为每个群众、无名守卫、背景声音或只出现一次的普通职业生成卡，除非用户明确要求完整演员表式覆盖。
- 开启 `name_only` 或 `full_visual` 时，才以“第一次有意义的画面出场”为显示候选；不要把这个候选误写成身份揭示时间。
- `identity_after` 以电影已经给观众的身份信息为准，而不是强行追求最早画面。
- 默认不泄露首次出场之后才揭示的秘密、阵营变化、死亡或结局；`spoiler_policy` 为 `no_future_spoilers`。

## 证据与联网检索

人物身份可以来自电影上下文、用户提供的信息或外部资料，但卡片时间必须有可追溯证据：

1. 先用文字搜索定位姓名、别名和人物专属语义组；
2. 需要确认“人什么时候真的进入画面”时，再使用已核验的视频画面时间；
3. 字幕中首次出现姓名/别名只能标记 `literal_name_or_alias`，不能直接当作画面首次出现；
4. 如果字幕只出现代词或身份不明确，使用 `visual_start`/`visual_end` 或 `identity_start`/`identity_end`，但必须标记 `video_review` 或 `user_verified`，不能猜时间；
5. 对人物身份、关系或时代背景不确定时，再进行联网检索。优先官方制片方、发行方、作者/版权方资料和可靠参考资料；保存来源标题、URL 和访问日期到 JSON，不把来源 URL 显示在画面中。

联网检索用于确认人物资料，不用于伪造镜头时间。不同来源冲突时保守处理，缩短说明或省略卡片，并在交付中报告未确认项。

### 四层证据融合

不要把 `Arwen` 这个字符串的首次命中直接当作人物首次出场。为每个人物分别保留以下证据：

| 证据 | 能证明什么 | 不能单独证明什么 |
|---|---|---|
| `literal_name_or_alias` | 字幕第一次明确写出姓名、别名或说话人标签。 | 不能证明人物第一次进入画面；角色可能已经出现但字幕还没点名。 |
| `semantic_context_group` | 一组相邻对白共同指向一个人物，例如“Who is she?”、“She's an elf.”、“my father”。 | 单独的通用句子可能属于前面的另一段叙事。 |
| `web_identity` | 角色别名、关系、身份和无剧透说明。 | 不能证明电影中的镜头时间。 |
| `video_review` | 候选窗口中实际看到人物进入画面或镜头切换。 | 不应通过全片逐帧扫描获得；只检查文字证据附近的窄窗口。 |

推荐顺序是：一次全文文字搜索 → 语义上下文组 → 必要时联网确认身份 → 只对候选窗口抽取少量视频帧。文字搜索负责速度，画面检查负责纠正“先出现、后命名”的叙事结构。

`character_evidence.py` 会输出所有文字命中、第一条语义上下文组和可选的视频 contact sheet。最终卡片由 Agent 根据证据裁决，分别填写 `visual_start`、`identity_start`、`display_start`、`timing_source` 和 `confidence`。旧 JSON 中的 `start`/`end` 仍兼容，但如果证据是 `video_review`，在 `identity_after` 下会被视为视觉候选，不会直接提前显示。

## Profile 规则

| Profile | 角色说明要求 |
|---|---|
| `a2` | 6–10 个基础词；只说人物身份或最直接的行动。 |
| `cet4` | 8–14 个简单句词；可加入与当前出场直接相关的关系或任务。 |
| `b1` | 10–18 个词；可以包含动机、职责或世界观身份。 |
| `b2/cet6` | 可保留文学、历史和世界观细节，但仍不提前剧透。 |
| `custom` | 按用户指定长度、语言、是否加中文提示执行。 |

说明应是简短英文句子，例如：

```text
ARAGORN
A quiet ranger with a hidden royal past.
```

不要写百科段落、演员介绍、内部推理或“这是一个重要角色”之类的空话。

## Agent 输入 JSON

Agent/联网检索阶段生成临时 JSON。`character_cards.py` 会把它解析成 ASS art-cue JSON：

```json
{
  "film": "The Lord of the Rings: The Fellowship of the Ring",
  "profile": "cet4",
  "spoiler_policy": "no_future_spoilers",
  "character_card_mode": "identity_after",
  "visual_style": "elegant",
  "sources": [
    {
      "title": "Authoritative character guide",
      "url": "https://example.com/character-guide",
      "accessed": "2026-08-09"
    }
  ],
  "characters": [
    {
      "id": "aragorn",
      "name": "Aragorn",
      "aliases": ["Strider"],
      "anchor": "Strider",
      "semantic_groups": [
        {
          "label": "first identity context",
          "phrases": ["Who is he?", "He's a ranger"],
          "within_seconds": 20,
          "min_matches": 2
        }
      ],
      "explanation": "A quiet ranger who protects the travelers.",
      "zh_hint": "保护旅人的神秘游侠",
      "evidence": "subtitle_and_video_review",
      "timing_source": "video_review",
      "confidence": "high",
      "visual_start": "01:00:42.000",
      "identity_start": "01:00:47.000",
      "duration": 4.5,
      "style": "ArtTitle",
      "position": [960, 430]
    }
  ]
}
```

字段规则：

- `id` 必须在本次文件中唯一；`name` 是画面上显示的英文名。
- `aliases`/`anchor` 用于在字幕里寻找首次提及；可以用 `anchors` 提供多个锚点。
- `semantic_anchors` 只适合人物专属短语；`semantic_groups` 适合 `Who is she?` 这类通用句，要求多个短语在指定秒数内共同出现，避免误命中前面的叙事。
- `card_mode` 可逐人物覆盖顶层的 `character_card_mode`；未填写时使用 `identity_after`。总开关关闭时使用 `off`，不生成艺术卡片。
- `visual_style` 可使用 `elegant` 或 `classic`；未填写时使用 `elegant`。单个人物可用 `font_name`、`font_size`、`spacing`、`color`、`outline` 和 `shadow` 做局部覆盖。
- 如果能核验视频时间，填写 `visual_start` 和 `visual_end`；如果身份在更晚的对白中明确，另填写 `identity_start` 和 `identity_end`。不要用一个 `start` 字段掩盖两种时间。
- `start`/`end` 是兼容旧输入的显示时间字段；在 `identity_after` 下，带有视频/画面证据的旧时间不会覆盖更晚的身份揭示时间。
- 如果只有字幕证据，脚本使用首次匹配 cue 的开始时间，并按 `duration`（默认 4.5 秒）生成结束时间。
- `explanation` 必须是 Profile 适合的英文短句；`zh_hint` 只在 `--include-hints` 或卡片设置 `include_zh_hint: true` 时显示。
- `sources` 可以写在顶层，也可以写在单个人物卡上；它们会留在中间 JSON 的元数据里。

## 证据候选生成

先快速生成报告；这一步不会改视频，也不会逐帧扫完整部电影：

```bash
python3 "$SKILL_DIR/scripts/character_evidence.py" \
  --input "/path/to/movie.en.srt" \
  --characters "/tmp/movie.characters.json" \
  --output "/tmp/movie.character-evidence.json"
```

如果文字证据之间存在“先出现、后命名”的疑点，再只检查候选窗口：

```bash
python3 "$SKILL_DIR/scripts/character_evidence.py" \
  --input "/path/to/movie.en.srt" \
  --characters "/tmp/movie.characters.json" \
  --video "/path/to/movie.mkv" \
  --video-samples-dir "/tmp/movie-character-frames" \
  --lookback 45 \
  --lookahead 15 \
  --max-samples 12 \
  --output "/tmp/movie.character-evidence.json"
```

例如 Arwen 的文字姓名可能在约 80 分钟才出现，但语义组和视频抽样可能更早证明她已经进入画面。默认 `identity_after` 应使用身份/姓名揭示时间；只有用户选择 `name_only` 或 `full_visual` 时，才使用视频核验的视觉时间。三者应在最终 JSON 中分开保存，便于复核。

## 生成流程

```bash
python3 "$SKILL_DIR/scripts/character_cards.py" \
  --input "/path/to/movie.cet4.glossed.srt" \
  --characters "/tmp/movie.cet4.characters.json" \
  --profile cet4 \
  --output "/tmp/movie.cet4.character-art-cues.json" \
  --resolution 1920x1080 \
  --card-mode identity_after \
  --visual-style elegant

python3 "$SKILL_DIR/scripts/ass_styled_subtitle.py" \
  --input "/path/to/movie.cet4.glossed.srt" \
  --art-cues "/tmp/movie.cet4.character-art-cues.json" \
  --output "/path/to/movie.cet4.characters.ass" \
  --resolution 1920x1080
```

如果用户明确选择其他观感策略，把最后的模式换成 `--card-mode name_only` 或 `--card-mode full_visual`。若用户没有开启人物艺术字幕，不运行这一步；若需要显式验证关闭行为，可使用 `--card-mode off`，输出的 `items` 应为空。

脚本默认遇到无法定位时间的人物就停止，避免把错误卡片伪装成完整结果；需要允许部分交付时才使用 `--skip-unresolved`，并在最终报告中列出省略的人物。
