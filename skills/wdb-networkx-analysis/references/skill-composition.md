# Skill Group Composition

## Nearby Skills Inspected

| Skill | 路由合同 | 分类 | 结论 |
| --- | --- | --- | --- |
| `lov-wdb-cli`（万能微信秘钥） | 准备本地微信密钥，查询聊天、联系人、朋友圈与只读 SQL | upstream atom | 提供只读、隔离副本的数据通道；本 Skill 的导出脚本调用它的 `sql` 命令产出 `network.json` |
| `lov-do-they-love-me` | 把两个人的微信私聊做成有证据的恋爱指数分析与竖版信息图 | optional downstream | 本 Skill 只做全网结构、不做单段关系的内容判断；用户可从报告里挑出某个人，再交给它深挖这一段私聊 |
| `lov-search-chat` | 从本机 Ataru 记忆索引召回过去的 AI 会话 | not composed | 面向 AI 会话记忆，与微信数据无关 |
| `dataviz` / `lov-professional-infographic` | 图表与信息图设计 | optional downstream | 可把报告中的汇总数字再做成对外信息图；需先去除真实名称 |
| `lov-branding-consistency` | 读者可见文本的品牌与语境门禁 | declared dependency | 主要发现属于作者型文本，按规范声明 |

## Atomic Handoffs

```text
lov-wdb-cli（可选上游，已完成密钥准备）
   │  只读 sql 查询（隔离副本）
   ▼
export_network.py → network.json（wdb-network/v1，无账号 ID）
   │
   ▼
analyze.py → results.json / chartdata.json → charts.py → charts.json
   │
   ▼
Agent 撰写 findings.md（可选） → report.py → 本地 HTML 报告
```

- 输入合同：`references/network-schema.md`。没有 `lov-wdb-cli` 时，用户可直接提供同格式文件。
- 最终验收归本 Skill：报告完整、无账号与路径泄露、只在本机交付。

## Overlap Decisions

没有其他 Skill 负责“社交网络结构分析与报告”。与 `lov-wdb-cli` 的边界是：它负责数据访问与
隔离读取，本 Skill 不直接打开任何微信数据库，也不复制它的密钥逻辑。

## Composition Decision

**Single Skill。** 导出、分析、出图、报告服务同一个用户结果，且导出只是对上游 CLI 的薄封装；
拆成 Kit 不带来独立可用的中间产物。`lov-wdb-cli` 保持为可选上游，不写入 `depends_on`，
因为已有 `network.json` 的用户无需它。
