#!/usr/bin/env python3
"""Run NetworkX analyses on a friend–group network (wdb-network/v1) and write results.json."""
import argparse
import json
import math
import random
import re
import signal
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import scipy.sparse as sp
from scipy import stats

TIER_LABEL = ["私聊≥200", "私聊50–199", "私聊10–49", "私聊1–9", "未私聊·有共同群", "未私聊·无共同群"]
BOT_HINT = re.compile(r"助手|机器人|小助理|bot\b|Bot\b|BOT\b|AI助理")


def burt(G, weight="weight"):
    """Burt constraint and effective size on sparse matrices.

    Same formulas as networkx.constraint / effective_size(nodes=...), which are pure
    Python and take seconds per high-degree node on dense friend projections.
    """
    nodes = list(G)
    A = nx.to_scipy_sparse_array(G, nodelist=nodes, weight=weight, format="csr").astype(float)
    A = (A + A.T).tocsr()
    rs = np.asarray(A.sum(axis=1)).ravel()
    P = (sp.diags(1 / np.where(rs > 0, rs, 1)) @ A).tocsr()
    mask = (A > 0).astype(float).tocsr()
    cons = np.asarray((P + (P @ P).multiply(mask)).power(2).sum(axis=1)).ravel()
    rmax = np.asarray(A.max(axis=1).todense()).ravel()
    M = (sp.diags(1 / np.where(rmax > 0, rmax, 1)) @ A).tocsr()
    T = (mask @ M).multiply(mask)
    deg = np.asarray(mask.sum(axis=1)).ravel()
    esize = deg - np.asarray(P.multiply(T).sum(axis=1)).ravel()
    return dict(zip(nodes, cons)), dict(zip(nodes, esize))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="network.json（wdb-network/v1）")
    ap.add_argument("--work", required=True, help="私有工作目录，写入 results.json 与 chartdata.json")
    ap.add_argument("--cap", type=int, default=50, help="紧密投影只使用好友数不超过该值的群（默认 50）")
    ap.add_argument("--samples", type=int, default=1000, help="介数与接近度抽样源点数（默认 1000）")
    ap.add_argument("--path-sources", type=int, default=600, help="距离分布抽样源点数（默认 600）")
    ap.add_argument("--inner", type=int, default=200, help="核心圈的私聊条数阈值（默认 200）")
    ap.add_argument("--series", help="可选：群名正则，比较同一系列群的成员重叠")
    ap.add_argument("--snap-timeout", type=int, default=0, help="大于 0 时尝试 SNAP 图摘要并限时（秒）；默认跳过")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    N = json.loads(Path(args.input).read_text())
    if N.get("schema") != "wdb-network/v1":
        raise SystemExit("输入不是 wdb-network/v1")
    R = {"errors": {}, "timing": {}, "skipped": {}}
    friends, groups = N["friends"], N["groups"]
    NF, NG = len(friends), len(groups)
    fname = [f["name"] for f in friends]
    gname = [g["name"] for g in groups]
    gsize = [g["size"] for g in groups]
    fmsg = [f.get("msg", 0) for f in friends]
    fsent = [f.get("sent", 0) for f in friends]
    gsaid = [g.get("said", 0) for g in groups]
    gown = [bool(g.get("owner_is_me")) for g in groups]
    has_msg = bool(N.get("has_messages")) and any(fmsg)
    members = [[] for _ in groups]
    fgroups = [[] for _ in friends]
    for j, i in N["memberships"]:
        members[j].append(i)
        fgroups[i].append(j)

    def ftier(i):
        n = fmsg[i]
        return 0 if n >= 200 else 1 if n >= 50 else 2 if n >= 10 else 3 if n >= 1 else 4 if fgroups[i] else 5

    F = lambda i: f"f{i}"
    Gn = lambda j: f"g{j}"
    idx = lambda n: int(n[1:])
    label = lambda n: fname[idx(n)] if n[0] == "f" else gname[idx(n)]

    def top(d, k=15, filt=None):
        items = sorted(((n, v) for n, v in d.items() if filt is None or filt(n)), key=lambda x: -x[1])[:k]
        return [{"name": label(n), "kind": n[0], "idx": idx(n), "value": float(v)} for n, v in items]

    def section(name, needs_msg=False):
        def deco(fn):
            if needs_msg and not has_msg:
                R["skipped"][name] = "没有私聊或发言条数"
                return fn
            t0 = time.time()
            try:
                fn()
            except Exception as exc:  # one failing analysis must not block the report
                R["errors"][name] = f"{type(exc).__name__}: {exc}"
                traceback.print_exc()
            R["timing"][name] = round(time.time() - t0, 1)
            print(f"[{R['timing'][name]:6.1f}s] {name}", flush=True)
            return fn
        return deco

    B = nx.Graph()
    B.add_nodes_from((F(i), {"bipartite": 0}) for i in range(NF))
    B.add_nodes_from((Gn(j), {"bipartite": 1}) for j in range(NG))
    B.add_edges_from((Gn(j), F(i)) for j, m in enumerate(members) for i in m)
    if B.number_of_edges() == 0:
        raise SystemExit("没有任何好友入群关系，无法分析")
    giant = max(nx.connected_components(B), key=len)
    Bc = B.subgraph(giant).copy()

    def project(cap=None):
        w, c = defaultdict(float), Counter()
        for m in members:
            n = len(m)
            if n < 2 or (cap and n > cap):
                continue
            s = sorted(m)
            inc = 1 / (n - 1)
            for a in range(n):
                for b in range(a + 1, n):
                    w[(s[a], s[b])] += inc
                    c[(s[a], s[b])] += 1
        P = nx.Graph()
        P.add_edges_from((F(a), F(b), {"weight": x, "shared": c[(a, b)]}) for (a, b), x in w.items())
        return P

    t0 = time.time()
    P = project()
    P50 = project(args.cap)
    Pg = P.subgraph(max(nx.connected_components(P), key=len)).copy()
    P50g = P50.subgraph(max(nx.connected_components(P50), key=len)).copy()
    print(f"projections {time.time() - t0:.1f}s: P {P.number_of_edges():,} edges, P{args.cap} {P50.number_of_edges():,}", flush=True)
    R["meta"] = {"networkx": nx.__version__, "seed": args.seed, "cap": args.cap, "samples": args.samples,
                 "pathSources": args.path_sources, "inner": args.inner, "hasMessages": has_msg,
                 "snapshot": N.get("snapshot"), "historyFrom": N.get("history_from")}
    chart = {}

    @section("properties")
    def _():
        comps = sorted((len(c) for c in nx.connected_components(B)), reverse=True)
        fdeg = np.array([len(x) for x in fgroups])
        gdeg = np.array([len(m) for m in members])
        connected = int((fdeg > 0).sum() + (gdeg > 0).sum())
        diam = nx.approximation.diameter(Bc)
        s = np.sort(gdeg)[::-1]
        sf = np.sort(fdeg)[::-1]
        k1 = max(1, int((sf > 0).sum() * 0.01))
        g = np.sort(gdeg[gdeg > 0]); n = len(g)
        R["properties"] = {
            "friends": NF, "groups": NG, "edges": B.number_of_edges(),
            "friendsWithGroups": int((fdeg > 0).sum()), "groupsWithFriends": int((gdeg > 0).sum()),
            "componentsNonTrivial": sum(1 for c in comps if c > 1), "giant": comps[0], "giantShare": comps[0] / connected,
            "isolatedFriends": int((fdeg == 0).sum()), "isolatedGroups": int((gdeg == 0).sum()),
            "diameterLowerBound": diam, "diameterFriendHops": diam / 2,
            "fdeg": {"median": float(np.median(fdeg[fdeg > 0])), "max": int(fdeg.max())},
            "gdeg": {"median": float(np.median(gdeg[gdeg > 0])), "max": int(gdeg.max())},
            "top10GroupsShare": float(s[:10].sum() / s.sum()), "top1pctFriendsShare": float(sf[:k1].sum() / sf.sum()),
            "gini": float((2 * np.arange(1, n + 1) - n - 1) @ g / (n * g.sum())),
        }
        chart["degree"] = {"friend": sorted(fdeg[fdeg > 0].tolist(), reverse=True), "group": sorted(gdeg[gdeg > 0].tolist(), reverse=True)}

    @section("projection")
    def _():
        pdeg = dict(P.degree())
        pairs = sorted(P.edges(data="shared"), key=lambda e: -e[2])[:15]
        R["projection"] = {
            "edgesP": P.number_of_edges(), "edgesP50": P50.number_of_edges(), "nodesP": P.number_of_nodes(),
            "reachMedian": float(np.median(list(pdeg.values()))), "reachMax": int(max(pdeg.values())),
            "topPairs": [{"a": label(a), "b": label(b), "shared": s} for a, b, s in pairs],
        }

    def friend_distances(G, sources):
        dist = Counter()
        for s in sources:
            for n, d in nx.single_source_shortest_path_length(G, s).items():
                if n[0] == "f" and n != s:
                    dist[d // 2] += 1
        tot = sum(dist.values())
        return {int(k): v / tot for k, v in sorted(dist.items())}

    @section("smallworld")
    def _():
        fnodes = [n for n in Bc if n[0] == "f"]
        real = friend_distances(Bc, random.sample(fnodes, min(args.path_sources, len(fnodes))))
        fdeg = [len(x) for x in fgroups if x]
        gdeg = [len(m) for m in members if m]
        RB = nx.bipartite.configuration_model(fdeg, gdeg, create_using=nx.Graph(), seed=args.seed)
        RBn = nx.relabel_nodes(RB, {n: (f"f{n}" if RB.nodes[n]["bipartite"] == 0 else f"g{n}") for n in RB})
        RBc = RBn.subgraph(max(nx.connected_components(RBn), key=len))
        rf = [n for n in RBc if n[0] == "f"]
        rand = friend_distances(RBc, random.sample(rf, min(args.path_sources, len(rf))))
        rmem = defaultdict(list)
        for u, v in RBn.edges():
            f_, g_ = (u, v) if u[0] == "f" else (v, u)
            rmem[g_].append(f_)
        RP = nx.Graph()
        for m in rmem.values():
            if 2 <= len(m) <= args.cap:
                RP.add_edges_from((m[a], m[b]) for a in range(len(m)) for b in range(a + 1, len(m)))
        mean = lambda d: sum(k * v for k, v in d.items())
        c_real, c_rand = nx.average_clustering(P50), nx.average_clustering(RP)
        R["smallworld"] = {
            "distReal": real, "distRand": rand, "meanReal": mean(real), "meanRand": mean(rand),
            "within2": sum(v for k, v in real.items() if k <= 2), "maxObserved": max(real),
            "clustering": c_real, "clusteringRand": c_rand, "transitivity": nx.transitivity(P50),
            "clusteringFullApprox": nx.approximation.average_clustering(P, trials=20000, seed=args.seed),
            "sigmaLike": (c_real / c_rand) / (mean(real) / mean(rand)) if c_rand else None,
            "removedParallel": sum(fdeg) - RB.number_of_edges(),
        }

    @section("bipartite")
    def _():
        Bw = B.subgraph([n for n in B if B.degree(n) > 0])
        fn = [n for n in Bw if n[0] == "f"]
        gn = [n for n in Bw if n[0] == "g"]
        lat = nx.bipartite.latapy_clustering(Bw, mode="dot")
        red = nx.bipartite.node_redundancy(Bw, [n for n in fn if Bw.degree(n) >= 2])
        shared = Counter()
        for gs in fgroups:
            s = sorted(gs)
            for a in range(len(s)):
                for b in range(a + 1, len(s)):
                    shared[(s[a], s[b])] += 1
        rows = []
        for (a, b), k in shared.items():
            na, nb = len(members[a]), len(members[b])
            if min(na, nb) >= 10:
                rows.append((k / (na + nb - k), a, b, k))
        rows.sort(reverse=True)
        Gov = nx.Graph()
        for jac, a, b, k in rows:
            Gov.add_edge(Gn(a), Gn(b), weight=1 - jac)
        T = nx.minimum_spanning_tree(Gov) if Gov.number_of_edges() else nx.Graph()
        R["bipartite"] = {
            "latapyFriends": float(np.mean([lat[n] for n in fn])), "latapyGroups": float(np.mean([lat[n] for n in gn])),
            "redundancy": float(np.mean(list(red.values()))) if red else None, "groupPairsSharing": len(shared),
            "topOverlap": [{"a": gname[a], "b": gname[b], "jaccard": jac, "shared": k} for jac, a, b, k in rows[:12]],
            "mst": {"nodes": T.number_of_nodes(), "components": nx.number_connected_components(T) if T.number_of_nodes() else 0,
                    "hubs": [gname[idx(n)] for n, _ in sorted(T.degree(), key=lambda x: -x[1])[:6]]},
            "series": [],
        }
        if args.series:
            pat = re.compile(args.series)
            ser = [j for j in range(NG) if pat.search(gname[j]) and members[j]]
            for x in range(len(ser)):
                for y in range(x + 1, len(ser)):
                    a, b = sorted((ser[x], ser[y]))
                    k = shared.get((a, b), 0)
                    na, nb = len(members[a]), len(members[b])
                    R["bipartite"]["series"].append({"a": gname[a], "b": gname[b], "shared": k, "jaccard": k / (na + nb - k)})

    def ab_core(alpha, beta):
        alive_f = {i for i in range(NF) if len(fgroups[i]) >= alpha}
        alive_g = {j for j in range(NG) if len(members[j]) >= beta}
        changed = True
        while changed:
            changed = False
            drop = {i for i in alive_f if sum(1 for j in fgroups[i] if j in alive_g) < alpha}
            if drop:
                alive_f -= drop; changed = True
            dropg = {j for j in alive_g if sum(1 for i in members[j] if i in alive_f) < beta}
            if dropg:
                alive_g -= dropg; changed = True
        return alive_f, alive_g

    @section("abcore")
    def _():
        alphas, betas = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15], [2, 3, 5, 10, 20, 30, 50, 80]
        grid = [[list(map(len, ab_core(a, b))) for b in betas] for a in alphas]
        R["abcore"] = {"alphas": alphas, "betas": betas, "grid": grid}
        for a in reversed(alphas):
            f_, g_ = ab_core(a, 10)
            if len(f_) >= 20:
                R["abcore"]["deep"] = {
                    "alpha": a, "beta": 10, "friends": len(f_), "groups": len(g_),
                    "msgMedian": float(np.median([fmsg[i] for i in f_])) if has_msg else None,
                    "topFriends": [{"name": fname[i], "groups": len(fgroups[i]), "msg": fmsg[i]} for i in sorted(f_, key=lambda i: -len(fgroups[i]))[:12]],
                }
                break

    @section("kcore")
    def _():
        core = nx.core_number(P50)
        kmax = max(core.values())
        tiers = defaultdict(list)
        for n, c in core.items():
            tiers[ftier(idx(n))].append(c)
        R["kcore"] = {"kmax": kmax, "innerSize": sum(1 for c in core.values() if c == kmax),
                      "onionLayers": max(nx.onion_layers(P50).values()),
                      "coreByTier": {TIER_LABEL[t]: float(np.median(v)) for t, v in sorted(tiers.items())} if has_msg else None}
        chart["kcore"] = {int(k): v for k, v in sorted(Counter(core.values()).items())}

    btw_cache = {}

    @section("centrality")
    def _():
        btw = nx.betweenness_centrality(Bc, k=min(args.samples, Bc.number_of_nodes()), seed=args.seed, normalized=True)
        harm = nx.harmonic_centrality(Bc, sources=random.sample(list(Bc), min(args.samples, Bc.number_of_nodes())))
        pr = nx.pagerank(P, weight="weight")
        eig = nx.eigenvector_centrality_numpy(Pg, weight="weight")
        deg, pdeg = dict(B.degree()), dict(P.degree())
        isF, isG = (lambda n: n[0] == "f"), (lambda n: n[0] == "g")
        topg = top(btw, 8, filt=isG)
        R["centrality"] = {
            "groupBetweenness": [dict(x, owned=gown[x["idx"]]) for x in topg],
            "friendBetweenness": top(btw, 10, filt=isF), "friendPagerank": top(pr, 10), "friendEigen": top(eig, 5),
            "top5AllGroups": sum(1 for n, _ in sorted(btw.items(), key=lambda x: -x[1])[:5] if n[0] == "g"),
        }
        fl = [n for n in Bc if isF(n) and n in Pg]
        cols = {"共同群数": [deg[n] for n in fl], "同群好友数": [pdeg[n] for n in fl], "介数": [btw[n] for n in fl],
                "调和接近度": [harm[n] for n in fl], "PageRank": [pr[n] for n in fl], "特征向量": [eig[n] for n in fl]}
        if has_msg:
            cols["私聊消息"] = [fmsg[idx(n)] for n in fl]
        keys = list(cols)
        R["centrality"]["spearman"] = {"keys": keys, "n": len(fl),
                                        "matrix": [[float(stats.spearmanr(cols[a], cols[b]).statistic) for b in keys] for a in keys]}
        rb = {n: r for r, n in enumerate(sorted(fl, key=lambda n: -btw[n]))}
        rd = {n: r for r, n in enumerate(sorted(fl, key=lambda n: -deg[n]))}
        brokers = sorted((n for n in fl if rb[n] < 150 and rd[n] > 600), key=lambda n: rb[n])[:12]
        R["centrality"]["brokers"] = [{"name": label(n), "btwRank": rb[n] + 1, "degRank": rd[n] + 1, "groups": deg[n], "msg": fmsg[idx(n)]} for n in brokers]
        R["centrality"]["possibleBots"] = [fname[i] for i in range(NF) if BOT_HINT.search(fname[i]) and len(fgroups[i]) >= 10][:10]
        if has_msg:
            chart["scatter"] = {"pagerank": [pr[n] for n in fl], "msg": [fmsg[idx(n)] for n in fl]}
        btw_cache.update(btw)

    @section("structuralHoles")
    def _():
        cons, eff = burt(P50g, "weight")
        rows = sorted(((n, cons[n], eff[n], P50g.degree(n)) for n in P50g if P50g.degree(n) >= 20), key=lambda r: r[1])[:12]
        inner = [cons[F(i)] for i in range(NF) if fmsg[i] >= args.inner and F(i) in cons]
        R["structuralHoles"] = {"evaluated": len(cons), "median": float(np.median(list(cons.values()))),
                                "medianInner": float(np.median(inner)) if inner else None,
                                "brokers": [{"name": label(n), "constraint": c, "effSize": e, "degree": d, "msg": fmsg[idx(n)]} for n, c, e, d in rows]}

    @section("fragility")
    def _():
        arts = set(nx.articulation_points(Bc))
        sole = Counter(gs[0] for gs in fgroups if len(gs) == 1)
        R["fragility"] = {"articulation": len(arts), "articulationGroups": sum(1 for n in arts if n[0] == "g"),
                          "singleGroupFriends": sum(1 for gs in fgroups if len(gs) == 1),
                          "soleTie": [{"name": gname[j], "sole": k, "friends": len(members[j]), "said": gsaid[j]} for j, k in sole.most_common(10)]}

    @section("communities")
    def _():
        Q = lambda G, cs: nx.community.modularity(G, cs, weight="weight")
        lou = nx.community.louvain_communities(P, weight="weight", seed=args.seed)
        lou50 = nx.community.louvain_communities(P50, weight="weight", seed=args.seed)
        gm50 = nx.community.greedy_modularity_communities(P50, weight="weight")
        lpa50 = list(nx.community.label_propagation_communities(P50))
        big = lambda cs: sum(1 for c in cs if len(c) >= 50)
        R["communities"] = {"compare": [
            {"algo": "Louvain（全量投影）", "n": len(lou), "big": big(lou), "Q": Q(P, lou)},
            {"algo": f"Louvain（紧密投影 ≤{args.cap}）", "n": len(lou50), "big": big(lou50), "Q": Q(P50, lou50)},
            {"algo": "贪心模块度 CNM（紧密投影）", "n": len(gm50), "big": big(gm50), "Q": Q(P50, gm50)},
            {"algo": "标签传播（紧密投影）", "n": len(lpa50), "big": big(lpa50), "Q": Q(P50, lpa50)},
        ]}
        main = [c for c in sorted(lou, key=len, reverse=True) if len(c) >= 80][:14]
        of = {n: k for k, c in enumerate(main) for n in c}
        desc = []
        for c in main:
            ids = {idx(n) for n in c}
            rep = sorted(((len(m), j) for j, m in enumerate(members) if len(m) >= 5 and sum(1 for i in m if i in ids) / len(m) >= 0.6), reverse=True)
            desc.append({"size": len(c), "msgMedian": float(np.median([fmsg[i] for i in ids])) if has_msg else None,
                         "close": sum(1 for i in ids if fmsg[i] >= 50), "repGroups": [gname[j] for _, j in rep[:3]]})
        K = len(main)
        W = np.zeros((K, K))
        for u, v, w in P.edges(data="weight"):
            a, b = of.get(u), of.get(v)
            if a is None or b is None:
                continue
            W[a, b] += w
            if a != b:
                W[b, a] += w
        sizes = np.array([len(c) for c in main], dtype=float)
        dens = W / np.outer(sizes, sizes)
        np.fill_diagonal(dens, np.diag(W) / (sizes * (sizes - 1) / 2))
        R["communities"].update({"main": desc, "block": dens.tolist(), "withinShare": float(np.trace(W) / W.sum()) if W.sum() else None,
                                 "covered": float(sizes.sum() / P.number_of_nodes())})
        inner = [F(i) for i in range(NF) if fmsg[i] >= args.inner and F(i) in P50]
        H = P50.subgraph(inner).copy()
        H.remove_nodes_from([n for n in list(H) if H.degree(n) == 0])
        if has_msg and H.number_of_nodes() >= 10:
            Hg = H.subgraph(max(nx.connected_components(H), key=len)).copy()
            best = None
            for level, comm in zip(range(8), nx.community.girvan_newman(Hg)):
                q = nx.community.modularity(Hg, comm)
                if best is None or q > best[0]:
                    best = (q, comm)
            parts = sorted(best[1], key=len, reverse=True)
            R["communities"]["girvanNewman"] = {"nodes": Hg.number_of_nodes(), "edges": Hg.number_of_edges(), "bestQ": best[0],
                                                "parts": [len(p) for p in parts[:6]]}
        else:
            R["skipped"]["girvanNewman"] = "核心圈不足 10 人或没有私聊数据"

    @section("richclub")
    def _():
        rc = nx.rich_club_coefficient(P50, normalized=False)
        Rr = P50.copy()
        nx.double_edge_swap(Rr, nswap=Rr.number_of_edges(), max_tries=Rr.number_of_edges() * 20, seed=args.seed)
        rcr = nx.rich_club_coefficient(Rr, normalized=False)
        ks = [k for k in sorted(rc) if rc[k] > 0][::max(1, len(rc) // 60)]
        ratio = [rc[k] / rcr[k] for k in rc if rcr.get(k) and k >= 50]
        R["richclub"] = {"ratioAbove50": float(np.median(ratio)) if ratio else None}
        chart["richclub"] = {"k": ks, "real": [rc[k] for k in ks], "rand": [rcr.get(k, 0) for k in ks]}

    @section("assortativity")
    def _():
        out = {"degree": float(nx.degree_assortativity_coefficient(P50))}
        if has_msg:
            for n in P50:
                P50.nodes[n]["tier"] = ftier(idx(n))
                P50.nodes[n]["logmsg"] = math.log1p(fmsg[idx(n)])
            out["tier"] = float(nx.attribute_assortativity_coefficient(P50, "tier"))
            out["logMsg"] = float(nx.numeric_assortativity_coefficient(P50, "logmsg"))
        R["assortativity"] = out

    @section("trustrank", needs_msg=True)
    def _():
        seeds = {F(i) for i in range(NF) if fmsg[i] >= args.inner and F(i) in P}
        if not seeds:
            R["skipped"]["trustrank"] = "没有达到核心圈阈值的好友"
            return
        tr = nx.pagerank(P, personalization={n: (1.0 if n in seeds else 0.0) for n in P}, weight="weight")
        quiet = sorted(((n, v) for n, v in tr.items() if n not in seeds and fmsg[idx(n)] < 10), key=lambda x: -x[1])[:12]
        R["trustrank"] = {"seeds": len(seeds), "quiet": [{"name": label(n), "msg": fmsg[idx(n)], "groups": len(fgroups[idx(n)])} for n, _ in quiet]}

    @section("interaction", needs_msg=True)
    def _():
        fdeg = [len(g) for g in fgroups]
        by_tier = defaultdict(list)
        for i in range(NF):
            by_tier[ftier(i)].append(fdeg[i])
        spoke = [(gsaid[j], len(members[j])) for j in range(NG) if members[j]]
        R["interaction"] = {
            "segments": {
                "纯私交（私聊≥50，无共同群）": sum(1 for i in range(NF) if fmsg[i] >= 50 and fdeg[i] == 0),
                "群里常见、从不私聊（共同群≥10，私聊0）": sum(1 for i in range(NF) if fdeg[i] >= 10 and fmsg[i] == 0),
                "群内外都密切（私聊≥50，共同群≥5）": sum(1 for i in range(NF) if fmsg[i] >= 50 and fdeg[i] >= 5),
                "只加了好友（私聊0，无共同群）": sum(1 for i in range(NF) if fmsg[i] == 0 and fdeg[i] == 0),
            },
            "sharedMedianByTier": {TIER_LABEL[t]: float(np.median(v)) for t, v in sorted(by_tier.items())},
            "groupsSpoke": sum(1 for s, _ in spoke if s > 0), "groupsTotal": len(spoke),
            "rhoSaidFriends": float(stats.spearmanr([s for s, _ in spoke], [n for _, n in spoke]).statistic),
            "pureDirect": [{"name": fname[i], "msg": fmsg[i], "sent": fsent[i]} for i in sorted((i for i in range(NF) if fdeg[i] == 0), key=lambda i: -fmsg[i])[:10]],
        }

    @section("dedensify")
    def _():
        Bw = B.subgraph([n for n in B if B.degree(n) > 0]).copy()
        R["dedensify"] = {str(th): nx.dedensify(Bw, threshold=th, copy=True)[0].number_of_edges() for th in (20, 50, 100)}
        R["dedensify"]["before"] = Bw.number_of_edges()

    @section("snap")
    def _():
        tb = np.zeros((6, 3))
        for j, m in enumerate(members):
            gt = 0 if gsaid[j] >= 50 else 1 if gsaid[j] >= 1 else 2
            for i in m:
                tb[ftier(i), gt] += 1
        R["snap"] = {"tierBlock": tb.tolist(), "attempted": bool(args.snap_timeout), "completed": False}
        if not args.snap_timeout:
            return
        Bw = B.subgraph([n for n in B if B.degree(n) > 0]).copy()
        for n in Bw:
            Bw.nodes[n]["kind"] = n[0]
            Bw.nodes[n]["tier"] = ftier(idx(n)) if n[0] == "f" else (0 if gsaid[idx(n)] >= 50 else 1 if gsaid[idx(n)] else 2)

        def stop(*_):
            raise TimeoutError
        old = signal.signal(signal.SIGALRM, stop)
        signal.alarm(args.snap_timeout)
        try:
            S = nx.snap_aggregation(Bw, node_attributes=("kind", "tier"))
            R["snap"].update({"completed": True, "supernodes": S.number_of_nodes()})
        except TimeoutError:
            R["snap"]["timeoutSec"] = args.snap_timeout
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

    @section("spectral")
    def _():
        from scipy.sparse.linalg import eigsh
        L = nx.normalized_laplacian_matrix(P50g, weight="weight").astype(float)
        k = min(30, P50g.number_of_nodes() - 2)
        vals = np.sort(eigsh(L, k=k, sigma=-1e-3, which="LM", return_eigenvectors=False))
        gaps = np.diff(vals[:min(25, k)])
        R["spectral"] = {"algebraicConnectivity": float(vals[1]), "nearZero": int((vals < 0.01).sum()),
                         "largestGapAfter": int(np.argmax(gaps[1:]) + 2)}

    (work / "results.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float))
    (work / "chartdata.json").write_text(json.dumps(chart, default=float))
    print(json.dumps({"results": str(work / "results.json"), "errors": R["errors"], "skipped": R["skipped"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
