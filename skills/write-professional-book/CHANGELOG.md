# Changelog

All notable changes to this skill are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/)

## [0.6.0] - 2026-10-20

### Added

- PDF 与 DOCX 改由 Skill 自带脚本构建：`scripts/build-pdf.py`、`scripts/build-docx.py`、`scripts/table-widths.py`、`scripts/pdfcheck.py`（公共部分 `scripts/booklib.py`），版式模板 `templates/header.tex`，配置模板 `templates/typeset.yaml`。书名、署名、编章结构、附录、开本、字体与断行例外都读自书根目录的 `typeset.yaml`，新书只需源稿加配置即可出 PDF 与 DOCX。
- 规则沉淀自《人工智能与政府治理》七轮逐页验收。用该书源稿复验：PDF 327 页、书签全同，仅附录扉页“附　录”一处文字抽取不同（字形相同）；DOCX 段落、样式、表格、图片全同。

### Changed

- `references/workflow.md` Phase 5 改为“准备、命令、PDF 排版要点、DOCX 要点、验收”五节，写明：pandoc 弯引号与省略号还原、不传 `lang`；xeCJK 引号字符类与相邻引号间距；表格小字、矮表浮动、长表跨页加续表、按估算行高预留、列宽用折行模拟；段末与单元格末尾禁断、不用有限 `\parfillskip`；数字量词、条号、机关代字禁断与窄表格列放宽；章末短页多遍回收；DOCX 按 OOXML 元素顺序插入节点、封面单独成节、目录用域；`pdfcheck.py` 自查与多代理逐页验收。
- `SKILL.md` 交付命令改为调用 Skill 脚本，Phase 1 不再在书里生成 PDF/DOCX 构建脚本；依赖加入 pymupdf、python-docx、pyyaml。
- 按发布校验整理源目录：`SKILL.md` 去掉非标准 frontmatter 键（`version`、`category`、`tagline`），description 精简到 200 字以内，`When to Use` 改为含不触发条件的 `## Triggers`，`metadata.tags` 改为列表；`src/` 补 README；README 安装命令改为 `npx lovstudio skills add write-professional-book`。

## [0.5.0] - 2026-10-20

### Added

- 交付默认同时提供可编辑的 DOCX 书稿（与 PDF 同源、内容一致），新增 DOCX 样式、LaTeX 片段转换与回读校验规范；构建流程加入 `scripts/build-docx.sh`。

## [0.4.0] - 2026-08-24

### Added

- add the shared feedback-classification and approval-invalidation gate used by every LovStudio Skill

