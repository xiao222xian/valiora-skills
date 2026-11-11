#!/usr/bin/env python3
"""Export an anonymised friend–group network from local WeChat data via lov-wdb-cli.

All reads go through lov-wdb-cli's `sql` command, which only opens isolated copies
of the databases. The output JSON keeps display names and counts but no WeChat
account ids, database paths or table names.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SYSTEM_ACCOUNTS = (
    "filehelper fmessage weixin floatbottle medianote newsapp qqmail qmessage tmessage "
    "notification_messages brandsessionholder qqsafe exmail_tool mphelper weibo qqfriend "
    "lbsapp shakeapp voip voipapp masssendapp feedsapp facebookapp linkedinplugin "
    "officialaccounts helper_entry blogapp cardpackage readerapp conversationbox "
    "opencustomerservicemsg"
).split()
CANDIDATES = [
    "~/.agents/skills/lov-wdb-cli/skills/wdb-query/scripts/wdb_cli.py",
    "~/.claude/skills/lov-wdb-cli/skills/wdb-query/scripts/wdb_cli.py",
]
CHUNK = 400


def resolve_cli(explicit):
    for c in [explicit, os.environ.get("WDB_CLI"), *CANDIDATES]:
        if c and Path(c).expanduser().is_file():
            return str(Path(c).expanduser())
    sys.exit("找不到 lov-wdb-cli 的 wdb_cli.py：请先安装 lov-wdb-cli，或用 --wdb-cli / WDB_CLI 指定路径。")


class Cli:
    def __init__(self, path, account, keys):
        self.base = [sys.executable, path]
        if keys:
            self.base += ["--keys", keys]
        if account:
            self.base += ["--account", account]

    def run(self, *args):
        proc = subprocess.run(self.base + list(args), capture_output=True, text=True)
        try:
            doc = json.loads(proc.stdout)
        except json.JSONDecodeError:
            sys.exit(f"lov-wdb-cli 输出无法解析（exit {proc.returncode}）：{proc.stderr.strip()[:400]}")
        errors = doc.get("meta", {}).get("errors")
        if errors:
            sys.exit("lov-wdb-cli 报错：" + json.dumps(errors, ensure_ascii=False)[:800])
        return doc

    def sql(self, database, query):
        doc = self.run("sql", "--database", database, "--query", query, "--limit", "1000000")
        if doc["meta"].get("truncated"):
            sys.exit(f"查询结果被截断：{database}")
        return doc["data"]


def friend_filter(self_user):
    excluded = ",".join(repr(s) for s in SYSTEM_ACCOUNTS + [self_user])
    return ("c.local_type=1 AND c.verify_flag=0 AND c.delete_flag=0 "
            "AND c.username NOT LIKE '%@%' AND c.username NOT LIKE 'gh_%' "
            f"AND c.username NOT IN ({excluded})")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="输出 network.json 路径（放在私有工作目录）")
    ap.add_argument("--account", help="多账号时限定账号（传给 lov-wdb-cli --account）")
    ap.add_argument("--keys", help="密钥清单路径（传给 lov-wdb-cli --keys）")
    ap.add_argument("--wdb-cli", help="wdb_cli.py 路径；默认读取 WDB_CLI 或常见安装位置")
    ap.add_argument("--no-messages", action="store_true", help="跳过私聊与发言条数统计（更快，但部分分析会降级）")
    args = ap.parse_args()

    cli = Cli(resolve_cli(args.wdb_cli), args.account, args.keys)
    t0 = time.time()
    doctor = cli.run("doctor")["data"]
    dbs = [d["filename"] for d in doctor.get("databases", [])]
    for need in ("contact.db", "session.db"):
        if need not in dbs:
            sys.exit(f"没有可读的 {need}：请先用 lov-wdb-cli 完成密钥准备（wdb_init.py status/scan）。")

    # The account owner is a member of every current group, so the most frequent member is "me".
    top = cli.sql("contact.db", """
        SELECT n.username u, COUNT(*) k FROM chatroom_member m JOIN name2id n ON n.rowid = m.member_id
        GROUP BY m.member_id ORDER BY k DESC LIMIT 1""")
    if not top:
        sys.exit("群成员表为空，无法构建网络。")
    self_user = top[0]["u"]
    ff = friend_filter(self_user)

    friends = cli.sql("contact.db", f"SELECT c.username u, c.remark r, c.nick_name n, c.alias a FROM contact c WHERE {ff}")
    groups = cli.sql("contact.db", """
        SELECT r.id id, r.username u, r.owner o, c.remark r, c.nick_name n,
               (SELECT COUNT(*) FROM chatroom_member m WHERE m.room_id = r.id) size
        FROM chat_room r JOIN contact c ON c.username = r.username WHERE c.is_in_chat_room = 1""")
    edges = cli.sql("contact.db", f"""
        SELECT m.room_id g, c.username f FROM chatroom_member m
        JOIN name2id n ON n.rowid = m.member_id JOIN contact c ON c.username = n.username
        JOIN chat_room r ON r.id = m.room_id JOIN contact rc ON rc.username = r.username
        WHERE {ff} AND rc.is_in_chat_room = 1""")
    sessions = {r["u"]: r["t"] for r in cli.sql("session.db", "SELECT username u, last_timestamp t FROM SessionTable WHERE last_timestamp > 0")}

    stats, earliest = {}, None
    if not args.no_messages:
        wanted = {f["u"] for f in friends} | {g["u"] for g in groups}
        by_table = {f"Msg_{hashlib.md5(u.encode()).hexdigest()}": u for u in wanted}
        for db in sorted(d for d in dbs if d.startswith("message_") and d[8:-3].isdigit()):
            names = [r["name"] for r in cli.sql(db, "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")]
            me = cli.sql(db, f"SELECT rowid id FROM Name2Id WHERE user_name='{self_user}'")
            me_id = me[0]["id"] if me else -1
            tables = [t for t in names if t in by_table]
            for k in range(0, len(tables), CHUNK):
                arms = [f"SELECT '{t}' t, COUNT(*) n, IFNULL(SUM(real_sender_id={me_id}),0) mine, MIN(NULLIF(create_time,0)) lo "
                        f"FROM {t} WHERE local_type<>10000" for t in tables[k:k + CHUNK]]
                for r in cli.sql(db, " UNION ALL ".join(arms)):
                    s = stats.setdefault(by_table[r["t"]], [0, 0])
                    s[0] += r["n"]; s[1] += r["mine"]
                    if r["lo"]:
                        earliest = r["lo"] if earliest is None else min(earliest, r["lo"])

    name = lambda r: r.get("r") or r.get("n") or r.get("a") or ""
    fidx = {f["u"]: i for i, f in enumerate(friends)}
    gidx = {g["id"]: j for j, g in enumerate(groups)}
    memberships = sorted({(gidx[e["g"]], fidx[e["f"]]) for e in edges if e["g"] in gidx and e["f"] in fidx})
    members = {}
    for j, i in memberships:
        members.setdefault(j, []).append(i)
    out_friends = [{
        "name": name(f) or f"好友{i + 1}",
        "nick": f["n"] if f.get("r") and f.get("n") and f["r"] != f["n"] else "",
        "msg": stats.get(f["u"], [0, 0])[0], "sent": stats.get(f["u"], [0, 0])[1],
        "last": sessions.get(f["u"], 0),
    } for i, f in enumerate(friends)]
    out_groups = []
    for j, g in enumerate(groups):
        gname = name(g)
        if not gname:
            ms = members.get(j, [])
            gname = ("、".join(out_friends[i]["name"] for i in ms[:3]) + ("等" if len(ms) > 3 else "") + "（未命名群）") if ms else f"未命名群（{g['size']}人）"
        out_groups.append({"name": gname, "size": g["size"], "owner_is_me": g["o"] == self_user,
                           "said": stats.get(g["u"], [0, 0])[1], "msg": stats.get(g["u"], [0, 0])[0],
                           "last": sessions.get(g["u"], 0)})
    doc = {
        "schema": "wdb-network/v1",
        "snapshot": time.strftime("%Y-%m-%d"),
        "history_from": time.strftime("%Y-%m-%d", time.localtime(earliest)) if earliest else None,
        "has_messages": not args.no_messages,
        "friends": out_friends, "groups": out_groups, "memberships": [list(p) for p in memberships],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False))
    print(json.dumps({"out": str(out), "friends": len(out_friends), "groups": len(out_groups),
                      "memberships": len(memberships), "history_from": doc["history_from"],
                      "seconds": round(time.time() - t0, 1)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
