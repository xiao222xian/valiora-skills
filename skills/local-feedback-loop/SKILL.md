---
name: local-feedback-loop
description: 在本机记录用户对 AI 交付的明确评价或有证据的反馈推断，跟踪修复验证并查看统计。用于反馈、评分、复盘、删除反馈记录；普通新增需求不触发。
metadata:
  version: "0.1.0"
---

# 本机反馈与改进

先读 [反馈协议](references/protocol.md)。本工具记录证据与处置，不训练模型，不自行修改全局偏好，不自动回扫其他聊天。

脚本真源：`python3 scripts/feedback.py`。
命令在任意工作目录可运行；`--store` 必须放在子命令前，通常使用默认本机账本。

- 明确评价/纠正或重复问题：判定类型与最窄作用域后，执行 `add --project <项目标签> --session <当前聊天ID> --source-id <消息ID，若有> --channel explicit|passive --polarity positive|negative|mixed|neutral --kind praise|approval|dissatisfaction|error|preference|correction --evidence <最小去敏原话> --scope task|skill|reference|root-prompt`。没有消息ID就省略 source-id。参数需正确 shell 引用，切勿把原话拼接为命令代码。
- 被动推断需明确原话依据，`--confidence` 小于 1；不确定时不记。正常需求变更不等于不满。只有用户主动打分时才传 `--rating 1..5`。
- 修复后执行 `update --id <事件ID> --status change-applied --action <实际动作>`；验证后再以 `verified` 回填 `--verification <验证证据>`。不得凭情绪信号扩大修改授权。共享规则或长期偏好必须有用户明确持久化要求。
- 查看：`stats`、`list`、`report`、`verify`。每次操作更新本机 dashboard.html；空库就是空库，禁止伪造用户评价充数。
- 删除：只有用户明确指明要删除哪些记录时，执行 `delete --id <事件ID> --confirm`。这是真实删除，会同步重建当前看板；另存截图或外部备份需要另行处理。
- 历史回扫仅在用户明确要求并限定聊天或时间范围后执行；读取宿主提供的用户消息，先排除注入的 AGENTS、文档和工具输出，不扫描整个主目录。

默认账本与页面：`~/.local/share/valiora-feedback/`。每条记录都是本机私有数据，不上传，不纳入 Git 或管理备份。记录失败时保留错误，不声称已记录。记录成功只需简短说明，不在每次回复重复流程。

修改已有 Skill 可参考资料库中的 skill-optimizer；明确经验入规参考 distill-to-system。它们是待审阅方法，现有授权、测试、提交与发布规则始终有效，不自动执行第三方提交/推送要求。
