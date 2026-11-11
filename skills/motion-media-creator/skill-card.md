# Skill Card — lov-motion-media-creator

本卡片与 `skill-card.yaml` 对应，是发布记录，不是实现说明。

## Description

无实拍，把一个主题沿一条轴（时间、地图、图鉴、工序或尺度）分章，做成每章一种视觉的动态设计短片：章节标题卡与进度轴 HUD、旁白（TTS 或真人原声）与一眼能读的大字幕（默认中文，可中英双语）、每章一段 AI 配乐并卡在拍上、事实核查；默认交付 16:9 平台成片、16:9 / 4:3 / 3:4 三张封面（AI 无字底图 + 合成排字）、质检报告与发布交接单，用户点名时加出 9:16 竖版。

## Owner

Lovstudio.AI，通过官网联系。

## License / Terms

MIT。起步模板中的示例数据与字形可自由修改；系统字体的授权以字体厂商条款为准。

## Use Case

面向做知识类短视频的创作者与品牌工作室。输入是一个主题与它的轴（时间、地图、图鉴、工序或尺度），可附资料与品牌素材；产出一条 2–4 分钟、带旁白与字幕的动态图志（默认 16:9）、三比例封面、交付报告（含 AI 生成内容清单、版本历史与费用汇总）与发布交接单（各平台文案的实测长度、章节时间轴、署名块）。

## Deployment Geography

全球；在本地 macOS / Linux 开发机上，由支持 Agent Skills 的宿主运行。

## Requirements / Dependencies

Node 24+、pnpm、Remotion 4；Python 3.9+（fontTools、Pillow、numpy、opentype-sanitizer 或 uv）；uv 临时拉起的 librosa；ffmpeg / ffprobe。依赖 `lov-branding-consistency`。可选：OpenRouter 的 `OPENROUTER_API_KEY`（AI 配乐与封面底图；出图要求余额不低于 1.00 美元）、豆包 Seed-TTS 2.0 的 `VOICENGINE_API_KEY`（都只从环境变量读取）、用户逐句的真人录音、`lov-media-creator` 质检脚本、`lov-channels-cover`、`lov-media-publisher`。

## Known Risks and Mitigations

- 史实错误或示意被当真：事实台账、对抗核查、就近与片尾示意说明。
- 画面泄露制作技术或工具署名：源码与渲染帧双路排查，元数据只留片名与出品方，文件内工具名回读清零。
- 系统字体商用授权不明：交付报告提醒，可换开源字体重渲。
- 旁白说出台账之外的事实，或 TTS 读错数字与专名：旁白稿只用台账里的事实，`tts` 字段写出读法并逐句试听，需要时换真人录音。
- AI 生成内容未声明或被代为决定：交付报告与发布交接单逐类列出 TTS 旁白、AI 配乐、AI 封面底图，附平台规则与法规原文；平台上怎么标由用户决定，清单在交接回复里直接给用户看（自动发布的平台提交前不再问），Skill 不代选。
- 付费调用失败仍被计费（2026-10-12 两次出图断线照样扣费）：每次调用记进费用账本，出图前查余额，断线不盲目重试。
- 片尾署名指向简介、简介被用户改写后链接丢失：片尾署名卡自己写全许可名与短链接。
- 平台文案超限或标签被拒：交接单的长度都是实测值，署名分完整版与压缩版，章节时间轴由工具生成并检查每章时长。

## References

- [Machine-readable card](skill-card.yaml)
- [Primary Skill instructions](SKILL.md)
- [流水线与门禁](references/pipeline.md)
- [片型语法](references/style-grammar.md)
- [封面](references/covers.md)
- [事实台账、片尾署名与 AI 生成内容清单](references/fact-and-disclosure.md)
- [发布交接](references/publish-handoff.md)

## Skill Output

横版 16:9 MP4（H.264 + AAC，用户点名时加竖版 9:16）、16:9 / 4:3 / 3:4 三张封面（按比例命名，PNG、JPG）、交付报告（含 AI 生成内容清单、版本历史与费用汇总）、发布交接单与质检产物。参数：主题、轴与范围、章节数与片长、品牌名与官方 Logo、印章文字。校验：从编码文件回读解码、响度、码率与元数据；每个交付画幅的逐章联系表与转场窗口；上屏文字不低于字号下限；分章配乐按拟合的节拍网格把小节强拍放在章节第一帧、换段提前叠入，各章节拍相位距网格与彼此都在 ±25 毫秒内，整片配乐进出的每处衔接两侧相位相差不超过 25 毫秒；旁白逐句不越界、不落在片名卡与片尾卡上；章节时间轴第一条 00:00、每章显示时长不少于 10 秒；三张封面在缩略尺寸下片名可读、底图无字无标志；片尾署名卡自足；事实台账无不成立项。

## Skill Version

0.9.1

## Ethical Considerations

史实内容必须有来源并标注示意范围；不伪造引文；品牌只用官方资产；第三方素材在片尾署名；AI 生成内容逐类列清单并附平台规则，由用户决定平台上的标注；不展示与题材无关的个人信息。

## LovStudio Evidence

### User Cases

见 [`cases/cases.json`](cases/cases.json)：《字里中国》（编年轴，175.5 秒）与《如何打造一款特斯拉》（三维工序轴，173.7 秒，v0.1 到 v0.5；2026-10-12 视频号原创审核中、B 站审核中、YouTube 已发布），Input → Prompt → Output 完整。

### Dimension Map

机器可读卡片中有三个维度（史实与标注、片型完成度、协作效率）及其证据，评分待更多案例后给出。

### Pricing Basis

见 [`pricing-card.yaml`](pricing-card.yaml)：一次性购买，官网显示 1394 Credits；复评条件已写明。

### Distribution

付费渠道：LovStudio 官网（`lovstudio`）上架中；`workbuddy`、`skillpay` 未上架。免费渠道：无。
