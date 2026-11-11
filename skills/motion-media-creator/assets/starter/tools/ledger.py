#!/usr/bin/env python3
"""Cost ledger: one JSON line per paid call (a music take, a TTS line, a cover image), so the delivery report can
say what each version cost and which calls failed.

  python3 tools/ledger.py add --kind image --provider openrouter --model openai/gpt-5.4-image-2 \\
      --qty 1 --unit image --cost-usd 0.27 --ref cover/takes/web-16x9.png   # made on the website, not by a script
  python3 tools/ledger.py add ... --failed          # a failed call (still billed when --cost-usd says so)
  python3 tools/ledger.py summary                   # Markdown table and notes for the delivery report
  python3 tools/ledger.py summary --since 2026-10-12T18:00 [--json]

File: ledger/costs.jsonl under the project root (the folder with src/ and tools/); LEDGER_PATH overrides it (a
relative LEDGER_PATH is taken from the current directory). Keep it in git: it is the film's spend record.

One line: {"ts", "kind", "provider", "model", "qty", "unit", "cost_usd", "ok", "ref"}
  ts        local time of the call, ISO 8601 with offset, to the second
  kind      what was bought: music, tts, image, ...
  provider  openrouter, volcengine, ...
  model     the provider's model id
  qty unit  how much, in the provider's billing unit where known: 1 clip, 1 track, 182 chars, 1 image
  cost_usd  the price the provider reported (OpenRouter: usage.cost); null when it reports none
  ok        false when the call failed; a failed call can still be billed
  ref       the file the call made or was for, relative to the project root

Scripts that pay write their own lines: audio/gen_chapter_music.py and audio/gen_bgm_openrouter.py through
record() (every request that can be billed, retries included, with OpenRouter's usage.cost), tools/narration.py
(one line per synthesized line: characters, no price, the TTS API returns none), tools/gen_cover_bg.py (every
paid attempt, failed ones included, with usage.cost; it writes the same line format without importing this file).
Do not add their calls again. `add` is only for calls made outside these scripts: an image made on a website, a
single test request.

A line that is not a JSON object, lacks a key or has a value of the wrong type (a string where a number belongs,
ok as "false", a cost of Infinity) is reported and left out of the summary, so one hand-edited line cannot break
the delivery report's table.

(2026-10-12, 《如何打造一款特斯拉》: the question how the film's versions went and what they cost had to be answered
from reports and session transcripts; two cover-image requests whose connection dropped after the model had run
(IncompleteRead, SSL EOF) were billed all the same: a failed line with an unknown cost is worth checking against
the provider's activity page.)
"""
import argparse
import json
import math
import os
import sys
import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

try:
    import fcntl  # POSIX: keeps lines from parallel processes whole
except ImportError:  # pragma: no cover - Windows
    fcntl = None

ROOT = Path(__file__).resolve().parent.parent
KEYS = ("ts", "kind", "provider", "model", "qty", "unit", "cost_usd", "ok", "ref")
_lock = threading.Lock()  # the music scripts pay from a thread pool


def ledger_path():
    p = os.environ.get("LEDGER_PATH")
    return Path(p).expanduser() if p else ROOT / "ledger" / "costs.jsonl"


def _num(x, what):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0:
        raise ValueError(f"{what} must be a finite number >= 0, got {x!r}")
    return int(x) if float(x).is_integer() else float(x)


def _invalid(d):
    """Why a parsed line cannot be summed, or None. Lines are added by hand too, so types are not a given."""
    for k in ("ts", "kind", "provider", "model", "unit"):
        if not isinstance(d[k], str) or not d[k].strip():
            return f"{k} is not a non-empty string ({d[k]!r})"
    if not isinstance(d["ok"], bool):
        return f"ok is not true or false ({d['ok']!r})"
    try:
        _num(d["qty"], "qty")
        if d["cost_usd"] is not None:
            _num(d["cost_usd"], "cost_usd")
    except ValueError as e:
        return str(e)
    return None


def _ref(ref):
    """A path inside the project is stored relative to it; anything else as given."""
    if ref is None:
        return ""
    s = str(ref)
    p = Path(s)
    if p.is_absolute():
        try:
            return str(p.resolve().relative_to(ROOT))
        except ValueError:
            return s
    return s


