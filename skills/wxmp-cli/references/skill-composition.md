# Skill Group Composition

## Nearby Skills Inspected

- lov-cli2anything：从授权网站观察证据生成 API 制品。当前任务是本地源码，按其明确路由转交 lov-cli-creator；没有声称新增通用网站适配器。
- lov-cli-creator：上游构建者，交付已经安装并验证的 CLI。本 Skill 仅消费 CLI 命令与 JSON 合同，不在运行时依赖生成器。
- lov-wdb-cli：读取个人微信聊天、联系人与朋友圈，不拥有微探公众号缓存。数据模型与目标不同，不组合。
- lov-skill-creator：创建与校验本地 Skill 外壳，不参与公众号检索执行。
- lov-branding-consistency：仅约束新撰写的说明，源文章、机器字段、链接和法律文本保留原样。

## Atomic Handoffs

上游输出为 agent-harness CLI、命令合同及测试证据；本 Skill 从真实命令取得 JSON 或导出目录，并负责报告业务结果。下游可消费已验证的 Markdown/HTML/JSON/CSV，但文章改写、发布与上传需单独任务授权，不隐式调用。

## Overlap Decisions

沿用 app 的 wcx 引擎；不复制另一个采集器，不包装闭源 GUI 控制，不重建已有 CLI 工坊。

## Composition Decision

Single Skill。查询、采集和导出共享同一账户选择、缓存及命令合同，一次最终验收是可读记录或已回读文件。运行依赖在 SKILL.md 中声明。
