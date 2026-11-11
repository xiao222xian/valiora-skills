# Skill Card — 微信人脉网络分析（lov-wdb-networkx-analysis）

本卡与 `skill-card.yaml` 对应，是发布记录，不是实现笔记。

## Description

把本地微信好友与群聊转成“好友—群”二部网络，参照 NetworkX 示例库跑 17 类社交网络分析，
在本机生成带 8 张图表的 HTML 报告，指出枢纽、桥、核心圈、结构社区与单线关系。

## Owner

WeChat Network Analysis Maintainers；通过仓库 issue 联系。

## License / Terms

MIT：允许使用、修改和分发，保留版权与许可声明。付费渠道的访问权益按 LovStudio 条款执行。

## Use Case

- 受众：想从结构上看清自己微信人脉的个人用户、社群运营者与研究者。
- 输入：本机微信 4.x 数据（经 lov-wdb-cli 导出），或符合 wdb-network/v1 的 `network.json`。
- 任务：只读导出 → 17 类网络分析 → 图表 → 由 Agent 依据指标撰写主要发现 → 本地报告。

## Deployment Geography

全球可用；在用户本机运行，导出面向 macOS 上的微信 4.x 本地数据。

## Requirements / Dependencies

- 密钥由 `lov-wdb-cli` 准备，本 Skill 不处理密钥。
- 导出：Python 3.9+；分析：Python 3.10+，networkx>=3.4、scipy、numpy、matplotlib。
- 声明依赖：`lov-branding-consistency`（主要发现属于作者型文本）。

## Known Risks and Mitigations

| 风险 | 缓解 |
| --- | --- |
| 报告含他人真实名称，被转发会泄露隐私 | 只在本机生成；导出不含账号、路径、表名；禁止未经用户决定的上传与发布 |
| 把结构指标误读为亲疏或人品判断 | 每条发现落到具体指标；社区只作结构描述；注明投影聚集系数偏高、特征向量局部化、机器人账号等偏差 |
| 大网络上个别算法耗时过长 | 抽样介数与距离；结构洞向量化；SNAP 默认跳过可限时；单项失败不阻断 |

## References

- [Machine-readable card](skill-card.yaml)
- [Primary Skill instructions](SKILL.md)
- [分析目录与 NetworkX 示例覆盖](references/analysis-catalog.md)
- [输入格式](references/network-schema.md)

## Skill Output

- 类型：本地 HTML 报告；`results.json`、`charts.json`。
- 参数：`--cap`、`--samples`、`--inner`、`--series`、`--snap-timeout`。
- 验收：errors 为空或已说明；wxid、路径、表名计数为 0；浏览器中章节与图表可读。

## Skill Version

0.1.0

## Ethical Considerations

只分析用户本人的数据；不推测动机、情感或人品；不公开含第三方名称的报告；导出与计算全部在本机完成。

## LovStudio Evidence

### User Cases

[`cases/cases.json`](cases/cases.json)：万人通讯录的真实分析（8,663 位好友、2,944 个群），只保留汇总数字。

### Dimension Map

| 维度 | 证据 |
| --- | --- |
| 分析覆盖度 | 17 类分析覆盖 NetworkX 示例库中 24 个相关示例，不适用项逐项说明 |
| 正确性与可复现 | 泛化脚本与探索版在 10 个关键指标上完全一致；Burt 实现与 networkx 误差 < 1e-15 |
| 运行效率 | 导出 135 秒，分析约 262 秒；结构洞从每节点约 5 秒降到全图 1.9 秒 |
| 隐私边界 | 导出、结果与报告中 wxid、路径、表名计数均为 0 |

### Pricing Basis

付费 268 Credits，依据见 [`pricing-card.yaml`](pricing-card.yaml)。

### Distribution

| 渠道 | 类型 | 状态 |
| --- | --- | --- |
| lovstudio | 付费 | 准备中 |
| workbuddy | 付费 | 未发布 |
| skillpay | 付费 | 未发布 |
| github | 源码仓库 | 未发布 |
