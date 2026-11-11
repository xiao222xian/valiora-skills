# 微信人脉网络分析 · WeChat Network Analysis

![Version](https://img.shields.io/badge/version-0.1.0-CC785C)

把你的微信好友和群聊看成一张“好友—群”网络，用 NetworkX 跑一遍社交网络分析，
在本机生成一份带图表的 HTML 报告：谁是枢纽和桥、哪些人处在核心、关系网能切出哪些结构社区、
哪些关系只挂在一个群上、谁和你的核心圈很近却几乎没单独聊过。

## 安装

```bash
npx skills add lov-wdb-networkx-analysis -g -y
```

付费 Skill：安装与使用需要登录 LovStudio 账号并拥有对应权益。

本地源码安装（开发者）：

```bash
ln -s "$(pwd)" "$HOME/.agents/skills/lov-wdb-networkx-analysis"
```

## 使用

对 Agent 说：

- “分析一下我的微信好友和群聊，出一份网络分析报告。”
- “用 networkx 看看谁是我微信网络里的枢纽和桥。”
- “Analyze my WeChat friends and groups as a network.”

流程：

1. 用 `lov-wdb-cli` 准备好本地微信密钥（已准备可跳过）。
2. `scripts/export_network.py` 经 `lov-wdb-cli` 只读导出 `network.json`（不含微信账号）。
3. `scripts/analyze.py` 跑 17 类分析，`scripts/charts.py` 出 8 张图。
4. Agent 依据结果写主要发现，`scripts/report.py` 生成本地 HTML 报告。

没有微信数据也能试跑：

```bash
python3 scripts/make_demo_network.py --out demo/network.json
python3 scripts/analyze.py --input demo/network.json --work demo/work
python3 scripts/charts.py --work demo/work
python3 scripts/report.py --work demo/work --out demo/report.html
```

## 覆盖的分析

度分布、连通与几度分隔、小世界（对比二部配置模型）、介数 / PageRank / 接近度 / 特征向量、
Burt 结构洞、α/β 核、k 核与洋葱分解、富人俱乐部、Louvain / CNM / 标签传播 / Girvan–Newman、
块模型、群重叠与最小生成树、TrustRank、关节点与单线关系、同配性、Dedensification、谱分析。
逐项对应 NetworkX 示例库，见 [`references/analysis-catalog.md`](references/analysis-catalog.md)。

## 隐私

- 所有计算在本机完成；导出与报告只写入你指定的目录。
- `network.json` 不保存微信账号、数据库路径或表名；报告含好友与群的真实名称，请勿外传。
- 本 Skill 不直接打开微信数据库，全部读取经 `lov-wdb-cli` 的隔离副本。

## 用户 Profile（跨 session）

`skill.yaml` 声明 `user-profile/v1`。可记住的长期偏好：工作目录、报告目录、默认账号，
写入 `skills.lov-wdb-networkx-analysis.records`。详见 [`references/user-profile.md`](references/user-profile.md)。

## 依赖

- 导出：`lov-wdb-cli`（万能微信秘钥）（完成密钥准备），Python 3.9+。
- 分析：Python 3.10+，`networkx>=3.4`、`scipy`、`numpy`、`matplotlib`。

## 可信度卡

- [`skill-card.md`](skill-card.md) / [`skill-card.yaml`](skill-card.yaml)：用途、风险、输出与维度证据。
- [`cases/cases.json`](cases/cases.json)：真实案例（已去除个人信息）。
- [`pricing-card.yaml`](pricing-card.yaml)：定价依据与边界。

## 质量门

```bash
python3 scripts/validate_skill.py .
```

## License

MIT
