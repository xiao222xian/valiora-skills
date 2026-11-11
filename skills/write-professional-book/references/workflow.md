# tech-book — Complete 5-Phase Workflow

**You MUST follow these steps in order. Each major phase is a separate conversation session.**

---

## Phase 1: Book Planning (首次调用)

Use `AskUserQuestion` 收集以下信息：

1. **书名 + 副标题**
2. **目标读者**（初学者 / 中级 / 高级 / 混合）
3. **核心主题**（用户描述想写什么）
4. **预期章节数**（推荐 8-15 章）
5. **特殊要求**（是否需要代码示例 repo、是否需要习题等）

然后执行：

1. 用 `gh repo create` 创建 GitHub repo（private by default）
2. 生成 `OUTLINE.md`：
   - 每章标题 + 3-5 行内容摘要
   - 标注章节间依赖关系
   - 标注每章预估字数（中文 5000-8000 字/章为宜）
3. 生成 `book.toml`（mdBook 配置）
4. 生成空的目录结构（所有 chapter-xx/ 文件夹 + 空 README.md）
5. 生成 `references/core-papers.md`：用 WebSearch 搜索该领域核心论文/文档，整理初始参考文献库
6. 生成 `BOOK_SUMMARY.md`（初始为每章一行 placeholder）
7. 复制 Skill 的 `templates/typeset.yaml` 到书根目录，填好书名、副书名、署名、日期与编章结构（PDF、DOCX 构建共用，见 Phase 5）；生成 mdBook 用的 `scripts/build-html.sh` 与 `scripts/sync-summary.sh`。PDF 与 DOCX 直接调用 Skill 自带的 `scripts/`，不在书里另写构建脚本
8. 初始 commit + push
9. 生成 `README.md`（遵循 better-readme 规范）：
   - 顶部 cover image（用 image-gen skill 生成，保存到 `docs/images/cover.png`）
   - `<h1 align="center">` 格式标题（书名 + logo）
   - 一行描述 + 目标读者
   - 全书目录（从 OUTLINE.md 提取章节标题，带状态标记）
   - 技术栈 / 构建方式（mdBook + Pandoc）
   - 写作进度表（章节 × 状态矩阵）
   - License 区块
   - 如无 LICENSE 文件，创建 Apache-2.0

**交付物**：一个可 clone 的 repo，包含完整大纲、空章节骨架和专业 README。

---

## Phase 2: Research & References (可选，推荐)

针对每章补充参考文献：

1. 读取 `OUTLINE.md` 确定当前章主题
2. 用 `WebSearch` 搜索：
   - arxiv 最新论文（关键词 + "2024" or "2025" or "2026"）
   - 官方文档 / API reference
   - 高质量博客文章 / 技术演讲
3. 用 `context7` MCP 拉取框架/库的官方文档片段
4. 将搜索结果整理到 `src/chapter-xx/refs.md`：
   ```markdown
   ## 参考文献

   1. [论文标题](https://...) — 作者, 年份. 一句话摘要.
   2. [文档标题](https://...) — 访问日期: YYYY-MM-DD. 相关内容概述.
   ```
5. 更新 `bibliography.md`
6. Commit + push

---

## Phase 3: Chapter Writing (核心循环 — 每章一次会话)

**上下文加载策略（MANDATORY）：**

每次写作新章节时，MUST 加载以下文件：

1. `OUTLINE.md` — 全局大纲（理解全书结构）
2. `BOOK_SUMMARY.md` — 全书压缩摘要（理解已写内容）
3. `src/chapter-xx/refs.md` — 当前章参考文献（如有）
4. `glossary.md` — 术语表（保持术语一致）

**不要加载其他章节全文** — 这是上下文窗口管理的关键。

写作流程：

1. **加载上下文**：读取上述 4 个文件
2. **生成章节大纲**：基于 OUTLINE.md 中该章的描述，展开为小节级大纲，用 `AskUserQuestion` 确认
3. **逐节写作**：
   - 每小节 1000-2000 字
   - 代码示例必须可运行（标注语言和依赖）
   - 引用标注格式：`[^1]`，对应 refs.md 中的条目
   - 术语首次出现时中英对照：`注意力机制（Attention Mechanism）`
