#!/usr/bin/env python3
"""Build the local HTML network analysis report from results.json and charts.json."""
import argparse
import html
import json
import re
from pathlib import Path

CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink-2:#52514e;--muted:#898781;--hair:#e1e0d9;--axis:#c3c2b7;--s1:#2a78d6;--s2:#eb6834;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink-2:#c3c2b7;--muted:#898781;--hair:#2c2c2a;--axis:#383835;--s1:#3987e5;--s2:#d95926;--accent:#3987e5}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink-2:#c3c2b7;--muted:#898781;--hair:#2c2c2a;--axis:#383835;--s1:#3987e5;--s2:#d95926;--accent:#3987e5}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);font:15px/1.75 system-ui,-apple-system,"PingFang SC","Segoe UI",sans-serif}
.wrap{max-width:880px;margin:0 auto;padding:40px 20px 80px}h1{font-size:28px;line-height:1.3;margin:0 0 8px}
.lede{color:var(--ink-2);margin:0}.meta{color:var(--muted);font-size:13px;margin-top:8px}
h2{font-size:20px;margin:48px 0 10px;padding-top:12px;border-top:1px solid var(--hair)}h3{font-size:15px;margin:22px 0 6px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.tile{background:var(--surface);border:1px solid var(--hair);border-radius:10px;padding:12px 14px}.tile .v{font-size:24px;font-weight:650}.tile .l{color:var(--muted);font-size:12.5px}
.findings{background:var(--surface);border:1px solid var(--hair);border-radius:12px;padding:6px 20px 10px}.findings li{margin:8px 0}
figure{margin:16px 0;background:var(--surface);border:1px solid var(--hair);border-radius:12px;padding:14px 14px 8px}figure svg{width:100%;height:auto;display:block}
figcaption{color:var(--muted);font-size:13px;margin-top:6px}table{width:100%;border-collapse:collapse;font-size:13.5px;margin:10px 0;font-variant-numeric:tabular-nums}
th{text-align:left;font-weight:500;color:var(--muted);border-bottom:1px solid var(--hair);padding:6px 8px 6px 0;font-size:12.5px}td{border-bottom:1px solid var(--hair);padding:6px 8px 6px 0}
.num{text-align:right}.scroll{overflow-x:auto}.callout{border-left:3px solid var(--accent);padding:4px 0 4px 14px;color:var(--ink-2)}.muted{color:var(--muted)}
nav.toc{background:var(--surface);border:1px solid var(--hair);border-radius:12px;padding:10px 18px;margin:18px 0;font-size:14px}nav.toc ol{columns:2;column-gap:28px;margin:6px 0}nav.toc a{color:var(--ink-2);text-decoration:none}
.theme{position:fixed;top:14px;right:14px;width:34px;height:34px;border-radius:8px;border:1px solid var(--hair);background:var(--surface);color:var(--ink-2);cursor:pointer}
@media (max-width:640px){nav.toc ol{columns:1}h1{font-size:23px}.wrap{padding:28px 16px 60px}}
"""
THEME_JS = "document.querySelector('.theme').addEventListener('click',()=>{const r=document.documentElement;const d=r.dataset.theme?r.dataset.theme==='dark':matchMedia('(prefers-color-scheme: dark)').matches;r.dataset.theme=d?'light':'dark';});"
MOON = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>'

e = lambda s: html.escape(str(s), quote=True)
fmt = lambda x: f"{int(round(x)):,}"
pct = lambda x, nd=0: f"{x * 100:.{nd}f}%"


def tiles(items):
    return '<div class="tiles">' + "".join(f'<div class="tile"><div class="v">{e(v)}</div><div class="l">{e(l)}</div></div>' for v, l in items) + "</div>"


def table(head, rows, num=()):
    th = "".join(f'<th class="{"num" if i in num else ""}">{e(h)}</th>' for i, h in enumerate(head))
    body = "".join("<tr>" + "".join(f'<td class="{"num" if i in num else ""}">{e(c)}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def md_inline(s):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e(s))


def auto_findings(R):
    """Conservative, data-derived findings; every sentence states the metric it rests on."""
    out = []
    P, SW = R.get("properties"), R.get("smallworld")
    if P and SW:
        out.append(f"**连通程度**：有共同群的 {fmt(P['friendsWithGroups'])} 位好友中，{pct(P['giantShare'],1)} 的节点在同一个连通块里；好友之间平均隔 {SW['meanReal']:.1f} 层群，{pct(SW['within2'])} 在 2 层以内。")
        d3r, d3x = SW["distReal"].get("3", 0), SW["distRand"].get("3", 0)
        tail = f"相隔 3 层的好友对占 {pct(d3r)}，随机网络是 {pct(d3x)}，" + ("说明存在离主体较远的区域。" if d3r > d3x * 1.3 else "两者接近。")
        if SW.get("sigmaLike"):
            out.append(f"**与随机网络对比**：保持度序列的随机网络平均相隔 {SW['meanRand']:.2f} 层、聚集系数 {SW['clusteringRand']:.2f}（你的网络是 {SW['meanReal']:.2f} 与 {SW['clustering']:.2f}，类 σ≈{SW['sigmaLike']:.2f}）；{tail}")
    C = R.get("centrality")
    if C:
        names = "、".join(x["name"] for x in C["groupBetweenness"][:3])
        owned = sum(1 for x in C["groupBetweenness"][:5] if x.get("owned"))
        out.append(f"**枢纽**：介数最高的 5 个节点中有 {C['top5AllGroups']} 个是群，排名前三的是 {names}；介数前五的群里有 {owned} 个由你担任群主。")
        sp = C.get("spearman", {})
        if "私聊消息" in sp.get("keys", []):
            row = sp["matrix"][sp["keys"].index("私聊消息")][:-1]
            out.append(f"**私聊与网络位置**：私聊条数与各项结构中心性的秩相关在 {min(row):.2f}–{max(row):.2f} 之间。")
    I = R.get("interaction")
    if I:
        s = I["segments"]
        out.append(f"**关系类型**：{fmt(s['群里常见、从不私聊（共同群≥10，私聊0）'])} 人和你同在 10 个以上群却从未私聊；{fmt(s['纯私交（私聊≥50，无共同群）'])} 人私聊超过 50 条但没有共同群。")
    AB, KC, RC = R.get("abcore"), R.get("kcore"), R.get("richclub")
    if AB and AB.get("deep"):
        d = AB["deep"]
        extra = ""
        if KC and KC.get("coreByTier"):
            t = KC["coreByTier"]
            extra = f"私聊 200 条以上的好友 k 核中位数 {t.get('私聊≥200', 0):.0f}，未私聊者 {t.get('未私聊·有共同群', 0):.0f}；"
        rc = f"度超过 50 的人之间连边比例是随机的 {RC['ratioAbove50']:.2f} 倍。" if RC and RC.get("ratioAbove50") else ""
        out.append(f"**核心—边缘**：α≥{d['alpha']}、β≥{d['beta']} 的深核有 {fmt(d['friends'])} 位好友、{fmt(d['groups'])} 个群；{extra}{rc}")
    CO = R.get("communities")
    if CO:
        qs = [x["Q"] for x in CO["compare"][:3]]
        gn = CO.get("girvanNewman")
        tail = ""
        if gn:
            tail = f"核心圈 {fmt(gn['nodes'])} 人内部的 Girvan–Newman 最佳模块度为 {gn['bestQ']:.3f}" + ("，几乎切不开。" if gn["bestQ"] < 0.05 else "。")
        out.append(f"**社区结构**：模块度 {min(qs):.2f}–{max(qs):.2f}；{tail}")
    FR = R.get("fragility")
    if FR and FR["soleTie"]:
        out.append(f"**单线关系**：{fmt(FR['singleGroupFriends'])} 位好友只通过一个群与你相连；“{FR['soleTie'][0]['name']}”是其中 {FR['soleTie'][0]['sole']} 人的唯一纽带。")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", required=True, help="analyze.py / charts.py 的工作目录")
    ap.add_argument("--out", required=True, help="输出 HTML 路径")
    ap.add_argument("--findings", help="可选：Agent 撰写的主要发现（每行一条，以 - 开头，可用 **加粗**）")
    ap.add_argument("--title", default="微信好友与群聊网络分析")
    args = ap.parse_args()
    work = Path(args.work)
    R = json.loads((work / "results.json").read_text())
    C = json.loads((work / "charts.json").read_text()) if (work / "charts.json").exists() else {}
    M = R["meta"]
    fig = lambda k, cap: f"<figure>{C[k]}<figcaption>{e(cap)}</figcaption></figure>" if k in C else ""
    S, toc = [], []

    def sec(anchor, title, body):
        toc.append((anchor, title))
        S.append(f'<h2 id="{anchor}">{e(title)}</h2>{body}')

    if args.findings:
        items = [ln.strip()[1:].strip() for ln in Path(args.findings).read_text().splitlines() if ln.strip().startswith("-")]
    else:
        items = auto_findings(R)
    findings = '<section class="findings"><h3>主要发现</h3><ol>' + "".join(f"<li>{md_inline(x)}</li>" for x in items) + "</ol></section>"

    P = R.get("properties", {})
    head = (f'<header><h1>{e(args.title)}</h1><p class="lede">把 {fmt(P.get("friends", 0))} 位好友和 {fmt(P.get("groups", 0))} 个群看成一张“好友—群”二部网络，'
            f'参照 NetworkX 示例库跑了度分布、连通性、小世界、中心性、结构洞、核心—边缘、社区与块模型、谱分析等。</p>'
            f'<p class="meta">快照 {e(M.get("snapshot") or "—")}；消息统计起点 {e(M.get("historyFrom") or "无")}；NetworkX {e(M["networkx"])}，随机种子 {M["seed"]}。本报告只在本机生成，含真实名称，请勿外传。</p></header>')

    sec("method", "数据与建模",
        f"<p>好友与群构成二部图 B，好友入群记一条边，共 {fmt(P.get('edges', 0))} 条。好友投影 P 按 Newman 合作网络加权：同在一个有 n 位好友的群记 1/(n−1)。"
        f"紧密投影只用好友数 ≤{M['cap']} 的群，用于聚集系数、k 核、结构洞与富人俱乐部。介数与接近度用 {M['samples']} 个源点抽样，距离分布用 {M['pathSources']} 个源点；随机基线为保持双方度序列的二部配置模型。</p>")

    if P:
        PR = R.get("projection", {})
        sec("overview", "网络概况", tiles([
            (fmt(P["friendsWithGroups"]), "有共同群的好友"), (fmt(P["isolatedFriends"]), "无共同群的好友"),
            (fmt(P["groupsWithFriends"]), "有好友的群"), (fmt(P["giant"]), "最大连通块节点"),
            (f"{P['fdeg']['median']:.0f} / {P['fdeg']['max']}", "每位好友的共同群（中位/最多）"),
            (f"{P['gdeg']['median']:.0f} / {P['gdeg']['max']}", "每个群里的好友（中位/最多）"),
        ]) + f"<p>最大连通块之外还有 {max(P['componentsNonTrivial'] - 1, 0)} 个小连通块；二部图直径下界 {P['diameterLowerBound']}（约 {P['diameterFriendHops']:.1f} 层群）。"
            + (f"每位好友通过共同群能接触到的好友数中位数为 {PR['reachMedian']:.0f}，最多 {fmt(PR['reachMax'])}（二跳自我网络）。</p>" if PR else "</p>"))
        sec("degree", "度分布", fig("degree", "度排名图（双对数）") +
            f"<p>好友最多的 10 个群占全部入群关系的 {pct(P['top10GroupsShare'],1)}；入群最多的 1% 好友占 {pct(P['top1pctFriendsShare'],1)}；各群好友数基尼系数 {P['gini']:.2f}。</p>")

    SW = R.get("smallworld")
    if SW:
        sec("paths", "连通性、几度分隔与小世界", fig("path", "好友对相隔层数分布：你的网络对比同度序列随机网络") + table(
            ["指标", "你的网络", "随机网络"],
            [["好友平均相隔（层）", f"{SW['meanReal']:.2f}", f"{SW['meanRand']:.2f}"],
             ["紧密投影平均聚集系数", f"{SW['clustering']:.3f}", f"{SW['clusteringRand']:.3f}"],
             ["紧密投影传递性", f"{SW['transitivity']:.3f}", "—"],
             ["全量投影聚集系数（抽样）", f"{SW['clusteringFullApprox']:.3f}", "—"]], num=(1, 2)) +
            "<p>投影后每个群都是完全子图，聚集系数天然偏高，因此以随机基线的比值为准。</p>")

    CE = R.get("centrality")
    if CE:
        body = "<h3>群的介数</h3>" + table(["群", "介数", "我是群主"], [[x["name"], f"{x['value']:.4f}", "是" if x.get("owned") else ""] for x in CE["groupBetweenness"]], num=(1,))
        body += "<h3>好友的介数与 PageRank</h3>" + table(["好友（介数）", "介数"], [[x["name"], f"{x['value']:.4f}"] for x in CE["friendBetweenness"]], num=(1,))
        body += table(["好友（PageRank）", "PageRank ×1000"], [[x["name"], f"{x['value'] * 1000:.2f}"] for x in CE["friendPagerank"]], num=(1,))
        body += fig("spearman", f"各项中心性的 Spearman 秩相关，n = {fmt(CE['spearman']['n'])}")
        if CE["brokers"]:
            body += "<h3>低调的桥：连接不多，但处在关键路径上</h3>" + table(["好友", "介数排名", "共同群数排名", "共同群", "私聊"], [[x["name"], x["btwRank"], x["degRank"], x["groups"], x["msg"]] for x in CE["brokers"]], num=(1, 2, 3, 4))
        if CE["possibleBots"]:
            body += f"<p class='callout'>名称疑似机器人或助手的账号可能抬高部分排名：{e('、'.join(CE['possibleBots']))}。</p>"
        body += "<p class='muted'>特征向量中心性容易集中在稠密小团上，只作参考。</p>"
        sec("centrality", "中心性：枢纽与桥", body)

    I = R.get("interaction")
    if I:
        tiers = I["sharedMedianByTier"]
        sec("interaction", "私聊与网络位置", fig("scatter", "每个点是一位好友：PageRank 与私聊条数") +
            table(["人群", "人数"], [[k, fmt(v)] for k, v in I["segments"].items()], num=(1,)) +
            table(["亲疏层", "共同群中位数"], [[k, f"{v:.0f}"] for k, v in tiers.items()], num=(1,)) +
            f"<p>你在 {fmt(I['groupsSpoke'])} / {fmt(I['groupsTotal'])} 个群里发过言，发言条数与群内好友数的秩相关为 {I['rhoSaidFriends']:.2f}。</p>" +
            "<h3>纯私交：私聊最多但没有共同群的人</h3>" + table(["好友", "私聊", "我发出"], [[x["name"], fmt(x["msg"]), fmt(x["sent"])] for x in I["pureDirect"]], num=(1, 2)))

    SH = R.get("structuralHoles")
    if SH:
        inner = f"，私聊 ≥{M['inner']} 条的好友中位数为 {SH['medianInner']:.3f}" if SH.get("medianInner") is not None else ""
        sec("holes", "结构洞", table(["好友", "约束度", "有效规模", "同群好友", "私聊"], [[x["name"], f"{x['constraint']:.4f}", f"{x['effSize']:.0f}", x["degree"], x["msg"]] for x in SH["brokers"]], num=(1, 2, 3, 4)) +
            f"<p>约束度越低，联系人彼此越不相识。全体中位数 {SH['median']:.3f}{inner}。约束度与有效规模按 Burt 公式用稀疏矩阵计算，覆盖 {fmt(SH['evaluated'])} 个节点。</p>")

    AB, KC, RC = R.get("abcore"), R.get("kcore"), R.get("richclub")
    if AB or KC:
        body = fig("abcore", "α/β 核规模（格内为好友数）")
        if AB and AB.get("deep"):
            d = AB["deep"]
            body += f"<p>α≥{d['alpha']}、β≥{d['beta']} 时剩下 {fmt(d['friends'])} 位好友、{fmt(d['groups'])} 个群。</p>" + table(["深核好友", "共同群", "私聊"], [[x["name"], x["groups"], fmt(x["msg"])] for x in d["topFriends"]], num=(1, 2))
        if KC:
            body += fig("kcore", "紧密投影的 k 核分布（纵轴对数）") + f"<p>最大 k 核 {KC['kmax']}，最里层 {fmt(KC['innerSize'])} 人，洋葱分解 {fmt(KC['onionLayers'])} 层。</p>"
            if KC.get("coreByTier"):
                body += table(["亲疏层", "k 核中位数"], [[k, f"{v:.0f}"] for k, v in KC["coreByTier"].items()], num=(1,))
        if RC:
            body += fig("richclub", "富人俱乐部系数") + (f"<p>度超过 50 后，高连接者之间连边比例中位数是随机的 {RC['ratioAbove50']:.2f} 倍。</p>" if RC.get("ratioAbove50") else "")
        sec("core", "核心—边缘结构", body)

    CO = R.get("communities")
    if CO:
        body = table(["算法", "社区数", "≥50 人", "模块度 Q"], [[x["algo"], x["n"], x["big"], f"{x['Q']:.3f}"] for x in CO["compare"]], num=(1, 2, 3))
        body += table(["社区", "人数", "私聊中位数", "私聊≥50 的人", "代表群（好友占六成以上）"], [[k + 1, fmt(m["size"]), "—" if m["msgMedian"] is None else f"{m['msgMedian']:.0f}", fmt(m["close"]), "；".join(m["repGroups"]) or "—"] for k, m in enumerate(CO["main"])], num=(0, 1, 2, 3))
        body += "<p class='callout'>结构社区只表示谁和谁常在同一批小群，代表群仅用于辨认，不代表同一类人。</p>"
        body += fig("block", "块模型：社区间连边密度（对数刻度）")
        if CO.get("withinShare") is not None:
            body += f"<p>按权重计，{pct(CO['withinShare'])} 的同群关系落在社区内部。</p>"
        gn = CO.get("girvanNewman")
        if gn:
            body += f"<p>核心圈 {fmt(gn['nodes'])} 人（{fmt(gn['edges'])} 条同群关系）内部 Girvan–Newman 前 8 层最佳模块度 {gn['bestQ']:.3f}，切分规模 {e(' / '.join(map(str, gn['parts'])))}。</p>"
        sec("communities", "社区结构与块模型", body)

    BP = R.get("bipartite")
    if BP:
        body = f"<p>共有 {fmt(BP['groupPairsSharing'])} 对群至少共享一位好友。好友都不少于 10 位的群里，重叠度最高的是：</p>" + table(["群 A", "群 B", "共同好友", "Jaccard"], [[x["a"], x["b"], x["shared"], f"{x['jaccard']:.2f}"] for x in BP["topOverlap"][:10]], num=(2, 3))
        if BP["series"]:
            body += "<h3>指定系列群的成员重叠</h3>" + table(["群 A", "群 B", "共同好友", "Jaccard"], [[x["a"], x["b"], x["shared"], f"{x['jaccard']:.3f}"] for x in BP["series"]], num=(2, 3))
        body += f"<p>群重叠最小生成树覆盖 {BP['mst']['nodes']} 个群，连接度最高的有：{e('、'.join(BP['mst']['hubs']))}。二部 Latapy 聚集系数：好友侧 {BP['latapyFriends']:.3f}，群侧 {BP['latapyGroups']:.3f}。</p>"
        sec("overlap", "群与群的重叠", body)

    TR = R.get("trustrank")
    if TR:
        sec("trustrank", "离核心圈最近、却很少私聊的人", f"<p>以私聊 ≥{M['inner']} 条的 {TR['seeds']} 人为种子跑个性化 PageRank（TrustRank 做法），只列私聊少于 10 条的人：</p>" +
            table(["好友", "私聊", "共同群"], [[x["name"], x["msg"], x["groups"]] for x in TR["quiet"]], num=(1, 2)))

    FR = R.get("fragility")
    if FR:
        sec("fragility", "脆弱点：单线关系", table(["群", "以它为唯一纽带的好友", "群内好友", "我的发言"], [[x["name"], x["sole"], x["friends"], fmt(x["said"])] for x in FR["soleTie"]], num=(1, 2, 3)) +
            f"<p>{fmt(FR['singleGroupFriends'])} 位好友只通过一个群相连；最大连通块有 {fmt(FR['articulation'])} 个关节点，其中群 {fmt(FR['articulationGroups'])} 个。</p>")

    AS, DD, SN, SP = R.get("assortativity"), R.get("dedensify"), R.get("snap"), R.get("spectral")
    body = ""
    if AS:
        body += f"<p>同配性：度 {AS['degree']:.3f}" + (f"，亲疏层 {AS['tier']:.3f}，log 私聊 {AS['logMsg']:.3f}" if "tier" in AS else "") + "。</p>"
    if DD:
        body += f"<p>Dedensification：阈值 20 / 50 / 100 时边数由 {fmt(DD['before'])} 降到 {fmt(DD['20'])} / {fmt(DD['50'])} / {fmt(DD['100'])}。</p>"
    if SN:
        state = "已完成" if SN.get("completed") else (f"在 {SN['timeoutSec']} 秒内未完成" if SN.get("timeoutSec") else "未运行（默认跳过，--snap-timeout 可尝试）")
        body += f"<p>SNAP 图摘要：{state}。按“亲疏层 × 群发言活跃度”分组后的连边计数如下：</p>" + table(["好友亲疏层", "常发言的群（≥50）", "偶尔发言的群", "未发言的群"], [[lab, fmt(r[0]), fmt(r[1]), fmt(r[2])] for lab, r in zip(["私聊≥200", "私聊50–199", "私聊10–49", "私聊1–9", "未私聊·有共同群"], SN["tierBlock"])], num=(1, 2, 3))
    if SP:
        body += f"<p>谱特征：紧密投影最大连通块代数连通度 {SP['algebraicConnectivity']:.4f}，近零特征值 {SP['nearZero']} 个，前段最大间隙出现在第 {SP['largestGapAfter']} 个特征值之后。</p>"
    if body:
        sec("more", "同配性、压缩摘要与谱特征", body)

    notes = [f"{k}：{v}" for k, v in R.get("skipped", {}).items()] + [f"{k} 出错：{v}" for k, v in R.get("errors", {}).items()]
    sec("appendix", "附录：口径与局限",
        "<ul><li>消息统计只来自本机聊天记录；群成员名单为本机记录，可能不完整。</li><li>介数、接近度、距离分布基于抽样；随机基线为单次实现。</li><li>社区划分依赖算法与随机种子，边界不是硬性的。</li></ul>" +
        (f"<p class='muted'>未运行或出错：{e('；'.join(notes))}</p>" if notes else "") +
        f"<p class='muted'>计算耗时：{e('、'.join(f'{k} {v}s' for k, v in R.get('timing', {}).items()))}</p>")

    nav = '<nav class="toc"><b>目录</b><ol>' + "".join(f'<li><a href="#{a}">{e(t)}</a></li>' for a, t in toc) + "</ol></nav>"
    page = (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="referrer" content="no-referrer"><title>{e(args.title)}</title><style>{CSS}</style></head><body>'
            f'<button class="theme" type="button" aria-label="切换明暗主题">{MOON}</button><div class="wrap">{head}{findings}{nav}{"".join(S)}</div>'
            f"<script>{THEME_JS}</script></body></html>")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(json.dumps({"out": str(out), "bytes": out.stat().st_size, "sections": len(toc), "findings": len(items)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
