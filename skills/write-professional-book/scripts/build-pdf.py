#!/usr/bin/env python3
"""拼装全书 Markdown，经 pandoc 生成 LaTeX，后处理引号、断行与表格分页，再用 xelatex 输出 PDF。

书名、署名、编章结构与版式读自书根目录的 typeset.yaml（模板见 templates/typeset.yaml），
版式模板为 templates/header.tex。中间文件写在书根目录的 build/：book.md、book.tex、latex-out/。
构建会多遍运行：发现章末页只剩几行时，缩短该章末节起始页，重排直到没有短页。

用法：python3 build-pdf.py [--book 书根目录] [-o 输出 PDF]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import booklib  # noqa: E402

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(SKILL, "templates", "header.tex")

B = None  # booklib.Book，main() 中设置


def raw(tex):
    return "```{=latex}\n" + tex + "\n```\n"


def tex_escape(s):
    return re.sub(r"([&%$#_{}])", r"\\\1", s)


def part_page(label, title="", image=None, note="", appendix=False):
    """编扉页（或附录扉页）：进目录、无页码；附录扉页之后切换到附录编号。"""
    label, title, note = tex_escape(label), tex_escape(title), tex_escape(note)
    toc = label if appendix or not title else label + "\u3000" + title
    body = ["{\\color{bookaccent}\\rule{72pt}{2pt}}\\\\[9mm]"]
    if title:
        body += ["{\\Large %s}\\\\[7mm]" % label, "{\\Huge\\bfseries %s}\\\\[16mm]" % title]
    else:
        body.append("{\\Huge\\bfseries %s}\\\\[16mm]" % label)
    if image:
        body.append("\\includegraphics[width=\\textwidth]{%s}\\\\[11mm]" % image)
    if note:
        body.append("{\\small\\color{bookfootergray} %s}" % note)
    body[-1] = re.sub(r"\\\\\[\d+mm\]$", "", body[-1])
    return raw("\n".join([
        "\\clearpage", "\\phantomsection", "\\addcontentsline{toc}{part}{%s}" % toc,
        "\\bookcoverpagetrue", "\\thispagestyle{empty}", "\\vspace*{%dmm}" % (18 if image else 28),
        "\\begin{center}"] + body + ["\\end{center}"] + (["\\appendix"] if appendix else []) + [
        "\\clearpage", "\\bookcoverpagefalse"])) + "\n"


# ---------- Markdown 预处理 ----------

CJK = re.compile(r"[\u2e80-\u9fff\uff00-\uffef]")
LATIN = re.compile(r"[A-Za-z]")
URL = re.compile(r"(?<![<(])(https?://[^\s<>（）()，。；、“”\]]+)")
PUSH = re.compile(r"^(## .*?) \{\.push(\d+)\}\s*$")


def latin_quotes(line):
    """引号内含西文字母且不含汉字时，改用西文引号宏（不经 xeCJK 全角处理）。"""
    def rep(m):
        inner = m.group(1)
        if CJK.search(inner) or not LATIN.search(inner):
            return m.group(0)
        return "`\\bookldq{}`{=latex}" + inner + "`\\bookrdq{}`{=latex}"
    return re.sub(r"“([^“”]*)”", rep, line)


def protect_terms(line):
    """pdf.plus_terms 列出的“人工智能+”“互联网+”这类词，“+”不与前字分开、不插中西文间距
    （“文本 + 机器人”这类连接用法保留 xeCJK 默认间距）；ECLI、DOI 与斜杠长编号加断点。"""
    line = re.sub(r"(?<=[\u4e00-\u9fff])＋(?=[\u4e00-\u9fff])", "+", line)
    for term in B.pdf["plus_terms"] or []:
        line = line.replace(term + "+", term + "`\\bookplus{}`{=latex}")
    line = re.sub(r"(?<![=/])ECLI:([A-Z]+):([A-Z]+):(\d{4}):(\d+)",
                  r"ECLI:`\\allowbreak{}`{=latex}\1:`\\allowbreak{}`{=latex}\2:`\\allowbreak{}`{=latex}\3:\4", line)
    line = re.sub(r"(?<![<\w/])(10\.\d{4,})/([\w.\-]+)",
                  r"\1/`\\allowbreak{}`{=latex}\2", line)
    line = re.sub(r"(?<![<\w/:.])([A-Z][A-Z0-9]*(?:/[A-Z0-9]+){2,})",
                  lambda m: m.group(1).replace("/", "/`\\allowbreak{}`{=latex}"), line)
    return line


def link_urls(line):
    def rep(m):
        u = m.group(1).rstrip(".")
        return "<" + u + ">" + m.group(1)[len(u):]
    return URL.sub(rep, line)


def heading_quote_space(line):
    """“6.5 “人在回路””：编号后的空格加上左引号自带的半字空白太宽，去掉空格（书签里再补回）。"""
    return re.sub(r"^(#{2,4} [0-9A-Z][0-9A-Z.]*) (?=[“‘])", r"\1", line)


def heading_name(line):
    """二级标题去掉编号后的文字，如“## D.4　文献导读”→“文献导读”。"""
    return re.sub(r"^## (?:[0-9A-Z][0-9A-Z.]*[\s\u3000]*)?", "", line).strip()


