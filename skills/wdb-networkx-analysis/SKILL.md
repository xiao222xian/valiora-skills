---
name: lov-wdb-networkx-analysis
description: >
  微信人脉网络分析：把本地微信好友与群聊转成二部网络，用 NetworkX 跑中心性、社区、核心—边缘、结构洞等分析，生成本地 HTML 报告。Use when: “分析我的微信好友和群”“WeChat network analysis report”。
license: MIT
compatibility: "macOS 本地微信 4.x 数据经 lov-wdb-cli 导出（Python 3.9+）；分析需 Python 3.10+ 与 networkx>=3.4、scipy、numpy、matplotlib。"
depends_on:
  - lov-branding-consistency
metadata:
  author: contributors
  version: "0.1.0"
  card_standard: lovstudio/skill-card/v1
  content_class: authored-prose
  tags:
    - wechat
    - networkx
    - social-network-analysis
    - report
---

# 微信人脉网络分析 · WeChat Network Analysis

把一个人的微信好友和群看成“好友—群”二部网络，参照 NetworkX 示例库跑完度分布、
连通与几度分隔、小世界检验、中心性、结构洞、α/β 核与 k 核、社区与块模型、
群重叠、TrustRank、脆弱点、同配性与谱分析，最后交付一份只在本机打开的 HTML 报告。

## Triggers

### Activate when

- “分析一下我的微信好友和群聊”“出一份微信人脉网络分析报告”。
- “用 networkx 分析我的微信关系网”“看看谁是我微信网络里的枢纽和桥”。
- “Analyze my WeChat friends and group chats as a network” / “WeChat network analysis report”.
- 用户已有 `wdb-network/v1` 格式的 `network.json`，要求出网络分析报告。

### Do not activate when

- 查某天的聊天、某个人的资料或朋友圈：交给 `lov-wdb-cli`。
- 做可交互的关系图谱页面或可视化应用：这不是本 Skill 的交付物。
- 只问 NetworkX 的 API 用法，与用户自己的社交数据无关。
- 要把含真实好友名称的报告公开发布：先停下，说明隐私风险，由用户明确决定。

## Workflow (MANDATORY)

**按顺序执行。**

### Step 0: 解析运行环境与工作目录

1. 使用环境变量 `SKILL_DIR`；未设置时从当前 Skill 上下文解析安装目录。
2. 确认 `scripts/export_network.py`、`analyze.py`、`charts.py`、`report.py` 均存在。
3. 读取 Profile（见下文）：`records.work_dir`、`records.report_dir`、`records.account`。
   工作目录默认 `./wdb-networkx/`，放导出数据与中间结果；它含真实名称，保持私有。
4. 准备分析环境（Python 3.10+）。已有环境能 `import networkx, scipy, numpy, matplotlib`
   就直接用；否则在工作目录建虚拟环境：

```bash
python3 -m venv "$WORK/.venv"
"$WORK/.venv/bin/pip" install "networkx>=3.4" scipy numpy matplotlib
PY="$WORK/.venv/bin/python"
```

### Step 1: 取得网络数据（三选一）

- **本地微信（常规路径）**：需要已安装并完成密钥准备的 `lov-wdb-cli`
  （`wdb_init.py status` 显示 ready）。然后运行：

```bash
python3 "$SKILL_DIR/scripts/export_network.py" --out "$WORK/network.json" [--account ACCOUNT]
```

  导出只调用 `lov-wdb-cli sql`，读的是数据库隔离副本；输出不含微信账号、库路径或表名。
  “本人”账号自动识别为出现在最多群成员名单里的用户（你一定在自己当前所有群里）。
  约 1 万好友、7 GB 数据库时耗时 2–3 分钟。只要结构、不要消息统计时加 `--no-messages`。
- **已有文件**：用户提供符合 `references/network-schema.md` 的 `network.json`。
- **演示**：`python3 "$SKILL_DIR/scripts/make_demo_network.py" --out "$WORK/network.json"`，
  用占位名字生成合成网络，只用于试跑，不得当作用户数据解读。

### Step 2: 运行分析

