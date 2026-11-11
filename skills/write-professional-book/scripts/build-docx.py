#!/usr/bin/env python3
"""从与 PDF 相同的 Markdown 源生成可编辑的 DOCX 书稿。

书名、署名、编章结构与页面尺寸读自书根目录的 typeset.yaml，与 build-pdf.py 一致。
版式按中文书稿常规：正文宋体五号、首行缩进 2 字、1.5 倍行距；章、节标题黑体；
三线表、小五号字；图题在图下、表题在表上；封面单独一节铺满整页；页脚只放页码；
目录为 Word 目录域，打开文档更新域后生成页码。
中间文件写在书根目录的 build/：book-docx.md、reference.docx、book-raw.docx。

用法：python3 build-docx.py [--book 书根目录] [-o 输出 DOCX]
"""
import argparse
import os
import re
import subprocess
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Mm, Pt, RGBColor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import booklib  # noqa: E402

B = None  # booklib.Book，main() 中设置
PAGE_W = PAGE_H = TEXT_W = TEXT_H = None
MARGIN = {}
INK = RGBColor(0x1E, 0x14, 0x16)
GRAY = RGBColor(0x55, 0x55, 0x55)

PAGEBREAK = '```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n'
LINEBREAK = "`<w:r><w:br/></w:r>`{=openxml}"
TOC_FIELD = ('```{=openxml}\n<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
             '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-1" \\t "编标题,1" \\h \\z \\u </w:instrText></w:r>'
             '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
             '<w:r><w:t>（打开文档后，在此处右键选择“更新域”即可生成目录）</w:t></w:r>'
             '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>\n```\n')


def div(style, text):
    return '\n::: {custom-style="%s"}\n%s\n:::\n\n' % (style, text)


# ---------- Markdown 预处理：为 PDF 写的 LaTeX 片段改成 DOCX 等价写法 ----------

def convert_raw(text):
    """源稿里为 PDF 写的 LaTeX：分页块改成 Word 分页符，其余块删除；行内片段逐个改写，
    遇到没见过的片段直接报错，避免以原始代码留在正文。"""
    def block(m):
        return PAGEBREAK if "\\clearpage" in m.group(1) or "\\newpage" in m.group(1) else ""

    text = re.sub(r"```\{=latex\}\n(.*?)\n```\n?", block, text, flags=re.S)

    def inline(m):
        c = m.group(1)
        if c.startswith("\\newline") or c.startswith("\\\\"):
            return LINEBREAK
        if c.startswith(("\\hskip", "\\quad")):
            return "\u3000"
        if c.startswith(("\\rule", "\\nopagebreak", "\\allowbreak", "\\enlargethispage", "\\vspace")) or not c.strip():
            return ""
        mm = re.match(r"\\mbox\{(.*)\}$", c)
        if mm:
            return re.sub(r"\\hspace\{(\d+)em\}", lambda x: "\u3000" * int(x.group(1)), mm.group(1))
        raise ValueError("未处理的 LaTeX 片段：" + c)

    text = re.sub(r"`([^`]*)`\{=latex\}", inline, text)
    text = re.sub(r"<!--.*?-->\n?", "", text, flags=re.S)
    # 插图按版心宽度
    text = re.sub(r"^(!\[[^\]]*\]\([^)]+\))[ \t]*$", r"\1{width=100%}", text, flags=re.M)
    return text


def assemble():
    chunks = []
    if B.cover:
        chunks.append("![](%s)\n" % B.cover)
    front = div("书名", B.title)
    for style_name, value in (("副书名", B.subtitle), ("署名", B.author), ("日期", B.date)):
        if value:
            front += div(style_name, value)
    chunks.append(front)
    chunks.append(div("目录标题", "目　录") + TOC_FIELD)
    chunks += [B.read(p) for p in B.frontmatter()]
    for g in B.groups():
        if g["label"]:
            head = div("编标题", g["label"] + ("\u3000" + g["title"] if g["title"] else ""))
            if g["image"]:
                head += "\n![](%s){width=100%%}\n\n" % g["image"]
            if g["note"]:
                head += div("编说明", g["note"])
            chunks.append(head)
        for files in g["chapters"]:
            chunks += [B.read(f) for f in files]
    app = B.appendix()
    if app:
        if app["title"]:
            chunks.append(div("编标题", app["label"]) + div("编副题", app["title"])
                          + (div("编说明", app["note"]) if app["note"] else ""))
        chunks += [B.read(p) for p in app["files"]]
    ref = B.references()
    if ref:
        chunks.append(B.read(ref))
    text = "\n\n".join(c.rstrip() + "\n" for c in chunks)
    text = "\n".join(booklib.bind_table_captions(text.split("\n")))
    return convert_raw(text)