4. **章末总结**：每章末尾加 "本章小结" + "延伸阅读"
5. **更新 BOOK_SUMMARY.md**：为刚完成的章节写 ≤500 字压缩摘要
6. **更新 glossary.md**：添加本章新术语
7. Commit + push

**写作风格指南：**

- 语言：中文正文，代码/术语保留英文原文
- 风格：O'Reilly 实战派 — 概念解释 → 代码示例 → 最佳实践 → 常见陷阱
- 每章开头用一个实际问题或场景引入
- 避免纯理论堆砌，每个概念必须有代码或图示
- 段落简短，多用列表和代码块
- 中文排版：中英文之间加空格，数字与中文之间加空格

---

## Phase 4: Review & Polish (每几章做一次)

1. 加载 `BOOK_SUMMARY.md` 检查全书一致性
2. 检查术语一致性（`glossary.md` vs 正文用法）
3. 检查引用完整性（所有 `[^n]` 都有对应 refs.md 条目）
4. 检查章节间衔接（前一章结尾 → 后一章开头）
5. 输出修订建议，用户确认后批量修改
6. Commit + push

---

## Phase 5: Build & Publish

PDF 与 DOCX 用 Skill 自带的脚本构建（`$SKILL_DIR` 为本 Skill 目录，即 `SKILL.md` 所在目录）。新书只需提供源稿和一份 `typeset.yaml`，不要复制或重写构建脚本；本书专用的处理写进 `typeset.yaml` 的 `pdf.*` 配置或 `pdf.extra_header`，发现可复用的规则再回写 Skill 的脚本与本节。

### 5.1 准备

- 依赖：pandoc ≥ 3、xelatex（TeX Live；BasicTeX 按报错用 `sudo tlmgr install` 补包，常缺 `xecjk titlesec mdframed zref needspace newunicodechar placeins xurl eso-pic ragged2e`）、Python 3.9+ 与 `pip3 install pymupdf python-docx pyyaml`。默认字体均为 macOS 自带。
- 配置：书根目录的 `typeset.yaml`，从 `$SKILL_DIR/templates/typeset.yaml` 复制。必填 `title`；其余（副书名、署名、日期、封面、编、章、附录、参考文献、开本、字体、配色、断行例外）都有默认值，模板里逐项注释。
- 源稿约定（脚本依赖这些写法）：
  - 前置部分 `src/00-*.md`；章 `src/chapter-NN/README.md`，大章可拆出 `section-*.md` 接在后面；附录 `src/appendix-*.md`；参考文献 `src/references.md`。图片用相对源稿的路径。
  - 一级标题是章题，章题里用“：”或全角空格分出主副题，PDF 在此处换行。
  - 表题独立成段写在表格正上方（`表 3-1　标题`），构建时绑成表格标题；表注以“资料来源：”“注：”“说明：”开头，紧跟表后，随表排。
  - 每章末节用“延伸阅读”（可在配置里改），它是章末短页回收的锚点，并改为小字左对齐。
  - 为 PDF 写的 LaTeX 片段只用 `` `\newline{}`{=latex} ``、`` `\mbox{…}`{=latex} ``、`` `\hskip …`{=latex} ``、`` `\rule…`{=latex} ``、`` `\nopagebreak…`{=latex} `` 和含 `\clearpage` 的 `{=latex}` 块；DOCX 构建会改写这些片段，遇到别的片段直接报错。
  - 引号写中文弯引号“”‘’，不要写直引号。

### 5.2 命令

```bash
SKILL_DIR=/path/to/lov-write-professional-book   # 本 Skill 目录（SKILL.md 所在目录）

# 改表后先重设列宽（直接改写源稿的分隔行，幂等）
python3 "$SKILL_DIR/scripts/table-widths.py" --book . src/chapter-*/README.md src/appendix-*.md

# PDF（多遍构建，含章末短页回收；327 页的书两遍约 2 分钟）
python3 "$SKILL_DIR/scripts/build-pdf.py" --book . -o "书名-YYYY-MM-DD-v0.1.pdf"

# DOCX 可编辑书稿（与 PDF 同源、同编排，默认同时交付）
python3 "$SKILL_DIR/scripts/build-docx.py" --book . -o "书名-YYYY-MM-DD-v0.1.docx"

# 版面自检
python3 "$SKILL_DIR/scripts/pdfcheck.py" "书名-YYYY-MM-DD-v0.1.pdf" --book .

# HTML（mdBook）
bash scripts/build-html.sh
```

