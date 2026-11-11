# 微探命令行 · Weitan CLI

## Description

读取、检索、采集与导出微信公众号文章，复用微探真实缓存和 wcx 引擎。

## Owner

LovStudio，本 app 仓库维护者。

## License

MIT；文章版权归原作者。

## Use Case

微探用户或 Agent 从本地缓存精确检索文章，导出可继续处理的文件。

## Deployment Geography

本地执行，macOS 已验证，其他平台未验证。

## Requirements

Python 3.10+、微探源码、同仓库 wcx、已安装 lov-wxmp-cli。在线操作使用 app 保存的有效会话；新撰写的说明遵循 lov-branding-consistency。

## Known Risks

同标题文章独立保存，已有目标拒绝覆盖。登录失效和频率保护返回明确失败。凭据不输出，文章不隐式上传。

## References

[使用指令](SKILL.md) · [验证证据](references/validation.md)

## Skill Output

JSON 记录或 Markdown/HTML/JSON/CSV 文件。支持公众号选择、关键词、分页和导出格式，回读文件并核验哈希。

## Skill Version

0.1.1

## Ethical Considerations

只处理有权访问的内容，保留来源，不绕过访问或频率保护。

## User Cases

[cases/cases.json](cases/cases.json) 记录本次真实 app 转换请求；不包含私人文章正文。

## Dimension Map

真实后端、文件完整性、可调用性；证据见 validation，分数未评定。

## Pricing Basis

渠道价格以官网为准，无托管服务承诺；边界见 [pricing-card.yaml](pricing-card.yaml)。

## Distribution

渠道状态以发布记录和官网回读为准。未宣称在线成功采集、云端同步或发布已验证。
