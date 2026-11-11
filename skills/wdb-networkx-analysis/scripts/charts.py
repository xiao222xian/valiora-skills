#!/usr/bin/env python3
"""Render the report charts as theme-aware SVG (sentinel colours become CSS variables)."""
import argparse
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm, TwoSlopeNorm

# Sentinels are swapped for CSS variables after rendering, so charts follow the page theme.
INK, AXIS, GRID, S1, S2 = "#010101", "#020202", "#030303", "#2a78d6", "#eb6834"
SWAP = {INK: "var(--ink-2)", AXIS: "var(--axis)", GRID: "var(--hair)", S1: "var(--s1)", S2: "var(--s2)"}
BLUES = LinearSegmentedColormap.from_list("blues", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"])
DIVERGE = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#86b6ef", "#f0efec", "#f19a9a", "#e34948"])

plt.rcParams.update({
    "svg.fonttype": "none", "font.family": ["PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", "Arial Unicode MS", "sans-serif"],
    "font.size": 10.5, "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.facecolor": "none", "figure.facecolor": "none",
    "savefig.facecolor": "none", "legend.frameon": False, "xtick.major.size": 0, "ytick.major.size": 0,
    "axes.axisbelow": True, "lines.linewidth": 2,
})


def svg(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    out = buf.getvalue()
    out = out[out.index("<svg"):]
    for k, v in SWAP.items():
        out = out.replace(k, v).replace(k.upper(), v)
    return out


def heat_axes(ax):
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", required=True, help="analyze.py 的工作目录")
    args = ap.parse_args()
    work = Path(args.work)
    R = json.loads((work / "results.json").read_text())
    C = json.loads((work / "chartdata.json").read_text())
    out = {}

    def degree():
        fig, ax = plt.subplots(figsize=(6.6, 3.4))
        for key, color, name in (("group", S2, "每个群里的好友数"), ("friend", S1, "每位好友的共同群数")):
            y = C["degree"][key]
            ax.plot(range(1, len(y) + 1), y, color=color, label=name)
            # Label each line at its start, where the curves are far apart.
            ax.annotate(name, (1, y[0]), xytext=(6, 5), textcoords="offset points", va="bottom", color=INK, fontsize=9.5)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("排名（对数）"); ax.set_ylabel("数量（对数）")
        ax.legend(loc="upper right")
        return svg(fig)

    def path():
        sw = R["smallworld"]
        real = {int(k): v for k, v in sw["distReal"].items()}
        rand = {int(k): v for k, v in sw["distRand"].items()}
        ks = sorted(set(real) | set(rand))
        fig, ax = plt.subplots(figsize=(6.6, 3.0))
        w = 0.38
        ax.bar([k - w / 2 - 0.01 for k in ks], [real.get(k, 0) * 100 for k in ks], w, color=S1, label="你的网络")
        ax.bar([k + w / 2 + 0.01 for k in ks], [rand.get(k, 0) * 100 for k in ks], w, color=S2, label="同度序列的随机网络")
        ax.set_xticks(ks); ax.set_xlabel("两位好友之间隔了几层（经共同群）"); ax.set_ylabel("好友对占比 %")
        ax.grid(axis="x", visible=False); ax.legend(loc="upper right")
        return svg(fig)

    def abcore():
        a = R["abcore"]
        grid = [[c[0] for c in row] for row in a["grid"]]
        fig, ax = plt.subplots(figsize=(6.6, 3.8))
        ax.imshow([[max(v, 0.9) for v in row] for row in grid], cmap=BLUES, norm=LogNorm(vmin=1, vmax=max(max(r) for r in grid)), aspect="auto")
        for i, row in enumerate(grid):
            for j, v in enumerate(row):
                ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=8.5, color="#ffffff" if v > 300 else "#0b0b0b")
        ax.set_xticks(range(len(a["betas"])), [f"≥{b}" for b in a["betas"]])
        ax.set_yticks(range(len(a["alphas"])), [f"≥{x}" for x in a["alphas"]])
        ax.set_xlabel("β：群里至少有几位核心好友"); ax.set_ylabel("α：好友至少在几个核心群里")
        heat_axes(ax)
        return svg(fig)

    def kcore():
        d = {int(k): v for k, v in C["kcore"].items()}
        fig, ax = plt.subplots(figsize=(6.6, 2.8))
        ks = sorted(d)
        ax.bar(ks, [d[k] for k in ks], width=0.8, color=S1)
        ax.set_xlabel("核数 k"); ax.set_ylabel("好友数"); ax.set_yscale("log"); ax.grid(axis="x", visible=False)
        return svg(fig)

    def scatter():
        s = C["scatter"]
        fig, ax = plt.subplots(figsize=(6.6, 3.4))
        ax.scatter(s["pagerank"], [m + 1 for m in s["msg"]], s=6, color=S1, alpha=0.35, linewidths=0)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("网络影响力 PageRank（对数）"); ax.set_ylabel("私聊消息数 + 1（对数）")
        return svg(fig)

    def block():
        dens = R["communities"]["block"]
        K = len(dens)
        flat = [v for row in dens for v in row if v > 0]
        fig, ax = plt.subplots(figsize=(5.2, 4.4))
        ax.imshow([[max(v, min(flat)) for v in row] for row in dens], cmap=BLUES, norm=LogNorm(vmin=min(flat), vmax=max(flat)))
        ax.set_xticks(range(K), [str(k + 1) for k in range(K)]); ax.set_yticks(range(K), [str(k + 1) for k in range(K)])
        ax.set_xlabel("结构社区"); ax.set_ylabel("结构社区")
        heat_axes(ax)
        return svg(fig)

    def richclub():
        r = C["richclub"]
        fig, ax = plt.subplots(figsize=(6.6, 3.0))
        ax.plot(r["k"], r["real"], color=S1, label="你的网络")
        ax.plot(r["k"], r["rand"], color=S2, label="保度随机重连")
        ax.set_xlabel("度阈值 k"); ax.set_ylabel("富人俱乐部系数 φ(k)"); ax.legend(loc="upper left")
        return svg(fig)

    def spearman():
        sp = R["centrality"]["spearman"]
        keys, M = sp["keys"], sp["matrix"]
        fig, ax = plt.subplots(figsize=(5.8, 4.6))
        ax.imshow(M, cmap=DIVERGE, norm=TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1))
        for i in range(len(keys)):
            for j in range(len(keys)):
                ax.text(j, i, f"{M[i][j]:.2f}", ha="center", va="center", fontsize=8.5, color="#ffffff" if abs(M[i][j]) > 0.7 else "#0b0b0b")
        ax.set_xticks(range(len(keys)), keys, rotation=40, ha="right"); ax.set_yticks(range(len(keys)), keys)
        heat_axes(ax)
        return svg(fig)

    for name, fn in [("degree", degree), ("path", path), ("abcore", abcore), ("kcore", kcore), ("scatter", scatter),
                     ("block", block), ("richclub", richclub), ("spearman", spearman)]:
        try:
            out[name] = fn()
        except (KeyError, ValueError, TypeError) as exc:  # a skipped analysis leaves its chart out
            print(f"chart skipped: {name} ({type(exc).__name__}: {exc})")
    (work / "charts.json").write_text(json.dumps(out))
    print(json.dumps({"charts": list(out)}))


if __name__ == "__main__":
    main()