def append(kind, provider, model, qty, unit, cost_usd=None, ok=True, ref="", ts=None, path=None):
    """Add one line and return it. Raises ValueError on a bad value and OSError when the file cannot be written."""
    for name, v in (("kind", kind), ("provider", provider), ("model", model), ("unit", unit)):
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"{name} must be a non-empty string, got {v!r}")
    if not isinstance(ok, bool):
        raise ValueError(f"ok must be true or false, got {ok!r}")
    line = OrderedDict([
        ("ts", ts or datetime.now().astimezone().isoformat(timespec="seconds")),
        ("kind", kind.strip()), ("provider", provider.strip()), ("model", model.strip()),
        ("qty", _num(qty, "qty")), ("unit", unit.strip()),
        ("cost_usd", None if cost_usd is None else _num(cost_usd, "cost_usd")),
        ("ok", ok), ("ref", _ref(ref)),
    ])
    p = Path(path) if path else ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(line, ensure_ascii=False) + "\n"
    with _lock, open(p, "a", encoding="utf-8") as f:
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(data)
            f.flush()
        finally:
            if fcntl:
                fcntl.flock(f, fcntl.LOCK_UN)
    return dict(line)


def record(**kw):
    """append() for a script that has just paid: a ledger problem is printed, never raised, so it can neither
    trigger a retry (a second payment) nor lose the output already written."""
    try:
        return append(**kw)
    except Exception as e:  # noqa: BLE001 - the call is paid for; say so and go on
        print(f"ledger: call not recorded ({e}); add it with tools/ledger.py add "
              f"--kind {kw.get('kind')} --provider {kw.get('provider')} --model {kw.get('model')} ...", file=sys.stderr)
        return None


def usage_cost(usage):
    """OpenRouter's usage.cost (USD) when the response carried one, else None."""
    c = (usage or {}).get("cost") if isinstance(usage, dict) else None
    return float(c) if isinstance(c, (int, float)) and not isinstance(c, bool) else None


def read(path=None):
    p = Path(path) if path else ledger_path()
    if not p.exists():
        return []
    rows = []
    for i, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            d = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"ledger: {p.name}:{i} is not JSON ({e.msg}): skipped", file=sys.stderr)
            continue
        if not isinstance(d, dict):
            print(f"ledger: {p.name}:{i} is not a JSON object: skipped", file=sys.stderr)
            continue
        missing = [k for k in KEYS if k not in d]
        if missing:
            print(f"ledger: {p.name}:{i} lacks {', '.join(missing)}: skipped", file=sys.stderr)
            continue
        bad = _invalid(d)
        if bad:
            print(f"ledger: {p.name}:{i} {bad}: skipped", file=sys.stderr)
            continue
        rows.append(d)
    return rows


def _when(s):
    t = datetime.fromisoformat(s)
    return t if t.tzinfo else t.astimezone()  # a time without offset is local time


def summarize(rows):
    groups = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["kind"], r["provider"], r["model"], r["unit"])):
        g = groups.setdefault((r["kind"], r["provider"], r["model"], r["unit"]),
                              {"calls": 0, "failed": 0, "qty": 0, "cost_usd": 0.0, "unpriced": 0})
        g["calls"] += 1
        g["failed"] += not r["ok"]
        g["qty"] += r["qty"] or 0
        if r["cost_usd"] is None:
            g["unpriced"] += 1
        else:
            g["cost_usd"] += r["cost_usd"]
    failed = [r for r in rows if not r["ok"]]
    billed = [r for r in failed if (r["cost_usd"] or 0) > 0]
    return {
        "calls": len(rows),
        "cost_usd": round(sum(r["cost_usd"] or 0 for r in rows), 6),
        "unpriced": sum(1 for r in rows if r["cost_usd"] is None),
        "failed": len(failed),
        "failed_billed": len(billed),
        "failed_billed_usd": round(sum(r["cost_usd"] for r in billed), 6),
        "failed_cost_unknown": sum(1 for r in failed if r["cost_usd"] is None),
        "first": min((r["ts"] for r in rows), default=None),
        "last": max((r["ts"] for r in rows), default=None),
        "groups": [{"kind": k[0], "provider": k[1], "model": k[2], "unit": k[3], **v,
                    "qty": int(v["qty"]) if float(v["qty"]).is_integer() else round(v["qty"], 3),
                    "cost_usd": round(v["cost_usd"], 6)} for k, v in groups.items()],
    }


