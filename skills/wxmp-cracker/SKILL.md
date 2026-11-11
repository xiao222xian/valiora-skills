---
name: lov-wxmp-cracker
version: "0.4.2"
description: >
  微信公众号文章抓取与导出。自动处理 mp.weixin.qq.com 的登录态获取与续期，
  支持按公众号搜索、抓取文章列表与正文、按日期窗口导出 Markdown / JSON / CSV。
  Trigger when the user wants to crawl a WeChat public account, export recent
  articles, or 提到 "wcx"、"微信公众号"、"公众号文章"、"mp.weixin"、"抓公众号"、
  "crawl wechat official account"、"wxmp"、"最近十天的文章"。
license: MIT
compatibility: >
  Requires Python 3.10+, agent-browser (`npm i -g agent-browser`),
  wcx CLI (`pip install git+https://github.com/lovstudio/wcx.git`), and
  a personal subscription / service account at mp.weixin.qq.com.
  macOS / Linux (agent-browser launches headed Chrome).
dependencies:
  - name: wcx
    check: wcx --help >/dev/null 2>&1
    install: pip install git+https://github.com/lovstudio/wcx.git
  - name: agent-browser
    check: command -v agent-browser >/dev/null 2>&1
    install: npm i -g agent-browser
metadata:
  author: contributors
  version: "0.4.2"
  tags: wechat wxmp wcx crawler agent-browser
  internal: true  # plaintext source — never installed; the encrypted public/SKILL.md is what users get
---

# 公众号神器 · WeChat Archiver

封装 `wcx` CLI，外加"agent-browser → mp.weixin.qq.com → 扫码 → 自动提取 token + 完整 cookie 集（含 HttpOnly）→ wcx login"这条取证链路。用户只需要说"抓下某某号最近的文章"，你负责：

1. 判断当前凭证是否可用（不可用就触发自动刷新）
2. 调度 `wcx search / fetch / export` 完成任务
3. 凭证中途失效时 **自动重抿 + 重试一次**，不打断用户流程

## ⚠️ 硬规则（违反 = 用户报 bug）

1. **绝不直接调 `wcx ...`**。任何对 wcx 的调用都必须走 `wcx_run.py`（哪怕只是 `wcx status` / `wcx --version`），因为 `wcx_run.py` 带了：(a) wcx 版本预检与自动升级，(b) 501 bug 自愈（force-reinstall + 重试），(c) 凭证失效自动重扫。直接调 wcx 会让用户卡在已知 bug 上。
2. **看到 `HTTP Error 501: Not Implemented` 立即升级 wcx**，不要当成"微信 API 限制"或"接口已弃用"。这是 wcx < 0.2.0 的 http→https 301 处理 bug。`wcx_run.py` 会自愈；如果用户绕过了它，告诉用户：`pip install -U --force-reinstall git+https://github.com/lovstudio/wcx.git`，然后重跑。
3. **Windows 用户用 `python` 或 `py`，不是 `python3`**。下面示例里的 `python3` 在 Windows git bash / cmd 里不存在。根据平台自适应：`sys.executable` 最稳，其次 `python`，最后 `python3`。

## 前置条件

