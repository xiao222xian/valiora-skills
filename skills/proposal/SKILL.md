---
name: lov-proposal
version: "1.1.1"
category: "Business"
tagline: "Business proposal with architecture, budget & PDF / 完整商业提案"
description: >
  Generate complete business proposals for client projects. Takes client
  requirement documents (docx/pdf/md) or verbal descriptions as input,
  outputs a professionally formatted proposal with technical architecture,
  budget, timeline, risk analysis, and team introduction. Automatically
  calls illustrate for images and any2pdf for final PDF delivery.
  Trigger when user mentions "商务方案", "合作评估", "项目评估", "报价方案",
  "proposal", "需求评估", "给客户出方案", or wants to generate a client-facing
  project proposal from requirements.
license: Commercial
compatibility: >
  Pure instruction skill — no scripts. Depends on lov-illustrate
  and lov-any2pdf for the full pipeline.
depends_on:
  - lov-branding-consistency
metadata:
  author: contributors
  version: "1.1.1"
  tags: proposal evaluation budget b2b business
  internal: true  # plaintext source — never installed; the encrypted public/SKILL.md is what users get
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, Agent]
---

# 提案专家 · Proposal Expert

从客户需求文档（或口头描述）到完整商务方案 PDF 的一条龙生成。
基于品牌工作室的真实项目交付经验，结构化输出专业的技术方案+预算+工期评估。

## When to Use

- 收到客户需求文档，需要出一份合作评估/商务方案
- 客户口头描述了需求，需要整理成正式方案
- 需要快速报价和技术可行性评估

## Workflow (MANDATORY)

### Step 1: 获取需求输入

**有文档时：** 读取客户提供的需求文档（.docx/.pdf/.md）。
如果是 .docx，先用 pandoc 转换：

    pandoc --wrap=none input.docx -o /tmp/requirements.md

**无文档时：** 通过对话收集以下信息：

- 客户行业和公司规模
- 核心需求场景（哪些部门/业务需要什么功能）
- 是否有现有系统需要对接
- 预期上线时间和预算区间

### Step 2: 需求分析 & 确认选项

**使用 `AskUserQuestion` 收集方案参数（MANDATORY）：**

```
开始生成商务方案！先确认几个关键参数 👇

━━━ 🏢 方案定位 ━━━
 a) AI 智能化方案  — 以 Agent/大模型为核心，适合知识密集型需求
 b) 全栈开发方案   — Web/App/小程序开发为主，AI 为辅
 c) 数据平台方案   — 数据采集/分析/可视化为核心
 d) 综合方案       — 混合以上多种

━━━ 💰 报价策略 ━━━
 1) 精简报价  — 展示核心能力和效率优势，总价偏低
 2) 标准报价  — 行业正常水平
 3) 重点客户  — 突出服务深度和长期价值

━━━ 📄 品牌信息 ━━━
 默认使用品牌工作室品牌。如需修改请说明。

━━━ 🎨 PDF 风格 ━━━
 调用 any2pdf 时使用的主题（默认 chinese-red）

示例回复："AI方案, 精简报价, 默认品牌, 中国红"
```

### Mapping to Generation

| Choice | Impact |
|--------|--------|
| AI 智能化方案 | 采用 Agent Skills 架构，A/B/C 分层，强调配置>开发 |
| 全栈开发方案 | 传统前后端架构，按模块估价 |
| 数据平台方案 | ETL + 分析引擎 + 可视化，按数据流估价 |
| 精简报价 | 强调 Vibe Coding 效率，单人精英团队，预算 = 传统 1/5~1/10 |
| 标准报价 | 小团队配置（2-3人），预算按人天标准计算 |
| 重点客户 | 加深服务承诺，突出长期合作价值 |

### Step 3: 生成评估报告 Markdown

按以下结构生成方案文档。**所有内容必须基于需求文档的实际场景，禁止虚构需求。**

#### 文档结构（10 章 + 附录）

