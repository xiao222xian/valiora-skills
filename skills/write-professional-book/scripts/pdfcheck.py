#!/usr/bin/env python3
"""成品 PDF 的版面自检（逐页验收前先跑一遍，不替代人工逐页看）：

1. 字距：正文行内相邻汉字的字距中位数明显被拉开（>1.12 字宽）的行；
2. 单字成行：段末或单元格末行只有一个汉字（可带标点）的行；
3. 页底留白：版心下部空白超过 22% 的页（章末页、编扉页、浮动体前的空白都会列出，需人工判断）。

给 --book 时正文字号与版心上下边距读 typeset.yaml；否则正文字号取全书出现最多的字号、边距用默认 16 开版式。

用法：python3 pdfcheck.py PDF [--book 书根目录] [--pages A-B]
"""
import argparse
import os
import re
import sys
from collections import Counter

import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import booklib  # noqa: E402

HAN = re.compile(r"[一-鿿]")


def body_size(doc):
    cnt = Counter()
    step = max(1, len(doc) // 60)
    for k in range(0, len(doc), step):
        for b in doc[k].get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                for sp in ln["spans"]:
                    cnt[round(sp["size"], 1)] += len(sp["text"].strip())
    return cnt.most_common(1)[0][0]


def lines_of(page, lo, hi):
    """水平文字行：[(bbox, 字号, [字符…])]，只取字号在 [lo, hi] 内的字符。"""
    out = []
    for b in page.get_text("rawdict")["blocks"]:
        for ln in b.get("lines", []):
            if ln["dir"] != (1.0, 0.0):
                continue
            spans = [sp for sp in ln["spans"] if lo <= sp["size"] <= hi]
            chars = [c for sp in spans for c in sp["chars"]]
            if chars:
                out.append((ln["bbox"], spans[0]["size"], chars))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--book", help="书根目录（读 typeset.yaml 的正文字号与页边距）")
    ap.add_argument("--pages", help="页码范围，如 20-40（物理页）")
    args = ap.parse_args()
    book = booklib.Book(args.book) if args.book else None
    page_cfg = book.page if book else booklib.DEFAULTS["page"]
    doc = fitz.open(args.pdf)
    a, b = 1, len(doc)
    if args.pages:
        a, b = map(int, args.pages.split("-"))
    size = book.body_pt if book else body_size(doc)
    lo, hi = size * 0.87, size * 1.05
    loose, single, gaps = [], [], []
    for pno in range(a - 1, b):
        page = doc[pno]
        h = page.rect.height
        top = h * page_cfg["top"] / page_cfg["height"]
        bot = h * (page_cfg["height"] - page_cfg["bottom"]) / page_cfg["height"]
        for (x0, y0, x1, y1), sz, chars in lines_of(page, lo, hi):
            if y1 > bot + 2:
                continue
            steps = [c2["origin"][0] - c1["origin"][0] for c1, c2 in zip(chars, chars[1:])
                     if HAN.match(c1["c"]) and HAN.match(c2["c"]) and abs(c1["origin"][1] - c2["origin"][1]) < 1]
            if len(steps) >= 3:
                med = sorted(steps)[len(steps) // 2]
                if med > sz * 1.12:
                    loose.append((pno + 1, round(med / sz, 2), "".join(c["c"] for c in chars)[:30]))
            text = "".join(c["c"] for c in chars).strip()
            han = [c for c in chars if HAN.match(c["c"])]
            if len(han) == 1 and len(text) <= 3 and HAN.match(text[0]):
                single.append((pno + 1, text))
        last_y = max([y1 for (x0, y0, x1, y1), _, _ in lines_of(page, size * 0.78, 30) if y1 <= bot + 2] or [0])
        if last_y:
            gap = (bot - last_y) / (bot - top)
            if gap > 0.22:
                gaps.append((pno + 1, round(gap, 2)))
    print("正文字号：%spt" % size)
    print("字距明显拉开的行：%d" % len(loose))
    for x in loose[:40]:
        print("  ", x)
    print("单字成行：%d" % len(single))
    for x in single[:60]:
        print("  ", x)
    print("页底留白 >22%% 的页：%d" % len(gaps))
    print("  ", gaps)


if __name__ == "__main__":
    main()
