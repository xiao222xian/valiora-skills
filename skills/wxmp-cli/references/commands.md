# 微探命令行 · lov-wxmp-cli

版本 0.1.1。复用微探仓库的 `vendor/wcx` 采集引擎，与桌面 app 共用文章缓存。默认输出中文，`--json` 返回稳定结构。

## 安装

在本项目运行：

```bash
bash agent-harness/scripts/install.sh
lov-wxmp-cli doctor
```

需要 Python 3.10+（推荐已有 `uv`）。安装脚本创建独立环境，安装仓库中的 wcx 与 CLI，并在 `~/.local/bin/lov-wxmp-cli` 建立链接；不会替换已有不同命令。将 `~/.local/bin` 加入 PATH，或直接使用 `agent-harness/.venv/bin/lov-wxmp-cli`。移动项目后重新安装。

本地 Skill 入口是 `wxmp-cli-skill/SKILL.md`，调用名称 `/lov-wxmp-cli`。它属于本 app 仓库，随 CLI 一起维护，无单独远程发布。

## 用法

全局参数 `--json`、`--db`、`--project-root` 放在子命令之前。

```bash
lov-wxmp-cli status
lov-wxmp-cli accounts
lov-wxmp-cli articles '公众号名称' --query '关键词' --limit 20
lov-wxmp-cli --json articles '公众号名称' --offset 20 --limit 20
lov-wxmp-cli --json article '上一步返回的 aid'
lov-wxmp-cli export '公众号名称' --out ./articles-export --dry-run
lov-wxmp-cli export '公众号名称' --out ./articles-export
lov-wxmp-cli export '公众号名称' --out ./html-export --body html
lov-wxmp-cli --db ./cache-copy.db accounts
```

索引格式：`--format all|md|json|csv`；正文：`--body md|html|none`。导出默认包含全部缓存文章，可用 `--limit` 限定。正文不存在时保留引擎提供的缺失提示，不伪造正文。JSON 索引保持 wcx 原生格式，包含缓存正文，即使 `--body none` 也如此。

公众号可按精确名称、别名或 JSON 中的 `fakeid` 选择；重名时返回冲突，不能自动选第一项。普通输出隐藏内部选择值，JSON 面向脚本保留源字段。

在线命令：

```bash
lov-wxmp-cli --json search '公众号名称'
lov-wxmp-cli fetch '已缓存公众号名称' --limit 10 --content --dry-run
lov-wxmp-cli fetch '已缓存公众号名称' --limit 10 --content
lov-wxmp-cli fetch 'search 返回的 fakeid' --nickname 'search 返回的 nickname' --limit 10
lov-wxmp-cli fetch '公众号名称' --mode backward --limit 10
lov-wxmp-cli fetch '公众号名称' --mode audit --date 2026-09-01 --limit 20
```

在线搜索与采集使用 app 已保存的登录配置，以及 wcx 原有的跨进程请求保护、暂停与缓存写入机制。单次采集限制 1–500 篇；不支持更改保护间隔。`--mode classify` 复用旧文章分类补全。首次采集需明确使用搜索返回的公众号选择值和名称。`--db` / `LOV_WXMP_DB` 仅选择只读缓存，采集只写默认缓存。

## 状态与输出

- `doctor` 检查项目、实际引擎来源、依赖和已有缓存结构；不发送网络请求。
- `status` 只报告是否保存登录配置，不代表当前会话有效，不显示凭据。
- 本地列表和检索使用 SQLite 只读事务，不新建或迁移数据库。
- 导出拒绝已有目录，独立保存同标题文章，并生成 `manifest.json`，包含文件大小和 SHA-256；最后回读验证。
- `export --dry-run` 与 `fetch --dry-run` 不导出、不采集。真实采集逐篇保存，中断后可继续。
- `search` 不改文章缓存，但 wcx 会更新请求保护状态；它需要联网。
- 未接入扫码窗口、云端同步、GitHub/飞书发布、桌面分析工作区和标签编辑。扫码仍在 app 完成。
- 本地查询与导出已用真实缓存验证；在线成功搜索与采集尚未现场验证，不将 dry-run 当成线上验收。

详见 命令合同 CLI_SPEC.md 和 验证记录 TEST.md。

```bash
agent-harness/.venv/bin/python -m unittest discover -s agent-harness/tests -v
```

真实 E2E 要求当前环境具有已保存正文的 app 缓存。缺失时明确失败，不跳过、不替换成模拟引擎。