```bash
"$PY" "$SKILL_DIR/scripts/analyze.py" --input "$WORK/network.json" --work "$WORK/work"
```

- 约 1 万好友、3 千群、3 万条入群关系时约 3–5 分钟，应放后台运行并等待完成通知。
- 常用参数：`--cap 50`（紧密投影的群规模上限）、`--samples 1000`（介数抽样）、
  `--inner 200`（核心圈私聊阈值）、`--series 正则`（比较一组同名系列群的成员重叠）、
  `--snap-timeout 秒`（尝试 SNAP 图摘要；大图通常跑不完，默认跳过）。
- 单项失败或被跳过会写进 `results.json` 的 `errors` / `skipped`，不影响其他分析。

### Step 3: 生成图表

```bash
"$PY" "$SKILL_DIR/scripts/charts.py" --work "$WORK/work"
```

### Step 4: 撰写主要发现（作者型文本）

读取 `$WORK/work/results.json`，按 `references/authorship-integrity.md` 写 5–8 条发现，
保存为 `$WORK/findings.md`（每行以 `- ` 开头，可用 `**加粗**`）。约束：

- 每条都落到 results 里的具体数值；数字与名称原样引用，不改写。
- 只陈述结构事实与可检验的对比，不推测动机、关系好坏或人品。
- 保留反例与不确定：投影网络聚集系数天然偏高，以随机基线比值为准；特征向量中心性
  可能集中在稠密小团；名称疑似机器人的账号会抬高排名；消息统计只覆盖本机记录。
- 结构社区不等于同类人群；代表群只用于辨认。

不写 findings 也可以：`report.py` 会用规则生成保守的数据型发现。

### Step 5: 生成报告并验收

```bash
"$PY" "$SKILL_DIR/scripts/report.py" --work "$WORK/work" --out "$REPORT/微信人脉网络分析.html" [--findings "$WORK/findings.md"]
```

验收：

1. 报告能在浏览器打开，章节、图表与明暗主题正常；`errors` 为空或已在附录说明。
2. 报告与工作目录不含微信账号（`wxid_`）、数据库路径或表名：
   `grep -c -E 'wxid_|db_storage|Msg_[0-9a-f]{32}' report.html` 应为 0。
3. 回答里先给 3–5 条最重要的发现，再说明未运行项与局限。
4. 报告只交付到本机；不上传、不发布、不写进公开仓库。

## Interpretation Rules

- 好友间“隔几层”= 二部图距离 / 2；“同群好友数”= 投影度数（二跳自我网络）。
- 小世界以同度序列随机网络为基线（二部配置模型），不要只报绝对聚集系数。
- “低调的桥”= 介数排名靠前但共同群数排名靠后的人。
- 结构洞用 Burt 约束度与有效规模；脚本以稀疏矩阵实现，与 networkx 逐节点公式一致。
- 详细覆盖表与方法见 `references/analysis-catalog.md`。

## User Profile (cross-session)

`skill.yaml` 声明 `user-profile/v1`。每次运行读取 user、workspace、preferences 与
`skills.lov-wdb-networkx-analysis`。用户明确说出的长期偏好（如固定工作目录、报告目录、
默认账号）用 `scripts/profile_store.py record ... --confirm` 写入 `records.<field>`，
并报告保存路径。不保存密钥、好友名单或任何导出数据。详见 `references/user-profile.md`。

## Skill Group Composition

读取 `references/skill-composition.md`：`lov-wdb-cli` 是可选上游（提供只读导出通道），
本 Skill 负责网络分析与报告；二者通过 `network.json` 交接，不存在隐藏依赖。

## Authorship Integrity

Step 4 属于作者型文本：先按 `references/authorship-integrity.md` 建立证据台账，再写发现；
不编造经历、动机、引语、数字或因果。

## Dependencies

- 导出：`lov-wdb-cli`（已完成密钥准备），Python 3.9+。
- 分析：Python 3.10+，`networkx>=3.4`、`scipy`、`numpy`、`matplotlib`。
- 可选：中文字体（PingFang SC / Noto Sans CJK 等）使图表中文正常显示。
