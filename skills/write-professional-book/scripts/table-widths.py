#!/usr/bin/env python3
"""按内容重设 pipe 表格的列宽（直接改写源稿，幂等）。

pandoc 在表格行超过 --columns（默认 72）时，用分隔行中各列破折号数量的比例决定列宽；
本脚本把分隔行写满 72 个破折号，因而总会触发按比例设宽。规则如下（显示宽度：中文计 2，西文计 1.1）：
1. 每列保底宽度 = max(最长不可断西文串 + 2, 表头中最长的四字片段)；
2. 短列（最长单元格不超过 SHORT）给足“最长内容 + 3”；
3. 长列先给保底宽度，再按平均内容长度分配剩余宽度；
4. 二次调整：按实际版心宽度与表格字号模拟每格的折行，末行只剩一个字（如“工具电子/化”）时，
   从其他列匀出少量宽度，直到单字折行不再减少。
表格前一行（或表题前一行）写有 <!-- widths: fixed --> 的表格不处理（供表单类表格手工设宽）。
单元格内的 `\\newline{}`{=latex} 视为强制换行，按最长一段计宽。

用法：python3 table-widths.py [--book 书根目录] 文件 ...
"""
import argparse
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import booklib  # noqa: E402

SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")
TOTAL = 74.0
SHORT = 16
DASHES = 72
TABCOL_PT = 6.0    # \tabcolsep
LINE_PT = FONT_PT = None  # 版心宽、表格字号（\small），main() 中按 typeset.yaml 设置


def segments(s):
    s = re.sub(r"`\\newline(\{\})?`\{=latex\}", "\n", s)
    s = re.sub(r"`\\[a-zA-Z]+\{([^`]*)\}`\{=latex\}", r"\1", s)
    s = re.sub(r"`[^`]*`\{=latex\}", "", s)
    s = re.sub(r"\*\*|`", "", s.strip())
    return [x.strip() for x in s.split("\n")]


def width(s):
    return max(sum(2.0 if ord(c) > 0x2E80 else 1.1 for c in seg) for seg in segments(s))


def em(seg):
    """排版宽度（以字宽计）：汉字与全角标点 1，西文约 0.5。"""
    return sum(1.0 if ord(c) > 0x2E80 else 0.52 for c in seg)


def longest_token(s):
    toks = re.findall(r"[A-Za-z0-9][A-Za-z0-9.:/_()%]*", " ".join(segments(s)))
    return min(max((len(t) * 1.1 for t in toks), default=0), 16)


def split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return re.split(r"(?<!\\)\|", s)


OPEN = "“‘（《〔【"
CLOSE = "”’）》〕】，。、；：？！…"


def tokens(seg):
    """切成排版单位：汉字与全角标点各算一个，连续的西文、数字算一个不可断的整体。"""
    out = []
    for m in re.finditer(r"[A-Za-z0-9.,:%/()\-+&@~ ]+(?: [A-Za-z0-9.,:%/()\-+&@]+)*|.", seg):
        t = m.group(0)
        if t.isspace():
            continue
        out.append((t, em(t)))
    return out


def layout(seg, cap):
    """按行宽 cap（字）贪心折行，计入行首、行尾禁则；返回每行的汉字数。"""
    lines, cur, w = [], [], 0.0
    for t, tw in tokens(seg):
        if w + tw <= cap + 0.05 or not cur:
            cur.append((t, tw))
            w += tw
            continue
        if t in CLOSE and w + 0.5 <= cap + 0.05:
            # 行末标点可挤进半个字
            cur.append((t, tw))
            w = cap
            continue
        carry = []
        if t in CLOSE and len(cur) > 1:
            carry = [cur.pop()]
        while len(cur) > 1 and cur[-1][0] in OPEN:
            carry.insert(0, cur.pop())
        lines.append(cur)
        cur = carry + [(t, tw)]
        w = sum(x[1] for x in cur)
    if cur:
        lines.append(cur)
    return [sum(1 for t, _ in ln if re.match(r"[一-鿿]", t)) for ln in lines]


def orphans(dashes, cells_by_col):
    """估算单字折行数：末行只有一个汉字（可带标点）计为一次。"""
    n = len(dashes)
    avail = (LINE_PT - 2 * (n - 1) * TABCOL_PT) / FONT_PT
    tot = sum(dashes)
    count = 0
    for i, cells in enumerate(cells_by_col):
        cap = dashes[i] / tot * avail
        if cap < 2:
            continue
        for cell in cells:
            for seg in segments(cell):
                if em(seg) <= cap:
                    continue
                han = layout(seg, cap)
                if len(han) >= 2 and han[-1] <= 1:
                    count += 1
    return count


