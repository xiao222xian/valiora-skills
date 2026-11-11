---
name: lov-write-professional-book
description: >
  逐章写完一本书：定大纲、按章写作并保持全书前后一致、通审润色，再用自带脚本排出 PDF 定稿、可编辑 DOCX 与 HTML。Use when the user wants to write a book: 写书、出书、技术书、逐章写作、O'Reilly、mdbook.
license: Commercial
compatibility: >
  Requires mdbook (cargo install mdbook or brew install mdbook),
  pandoc + basictex (brew install pandoc basictex),
  Python 3.9+ with pymupdf, python-docx and pyyaml (pip3 install pymupdf python-docx pyyaml),
  gh CLI (brew install gh). Default fonts are macOS system fonts. Optional: context7 MCP for live docs.
depends_on:
  - lov-branding-consistency
metadata:
  author: contributors
  version: "0.6.0"
  tags:
    - book-writing
    - cjk
    - mdbook
    - pandoc
    - xelatex
    - docx
  internal: true
---

# 写书专家 · Book Writing Expert

以 GitHub repo 为单一数据源，逐章写作完整书籍。通过「全书压缩摘要 + 当前章全文」策略解决上下文窗口限制。

## Triggers

### Activate when

- 用户想写一本完整的书（技术书、教程、专著、教材、白皮书），或把系列内容组织成书
- 用户提到写书、出书、逐章写作、O'Reilly 风格、mdBook
- 用户要把本 Skill 写成的书稿排成 PDF 定稿或可编辑的 DOCX 书稿

### Do not activate when

- 只写单篇文章、公众号推文或报告，不是多章书稿
- 只把一个 Markdown 文件转成 PDF 或 DOCX，不涉及书的编章结构

## Repo Structure

每本书是一个独立 GitHub repo，结构如下：

```
book-repo/
├── book.toml              # mdBook config
├── typeset.yaml           # PDF/DOCX 排版配置：书名、署名、编章结构、开本（模板见 templates/typeset.yaml）
├── SUMMARY.md             # mdBook TOC (auto-generated from OUTLINE.md)
├── OUTLINE.md             # 全局大纲 — 每次写作会话必须加载
├── BOOK_SUMMARY.md        # 全书压缩摘要 — 每章≤500字，每次写作加载
├── bibliography.md        # 完整参考文献（BibTeX 风格）
├── glossary.md            # 术语表（中英对照）
├── src/                   # mdBook source
│   ├── SUMMARY.md         # mdBook 目录（从 OUTLINE.md 生成）
│   ├── 00-frontmatter.md  # 前置部分（版权说明、前言），排在目录之后
│   ├── chapter-01/
│   │   ├── README.md      # 章节正文
│   │   ├── section-01.md  # 小节（大章节拆分时用）
│   │   └── refs.md        # 本章参考文献 + 研究笔记
│   ├── chapter-02/
│   │   └── ...
│   ├── appendix-a.md      # 附录（appendix-*.md）
│   └── references.md      # 全书参考文献
├── references/            # 预置参考文献库
├── assets/images/         # 图片、图表
├── build/                 # PDF/DOCX 中间文件（gitignore）
├── scripts/               # mdBook 构建脚本（PDF/DOCX 用 Skill 自带脚本）
└── .github/workflows/     # GitHub Actions 自动构建
```

## Workflow

The complete 5-phase workflow lives in `references/workflow.md`. Read it before starting a book.

**Phase summary:**

1. **Plan** — Collect book info → OUTLINE.md → repo skeleton → initial commit
2. **Research** — WebSearch + context7 → refs.md per chapter
3. **Write** — One chapter per session, load OUTLINE + BOOK_SUMMARY + refs + glossary
4. **Review** — Consistency, terms, cross-references, polish
5. **Build** — mdBook → HTML | Skill 脚本：pandoc → LaTeX 后处理 → xelatex 出 PDF | pandoc → python-docx 后处理出 DOCX（可编辑书稿，默认同时交付）

## 交付物（MANDATORY）

成书默认同时交付三种格式，缺一不算完成：

| 格式 | 用途 | 构建 |
|------|------|------|
| PDF | 排好版的定稿，供阅读、打印、评审 | `python3 "$SKILL_DIR/scripts/build-pdf.py" --book . -o 书名.pdf` |
| DOCX | 可编辑书稿，供作者修改、交出版社或继续排版 | `python3 "$SKILL_DIR/scripts/build-docx.py" --book . -o 书名.docx` |
| HTML | 在线阅读站点（用户不需要时可省略） | `bash scripts/build-html.sh` |

`$SKILL_DIR` 是本 Skill 目录（本 `SKILL.md` 所在目录）。新书只需源稿加书根目录的 `typeset.yaml`（复制 `templates/typeset.yaml` 填写），不要复制或重写构建脚本；`scripts/table-widths.py` 重设表格列宽，`scripts/pdfcheck.py` 做版面自检。排版要点、DOCX 要点与验收流程见 `references/workflow.md` Phase 5，构建或排查版面前读完。

DOCX 规范（从同一份 Markdown 源生成，内容必须与 PDF 一致）：

- 用 Pandoc 生成，配 `reference.docx` 定样式：正文宋体五号（10.5pt）、首行缩进 2 字、1.5 倍行距；章、节、小节标题用黑体并依次递减字号；章标题前分页；
- 表格为三线表、小五号字，表题在表上；图片按版心宽度插入，图题在图下；
- 封面图单独成页，其后为扉页（书名、副书名、署名、日期）、Word 目录域（打开后更新域即可生成页码）、前置部分（版权说明、前言），顺序与 PDF 相同；
- 源稿中为 PDF 写的 LaTeX 片段（如 `\newline{}`、`\mbox{}`、分页命令）在 DOCX 中改成等价写法或删除，不能以原始代码留在正文；
- 页脚放页码；品牌、水印、AI 生成标识等与同书 PDF 保持一致；
- 回读校验：章、节、表、图的数量与 PDF 一致，正文无残留 LaTeX 命令、无 `{=latex}`、无 Markdown 符号外露。

## Context Window Strategy (MANDATORY)

每次写作新章节时，MUST 加载以下文件：

1. `OUTLINE.md` — 全局大纲（理解全书结构）
2. `BOOK_SUMMARY.md` — 全书压缩摘要（理解已写内容）
3. `src/chapter-xx/refs.md` — 当前章参考文献（如有）
4. `glossary.md` — 术语表（保持术语一致）

**不要加载其他章节全文** — 这是上下文窗口管理的关键。

## Writing Style

- 语言：中文正文，代码/术语保留英文原文
- 风格：默认 O'Reilly 实战派（概念 → 代码 → 最佳实践 → 陷阱），可按用户要求调整
- 每章开头用一个实际问题或场景引入
- 每章末尾加 "本章小结" + "延伸阅读"
- 完成后更新 BOOK_SUMMARY.md（≤500 字）+ glossary.md

## Dependencies

```bash
cargo install mdbook    # or: brew install mdbook
brew install pandoc basictex
pip3 install pymupdf python-docx pyyaml
brew install gh
```

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