```
# {项目名称}合作方案

| 项目名称 | xxx |
| 编制单位 | 品牌工作室 |
| 编制日期 | {date} |
| 文档版本 | v1.0 |
| 保密级别 | 商业机密 — 仅限项目相关人员阅览 |

---

## 目录
（bullet list，非自动生成）

## 一、项目背景与目标
### 1.1 背景
  — 客户行业特点、当前痛点
### 1.2 项目目标
  — 3-5 条具体可衡量的目标

## 二、需求分析与分层
### 2.1 需求分层
  — 表格：按实现难度/方式分层（如 A/B/C 层）
### 2.2 关键发现
  — 最有价值的洞察（如"60%需求只需配置即可交付"）

## 三、技术架构
### 3.1 设计原则
  — 3-4 条核心原则
### 3.2 整体架构
  — ASCII 架构图 + 文字说明
### 3.3 与传统方案对比
  — 对比表格，突出效率优势

## 四、实施方案
  — 按分层展开，每层列出场景表格：
  | 场景 | 功能描述 | 技术实现 |

## 五、项目排期
### 5.1 总体时间线
  — 阶段划分 + 里程碑
### 5.2 推进节奏
  — 强调"快打快收"，每周有可交付物

## 六、投资预算
### 6.1 总投资概览
  — 汇总表
### 6.2-6.3 分期明细
  — 一期/二期费用拆解
### 6.4 年度持续费用
  — API/云服务/存储
### 6.5 为什么能这么低（精简报价时必写）
  — Vibe Coding、Agent Skills 架构、无团队开销等

## 七、项目管理与交付
### 7.1 团队组织
### 7.2 推进节奏
### 7.3 交付清单
### 7.4 验收标准

## 八、风险控制
  — 风险+应对 表格

## 九、服务承诺
  — 保密、质量、支持

## 十、关于品牌方
  — 核心能力表格 + 为什么选择品牌方

## 附录：场景清单
  — 全量需求列表，每条标注层级和优先级
```

#### 内容生成规则

1. **需求驱动**：所有场景必须来源于客户文档/描述，不编造需求
2. **预算逻辑**：
   - 精简报价：每个 Agent Skill 3-5天/0.3-0.5万，轻应用 1-3周/1-3万
   - 标准报价：按人天 2000-3000 元计算
   - 基座/共享组件单独计价
3. **工期逻辑**：
   - A 层（纯配置）：每场景 3-7 天
   - B 层（轻应用）：每场景 1-3 周
   - C 层（系统集成）：单独评估
4. **架构图**：使用 ASCII art，不依赖外部工具
5. **对比表**：必须有"传统做法 vs 我们的做法"对比
6. **量化**：尽量给出具体数字而非模糊表述

#### 文件命名

按品牌方命名规范：

    品牌方-{客户名}-{主题slug}-{YYYY-MM-DD}-v0.1.md

示例：`品牌方-一滕-ai-cooperation-evaluation-2026-04-13-v1.0.md`

### Step 4: 自动配图

生成 markdown 后，调用 illustrate skill：

    /lov-illustrate {file_path} --auto --max 8

建议配图位置：
- Hero image（开篇，建筑/行业+AI 融合主题）
- 需求分层金字塔/架构图
- 技术架构可视化
- 传统 vs Agent 对比
- 项目时间线
- 投资回报概念图
- 关于品牌方（官网截图等真实素材）

### Step 5: 自动生成 PDF

配图完成后，调用 any2pdf skill：

    /lov-any2pdf {illustrated_file_path}

默认推荐选项：
- 主题：chinese-red（政企客户）或 warm-academic（科技客户）
- 扉页：AI 生成
- 水印：商业机密
- 封底：品牌方品牌信息

### Step 6: 交付确认

输出：
- markdown 源文件路径
- illustrated 版本路径
- PDF 文件路径
- 总页数和文件大小

## 参考：品牌方品牌信息

以下信息用于"关于品牌方"章节和封底：

| 字段 | 内容 |
|------|------|
| 品牌名 | 品牌工作室 |
| 英文 | Skill Publisher |
| 官网 | example.com |
| 公众号 | 品牌方 |
| 定位 | 独立开发者 + AI 工程化落地 |
| 核心能力 | AI Agent 系统设计、全栈开发、Vibe Coding |
| 版权声明 | © {year} 品牌工作室 example.com |

**如果用户有不同品牌信息，以用户为准。**

## Dependencies

纯指令 skill，无独立脚本。依赖：
- `lov-illustrate` — 自动配图
- `lov-any2pdf` — PDF 生成
- `pandoc` — 文档格式转换（如需解析 .docx）

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
