# Skill Card — 采访短片 · Interview Short（lov-interview-media-creator）

本卡与 `skill-card.yaml` 对应，是发布记录，不是实现说明。

## Description

把一场采访录像（手机竖拍、领夹麦为主，可加微信聊天、被访者自述、公众号文章与现场照片）剪成 2–4 分钟（最长约 4 分钟）的视频号竖版采访短片：
被访者原话做冷开场，重排成约 5 章，提问卡与回答大字幕分开，人名条、地点条、讲解图形、跳切推近、自然美颜、按内容生成的配乐、
合影与官方 Logo 收尾；交付审片版、字幕、封面 A/B、发布文案与交付报告，批准后交给发布环节。

## Owner

Lovstudio.AI，通过 Lovstudio.AI 官网联系。

## License / Terms

MIT。起步工程与脚本可自由修改；字体、配乐与第三方模型的授权以各自条款为准。

## Use Case

做创业者、嘉宾访谈短视频的创作者与品牌工作室：活动或拜访中用手机拍了一段单人采访，想当天做成一条适合视频号传播的竖版短片。
横版深度访谈、访谈长片与访谈纪录片不在范围内，由 `lov-media-creator` narrative-vlog「访谈长片」承担。

## Deployment Geography

全球；本地 macOS（Apple Silicon）开发机，支持 Agent Skills 的宿主（Claude Code、Codex 等）。

## Requirements / Dependencies

- Python 3.9+：numpy、opencv-python、mlx-whisper、opencc、jieba；FFmpeg / FFprobe（含 zscale）；macOS `avconvert`（杜比视界素材）；Node 20+ 与 Remotion 4。
- OpenCV YuNet 人脸模型（OpenCV model zoo 下载）；macOS `swiftc`（配乐人声检查）。
- 首次转写从 Hugging Face 下载两个 Whisper 模型（约 3.1 GB + 1.6 GB），缓存后可离线。
- `lov-media-creator` 的混音、母带与音频质检脚本（必需）；`lov-branding-consistency`；可选 `lov-media-publisher`、`lov-wdb-cli`、`lov-channels-cover`。
- 可选 `OPENROUTER_API_KEY`（Lyria 配乐，只从环境变量读取）。

## Known Risks and Mitigations

| 风险 | 缓解 |
| --- | --- |
| 把转写错误或推断写进字幕、人名条 | 两模型交叉转写；分歧专名交作者；只用事实台账里有出处的信息 |
| 剪口吃字或带进口水词、另一人的插话 | 包络加回转写试切每个切点；逐句两模型复检；同源相邻句共用切点 |
| 公开了被访者不愿公开的信息 | 拒答与「不方便」的内容整段删；二维码扫描加全片联系表；身份信息能否公开问作者 |
| 替被访者的宣传口径背书 | 宣传口径保留为引述 |
| 配乐含人声或尾部断档 | 人声分离判定；按可闻尾音对齐；音乐 stem 断档扫描 |
| 代作者接受平台条款或未经确认就发布 | 原创条款、合集、位置与字幕批准在终稿确认里一次问齐，作者同意后才提交 |
| 杜比视界素材经 ffmpeg 色调映射过亮偏品红 | `sdr_source.py` 检测杜比视界，用 avconvert 转整条 SDR 源并核对；`build_timeline` 遇到杜比视界源打印 WARN |
| 单模型取字幕时间出现闪行、首行晚出或边缘行退回临时时间 | `subs_from_lines` 两模型逐句择优、缺字行跨模型补位、首行从句首开始、行首吸附片段起点、单字闪行并入邻行 |
| 中间轨色彩矩阵与渲染端不一致，整片轻微偏色 | 编解码都显式 BT.709 并写标记；`check_timeline --mezz` 断言 bt709（首个案例成片有此轻微偏色，已知局限） |
| 盘点漏掉子文件夹里的素材（作者后放进去的被访者照片） | 素材清单用 `find -maxdepth 2` 连子文件夹一起列；作者说加了照片时先找第一次盘点之后新增的目录 |
| 美颜过度或改变被访者样貌 | 默认自然档，交付前给作者看近景前后对比；强档只在被访者要求时用；两档都不改脸型，改脸型要被访者明确同意 |
| 渲染偶发的单帧坏帧（花屏、错位）只有一帧，5 fps 联系表抽不到 | 封装时逐帧分块比对前后两帧（`glitch_scan.py`），每处命中出三联图人工判；片尾闪白、照片快门闪白、运动模糊只打标签、不自动放行；真坏帧重渲那一段再扫 |