# OOXML 子元素有固定顺序，插入时必须遵守，否则 Word 会提示内容不可读
ORDER = {
    "pPr": ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
            "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
            "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid",
            "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
            "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"],
    "sectPr": ["headerReference", "footerReference", "footnotePr", "endnotePr", "type", "pgSz", "pgMar",
               "paperSrc", "pgBorders", "lnNumType", "pgNumType", "cols", "formProt", "vAlign", "noEndnote",
               "titlePg", "textDirection", "bidi", "rtlGutter", "docGrid", "printerSettings", "sectPrChange"],
    "tblPr": ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW",
              "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
              "tblCaption", "tblDescription", "tblPrChange"],
    "tcPr": ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
             "textDirection", "tcFitText", "vAlign", "hideMark", "headers", "cellIns", "cellDel", "cellMerge",
             "tcPrChange"],
}


def put(parent, child, kind):
    """按 ORDER[kind] 的顺序把 child 插入 parent；同名旧元素先删除。"""
    order = ORDER[kind]
    tag = child.tag.split("}")[1]
    for old in parent.findall(qn("w:" + tag)):
        parent.remove(old)
    idx = order.index(tag)
    for el in list(parent):
        t = el.tag.split("}")[1]
        if t in order and order.index(t) > idx:
            el.addprevious(child)
            return child
    parent.append(child)
    return child


# ---------- 样式 ----------

def _rfonts(el, east, latin):
    rpr = el.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for k in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(k)) is not None:
            del rf.attrib[qn(k)]
    rf.set(qn("w:ascii"), latin)
    rf.set(qn("w:hAnsi"), latin)
    rf.set(qn("w:eastAsia"), east)
    rf.set(qn("w:cs"), latin)


def _ind_chars(ppr, first_chars):
    ind = ppr.find(qn("w:ind"))
    if ind is None:
        ind = put(ppr, OxmlElement("w:ind"), "pPr")
    for k in list(ind.attrib):
        if "firstLine" in k or "hanging" in k:
            del ind.attrib[k]
    if first_chars:
        ind.set(qn("w:firstLineChars"), str(first_chars * 100))
        ind.set(qn("w:firstLine"), str(int(first_chars * 210)))


def _outline(ppr, level):
    o = OxmlElement("w:outlineLvl")
    o.set(qn("w:val"), str(level))
    put(ppr, o, "pPr")


def style(doc, name, east=None, latin=None, size=10.5, bold=False, color=INK,
          align=None, first_chars=0, line=1.5, before=0, after=0, page_break=False,
          keep_next=False, outline=None):
    st = doc.styles[name] if name in [s.name for s in doc.styles] else doc.styles.add_style(name, 1)
    _rfonts(st.element, east or B.docx["body_font"], latin or B.docx["latin_font"])
    st.font.size = Pt(size)
    st.font.bold = bold
    st.font.italic = False
    st.font.color.rgb = color
    pf = st.paragraph_format
    pf.line_spacing = line
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.page_break_before = page_break
    pf.keep_with_next = keep_next
    if align is not None:
        pf.alignment = align
    ppr = st.element.get_or_add_pPr()
    _ind_chars(ppr, first_chars)
    if outline is not None:
        _outline(ppr, outline)
    return st