中间文件写在 `build/`（`book.md`、`book.tex`、`latex-out/`、`book-docx.md`、`reference.docx`、`book-raw.docx`），加进 `.gitignore`。`build-pdf.py` 每一遍都打印“缺字、超宽、浮动体过大、页面溢出、章末短页”，交付前必须全为 0（章末短页由脚本回收，回收无效的章会列出，需改稿或调整图表位置）。

### 5.3 PDF 排版要点

脚本已实现以下规则，改脚本、写 `extra_header` 或排查版面问题时按此理解；它们来自《人工智能与政府治理》七轮逐页验收。

1. **两步构建**：pandoc 只生成 `.tex`，由 `build-pdf.py` 后处理后再用 xelatex 跑三遍。pandoc 用 `-f markdown-smart`；**不传 `lang`**，否则会加载 babel，接管中文标点和“目录”标题（模板里直接把 `\contentsname` 设为“目录”）。
2. **引号与省略号还原**：pandoc 会把弯引号写成 ``` ``…'' ```、把“……”写成 `\ldots\ldots`，xeCJK 看不到中文标点，引号变成西文窄引号、省略号不居中。后处理在 `\begin{document}` 之后还原为 Unicode，并去掉 pandoc 在相邻引号之间插入的 `\,`；单引号在内含汉字或前面是中文标点时还原为‘’。只含西文的“…”在预处理时改用 `\bookldq`/`\bookrdq`，保持西文引号。
3. **xeCJK 引号字符类与相邻引号间距**：把 U+2018/U+201C 声明为 `FullLeft`、U+2019/U+201D 声明为 `FullRight`，宽度 1em；宋体弯引号字形窄，默认挤压后相邻引号会贴在一起，用 `\xeCJKsetkern` 留出可见间距（”“、”‘、’“、’‘ 0.3em，’”、“‘ 0.12em，”与？！之间 0.1em）。连接号 U+2013 按西文、省略号 U+2026 按中文字体排。
4. **表格**：一律小一号字（`\small`），按估算行高（汉字 1em、西文 0.5em，乘 1.15 的禁则损耗，除以 `\real{}` 换算的列宽）决定排法：
   - 估算总高不超过 `float_max`（默认约为一页表格行数的 76%，16 开约 30 行）且有表题的矮表，改为浮动体整表排，放不下时移到下页顶部，后文回填，不留大片空白；
   - 长表保留 longtable 跨页：首两行、末两行都较矮时才绑定（高行单独排在页底不算孤行），续页表头上加“表 X-Y（续）”；表前按“表题 + 表头 + 首块”的估算高度用 `\Needspace` 预留，表前紧邻标题或加粗引导语时，预留放到标题链之前；
   - 无表题的矮表（表单）不浮动、整表不拆；必须紧跟说明段的有题表列入 `nofloat_tables`，按长表处理；
   - 表注并入浮动体或长表末页表脚；`keep_after_table` 列出的表后加粗行不与表尾分页。
