---
name: lov-wxmp-cli
description: >
  微探命令行：读取、检索并导出微探缓存的微信公众号文章，按授权搜索或采集公众号。用户说“用微探查文章”“导出公众号文章”或“search or export WeChat articles”时使用。
license: MIT
compatibility: "macOS, uv and Python 3.10+; includes the matching wcx engine; app cache or login required for article workflows."
depends_on:
  - lov-branding-consistency
metadata:
  author: LovStudio
  version: "0.1.2"
  content_class: deterministic-output
  card_standard: lovstudio/skill-card/v1
  tags:
    - wechat
    - cli
    - article-cache
---

# 微探命令行 · Weitan CLI

把自然语言请求映射到已验证的 `lov-wxmp-cli`，复用微探真实采集和导出引擎。
源文章与 JSON 字段原样保留；只有新撰写的说明遵循品牌表达规范。

## Triggers

### Activate when

- “用微探查一下本地有哪些公众号”“检索某公众号包含关键词的文章”。
- “导出某公众号的缓存文章为 Markdown/HTML/JSON/CSV”。
- “用微探搜索公众号”“采集这个已选定公众号的最新十篇文章”。
- “Use Weitan CLI to search or export WeChat articles.”

### Do not activate when

- 查询个人微信聊天、联系人或朋友圈：属于本地微信数据工具。
- 操作公众号发布、飞书/GitHub 同步、云端授权或扫码窗口：本 CLI 不提供这些命令。
- 要求文章改写、文风分析或创作：本 Skill 输出源文章，不冒充分析工具。
- 未授权账户或流量发现、绕过访问或频率保护。

## Workflow

### 1. Read context and diagnose

每次读取 `skill.yaml` 与共享 Profile：

```bash
python3 "$SKILL_DIR/scripts/profile_store.py" read --skill-id lov-wxmp-cli --pretty
python3 "$SKILL_DIR/scripts/wxmp_cli.py" --json doctor
```

`SKILL_DIR` 是本 Skill 的安装目录。安装包已包含匹配的采集引擎（`runtime/`），无需另行取得 app 源码。需要 uv 与 Python 3.10+，首次运行会安装第三方依赖。

优先级：当前请求、项目上下文、Skill records、共享 preferences、共享 Profile、安全默认值。只持久化用户明确要求跨会话保存的偏好，通过 `scripts/profile_store.py record --skill-id lov-wxmp-cli --path records.KEY --value JSON --confirm` 写入并报告 Profile 路径；不保存推断的路径、账户正文、Cookie、Token。

### 2. Inspect before selecting

```bash
python3 "$SKILL_DIR/scripts/wxmp_cli.py" --json status
python3 "$SKILL_DIR/scripts/wxmp_cli.py" --json accounts
python3 "$SKILL_DIR/scripts/wxmp_cli.py" --json articles '公众号名称' --query '关键词' --limit 20
python3 "$SKILL_DIR/scripts/wxmp_cli.py" --json article 'articles 返回的 aid'
```

全局选项放在命令前。公众号按精确名称、别名或结果中的选择值定位，不猜测身份；重名时让用户选择。仅向用户呈现名称、标题和业务结果，内部字段保留在机器数据中。登录配置存在不等于登录有效。

### 3. Execute the requested workflow

本地导出不需要网络：

```bash
python3 "$SKILL_DIR/scripts/wxmp_cli.py" --json export '公众号名称' --out ./article-export --dry-run
python3 "$SKILL_DIR/scripts/wxmp_cli.py" --json export '公众号名称' --out ./article-export
```

按用户目标选择 `--format all|md|json|csv` 与 `--body md|html|none`。默认导出全部缓存文章；可指定 `--limit`。正文缺失会保留提示。JSON 索引包含原生缓存正文，`--body none` 仅不另写正文文件。
已有目录一律不覆盖，换一个新路径。用户已请求导出时，dry-run 后可直接执行，不重复确认。

仅在用户要求且有目标访问授权时在线搜索和采集：

```bash
python3 "$SKILL_DIR/scripts/wxmp_cli.py" --json search '公众号名称'
python3 "$SKILL_DIR/scripts/wxmp_cli.py" --json fetch '已缓存公众号名称' --limit 10 --content
python3 "$SKILL_DIR/scripts/wxmp_cli.py" --json fetch 'search 返回的 fakeid' --nickname 'search 返回的 nickname' --limit 10
```

首次采集使用真实搜索结果，不自动选模糊匹配的第一项。支持 `--mode forward|backward|audit|classify`；回查可加 `--date YYYY-MM-DD`。采集前可 `--dry-run`；采集只写微探默认缓存。凭据失效时请用户在 app 扫码，不要求用户粘贴凭据，不启用 Computer Use。

### 4. Verify and report

- 检查 JSON `ok` 与退出状态，错误不得报告成功。
- 导出回读 `manifest.json` 与生成文件；完成报告包含实际路径、篇数和格式。
- 采集后重新执行 `articles` 查看保存结果；中断时报告已保存状态，稍后续采，不重置保护。
- 临时不可取得文章列表时报告未完成，不将零条或 dry-run 当作在线成功证据。
- 目前现场验证覆盖真实缓存读取和四种格式导出；在线成功采集仍需当次有效会话验证。
- 不发送、上传或发布源文章，除非用户另行明确要求且有相应工具。

完整命令说明见 [命令参考](references/commands.md)。组合边界见 [Skill composition](references/skill-composition.md)。本 Skill 通过官网交付；文章仍只保存在用户本机。