def fix_orphans(dashes, cells_by_col, floors):
    """贪心地在列之间挪动宽度（每次 1—6 个破折号），只接受让单字折行减少的调整。"""
    dashes = list(dashes)
    best = orphans(dashes, cells_by_col)
    for _ in range(30):
        if best == 0:
            break
        cand = None
        for i in range(len(dashes)):
            for j in range(len(dashes)):
                if i == j:
                    continue
                for d in (1, 2, 3, 4, 5, 6):
                    if dashes[j] - d < floors[j]:
                        break
                    trial = list(dashes)
                    trial[i] += d
                    trial[j] -= d
                    c = orphans(trial, cells_by_col)
                    if c < best and (cand is None or (c, d) < (cand[0], cand[3])):
                        cand = (c, i, j, d)
        if cand is None:
            break
        best, i, j, d = cand
        dashes[i] += d
        dashes[j] -= d
    return dashes


def rebuild_sep(sep_line, head, body):
    seps = split_row(sep_line)
    n = len(seps)
    heads = split_row(head) + [""] * n
    cols = [[] for _ in range(n)]
    cells_by_col = [[heads[i]] for i in range(n)]
    tok = [0.0] * n
    for r in body:
        cells = split_row(r)
        for i in range(min(n, len(cells))):
            cols[i].append(min(width(cells[i]), 120))
            cells_by_col[i].append(cells[i])
            tok[i] = max(tok[i], longest_token(cells[i]))
    for i in range(n):
        tok[i] = max(tok[i], longest_token(heads[i]))
    mx = [max(c) if c else 2 for c in cols]
    mean = [sum(c) / len(c) if c else 2 for c in cols]
    hw = [width(heads[i]) for i in range(n)]
    floor = [max(tok[i] + 2, (hw[i] if hw[i] <= 8 else math.ceil(hw[i] / 4) * 2) + 1.5, 5) for i in range(n)]
    short = [mx[i] <= SHORT for i in range(n)]
    w = [0.0] * n
    for i in range(n):
        if short[i]:
            w[i] = max(floor[i], min(mx[i], 12) + 1.5)
    longs = [i for i in range(n) if not short[i]]
    if longs:
        fixed = sum(w[i] for i in range(n) if short[i])
        avail = TOTAL - fixed
        base = sum(floor[i] for i in longs)
        extra = max(avail - base, 0.3 * TOTAL)
        tot = sum(mean[i] for i in longs)
        for i in longs:
            w[i] = floor[i] + extra * mean[i] / tot
    s = sum(w)
    dashes = [max(3, round(DASHES * w[i] / s)) for i in range(n)]
    floors = [max(3, round(DASHES * floor[i] / s)) for i in range(n)]
    dashes = fix_orphans(dashes, cells_by_col, floors)
    out = []
    for i, cell in enumerate(seps):
        c = cell.strip()
        lft = ":" if c.startswith(":") else ""
        rgt = ":" if c.endswith(":") and len(c) > 1 else ""
        out.append(lft + "-" * dashes[i] + rgt)
    return "|" + "|".join(out) + "|"


def process(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    changed = 0
    i = 0
    while i < len(lines) - 1:
        if lines[i].lstrip().startswith("|") and SEP.match(lines[i + 1]):
            j = i + 2
            body = []
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                body.append(lines[j])
                j += 1
            above = [lines[k] for k in range(i - 1, -1, -1) if lines[k].strip()][:2]
            # 标记可以紧贴表头，也可以在表题之前
            fixed = bool(above) and ("widths: fixed" in above[0] or (
                re.match(r"^表\s*[0-9A-Z]+-\d+", above[0]) and len(above) > 1 and "widths: fixed" in above[1]))
            if not fixed:
                new = rebuild_sep(lines[i + 1], lines[i], body)
                if new != lines[i + 1]:
                    lines[i + 1] = new
                    changed += 1
            i = j
        else:
            i += 1
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    print("%s: %d 个表格" % (path, changed))


def main():
    global LINE_PT, FONT_PT
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--book", default=".", help="书根目录（含 typeset.yaml），默认当前目录")
    ap.add_argument("files", nargs="+", help="要处理的 Markdown 源稿")
    args = ap.parse_args()
    book = booklib.Book(args.book)
    LINE_PT, FONT_PT = book.text_w, book.small_pt
    for p in args.files:
        process(p)


if __name__ == "__main__":
    main()
