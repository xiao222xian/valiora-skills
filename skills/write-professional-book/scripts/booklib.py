"""写书 Skill 构建脚本的公共部分：读取 typeset.yaml，按编章顺序收集源稿，整理图片路径与表题。

build-pdf.py、build-docx.py、table-widths.py、pdfcheck.py 共用。配置模板见 templates/typeset.yaml。
"""
import glob
import os
import re
import sys

import yaml

# 估算版心宽高用 bp（72/英寸），比 TeX pt 窄约 0.4%，估算偏保守；第一本书逐页验收时用的就是这个值
MM = 72 / 25.4

DEFAULTS = {
    "page": {"width": 185, "height": 260, "top": 22, "bottom": 24, "inner": 20, "outer": 18,
             "fontsize": 11, "linestretch": 1.28},
    "fonts": {"cjk_main": "Songti SC", "cjk_sans": "PingFang SC", "cjk_mono": "PingFang SC",
              "main": "Times New Roman", "sans": "Helvetica Neue", "mono": "Menlo",
              "hangul_main": "Apple SD Gothic Neo", "hangul_sans": "Apple SD Gothic Neo",
              "symbol": "Apple Symbols", "symbol2": "Arial Unicode MS"},
    "colors": {"accent": "8A3324", "ink": "1E1416"},
    "pdf": {"extra_header": None, "backmatter": None, "ragged_sections": ["延伸阅读"],
            "squeeze_anchor": "延伸阅读", "nofloat_tables": [], "keep_after_table": [], "nobreak_terms": [],
            "plus_terms": ["人工智能", "互联网"], "float_max": None},
    "docx": {"body_font": "宋体", "heading_font": "黑体", "quote_font": "楷体", "latin_font": "Times New Roman"},
}

# 正文字号（pt）→ book 类的实际正文字号与 \small 字号
BODY_PT = {10: 10.0, 11: 10.95, 12: 12.0}
SMALL_PT = {10: 9.0, 11: 10.0, 12: 10.95}


class Book:
    """一本书的配置与源稿编排。"""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.build = os.path.join(self.root, "build")
        path = os.path.join(self.root, "typeset.yaml")
        if not os.path.exists(path):
            sys.exit("缺少 %s：从 Skill 的 templates/typeset.yaml 复制一份并填写书名、署名与编章" % path)
        cfg = yaml.safe_load(open(path, encoding="utf-8")) or {}
        for sec, vals in DEFAULTS.items():
            cfg[sec] = dict(vals, **(cfg.get(sec) or {}))
        if not cfg.get("title"):
            sys.exit("typeset.yaml 缺少 title")
        self.cfg = cfg
        self.title = cfg["title"]
        self.subtitle = cfg.get("subtitle") or ""
        self.author = cfg.get("author") or ""
        self.date = cfg.get("date") or ""
        self.keywords = cfg.get("keywords") or []
        self.cover = cfg.get("cover")
        self.page, self.fonts, self.colors = cfg["page"], cfg["fonts"], cfg["colors"]
        self.pdf, self.docx = cfg["pdf"], cfg["docx"]

        size = int(self.page["fontsize"])
        if size not in BODY_PT:
            sys.exit("page.fontsize 只支持 10、11、12")
        p = self.page
        self.text_w_mm = p["width"] - p["inner"] - p["outer"]
        self.text_h_mm = p["height"] - p["top"] - p["bottom"]
        self.text_w = self.text_w_mm * MM
        self.text_h = self.text_h_mm * MM
        self.body_pt = BODY_PT[size]
        self.small_pt = SMALL_PT[size]

    # ---------- 编章结构 ----------

    def _glob(self, pattern):
        return sorted(glob.glob(os.path.join(self.root, pattern)))

    def _path(self, rel):
        return rel if os.path.isabs(rel) else os.path.join(self.root, rel)

    def chapter_files(self, spec):
        """章：数字 n 指 src/chapter-nn/，也可写目录或文件路径；目录取 README.md 再接 section-*.md。"""
        d = os.path.join(self.root, "src", "chapter-%02d" % spec) if isinstance(spec, int) else self._path(spec)
        if os.path.isdir(d):
            files = [os.path.join(d, "README.md")] + sorted(glob.glob(os.path.join(d, "section-*.md")))
        else:
            files = [d]
        found = [f for f in files if os.path.exists(f)]
        if not found:
            print("警告：缺少章节 %s，跳过" % spec, file=sys.stderr)
        return found

    def frontmatter(self):
        fm = self.cfg.get("frontmatter")
        return [self._path(f) for f in fm] if fm is not None else self._glob("src/00-*.md")

    def groups(self):
        """[{label, title, image, note, chapters: [[文件…], …]}]；不分编的书只有一组，label 为空。"""
        parts = self.cfg.get("parts")
        if not parts:
            specs = self.cfg.get("chapters")
            if specs is None:
                specs = [os.path.relpath(d, self.root) for d in self._glob("src/chapter-*") if os.path.isdir(d)]
            parts = [{"chapters": specs}]
        out = []
        for g in parts:
            chs = [f for f in (self.chapter_files(s) for s in g.get("chapters") or []) if f]
            out.append({"label": g.get("label") or "", "title": g.get("title") or "",
                        "image": g.get("image"), "note": g.get("note") or "", "chapters": chs})
        return out

    def appendix(self):
        """{label, title, note, files}；没有附录时返回 None。title 为空时不排附录扉页。"""
        a = self.cfg.get("appendix") or {}
        files = [self._path(f) for f in a["files"]] if a.get("files") is not None else self._glob("src/appendix-*.md")
        files = [f for f in files if os.path.exists(f)]
        if not files:
            return None
        return {"label": a.get("label") or "附　录", "title": a.get("title") or "",
                "note": a.get("note") or "", "files": files}

    def references(self):
        ref = self.cfg.get("references", "src/references.md")
        return self._path(ref) if ref and os.path.exists(self._path(ref)) else None

    def read(self, path):
        """读源稿，并把相对图片路径改为相对书根目录（构建时以书根目录为工作目录）。"""
        return rebase_images(open(path, encoding="utf-8").read(), os.path.dirname(path), self.root)


IMAGE = re.compile(r"(!\[[^\]]*\]\()([^)\s]+)")


def rebase_images(text, base, root):
    def rep(m):
        target = m.group(2)
        if re.match(r"^(?:[a-z]+:|/|#)", target):
            return m.group(0)
        return m.group(1) + os.path.relpath(os.path.normpath(os.path.join(base, target)), root)
    return IMAGE.sub(rep, text)


CAPTION = re.compile(r"^表\s*[0-9A-Z]+-\d+")


def bind_table_captions(lines):
    """“表 X-Y　……”独立成段且紧接表格时，改为 pandoc 表格标题，随表换页。"""
    for i, l in enumerate(lines):
        if CAPTION.match(l.strip()) and "|" not in l:
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith("<!--")):
                j += 1
            if j < len(lines) and lines[j].lstrip().startswith("|"):
                lines[i] = "Table: " + l.strip()
    return lines
