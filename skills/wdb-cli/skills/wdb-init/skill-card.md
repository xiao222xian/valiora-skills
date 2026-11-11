# Skill Card — lov-wdb-init

## Description

在 macOS 上为本机微信准备 WDB Pro 管理的 SQLCipher 密钥，支持内存扫描和微信
4.1.10+ 登录期捕获，输出供 `lov-wdb-query` 使用的私有密钥清单。

## Owner

WDB Pro Team；问题反馈地址为
https://github.com/lovstudio/wdb-pro/issues。

## License / Terms

MIT。原生 `wechat-key-scanner` 保留 Apache-2.0 和 MIT 第三方声明，详见
assets/THIRD_PARTY_NOTICES.md。

## Use Case

面向 macOS 微信用户和 Agent 工作流。当本机没有可读取的数据库密钥，或微信
升级后需要重新连接本地数据时使用。

## Deployment Geography

全球，仅 macOS；支持 Apple Silicon 与 Intel。

## Requirements / Dependencies

- macOS 10.15+
- Python 3.9+
- arm64/x86_64 `wechat-key-scanner` 二进制
- 系统自带 `codesign`、`plutil` 与 `cp`

## Known Risks and Mitigations

- 密钥是本地隐私数据：只写私有 0600 文件，不打印密钥值，清理临时副本。
- 微信版本或签名变化导致进程访问失败：提供 doctor 自检和结构化错误码。
- 用户退出微信后忘记重新登录：捕获流程等待登录并恢复原始微信。

## References

- [Machine-readable card](skill-card.yaml)
- [Primary Skill instructions](SKILL.md)

## Skill Output

输出 WDB Pro managed key JSON、账号、数据库数量与密钥文件路径。验证条件为
`status: ready`、数据库数量大于零、输出不含密钥值。

## Skill Version

0.1.0

## Ethical Considerations

仅在用户明确要求的本机数据访问中扫描进程或捕获登录；不修改已安装微信，
不跨设备共享密钥。

## LovStudio Evidence

### User Cases

见 cases/cases.json。当前真实案例记录了微信 4.1.11 环境中无管理密钥时的
诊断结果：scanner 自检通过，系统提示需要登录期捕获。

### Dimension Map

机器可读卡片包含 correctness、effectiveness、efficiency 三个维度和证据；
effectiveness 的完整成功率待真实登录捕获后补充。

### Pricing Basis

本模块随 lov-wdb-cli 付费包分发，不单独计价；边界为密钥获取与诊断，不包含
聊天查询。

### Distribution

付费渠道 lovstudio；无独立免费渠道。
