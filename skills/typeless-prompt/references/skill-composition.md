# Skill Group Composition

## Nearby Skills Inspected

- `lov-voice2srt`：输入音频或视频，输出 SRT、cue JSON 与纯文本。它拥有 ASR 与
  时间轴验收；本 Skill 只接收已经存在的文本，不调用识别服务。
- `lov-personal-vocabulary`：维护、去重和同步个人术语。它可以提高上游识别质量，
  但不负责消解改口、重建逻辑或安排正文版式。
- `humanizer-zh`：编辑已经成形的文章，去除 AI 写作痕迹并增强自然感。它与本
  Skill 都会精简措辞，但不处理 ASR 最终意图、被否定旧版本和口述结构。
- `lov-output`：把最终回复保存为 Markdown、TXT、JSON 或 YAML 文件。它不改写
  内容，只是可选的下游落盘能力。

## Atomic Handoffs

1. 可选上游：`lov-voice2srt` 输出 UTF-8 `transcript.txt`。其验收边界是音频识别、
   时间轴与转写产物有效；本 Skill 从纯文本语义整理开始。
2. 可选上游：`lov-personal-vocabulary` 向 ASR 提供术语词表。交接产物是规范词汇
   JSON 或上游已经纠正的文本；本 Skill 不管理词库生命周期。
3. 核心：`lov-typeless-prompt` 接收 ASR 转写或口述草稿，输出只包含最终正文的
   UTF-8 文本。验收边界是改口生效、信息完整、逻辑清楚、版式清爽且无新增事实。
4. 可选下游：`lov-output` 接收已验证正文并保存为文件。落盘格式和路径由下游
   验收，本 Skill 不宣称文件已经创建。

## Overlap Decisions

- 与 `humanizer-zh` 的共同点仅是减少冗余和元话语。前者处理 AI 成文风格，本
  Skill 处理口述转写的最终意图与结构，因此保持独立路由。
- 上游 ASR 可能已经修正术语或标点，本 Skill 会保留明确结果，但不会复制音频
  识别、词库同步或时间轴逻辑。
- OpenLess 自定义 Style Pack 是本 Skill 的真实使用背景，不是运行依赖；本 Skill
  不修改 OpenLess 内置 Prompt、应用配置或历史记录。

## Composition Decision

这是 Single Skill。用户可见结果始终是“口述转写文本 → 清爽、可直接发送的最终
正文”；意图消解、信息保留、逻辑重建和排版属于同一验收链，没有两个可以独立
触发和交付的产品阶段。所有 sibling Skill 都通过文本或 JSON 产物可选交接，不是
隐藏依赖，因此不需要自包含 Skill Kit。