5. **列宽用折行模拟**：`table-widths.py` 把分隔行写满 72 个破折号，使 pandoc 总按比例设列宽。保底宽度取“最长不可断西文串 + 2”和表头四字片段，短列给足内容宽度，长列按平均内容长度分配剩余；再按真实版心宽与表格字号模拟每格折行，在列间挪动 1—6 个破折号，直到末行只剩一个汉字的格子不再减少。表单类表格在表前（或表题前）写 `<!-- widths: fixed -->`，手工设宽。
6. **段末与单元格末尾禁断**：段落末尾 2—3 个汉字（单元格和短行末尾 2 个汉字）之间插 `\xeCJKnobreak{}`，末行不会只剩一个字。**不要用有限的 `\parfillskip`** 控制末行长度：它只规定末行最短多长，字数不够时 TeX 靠拉开字距去凑，排出明显变松的行；第三轮试过、第四轮撤回，同轮加入了 `pdfcheck.py` 的字距检查。
7. **数字量词、条号、机关代字禁断**：`第~N`、数字与量词（章节编条款项届次批期号版年月日页个家名所人种类部份张件万亿余多级岁）、`附录~A`、`GB/T~`、`表~3-1` 用不可断空格；“第十二条”“第（三）项”“共五章”“十五五”内部禁断（超过 4 字的条号改为 `\penalty3000` 高代价可断）；发文机关代字（国发、沪府办发、工信厅信发函）内部禁断，与“〔”之间加 `\penalty1000`，“〕”与号数之间 `\penalty4000`（高代价但可断）；书名号内 2—4 字的短名禁断；西文首字母缩写与姓（`J.~Smith`）、`nobreak_terms` 列出的型号、韩文词装盒。表格里只保护 4 字以内的代字，单元格分句末两字禁断，单元格以开引号、书名号、括号起首时左移半字与行首对齐。**窄表格列放不下这些禁断时，放宽该列（改 `table-widths.py` 结果或手工设宽），不要撤掉禁断规则。**
8. **标题**：章题在“：”或第一个全角空格处换行（附录在全角空格处），节标题超过一行时在“：”后换行；标题编号紧接左引号时去掉空格，书签与目录里补回；二、三级标题前预留 6、5 行，节标题紧跟小节标题时一次预留 8 行，独立成段的加粗引导语至少带两行正文；`\clubpenalty`、`\widowpenalty` 设 10000。超长章题需要额外断点时，在 `extra_header` 里重定义 `\booksplittitle`。
9. **章末短页多遍回收**：每遍渲染后读 `.aux` 里的章首、章末标签，用 PyMuPDF 数章末页的正文行数；章末页只剩 5 行以内、且不是本章唯一一页时，在本章 `squeeze_anchor` 节（默认“延伸阅读”，找不到时取最后一个二级标题）起始处插 `\enlargethispage{-N\baselineskip}`，把前页缩短 N 行（首次 7−行数，此后每遍加 2，上限 10），最多渲染 5 遍；缩到上限仍无效的章撤回缩行并列出，交人工处理。
10. **其他**：“延伸阅读”、参考文献改为小字左对齐并禁止连字符；网址转为链接、可任意处断行（`xurl`）；DOI、ECLI 与斜杠长编号加断点；`plus_terms` 列出的“人工智能+”“互联网+”的“+”紧贴前字、书签保留“+”；☐☑★○✓◆、罗马数字、带圈数字和韩文指定回退字体；封面铺满第一页，编扉页进目录、无页码；目录只列编与章，书签到节。

### 5.4 DOCX 要点

1. **同源同编排**：`build-docx.py` 与 `build-pdf.py` 共用 `booklib.py` 的配置读取、源稿顺序、图片路径与表题绑定，DOCX 的章、节、表、图与 PDF 一一对应。
2. **改写 LaTeX 片段**：含 `\clearpage` 的 `{=latex}` 块改成 Word 分页符，其余块删除；行内 `\newline` 改成换行、`\hskip` 改成全角空格、`\mbox{…}` 去壳、`\rule` 与 `\nopagebreak` 删除；遇到没见过的片段直接报错，不让原始代码留在正文。插图统一 `{width=100%}`。
3. **样式**：reference.docx 由 pandoc 默认模板加开本、页边距生成；python-docx 后处理正文宋体五号、首行缩进 2 字、1.5 倍行距，章题黑体三号居中、章前分页，节、小节黑体递减；编标题自定义样式“编标题”（大纲级别 1，进目录）；三线表（顶底 1.5 磅、表头下 0.75 磅、无竖线）、小五号字、表头行跨页重复；图宽不超过版心、图高不超过版心 82%；图题在图下、表题在表上。
4. **按 OOXML 元素顺序插入节点**：`pPr`、`sectPr`、`tblPr`、`tcPr` 的子元素有固定顺序（如 `pPr` 里 `pStyle` → `keepNext` → … → `spacing` → `ind` → … → `jc` → `outlineLvl` → … → `sectPr`）。直接 `append` 时 python-docx 和 LibreOffice 照常打开，Word 却提示“内容不可读”。一律用脚本里的 `put()` 按 `ORDER` 表插入，同名旧元素先删除。
5. **封面单独成节**：封面图所在段落带自己的 `sectPr`（页边距 0），图按页面等比铺满；正文节恢复版心页边距，页码从 1 起，页脚居中放 `PAGE` 域；封面节页脚断开链接，不显示页码。
6. **目录用域**：插入 `TOC \o "1-1" \t "编标题,1" \h \z \u` 域（`w:dirty="true"`），并在 settings 里设 `updateFields`，Word 打开时提示更新域即生成带页码的目录；不要用 pandoc `--toc` 生成静态目录。
7. **文档属性**：书名、副书名、署名、关键词写进 core properties，清空最后修改人与备注。
8. **只作用于 PDF 的配置**：`pdf.extra_header`、`pdf.backmatter` 不进 DOCX；书末页等需要两种格式都出现的内容写成 Markdown 放进源稿。