def section_blocks(lines):
    """pdf.ragged_sections 列出的节（如“延伸阅读”）多含不可断的西文长串，两端对齐会拉大间距，
    改为小字左对齐；带 {.pushN} 的节标题（章末短页回收）在标题后把本页缩短 N 行。"""
    ragged = set(B.pdf["ragged_sections"] or [])
    out, inside = [], False
    for l in lines:
        if inside and (re.match(r"^#{1,2} ", l) or l.startswith("```")):
            out += ["```{=latex}", "\\par\\endgroup", "```", ""]
            inside = False
        m = PUSH.match(l)
        head = m.group(1) if m else l
        push = int(m.group(2)) if m else 0
        out.append(head)
        is_ragged = head.startswith("## ") and heading_name(head) in ragged
        if is_ragged or push:
            tex = "\\enlargethispage{-%d\\baselineskip}" % push if push else ""
            if is_ragged:
                tex = "\\begingroup\\raggedright\\small\\hyphenpenalty=10000\\exhyphenpenalty=10000" + tex
                inside = True
            out += ["", "```{=latex}", tex, "```", ""]
    if inside:
        out += ["```{=latex}", "\\par\\endgroup", "```", ""]
    return out


def preprocess(text):
    lines = booklib.bind_table_captions(text.split("\n"))
    out, in_raw = [], False
    for l in lines:
        if l.startswith("```"):
            in_raw = not in_raw
            out.append(l)
            continue
        if in_raw or l.startswith("!["):
            out.append(l)
            continue
        out.append(link_urls(protect_terms(latin_quotes(heading_quote_space(l)))))
    return "\n".join(section_blocks(out))


# ---------- LaTeX 后处理：表格 ----------

TABCOL_PT = 6.0    # \tabcolsep
SLACK = 1.15       # 标点禁则与断行损耗
PAIR_MAX = 10      # 首两行（或末两行）合计不超过此值才绑在一起
HEADING_LINE = re.compile(r"^\\(?:section|subsection|subsubsection|paragraph)\{")
LEAD_LINE = re.compile(r"^\\textbf\{(?:[^{}]|\{\}){1,80}\}\s*$")  # 允许其中含 \xeCJKnobreak{}
NOTE_LINE = re.compile(r"^(资料来源|注|说明)：")


