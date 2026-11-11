# 人人字幕 · Subtitle Freedom · Skill Card

这张卡是「人人字幕」（内部标识 `lov-subtitle-freedom-skill`）的可读发布记录。它把《指环王》字幕加工过程
作为真实案例，同时保留普通 SRT 与可选 ASS 艺术层的边界。

## Description

为视频或英文字幕生成按学习者水平筛选的英语学习字幕，解释真正妨碍理解的词汇、
习语、俚语、文化表达和复杂句子；艺术层显式开启后才生成 ASS 人物卡与水印。

## Owner

手工川工作室 Agent 字幕组 · LovStudio Skills catalog

## License / Terms

MIT。用户提供自己的视频或字幕；本 Skill 不随包分发电影内容。

## Use Case

中文学习者输入视频或英文 SRT，指定 CET4 等 Profile 作为最低难度线，得到保留原时间轴且覆盖该级别以上必要表达的学习字幕。
需要时，用户可单独开启人物卡和自定义水印。

## Deployment Geography

Global；可在具备 Python 3.8+ 的本地 Agent 环境运行。视频输入需要 FFmpeg/FFprobe。

## Requirements / Dependencies

输入可以是视频或 SRT/VTT/ASS/SSA。普通字幕注释不需要凭据；联网和局部视频证据是人物卡
场景下的可选手段。

## Known Risks and Mitigations

- 注释过密：按 Profile 和上下文筛选必要语言单元，限制 cue 密度。
- 人物卡过早剧透：区分文字、语义、视觉和身份证据，默认 `identity_after` 且总开关关闭。
- ASS 播放器差异：固定水印锚点并运行布局回归检查。
- 版权边界：只处理用户有权使用的输入，不重新分发原片。

## References

- [`SKILL.md`](SKILL.md)
- [`references/level-profiles.md`](references/level-profiles.md)
- [`references/character-cards.md`](references/character-cards.md)
- [`references/ass-art-text.md`](references/ass-art-text.md)

## Skill Output

普通输出是保留 cue ID、时间轴和英文对白的 SRT。艺术层显式开启后，额外输出 ASS/SSA，
承载人物卡、场景卡和可自定义水印。验证包括 cue 对齐、UTF-8、括号平衡、密度和 FFmpeg
解析检查。

## Skill Version

1.3.1

## Ethical Considerations

用户应确认自己有权处理输入视频和字幕。人物解释不编造身份、不提前泄露后续剧情，也不
把私人信息写入字幕。

## LovStudio Evidence

### User Cases

[`cases/cases.json`](cases/cases.json) 记录了《指环王：护戒使者》的真实案例：输入电影中
提取的英文 SRT 与 CET4 Profile，使用最小 Prompt 选择必要语言单元，输出学习字幕，并在
艺术层开启时生成 Arwen 人物卡和全局水印。两张成品截图是可回看的视觉证据。

### Dimension Map

维度地图见 [`skill-card.yaml`](skill-card.yaml)，覆盖语义正确性、学习有效性、叙事安全、
播放器兼容性与交付效率；每个维度都带证据来源。

### Pricing Basis

`pricing-card.yaml` 记录一次可复用工作流的 ¥0.99 价格依据、交付边界和复评触发条件。

### Distribution

付费渠道：WorkBuddy、Alipay SkillPay。免费渠道：GitHub 与 LovStudio。实际发布状态以
目录和平台回读为准。
