#!/usr/bin/env python3
"""Generate a synthetic wdb-network/v1 file (placeholder names) for smoke tests and demos."""
import argparse
import json
import random
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="输出 network.json 路径")
    ap.add_argument("--friends", type=int, default=1500)
    ap.add_argument("--groups", type=int, default=400)
    ap.add_argument("--clusters", type=int, default=6, help="潜在圈子数")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rnd = random.Random(args.seed)
    home = [rnd.randrange(args.clusters) for _ in range(args.friends)]
    by_cluster = {c: [i for i, h in enumerate(home) if h == c] for c in range(args.clusters)}
    memberships = set()
    groups = []
    for j in range(args.groups):
        hub = j < 5  # a few large cross-cluster groups, like broadcast or community groups
        size = rnd.randint(150, 400) if hub else max(3, int(rnd.lognormvariate(1.6, 0.8)))
        c = rnd.randrange(args.clusters)
        picked = set()
        while len(picked) < min(size, args.friends):
            pool = range(args.friends) if hub or rnd.random() < 0.15 else by_cluster[c]
            picked.add(rnd.choice(list(pool)))
        for i in picked:
            memberships.add((j, i))
        groups.append({"name": f"群{j + 1:03d}", "size": len(picked) + rnd.randint(0, size), "owner_is_me": rnd.random() < 0.05,
                       "said": int(rnd.expovariate(1 / 30)) if rnd.random() < 0.4 else 0, "msg": rnd.randint(0, 5000), "last": 0})
    deg = [0] * args.friends
    for _, i in memberships:
        deg[i] += 1
    friends = []
    for i in range(args.friends):
        close = rnd.random() < 0.12 + 0.02 * deg[i]
        msg = int(rnd.expovariate(1 / 120)) if close else (rnd.randint(0, 9) if rnd.random() < 0.4 else 0)
        friends.append({"name": f"好友{i + 1:04d}", "nick": "", "msg": msg, "sent": msg // 2, "last": 0})
    # Friends without any shared group, as in real address books.
    for k in range(args.friends // 4):
        msg = int(rnd.expovariate(1 / 20)) if rnd.random() < 0.3 else 0
        friends.append({"name": f"好友{args.friends + k + 1:04d}", "nick": "", "msg": msg, "sent": msg // 2, "last": 0})
    doc = {"schema": "wdb-network/v1", "snapshot": "demo", "history_from": None, "has_messages": True,
           "friends": friends, "groups": groups, "memberships": sorted([list(p) for p in memberships])}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False))
    print(json.dumps({"out": str(out), "friends": len(friends), "groups": len(groups), "memberships": len(memberships)}))


if __name__ == "__main__":
    main()