def _row_lines(row, widths):
    """估算一行的高度（行数）：每格按显示宽度除以列宽，取最高的一格。"""
    cells = re.split(r"(?<!\\)&", row)
    # 表单行用 \rule 撑高（约 2.2—2.4em），至少按两行计
    best = 1.6 if "\\rule{0pt}" in row else 1
    for k, cell in enumerate(cells):
        w = widths[k] if k < len(widths) else widths[-1]
        text = cell.replace("[b]", "")
        text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", "", text)
        text = re.sub(r"[{}\\]", "", text)
        n = 0
        for para in re.split(r"\n\s*\n", text):
            em = sum(1.0 if ord(c) > 0x2E80 else 0.5 for c in para.strip())
            n += max(1, -(-em * SLACK // max(w, 1.0)))
        best = max(best, n)
    return best


def _brace_arg(s, k):
    """s[k] 为 “{”，返回与之配对的 “}” 的位置。"""
    depth = 0
    for n in range(k, len(s)):
        if s[n] == "{":
            depth += 1
        elif s[n] == "}":
            depth -= 1
            if depth == 0:
                return n
    raise ValueError("unbalanced braces")


def _parse_longtable(block):
    """拆出 pandoc longtable 的列格式、表题、表头和表体。"""
    k = block.index("{", len("\\begin{longtable}[]"))
    e = _brace_arg(block, k)
    spec = block[k + 1:e]
    rest = block[e + 1:].lstrip("\n")
    caption = ""
    if rest.startswith("\\caption{"):
        c1 = _brace_arg(rest, len("\\caption"))
        caption = rest[len("\\caption{"):c1]
        rest = rest[c1 + 1:]
    head = rest.split("\\toprule\\noalign{}\n", 1)[1].split("\\midrule\\noalign{}\n", 1)[0].rstrip("\n")
    rows = rest.split("\\endlastfoot\n", 1)[1].rsplit("\n\\end{longtable}", 1)[0]
    reals = [float(x) for x in re.findall(r"\\real\{([0-9.]+)\}", spec)]
    ncols = len(reals) or len(re.findall(r"[lcr]", re.sub(r"@\{\}", "", spec)))
    return spec, caption, head, rows, reals, ncols


def process_tables(tex):
    """按估算高度处理表格（表格一律小一号字）：
    1. 矮表改为浮动体（table + tabular），放不下时整表移到下页顶部，后文回填，不留大片空白；
    2. 高表保留 longtable 跨页：首两行、末两行都较矮时才绑定，续页表头上加“表 X-Y（续）”；
       表前（或表前紧邻的标题链前）按“表题 + 表头 + 首块”实际高度预留；
    3. 表后紧跟的“资料来源：”“注：”随表排（浮动体内或末页表脚）。"""
    line_pt, font_pt = B.text_w, B.small_pt
    page_rows = B.text_h / (font_pt * 1.2 * 1.28)
    float_max = B.pdf["float_max"] or round(page_rows * 0.76)
    whole_max = round(page_rows * 0.4)
    cpl = int(line_pt / B.body_pt)
    nofloat = tuple(p for x in B.pdf["nofloat_tables"] or [] for p in (x, x.replace(" ", "~")))
    lines = tex.split("\n")
    out = []
    i = 0
    while i < len(lines):
        if not lines[i].startswith("\\begin{longtable}"):
            out.append(lines[i])
            i += 1
            continue
        j = i
        while not lines[j].startswith("\\end{longtable}"):
            j += 1
        block = "\n".join(lines[i:j + 1])
        k = j + 1
        while k < len(lines) and not lines[k].strip():
            k += 1
        note = lines[k] if k < len(lines) and NOTE_LINE.match(lines[k]) else ""
        spec, caption, head, rows, reals, ncols = _parse_longtable(block)
        if reals:
            avail = line_pt - 2 * (len(reals) - 1) * TABCOL_PT
            widths = [r * avail / font_pt - 0.3 for r in reals]
        else:
            widths = [line_pt / font_pt / max(ncols, 1)] * max(ncols, 1)
        rl = rows.split("\n")
        ends = [n for n, l in enumerate(rl) if re.search(r"\\\\\*?\s*$", l)
                and ("&" in l or not l.lstrip().startswith("\\"))]
        starts = [0] + [e + 1 for e in ends[:-1]]
        h = [_row_lines("\n".join(rl[a:b + 1]), widths) for a, b in zip(starts, ends)]
        head_h = _row_lines(head, widths)
        total = 3 + head_h + sum(x + 0.3 for x in h) + (2 if note else 0)
        if total <= float_max and caption and not (nofloat and caption.startswith(nofloat)):
            fl = ["\\begin{table}[htbp]", "\\centering\\small", "\\caption{" + caption + "}",
                  "\\begin{tabular}{" + spec + "}", "\\toprule\\noalign{}", head,
                  "\\midrule\\noalign{}", rows, "\\bottomrule\\noalign{}", "\\end{tabular}"]
            if note:
                fl.append("\\par\\vspace{5pt}{\\small\\raggedright " + note + "\\par}")
            fl.append("\\end{table}")
            out += fl
        else:
            keep = []
            # 无表题的矮表（如表单）不浮动，以免与前面的小标题分开，整表不拆；
            # 有表题而不浮动的表（如课表）按长表处理，可跨页并加续表标识
            whole = total <= whole_max and not caption
            if whole:
                keep = list(range(len(h) - 1))
            elif len(h) > 2 and h[0] <= 2 and h[0] + h[1] <= PAIR_MAX:
                # 只有很矮的首行才需要绑定；高行单独排在页底不算孤行
                keep.append(0)
            if not whole and len(h) > 3 and h[-1] <= 2 and h[-2] + h[-1] <= PAIR_MAX:
                keep.append(len(h) - 2)
            for n in keep:
                rl[ends[n]] = re.sub(r"\\\\\s*$", r"\\\\*", rl[ends[n]].rstrip())
            body = block.replace(rows, "\n".join(rl), 1)
            m = re.match(r"(表[\s~]*[0-9A-Z]+-\d+)", caption)
            if m and "\\endfirsthead\n" in body:
                cont = ("\\multicolumn{%d}{c}{\\small\\color{bookfootergray}%s（续）}\\tabularnewline\n"
                        "\\noalign{\\vskip 2pt}\n" % (ncols, m.group(1)))
                body = body.replace("\\endfirsthead\n", "\\endfirsthead\n" + cont, 1)
            if note:
                foot = ("\\noalign{\\vskip 4pt}\n\\multicolumn{%d}{@{}p{\\dimexpr\\linewidth-2\\tabcolsep}@{}}"
                        "{\\small\\raggedright %s}\\tabularnewline\n" % (ncols, note))
                body = body.replace("\\bottomrule\\noalign{}\n\\endlastfoot\n",
                                    "\\bottomrule\\noalign{}\n" + foot + "\\endlastfoot\n", 1)
            first = (sum(h) if whole else h[0] + (h[1] if 0 in keep else 0)) if h else 1
            need = int(2 + head_h + first + 1.99)
            if whole:
                need = int(1 + head_h + sum(h) + 0.99)
            # 表前紧邻标题（链）时，把预留放到标题链之前
            p = len(out) - 1
            while p >= 0 and not out[p].strip():
                p -= 1
            if p >= 0 and out[p].startswith("{\\def\\LTcaptype"):
                # 无表题的表，pandoc 外包了一层编组
                p -= 1
                while p >= 0 and not out[p].strip():
                    p -= 1
            chain = []
            extra = 0
            if p >= 0 and not out[p].startswith("\\") and len(out[p]) <= 120:
                q = p - 1
                while q >= 0 and not out[q].strip():
                    q -= 1
                if q >= 0 and (HEADING_LINE.match(out[q]) or LEAD_LINE.match(out[q])):
                    chain.append(p)
                    extra = -(-len(out[p]) // cpl) - 3
                    p = q
            while p >= 0 and (HEADING_LINE.match(out[p]) or LEAD_LINE.match(out[p])):
                chain.append(p)
                p -= 1
                while p >= 0 and not out[p].strip():
                    p -= 1
            ns = "\\Needspace*{%d\\baselineskip}" % (need + 3 * len(chain) + extra)
            if chain:
                out.insert(chain[-1], ns)
                out.insert(chain[-1] + 1, "")
            else:
                out += [ns, ""]
            out += ["{\\setstretch{1}\\small"] + body.split("\n") + ["}"]
        i = j + 1
        if note:
            # 跳过已并入表内的表注
            while i < k:
                out.append(lines[i])
                i += 1
            i = k + 1
    return "\n".join(out)


def heading_chain_needspace(tex):
    """\\section 紧跟 \\subsection（中间无正文）时，在 \\section 前一次预留足两级标题和两行正文。"""
    lines = tex.split("\n")
    out = []
    for i, l in enumerate(lines):
        if l.startswith("\\section{"):
            k = i + 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k < len(lines) and lines[k].startswith("\\subsection{"):
                prev = next((x for x in reversed(out) if x.strip()), "")
                if not prev.startswith("\\Needspace"):
                    out += ["\\Needspace*{8\\baselineskip}", ""]
        out.append(l)
    return "\n".join(out)


def keep_after_table(tex):
    """pdf.keep_after_table 列出的表后加粗行（如“本维度小计”）不与表尾分页。"""
    for prefix in B.pdf["keep_after_table"] or []:
        tex = re.sub(r"(\\end\{longtable\}(?:\n\})*\n*)(\\textbf\{%s)" % re.escape(prefix),
                     r"\1\\nopagebreak[4]\n\2", tex)
    return tex


def lead_needspace(tex):
    """独立成段的加粗引导语（如“讨论问题。”）至少带两行正文换页。
    引导语紧跟在节标题之后时，预留放到标题之前（放在标题后会在标题下强制换页）。"""
    lines = tex.split("\n")
    out = []
    for l in lines:
        if LEAD_LINE.match(l):
            p = len(out) - 1
            while p >= 0 and not out[p].strip():
                p -= 1
            if p >= 0 and HEADING_LINE.match(out[p]):
                q = p - 1
                while q >= 0 and not out[q].strip():
                    q -= 1
                if not (q >= 0 and out[q].startswith("\\Needspace")):
                    out[p:p] = ["\\Needspace*{7\\baselineskip}", ""]
            elif not (p >= 0 and out[p].startswith("\\Needspace")):
                out += ["\\Needspace*{4\\baselineskip}", ""]
        out.append(l)
    return "\n".join(out)


# ---------- LaTeX 后处理：引号、书签与断行 ----------

CJK_BEFORE = re.compile(r"[一-鿿“‘（《，。、：；]")


def restore_cjk_quotes(tex):
    """pandoc 把 Unicode 弯引号写成 ``…''、把省略号写成 \\ldots，xeCJK 因而看不到中文标点；
    正文中还原为 Unicode，并去掉 pandoc 在相邻引号之间插入的细空。纯西文引号已改用 \\bookldq/\\bookrdq。"""
    i = tex.index("\\begin{document}")
    head, body = tex[:i], tex[i:]
    body = body.replace("``", "“").replace("''", "”")
    body = re.sub(r"\\ldots\\ldots(?: |\{\})?", "……", body)

    def single(m):
        inner = m.group(1)
        pre = m.string[m.start() - 1] if m.start() else ""
        if re.search(r"[一-鿿]|\\bookplus", inner) or CJK_BEFORE.match(pre):
            return "‘" + inner + "’"
        return m.group(0)

    body = re.sub(r"(?<=[“”‘’])\\,|\\,(?=[“”‘’])", "", body)
    body = re.sub(r"`([^`'\n]{1,80})'", single, body)
    body = re.sub(r"(?<=[“”‘’])\\,|\\,(?=[“”‘’])", "", body)
    return head + body


def unwrap_pdfstrings(tex):
    """标题含 \\bookplus 时，pandoc 会外包一层 \\texorpdfstring 并在书签里丢掉这段文字；
    \\bookplus 本身带书签文字，去掉外层后章题断行宏也能看到“：”。"""
    out, pos, key = [], 0, "\\texorpdfstring{"
    while True:
        k = tex.find(key, pos)
        if k < 0:
            break
        a0 = k + len(key) - 1
        a1 = _brace_arg(tex, a0)
        b1 = _brace_arg(tex, a1 + 1)
        first = tex[a0 + 1:a1]
        if "\\bookplus{}" in first:
            out.append(tex[pos:k] + first)
        else:
            out.append(tex[pos:b1 + 1])
        pos = b1 + 1
    out.append(tex[pos:])
    return "".join(out)


UNITS = "章节编条款项届次批期号版年月日页个家名所人种类部份张件万亿余多级岁"
HAN = "\u4e00-\u9fff"
TAIL = re.compile(r"([%s]{2,3})([^%sA-Za-z0-9\\]*)$" % (HAN, HAN))
TAIL2 = re.compile(r"([%s]{2})([^%sA-Za-z0-9\\]*)$" % (HAN, HAN))
TABLE_ROW = re.compile(r"&.*\\\\\*?\s*$")
SKIP_LINE = ("\\chapter", "\\addcontentsline", "\\part", "\\label")
NUM_CN = "一二三四五六七八九十百零〇"


def _bind(text, pat=TAIL):
    """段落末尾 2—3 个汉字（单元格末尾 2 个汉字）之间禁止断行，末行不会只剩一个字。"""
    m = pat.search(text)
    if not m:
        return text
    return text[:m.start()] + "\\xeCJKnobreak{}".join(m.group(1)) + m.group(2)


def bind_tail(line):
    if not re.search(r"[%s]" % HAN, line) or line.lstrip().startswith(("\\caption", "\\section", "\\subsection",
                                                                        "\\chapter", "\\addcontentsline")):
        return line
    m = re.search(r"\s*\\\\\*?\s*$", line)
    if m and "&" in line:
        cells = re.split(r"(?<!\\)&", line[:m.start()])
        return "&".join(_bind(c.rstrip(), TAIL2) + (" " if k < len(cells) - 1 else "")
                        for k, c in enumerate(cells)) + line[m.start():]
    if m:
        return line
    # 短行多为表头或窄栏文字，只绑末尾 2 字
    return _bind(line.rstrip(), TAIL if len(line) > 40 else TAIL2)


def _nb(m):
    return "\\xeCJKnobreak{}".join(m.group(0))


def line_fixes(l):
    """单行的断行细节：数字与量词、文号、条号、规划简称、外文缩写人名、不可断术语、韩文；末尾不留单字。
    章题、目录行不处理（章题断行宏要看到原文）。"""
    if l.lstrip().startswith(SKIP_LINE):
        return l
    table = bool(TABLE_ROW.search(l))
    l = re.sub(r"第 (\d{1,3})(?!\d)", r"第~\1", l)
    l = re.sub(r"(?<![\d.])(\d+(?:\.\d+)?) ?(?=[%s])" % UNITS, r"\1~", l)
    l = re.sub(r"附录 ([A-Z])(?![\w.])", lambda m: "附\\xeCJKnobreak{}录~" + m.group(1), l)
    l = re.sub(r"第[%s]+[条款项章节篇卷]" % NUM_CN,
               lambda m: _nb(m) if len(m.group(0)) <= 4 else "\\penalty3000{}".join(m.group(0)), l)
    l = re.sub(r"第（[%s]+）[条款项]" % NUM_CN, _nb, l)
    l = re.sub(r"(?<=[共计])[%s]+[章条款项篇节]" % NUM_CN, _nb, l)
    l = re.sub(r"十[四五六七]五", _nb, l)
    # 发文机关代字（国发、沪府办发、工信厅信发函……）内部不拆；正文中代字与“〔”也不拆
    # （表格窄列里只保护 4 字以内的代字）
    l = re.sub(r"([一-鿿]{1,5}[发函字令采改督])(?=〔\d{4}〕)",
               lambda m: (m.group(0) if len(m.group(0)) > 5 else _nb(m)) if table
               else _nb(m) + "\\penalty1000{}", l)
    if not table:
        l = re.sub(r"GB/T (?=\d)", "GB/T~", l)
    l = re.sub(r"(?<=《)[^《》&\\]{2,4}(?=》)", _nb, l)
    if table:
        # 单元格以开引号、书名号、括号起首时，抵消其左侧半字空白（与表头、正文行首一致）
        l = re.sub(r"(^|&\s*)(?=[“‘《（〔])", lambda m: m.group(1) + "\\kern-0.5em{}", l)
        # 分句末两字不拆
        l = re.sub(r"([%s])([%s])(?=[；，。、：])" % (HAN, HAN),
                   lambda m: m.group(1) + "\\xeCJKnobreak{}" + m.group(2), l)
    else:
        l = re.sub(r"第[%s]+[批部期编届次级个]" % NUM_CN, _nb, l)
        # 文号“〔年〕号”尽量不拆，行内实在排不下时允许断开
        l = re.sub(r"〕(?=\d)", lambda m: "〕\\penalty4000{}", l)
        l = re.sub(r"(?<=\d)\+(?=\d)", lambda m: "+\\allowbreak{}", l)
    l = re.sub(r"(?<![\w.])([A-Z]\.(?:-[A-Z]\.)?) (?=[A-Z][a-z])", r"\1~", l)
    l = re.sub(r"(?<![\w.])([A-Z]\.-[A-Z]\.)", lambda m: "\\mbox{" + m.group(1) + "}", l)
    for term in B.pdf["nobreak_terms"] or []:
        l = re.sub(r"(?<![\w/.-])%s(?!\w)" % re.escape(term), lambda m: "\\mbox{" + m.group(0) + "}", l)
    l = re.sub(r"[가-힯]+", lambda m: "\\mbox{" + m.group(0) + "}", l)
    return bind_tail(l)


def heading_bookmarks(tex):
    """标题编号紧接左引号时（版面上去掉了空格），书签与目录用带空格的短标题。"""
    out = []
    for l in tex.split("\n"):
        m = re.match(r"^\\(section|subsection|subsubsection)\{([0-9A-Z][0-9A-Z.]*)([“‘])", l)
        if m:
            k = l.index("{")
            e = _brace_arg(l, k)
            title = l[k + 1:e]
            short = title.replace(m.group(2) + m.group(3), m.group(2) + " " + m.group(3), 1)
            short = short.replace("\\xeCJKnobreak{}", "").replace("\\bookplus{}", "+")
            l = "\\%s[%s]%s" % (m.group(1), short, l[k:])
        out.append(l)
    return "\n".join(out)


def body_text_fixes(tex):
    """正文细节：逐行断行规则、加粗句末多余空格、参考文献句点后引号、图表题编号后引号。"""
    i = tex.index("\\begin{document}")
    head, body = tex[:i], tex[i:]
    body = "\n".join(line_fixes(l) for l in body.split("\n"))
    body = re.sub(r"(表|图) (\d+-\d+|[A-Z]-\d+)", r"\1~\2", body)
    body = re.sub(r"([。：；，！？”）])\} (?=[0-9A-Za-z])", r"\1}", body)
    body = body.replace(". “", ".“")
    body = "\n".join(l.replace("　“", "\\hspace{0.5em}“") if "\\caption{" in l else l
                     for l in body.split("\n"))
    return head + body


# ---------- 拼装与渲染 ----------

def add_push(text, push):
    """章末短页回收：在本章 squeeze_anchor 节（找不到时取最后一个二级标题）标题上标记缩行数。"""
    lines = text.split("\n")
    anchor = B.pdf["squeeze_anchor"]
    heads = [n for n, l in enumerate(lines) if l.startswith("## ")]
    named = [n for n in heads if anchor and heading_name(lines[n]) == anchor]
    target = (named or heads or [None])[-1]
    if target is None:
        return text
    lines[target] = lines[target].rstrip() + " {.push%d}" % push
    return "\n".join(lines)


def assemble(squeeze):
    """拼装全书 Markdown；squeeze 为 {章序号: 末节起始页缩短的行数}。"""
    chunks = [B.read(p).rstrip() + "\n" for p in B.frontmatter()]
    idx = 0
    for g in B.groups():
        if g["label"]:
            chunks.append(part_page(g["label"], g["title"], g["image"], g["note"]))
        for files in g["chapters"]:
            idx += 1
            text = "\n\n".join(B.read(f).rstrip() for f in files)
            if squeeze.get(idx):
                text = add_push(text, squeeze[idx])
            # 章首、章末各放一个标签：章末页只剩几行、且不是本章唯一一页时才回收
            text = re.sub(r"^(# .*)$", lambda m: m.group(1) + "\n\n" + raw("\\label{bookchapstart-%03d}" % idx),
                          text, count=1, flags=re.M)
            chunks.append(text + "\n\n" + raw("\\label{bookchapend-%03d}" % idx))
    app = B.appendix()
    if app:
        if app["title"]:
            chunks.append(part_page(app["label"], app["title"], None, app["note"], appendix=True))
        else:
            chunks.append(raw("\\appendix"))
        chunks += [B.read(p).rstrip() + "\n" for p in app["files"]]
    ref = B.references()
    if ref:
        chunks.append(raw("\\begingroup\\raggedright\\small\\hyphenpenalty=10000\\exhyphenpenalty=10000"))
        chunks.append(B.read(ref).rstrip() + "\n")
        chunks.append(raw("\\par\\endgroup"))
    return "\n\n".join(chunks)


def write_header():
    """把 typeset.yaml 的配色、封面与字体回退填进版式模板，返回生成的 header 路径。"""
    f, c = B.fonts, B.colors
    settings = [
        "\\definecolor{bookaccent}{HTML}{%s}" % c["accent"],
        "\\definecolor{bookink}{HTML}{%s}" % c["ink"],
        "\\definecolor{bookfootergray}{gray}{0.48}",
        "\\newfontfamily\\booksymbolfont{%s}" % f["symbol"],
        "\\newfontfamily\\bookcheckfont{%s}" % f["symbol2"],
        "\\newfontfamily\\bookromanfont{%s}" % f["cjk_main"],
        "% 韩文回退字体",
        "\\xeCJKDeclareSubCJKBlock{Hangul}{\"AC00 -> \"D7AF, \"1100 -> \"11FF, \"3130 -> \"318F}",
        "\\setCJKmainfont[Hangul={%s}]{%s}" % (f["hangul_main"], f["cjk_main"]),
        "\\setCJKsansfont[Hangul={%s}]{%s}" % (f["hangul_sans"], f["cjk_sans"]),
    ]
    if B.cover:
        settings.append("\\newcommand{\\bookcoverfile}{%s}" % B.cover)
    tpl = open(TEMPLATE, encoding="utf-8").read()
    os.makedirs(os.path.join(B.build, "tex"), exist_ok=True)
    path = os.path.join(B.build, "tex", "header.generated.tex")
    open(path, "w", encoding="utf-8").write(tpl.replace("%% BOOK-SETTINGS %%", "\n".join(settings)))
    return path


def render(text):
    """Markdown → LaTeX → PDF。"""
    md = preprocess(text)
    md_path = os.path.join(B.build, "book.md")
    tex_path = os.path.join(B.build, "book.tex")
    open(md_path, "w", encoding="utf-8").write(md)
    print("book.md 汉字数：%d" % len(re.findall(r"[一-鿿]", md)))

    p, f = B.page, B.fonts
    cmd = [
        "pandoc", md_path, "-f", "markdown-smart", "-t", "latex", "-s", "--wrap=none", "-o", tex_path,
        "--top-level-division=chapter", "--toc", "--toc-depth=1",
        "-V", "documentclass=book", "-V", "classoption=oneside",
        "-V", "geometry:paperwidth=%smm,paperheight=%smm,top=%smm,bottom=%smm,inner=%smm,outer=%smm"
        % (p["width"], p["height"], p["top"], p["bottom"], p["inner"], p["outer"]),
        "-V", "CJKmainfont=" + f["cjk_main"], "-V", "CJKsansfont=" + f["cjk_sans"],
        "-V", "CJKmonofont=" + f["cjk_mono"], "-V", "mainfont=" + f["main"],
        "-V", "sansfont=" + f["sans"], "-V", "monofont=" + f["mono"],
        "-V", "fontsize=%dpt" % int(p["fontsize"]), "-V", "linestretch=%s" % p["linestretch"],
        "-V", "colorlinks=true", "-V", "linkcolor=[HTML]{%s}" % B.colors["accent"],
        "-V", "toccolor=[HTML]{%s}" % B.colors["ink"],
        "-M", "title=" + B.title,
        "--include-in-header=" + write_header(),
    ]
    # 不传 lang：传了会加载 babel，接管中文标点与目录名
    for key in ("subtitle", "author", "date"):
        if getattr(B, key):
            cmd += ["-M", "%s=%s" % (key, getattr(B, key))]
    if B.pdf["extra_header"]:
        cmd.append("--include-in-header=" + B._path(B.pdf["extra_header"]))
    if B.pdf["backmatter"]:
        cmd.append("--include-after-body=" + B._path(B.pdf["backmatter"]))
    r = subprocess.run(cmd, cwd=B.root, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-6000:], file=sys.stderr)
        sys.exit(1)

    tex = open(tex_path, encoding="utf-8").read()
    tex = heading_bookmarks(body_text_fixes(unwrap_pdfstrings(restore_cjk_quotes(tex))))
    tex = heading_chain_needspace(lead_needspace(keep_after_table(process_tables(tex))))
    open(tex_path, "w", encoding="utf-8").write(tex)

    outdir = os.path.join(B.build, "latex-out")
    os.makedirs(outdir, exist_ok=True)
    # 以书根目录为工作目录、用相对路径调用：图片路径相对书根，且避开路径里的空格
    for _ in range(3):
        r = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error",
                            "-output-directory=" + os.path.relpath(outdir, B.root),
                            os.path.relpath(tex_path, B.root)],
                           cwd=B.root, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-6000:], file=sys.stderr)
            sys.exit(1)
    log = open(os.path.join(outdir, "book.log"), encoding="utf-8", errors="ignore").read()
    for kind, pat in (("缺字", r"Missing character"), ("超宽", r"Overfull \\hbox \((\d+\.\d+)pt"),
                      ("浮动体过大", r"Float too large"),
                      ("页面溢出", r"Overfull \\vbox \((\d+\.\d+)pt too high\) has occurred while \\output")):
        hits = re.findall(pat, log)
        if kind in ("超宽", "页面溢出"):
            hits = [h for h in hits if float(h) > 3]
        print("%s：%d" % (kind, len(hits)))