def _usd(x):
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s if "." in s else s + ".00" if s != "0" else "0"


def markdown(s):
    out = ["| 类型 | 服务商 | 模型 | 调用 | 失败 | 用量 | 费用（美元） |",
           "| --- | --- | --- | ---: | ---: | ---: | ---: |"]
    for g in s["groups"]:
        if g["unpriced"] == g["calls"]:
            cost = "未返回"
        else:
            cost = _usd(g["cost_usd"]) + (f"（另 {g['unpriced']} 次未返回）" if g["unpriced"] else "")
        out.append(f"| {g['kind']} | {g['provider']} | `{g['model']}` | {g['calls']} | {g['failed']} | "
                   f"{g['qty']} {g['unit']} | {cost} |")
    total = _usd(s["cost_usd"]) + (f"（另 {s['unpriced']} 次未返回）" if s["unpriced"] else "")
    out.append(f"| 合计 | | | {s['calls']} | {s['failed']} | | {total} |")
    out.append("")
    out.append(f"- 记录时段：{s['first']} 至 {s['last']}。" if s["calls"] else "- 账本为空。")
    out.append(f"- 失败但已计费：{s['failed_billed']} 次，{_usd(s['failed_billed_usd'])} 美元。")
    if s["failed_cost_unknown"]:
        out.append(f"- 失败且未返回费用：{s['failed_cost_unknown']} 次，需到服务商用量页核对（断线的请求可能已计费）。")
    if s["unpriced"]:
        out.append("- 「未返回」的调用按用量列计价（例如 TTS 按字符）。")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Cost ledger of the paid calls (ledger/costs.jsonl; LEDGER_PATH overrides).")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="append one call")
    a.add_argument("--kind", required=True, help="music, tts, image, ...")
    a.add_argument("--provider", required=True, help="openrouter, volcengine, ...")
    a.add_argument("--model", required=True, help="the provider's model id")
    a.add_argument("--qty", type=float, default=1, help="amount in --unit (default 1)")
    a.add_argument("--unit", default="call", help="clip, track, chars, image, ... (default call)")
    a.add_argument("--cost-usd", type=float, help="price the provider reported; leave out when unknown")
    a.add_argument("--failed", action="store_true", help="the call failed (ok false)")
    a.add_argument("--ref", default="", help="the file the call made or was for")
    a.add_argument("--ts", help="time of the call, ISO 8601 (default now); for calls entered afterwards")
    s = sub.add_parser("summary", help="totals by kind, provider and model as a Markdown table")
    s.add_argument("--since", help="only calls at or after this ISO 8601 time (e.g. the previous version's delivery)")
    s.add_argument("--json", action="store_true", help="print the totals as JSON instead")
    args = ap.parse_args()

    if args.cmd == "add":
        try:
            if args.ts:
                _when(args.ts)
            line = append(args.kind, args.provider, args.model, args.qty, args.unit, args.cost_usd,
                          not args.failed, args.ref, args.ts)
        except (ValueError, OSError) as e:
            sys.exit(f"ledger add: {e}")
        print(json.dumps(line, ensure_ascii=False))
        print(f"-> {ledger_path()}")
    elif args.cmd == "summary":
        rows = read()
        if args.since:
            try:
                since = _when(args.since)
            except ValueError as e:
                sys.exit(f"--since: {e}")
            kept = []
            for r in rows:
                try:
                    if _when(r["ts"]) >= since:
                        kept.append(r)
                except (TypeError, ValueError):
                    print(f"ledger: ts {r['ts']!r} is not ISO 8601: left out of --since", file=sys.stderr)
            rows = kept
        s = summarize(rows)
        print(json.dumps(s, ensure_ascii=False, indent=1) if args.json else markdown(s))
    else:
        ap.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
