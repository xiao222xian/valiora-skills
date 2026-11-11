# 输入格式：wdb-network/v1

`analyze.py` 只读这一种 JSON。`export_network.py` 从本地微信导出它；其他来源也可以
按同样结构生成（例如另一套通讯工具的群成员表）。

```json
{
  "schema": "wdb-network/v1",
  "snapshot": "2026-09-26",
  "history_from": "2025-10-05",
  "has_messages": true,
  "friends": [
    {"name": "显示名", "nick": "昵称（与显示名不同时）", "msg": 132, "sent": 60, "last": 1790000000}
  ],
  "groups": [
    {"name": "群名", "size": 156, "owner_is_me": false, "said": 45, "msg": 12345, "last": 1790000000}
  ],
  "memberships": [[0, 12], [0, 57]]
}
```

## 字段

| 字段 | 含义 |
| --- | --- |
| `friends[].name` | 显示名：备注 > 昵称 > 微信号别名；导出时不保留微信账号 |
| `friends[].msg` / `sent` | 本机记录中的私聊总条数 / 我发出的条数 |
| `friends[].last` | 最近一次会话时间（Unix 秒），没有时为 0 |
| `groups[].size` | 本机记录的群成员总数（含非好友） |
| `groups[].owner_is_me` | 我是否为群主 |
| `groups[].said` / `msg` | 我在群里的发言条数 / 群消息总条数 |
| `memberships` | `[群序号, 好友序号]`，序号对应两个数组的下标 |
| `has_messages` | 为 false 时，依赖私聊条数的分析会被跳过并在报告附录注明 |

## 口径

- 好友：通讯录联系人中排除公众号、服务号、系统账号、已删除联系人和本人。
- 群：本人当前仍在的群。群内非好友成员不作为节点，只计入 `size`。
- 消息统计来自本机保存的聊天记录，起点写在 `history_from`。
- 文件含真实名称，只放在私有工作目录，不提交、不上传。