def short_chapter_ends(max_lines=5):
    """找出最后一页只剩 max_lines 行以内的章，返回 {章序号: 行数}。"""
    import fitz
    aux = open(os.path.join(B.build, "latex-out", "book.aux"), encoding="utf-8", errors="ignore").read()
    labels = r"\\newlabel\{bookchap%s-(\d+)\}\{\{[^}]*\}\{([^}]*)\}"
    starts = {int(n): pg for n, pg in re.findall(labels % "start", aux)}
    ends = {int(n): pg for n, pg in re.findall(labels % "end", aux) if starts.get(int(n)) != pg}
    doc = fitz.open(os.path.join(B.build, "latex-out", "book.pdf"))
    phys = {doc[k].get_label(): k for k in range(len(doc))}
    lo, hi = B.body_pt * 0.78, B.body_pt * 1.05
    out = {}
    for n, pg in ends.items():
        k = phys.get(pg)
        if k is None:
            continue
        page = doc[k]
        bot = page.rect.height * (B.page["height"] - B.page["bottom"]) / B.page["height"]
        ys = set()
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                if ln["dir"] != (1.0, 0.0) or ln["bbox"][3] > bot + 2:
                    continue
                if any(lo <= sp["size"] <= hi and sp["text"].strip() for sp in ln["spans"]):
                    ys.add(round(ln["bbox"][1]))
        if len(ys) <= max_lines:
            out[n] = len(ys)
    return out