def apply_styles(doc):
    C, L = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT
    J = WD_ALIGN_PARAGRAPH.JUSTIFY
    H = B.docx["heading_font"]
    for n in ("Normal", "Body Text", "First Paragraph"):
        style(doc, n, first_chars=2, align=J)
    style(doc, "Compact", align=J, line=1.5)
    style(doc, "Block Text", east=B.docx["quote_font"], first_chars=2, align=J)
    style(doc, "Heading 1", east=H, size=16, align=C, line=1.3, before=36, after=30,
          page_break=True, keep_next=True, outline=0)
    style(doc, "Heading 2", east=H, size=14, align=L, line=1.3, before=18, after=10, keep_next=True, outline=1)
    style(doc, "Heading 3", east=H, size=12, align=L, line=1.3, before=12, after=6, keep_next=True, outline=2)
    style(doc, "Heading 4", east=H, size=10.5, align=L, line=1.3, before=8, after=4, keep_next=True, outline=3)
    style(doc, "Image Caption", size=9, color=GRAY, align=C, line=1.2, before=4, after=12)
    style(doc, "Table Caption", size=9, color=GRAY, align=C, line=1.2, before=12, after=4, keep_next=True)
    for n in ("Captioned Figure", "Figure"):
        if n in [s.name for s in doc.styles]:
            style(doc, n, align=C, line=1.0, before=6, after=0, keep_next=True)
    style(doc, "书名", east=H, size=26, align=C, line=1.3, before=150, after=18)
    style(doc, "副书名", size=14, align=C, line=1.4, after=60)
    style(doc, "署名", size=14, align=C, line=1.4, after=12)
    style(doc, "日期", size=12, align=C, line=1.4)
    style(doc, "目录标题", east=H, size=16, align=C, line=1.3, before=36, after=24, page_break=True)
    style(doc, "编标题", east=H, size=24, align=C, line=1.3, before=90, after=36, page_break=True, outline=0)
    style(doc, "编副题", east=H, size=16, align=C, line=1.4, after=24)
    style(doc, "编说明", size=10.5, color=GRAY, align=C, line=1.4, before=18)


# ---------- 表格、图片、分节 ----------

def _border(parent, tag, sz):
    el = OxmlElement("w:" + tag)
    if sz:
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
    else:
        el.set(qn("w:val"), "nil")
    parent.append(el)


def format_tables(doc):
    """三线表：顶线、底线粗，表头下细线，无竖线；小五号字；表头行跨页重复。"""
    for t in doc.tables:
        tblPr = t._tbl.tblPr
        for old in tblPr.findall(qn("w:tblStyle")):
            tblPr.remove(old)
        w = OxmlElement("w:tblW")
        w.set(qn("w:type"), "pct")
        w.set(qn("w:w"), "5000")
        put(tblPr, w, "tblPr")
        b = OxmlElement("w:tblBorders")
        for tag, sz in (("top", 12), ("left", 0), ("bottom", 12), ("right", 0), ("insideH", 0), ("insideV", 0)):
            _border(b, tag, sz)
        put(tblPr, b, "tblPr")
        for ri, row in enumerate(t.rows):
            if ri == 0:
                row._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
            for cell in row.cells:
                if ri == 0:
                    tb = OxmlElement("w:tcBorders")
                    _border(tb, "bottom", 6)
                    put(cell._tc.get_or_add_tcPr(), tb, "tcPr")
                for p in cell.paragraphs:
                    pf = p.paragraph_format
                    pf.line_spacing = 1.2
                    pf.space_before = Pt(1)
                    pf.space_after = Pt(1)
                    pf.first_line_indent = Pt(0)
                    _ind_chars(p._p.get_or_add_pPr(), 0)
                    for r in p.runs:
                        r.font.size = Pt(9)
                        if ri == 0:
                            r.font.bold = True


def format_images(doc):
    """只含图片的段落居中、无首行缩进；图片宽不超过版心、高不超过版心的 82%（封面另行处理）。"""
    for p in doc.paragraphs:
        if p._p.findall(".//" + qn("w:drawing")) and not p.text.strip():
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _ind_chars(p._p.get_or_add_pPr(), 0)
    shapes = list(doc.inline_shapes)
    for i, s in enumerate(shapes):
        if i == 0 and B.cover:
            continue
        if s.width > TEXT_W:
            ratio = TEXT_W / s.width
            s.width = Emu(int(s.width * ratio))
            s.height = Emu(int(s.height * ratio))
        limit = int(TEXT_H * 0.82)
        if s.height > limit:
            ratio = limit / s.height
            s.width = Emu(int(s.width * ratio))
            s.height = Emu(int(s.height * ratio))
    return shapes