## References

- [Machine-readable card](skill-card.yaml)
- [Primary Skill instructions](SKILL.md)
- [片型语法](references/style-grammar.md) · [流水线与门禁](references/pipeline.md) · [上下文来源](references/context-sources.md)
- [发布交接](references/publish-handoff.md) · [踩坑记录](references/pitfalls.md) · [Skill 组合](references/skill-composition.md)

## Skill Output

视频号竖版 9:16 审片版与平台成片（MP4，H.264 + AAC）、审片与批准字幕（SRT）、3:4 封面 A/B 与选定版的 4:3 分享卡（PNG）、
发布文案、导演阐述与交付报告（含事实核对；Markdown / JSON）。要发 B 站时另出同一条时间线派生的 16:9 横版成片、16:9 封面与 B 站文案。验收：逐句剪口复检、成片时间线与中间轨检查、lov-media-creator 的混音门禁、
编码成片解码与码率、bt709 标记、5 fps 分页联系表、逐帧二维码扫描与单帧坏帧扫描、封面缩略可读。

## Skill Version

0.6.0

## Ethical Considerations

被访者是主体：只用其原话，不替其宣传口径背书；拒答与不愿公开的信息不进片；聊天记录只读取与片子直接相关的事实，聊天正文不进交付物；
出镜人物美颜不改脸型，强档只在被访者要求时用，可关闭；AI 配乐在交付报告与发布交接里写明，平台标注由作者决定。

## LovStudio Evidence

### User Cases

见 [`cases/cases.json`](cases/cases.json)：「对话刘凯宁」，9 分 11 秒采访 → 2 分 53 秒视频号短片，已提交、平台审核中
（`publish_status=platform_pending`，2026-10-19 回读「原创审核中」）。已知局限：交付后的审查发现中间轨按 BT.601 编码且未加标记、
渲染端按 BT.709 解码，案例成片肤色轻微偏移，已在 `fx_pieces.py` 修复。案例里的证据路径属于源项目，不随 Skill 分发。

「对话 Ricky」（2026-10-26/27）：iPhone 17 Pro 横拍双人同框 67 分钟素材 → 3 分 42 秒视频号竖版（逐句裁到说话人、中英双语字幕、
概念参考卡、设备 B-roll、lov-logo-sting 片尾），2026-10-27 提交视频号、列表回读「原创审核中」；同一条时间线派生 16:9 横版发 B 站
（BV1CgxM6ZEWk，回读「开放浏览」）。作者三轮审片反馈（产品镜头、问答交界重复字、品牌片尾、去章节卡、中英双语、提问卡去标签、概念参考卡）都已写进片型语法与起步工程。

### Dimension Map

原话与事实、片型完成度、剪口效率三个维度，证据见 `skill-card.yaml`，分数暂不评。

### Pricing Basis

见 [`pricing-card.yaml`](pricing-card.yaml)：本 Skill 与必需依赖 `lov-media-creator`、`lov-branding-consistency` 均包含在 Lovstudio.AI VIP Membership
全套权益中，不单独定价、不兑换 Credits（作者 2026-10-21 确认）。会员金额以实际会员方案为准；会员权益不包含 AI 配乐等第三方服务费用、字体授权或人工代剪。置信度低。

### Distribution

Lovstudio.AI 官网会员分发（2026-10-21 选定，`distribution.paid`）。源码仓库保持私有，不进入免费镜像；未选择 WorkBuddy、SkillPay 等其他平台渠道。