### 5.5 验收

1. **构建日志**：缺字、超宽（>3pt）、浮动体过大、页面溢出全为 0；章末短页为 0 或已人工处理。
2. **pdfcheck 自查**：`pdfcheck.py` 列出字距明显拉开的行、单字成行、页底留白超过 22% 的页；逐条看对应页，属于问题的回到规则或源稿修，章末页、编扉页、浮动体前的合理留白记为通过。
3. **多代理逐页验收**（宿主与用户允许子代理时）：把 PDF 按页段分给多个代理（如 6 个代理各 50—60 页），每个代理把页面渲染成图片逐页看，按同一张清单报问题：单字成行与孤行、标题孤立在页底、表格跨页与续表标识、表注是否随表、列宽造成的单字折行、引号与标点间距、编号文号与量词被拆开、图题表题位置、页底大片空白、书签与目录。主代理去重归类，把问题变成规则改进脚本、配置或源稿（不要手改 `book.tex`），重建后复查受影响的页，直到一轮无新问题。第一本书用了七轮。
4. **DOCX 回读**：用 python-docx 统计章、节、表、图数量与 PDF 一致；全文搜索 `\命令`、`{=latex}`、`**` 等残留；在 Word 中打开不报“内容不可读”，更新域后目录有页码。
5. **交付**：PDF 与 DOCX 同名不同扩展名（`书名-YYYY-MM-DD-v0.1`），放书根目录；页数、文件大小与回读结果写进交付说明。

## BOOK_SUMMARY.md Format

这是上下文窗口管理的核心文件。每章完成后必须更新。

```markdown
# Book Summary (Auto-maintained — DO NOT edit manually except after chapter completion)

## Chapter 1: [标题]
Status: ✅ Done | 📝 Draft | ⬜ Not started
Word count: ~5000
Key points:
- 核心观点1（一句话）
- 核心观点2（一句话）
- 核心观点3（一句话）
Cross-references: Links to Chapter 3, 5
New terms: 术语A, 术语B

## Chapter 2: [标题]
Status: ⬜ Not started
...
```

## Data Source Strategy

### 预置参考文献库 (`references/`)

在 Phase 1 创建时初始化，包含：

- `core-papers.md` — 该领域经典论文（用 WebSearch 搜索整理）
- `official-docs.md` — 框架/工具官方文档链接
- `datasets.md` — 常用数据集和 benchmark

### 实时搜索补充

写作每章时，用以下工具补充最新内容：

- `WebSearch` — 搜索 arxiv, blog posts, release notes
- `context7` MCP — 拉取框架/库的最新官方文档
- `WebFetch` — 抓取特定页面内容

所有引用必须标注：
```markdown
[^1]: Author, "Title", URL, 访问日期: YYYY-MM-DD
```

## Tips

- **一次会话只写一章** — 这是设计核心，不要试图在一次会话里写多章
- **BOOK_SUMMARY.md 是续写的桥梁** — 每章完成后立即更新，下次会话依赖它
- **refs.md 先行** — 先整理参考文献，再写正文，质量更高
- **图片用 Mermaid** — 在 Markdown 中用 mermaid 语法画图，mdBook 原生支持
- **代码示例独立可运行** — 读者应该能直接复制运行