def _page(sectPr, top, bottom, left, right):
    sz = OxmlElement("w:pgSz")
    sz.set(qn("w:w"), str(int(PAGE_W / 635)))   # EMU → twip
    sz.set(qn("w:h"), str(int(PAGE_H / 635)))
    mar = OxmlElement("w:pgMar")
    for k, v in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        mar.set(qn("w:" + k), str(int(v / 635)))
    mar.set(qn("w:header"), str(int(Mm(10) / 635)))
    mar.set(qn("w:footer"), str(int(Mm(12) / 635)))
    mar.set(qn("w:gutter"), "0")
    put(sectPr, sz, "sectPr")
    put(sectPr, mar, "sectPr")


def _page_number_footer(section):
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _ind_chars(p._p.get_or_add_pPr(), 0)
    for kind, text in (("begin", None), (None, " PAGE "), ("separate", None), (None, "1"), ("end", None)):
        r = p.add_run()
        r.font.size = Pt(9)
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r._r.append(fc)
        elif text.strip() == "PAGE":
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = text
            r._r.append(it)
        else:
            r.text = text


def sections_and_cover(doc, shapes):
    body = doc.element.body
    main_sect = body.find(qn("w:sectPr"))
    _page(main_sect, MARGIN["top"], MARGIN["bottom"], MARGIN["left"], MARGIN["right"])
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:start"), "1")
    put(main_sect, pg, "sectPr")
    if B.cover:
        # 封面：第一段（只含封面图）单独成节，页边距为 0，图铺满整页
        cover = shapes[0]
        ratio = min(PAGE_W / cover.width, (PAGE_H - Mm(2)) / cover.height)
        cover.width = Emu(int(cover.width * ratio))
        cover.height = Emu(int(cover.height * ratio))
        first = doc.paragraphs[0]
        pf = first.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.0
        pf.page_break_before = False
        ppr = first._p.get_or_add_pPr()
        _ind_chars(ppr, 0)
        cs = OxmlElement("w:sectPr")
        _page(cs, 0, 0, 0, 0)
        put(ppr, cs, "pPr")
        doc.sections[0].footer.is_linked_to_previous = False
    _page_number_footer(doc.sections[-1])


def finish(doc):
    cp = doc.core_properties
    cp.title = B.title
    cp.subject = B.subtitle
    cp.author = B.author
    cp.last_modified_by = ""
    cp.comments = ""
    cp.keywords = "; ".join(B.keywords)
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    doc.settings.element.append(uf)


def main():
    global B, PAGE_W, PAGE_H, TEXT_W, TEXT_H, MARGIN
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--book", default=".", help="书根目录（含 typeset.yaml），默认当前目录")
    ap.add_argument("-o", "--output", help="输出 DOCX 路径，默认 build/book.docx")
    args = ap.parse_args()
    B = booklib.Book(args.book)
    p = B.page
    PAGE_W, PAGE_H = Mm(p["width"]), Mm(p["height"])
    MARGIN = {"top": Mm(p["top"]), "bottom": Mm(p["bottom"]), "left": Mm(p["inner"]), "right": Mm(p["outer"])}
    TEXT_W = PAGE_W - MARGIN["left"] - MARGIN["right"]
    TEXT_H = PAGE_H - MARGIN["top"] - MARGIN["bottom"]
    os.makedirs(B.build, exist_ok=True)
    out = os.path.abspath(args.output) if args.output else os.path.join(B.build, "book.docx")

    md_path = os.path.join(B.build, "book-docx.md")
    open(md_path, "w", encoding="utf-8").write(assemble())
    ref = os.path.join(B.build, "reference.docx")
    subprocess.run(["pandoc", "-o", ref, "--print-default-data-file", "reference.docx"], check=True)
    rd = Document(ref)
    _page(rd.element.body.find(qn("w:sectPr")), MARGIN["top"], MARGIN["bottom"], MARGIN["left"], MARGIN["right"])
    rd.save(ref)
    raw_out = os.path.join(B.build, "book-raw.docx")
    r = subprocess.run(["pandoc", md_path, "-f", "markdown-smart", "-t", "docx", "--reference-doc=" + ref,
                        "--resource-path=" + B.root, "-o", raw_out], cwd=B.root, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-4000:], file=sys.stderr)
        sys.exit(1)
    if r.stderr.strip():
        print(r.stderr.strip()[-2000:], file=sys.stderr)
    doc = Document(raw_out)
    apply_styles(doc)
    format_tables(doc)
    shapes = format_images(doc)
    sections_and_cover(doc, shapes)
    finish(doc)
    doc.save(out)
    print("DOCX: %s (%d bytes)" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    main()