一次性：
- 用户有微信公众号后台（个人订阅号/服务号均可）
- `agent-browser` 已安装：`npm i -g agent-browser`
- `wcx` CLI 已安装：`pip install git+https://github.com/lovstudio/wcx.git`（源码见 [lovstudio/wcx](https://github.com/lovstudio/wcx)）

数据目录（统一在 `~/.lovstudio/wxmp-cracker/` 下，与 cwd 无关）：

| 路径 | 内容 |
|------|------|
| `~/.lovstudio/wxmp-cracker/profile/` | agent-browser 持久 Chrome profile（首次扫码后长期复用） |
| `~/.lovstudio/wxmp-cracker/exports/<公众号>/` | `wcx export` 默认产物根目录（一号一目录，重复导出自动 merge） |

可通过 `WXMP_EXPORT_ROOT` 环境变量改根目录。

## Workflow

### Step 1: 判断用户意图

用 `AskUserQuestion` 仅在**真有歧义**时提问。常见三类意图直接推断：

| 用户说法 | 意图 | wcx 命令 |
|---------|------|----------|
| "搜一下 XXX 公众号" / "找叫 XXX 的号" | search | `wcx search <name>` |
| "抓下 XXX 的文章" / "XXX 最近发了啥" | search → fetch | `wcx search ...` 选定 fakeid → `wcx fetch <name-or-fakeid>` |
| "导出 XXX 最近 10 天的文章" | fetch → export --since | `wcx fetch ... --limit 100` → `wcx export ... --since 10d` |
| "导出 XXX 的文章成 markdown" | fetch → export | `wcx fetch ...` → `wcx export ...`（默认输出到 `~/.lovstudio/wxmp-cracker/exports/<公众号>/`，md+json+csv 三件套） |

**关于 `--out`**：默认**不要传** `--out`，让 `wcx_run.py` 注入全局路径 `~/.lovstudio/wxmp-cracker/exports/<公众号>/`。这样多次抓同一个号会幂等 merge，不会散落在各处 cwd。只有用户明确说"导到当前目录"或"导到 ./xxx"时才传 `--out`。

**抓取量的经验值**（多子标题号如量子位、机器之心通常每日 1 msg × 4-5 idx）：
目标 N 天的文章，`--limit` 传 `N × 8` 比较稳（每天最多~6 篇 + 余量）。默认分页 5 msg/page。

### Step 2: 执行，带自动重抿

**永远通过 `wcx_run.py` 调用 wcx**，不要直接调 `wcx`。`wcx_run.py` 会：
- 透传所有参数和输出
- 检测到"登录失效/凭证无效/请先登录"等标志时，自动调 `refresh_token.py` 重新扫码，然后重试一次

```bash
python3 ~/.claude/skills/lov-wxmp-cracker/scripts/wcx_run.py -- search "宝玉"
python3 ~/.claude/skills/lov-wxmp-cracker/scripts/wcx_run.py -- fetch "量子位" --limit 100
python3 ~/.claude/skills/lov-wxmp-cracker/scripts/wcx_run.py -- export "量子位" --since 10d
# ↑ 默认导出到 ~/.lovstudio/wxmp-cracker/exports/量子位/。要落到别处再传 --out。
```

### Step 3: 首次使用 / 主动刷新

如果 `wcx status` 显示未登录，或用户明确要求"重新登录/重抿 token"：

```bash
python3 ~/.claude/skills/lov-wxmp-cracker/scripts/refresh_token.py
```

这会：
1. 关掉现有 agent-browser daemon
2. 以 headed + 持久 profile 打开 `https://mp.weixin.qq.com/`
3. 若未登录 → 弹出 Chrome 窗口，打印"请扫码"提示，轮询等待登录完成（默认 180s）
4. 从 URL `?token=XXXXXX` 提取 token
5. 通过 CDP `cookies get` 拿完整 cookie jar（含 HttpOnly 的 `slave_sid` / `data_ticket`）
6. 调 `wcx login --token ... --cookie ...` 并校验（wcx 自带"凭证有效"测试）

扫码后的 profile 长期有效，下次如果 session 还在，headless 也能续命。

### Step 4: 报告结果

- 搜索：直接把 wcx 输出的表格透传给用户
- 抓取：告知缓存了多少条（`wcx status` 可查），问是否需要导出
- 导出：告知输出目录路径 + 文件数

## CLI Reference

### `refresh_token.py`

| Argument | Default | Description |
|----------|---------|-------------|
| `--timeout` | `180` | 等待扫码的秒数 |
| `--keep-open` | off | 完成后保留浏览器会话 |
| `--headless` | off | 尝试无头模式（仅当 profile session 仍活时有效） |

### `wcx_run.py`

| Argument | Default | Description |
|----------|---------|-------------|
| `--no-retry` | off | 关闭自动重抿（失效直接返回错误） |
| `--refresh-timeout` | `180` | 重抿时的扫码等待秒数 |
| `-- <wcx args>` | 必填 | `--` 后面的一切原样透传给 `wcx` |

### 底层 wcx 命令（由 wcx_run 透传）

- `wcx search <keyword>` — 搜公众号
- `wcx fetch <name|fakeid> [--limit N] [--content]` — 抓文章元数据（+正文）到本地缓存
- `wcx list <name|fakeid> [--limit N]` — 显示缓存里的文章
- `wcx export <name|fakeid> [--since 10d|2w|YYYY-MM-DD] [--format all|md|json|csv] [--articles md|html|none] [--out <dir>]` — 导出
  - `--out` 不传时由 `wcx_run.py` 注入 `~/.lovstudio/wxmp-cracker/exports/<name|fakeid>/`（推荐）
  - `--format` 默认 `all`，一次产出 `index.md / index.json / index.csv`
  - `--since` 支持相对（`10d` / `2w` / `1m`）或绝对（`2026-04-08`）
  - `--articles none` 表示只出索引、不逐篇生成文件
- `wcx status` — 查看登录状态 + 缓存统计

## 常见问题

**问：扫码后 wcx login 报错？**
检查 `wcx_run.py` 的输出。通常是 cookie 提取不全——确认 agent-browser 的 profile 里确实登录成功（URL 带了 `?token=`）。

**问：能不能完全无扫码？**
首次必须扫。之后 profile 持久化，只要会话没被微信风控踢掉，都免扫。

**问：多个微信号怎么办？**
改 profile 目录即可。复制 `refresh_token.py`，把 `PROFILE_DIR` 指向 `~/.lovstudio/wxmp-cracker/profile-<alias>/`；或支持该参数化（未来版本）。

**问：headed Chrome 窗口关了影响吗？**
不影响已保存的凭证。profile 目录在磁盘上。

**问：导出的 index.md 表格被一条巨长文本撑坏了？**
旧版本没把标题里的换行折叠。升级 `wcx` 后会自动 `\s+ → ' '` + 转义 `|`。

**问：按日期过滤后，文章日期不连续有大段缺失？**
曾有分页 bug：`begin` 按子标题数递进，多 idx 账号（量子位、机器之心）会跳过大量消息。
修复版 `begin` 按 page_size（消息数）递进并 aid 去重。如果发现缺口，`wcx fetch` 重抓一次即可。

**问：`wcx fetch --content` 报 `HTTP Error 501: Not Implemented`？**
这是 wcx < 0.2.0 的已知 bug（微信 `http://` 链接 301 到 `https://`，被 curl_cffi 误报成 501）。**不是微信 API 限制，也不是接口弃用。**

排查顺序：
1. 先确认是不是绕过 `wcx_run.py` 直接调了 `wcx` —— 如果是，改成 `python /path/to/wcx_run.py -- fetch ...`，`wcx_run.py` 会自动升级 wcx + 重试。
2. 如果已经走 `wcx_run.py` 还是 501，说明自动升级路径有问题（pip 找不到、用户在 Windows `python3` 不存在等）。让用户手动跑：
   ```bash
   pip install -U --force-reinstall git+https://github.com/lovstudio/wcx.git
   wcx --version   # 必须 ≥ 0.2.0
   ```
3. 验证升级成功后再跑 `wcx_run.py -- fetch <name> --limit N --content` 重抓。缓存里 metadata 已存在，不会重复消耗配额。

## Runtime context (shared)

运行前读取本 Skill 包的 `skill.yaml`，由宿主提供 `skill-runtime/v1` 上下文。字段解析顺序为：当前请求、项目上下文、个人 Preferences、品牌 Profile、通用默认值。

- 只使用 Manifest 声明的字段；Profile 保存公开品牌事实，Preferences 保存个人工作偏好。
- `required: true` 字段缺失时，按 Manifest 的问题配置向用户提出一个聚焦问题；用户明确同意后再保存回答。
- 报错提供可复制的 `context_id`、字段路径与来源，诊断内容避开秘密、完整私人路径和原始配置。

## 通用反馈闭环

用户在 Skill 驱动任务中提出修改意见时，继续当前产物前必须执行：

1. 先判断意见是 `task-specific`（仅本次）还是 `reusable`（可跨任务复用）。
2. `task-specific` 只修改当前任务，不改 Skill。
3. `reusable` 先确定作用域：领域规则先更新对应 canonical Skill；适用于所有 Skill 的规则先更新共享规范。
4. 完成规则更新、版本、lint 与分发核验后，再把修改应用到当前任务。
5. `reusable` 修改会使此前的“确认”“继续”“发吧”失效；完成当前产物修改和回读后必须停下，等待用户下一步指示，不自动进入发布、提交或其他外部写入。
