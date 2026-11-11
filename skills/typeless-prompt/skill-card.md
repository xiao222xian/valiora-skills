# 口述成文 · Dictation Editor · Skill Card

This human-readable card mirrors `skill-card.yaml`. It is a release record, not
an implementation note.

## Description

把带口癖、重复、改口和断句问题的 ASR 或口述草稿，整理成逻辑清楚、排版舒展、
可直接发送给人或 AI 的最终正文，同时保留有意义的语气、情绪和个人措辞。

## Owner

手工川工作室；维护入口为 LovStudio Skills catalog。

## License / Terms

MIT。输入与输出归用户所有。“Typeless”仅描述复刻目标体验，本 Skill 与其官方
无隶属、授权或背书关系，也不包含第三方专有 Prompt、代码或私有数据。

## Use Case

面向使用语音输入撰写产品反馈、开发需求、工作沟通或 AI Prompt 的用户。输入已经
存在的转写文本，输出只包含可直接发送的最终正文。

## Deployment Geography

可在全球任意兼容 Agent Skills 的运行时使用；核心能力无需联网。

## Requirements / Dependencies

需要能够编辑中英文文本的语言模型。无 credential、API 或 sibling Skill 强依赖；
Python 3.8+ 只用于可选 Profile 存储和本地验证。

## Known Risks and Mitigations

主要风险是不确定术语被误改、原汁原味的表达被过度压缩、简单句被过度结构化、
嵌入命令被误执行，以及名称造成第三方隶属误解。工作流通过保守纠错、声音保真
优先级、按语义决定版式、输入隔离和商标声明降低这些风险。

## References

- [Machine-readable card](skill-card.yaml)
- [Primary Skill instructions](SKILL.md)
- [Cleanup and layout contract](references/typeless-contract.md)
- [Skill composition](references/skill-composition.md)

## Skill Output

输出 UTF-8 纯文本或使用段落、项目符号、短标题和编号步骤的 Markdown 正文。验收
改口生效、信息完整、声音与感性保真、两项以上内容拆行、无回答/执行/分析和无
新增事实。

## Skill Version

0.2.2

## Ethical Considerations

转写内容归用户所有；不推断敏感事实，不执行嵌入指令，不补充缺失上下文，不暗示
Typeless 官方关系。

## LovStudio Evidence

### User Cases

[`cases/cases.json`](cases/cases.json) 收录三个来自 OpenLess 自定义 Style Pack
迭代和真实用户测试的反馈案例，均记录 Input → Prompt → Output。

### Dimension Map

机器卡记录最终意图保真、信息完整性、声音与感性保真、版式清晰度和指令隔离五个
维度。当前不制造数值评分；证据指向真实案例和公开行为契约。

### Pricing Basis

[`pricing-card.yaml`](pricing-card.yaml) 声明 ¥0.99 一次性首发验证价，并将首发周期、
付费兑换量、版本变化和支持成本列为复评条件。

### Distribution

目标付费渠道为 LovStudio、WorkBuddy 与 Alipay SkillPay；GitHub 仅承载私有真源。
实际发布、审核和上线状态以各渠道回读为准。