def main():
    global B
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--book", default=".", help="书根目录（含 typeset.yaml），默认当前目录")
    ap.add_argument("-o", "--output", help="输出 PDF 路径，默认 build/book.pdf")
    args = ap.parse_args()
    B = booklib.Book(args.book)
    os.makedirs(B.build, exist_ok=True)
    pdf = os.path.abspath(args.output) if args.output else os.path.join(B.build, "book.pdf")
    squeeze = {}
    for rnd in range(5):
        render(assemble(squeeze))
        short = short_chapter_ends()
        if not short:
            print("章末短页：0")
            break
        todo = {n: squeeze.get(n, 0) + (7 - k if not squeeze.get(n) else 2) for n, k in short.items()
                if squeeze.get(n, 0) < 10}
        print("章末短页（章序号: 行数）：", short, "；前页缩行：", todo or "已到上限")
        if not todo or rnd == 4:
            break
        squeeze.update(todo)
    # 缩到上限仍是短页的章：撤回缩行（否则白白留下一页短 10 行），交给人工改稿或调图表位置
    stuck = sorted(n for n in short if squeeze.get(n))
    if stuck:
        for n in stuck:
            del squeeze[n]
        print("回收无效、已撤回缩行，需人工处理的章（章序号）：", stuck)
        render(assemble(squeeze))
    shutil.copy(os.path.join(B.build, "latex-out", "book.pdf"), pdf)
    print("PDF: %s (%d bytes)" % (pdf, os.path.getsize(pdf)))


if __name__ == "__main__":
    main()
