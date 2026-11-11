#!/usr/bin/env python3
"""Cover backgrounds: one AI picture per ratio, without any text, for src/Cover.tsx to set the title on.

  python3 tools/gen_cover_bg.py --dry-run                        # prompt, request body, estimate; no network, no key
  python3 tools/gen_cover_bg.py                                  # 16:9 and 3:4 at 2K, missing ones only
  python3 tools/gen_cover_bg.py --ratio 16:9 --size 1K --force   # cheap composition test; replaces the current picture
  python3 tools/gen_cover_bg.py --ratio 4:3                      # a dedicated 4:3 picture (else Cover-4x3 reuses 16:9)

Model: OpenRouter openai/gpt-5.4-image-2 through chat/completions with modalities [image, text] and image_config
{aspect_ratio, image_size}. Measured 2026-10-12 (《如何打造一款特斯拉》): 1K (image_size left out) 1280x720 for
$0.132; 2K 2560x1440 for $0.265 and 1728x2304 for $0.357. Say the estimate before a real run.

Brief: cover/brief.json. The prompt is "<subject> <layouts[tone][ratio]> <style> <forbid>"; a real run refuses <...>
placeholders. The layout line reserves a quiet title area (left 40 % in landscape, top 40 % in portrait) in the
brief's tone: "dark" (near-black, validated on 《如何打造一款特斯拉》 2026-10-12) or "paper" (the film's paper colour).
The tone must equal COVER.tone in src/Cover.tsx, which sets the title ink to match; a real run refuses a mismatch.

Writes public/assets/cover/ai-<16x9|4x3|3x4>.png (.jpg when the model returns JPEG) and ai-<ratio>.json (prompt,
request, usage, generation id, pixel size). public/ is not tracked, so every take is also kept in cover/takes/
(timestamped, never overwritten). Every paid call, failed ones included, appends one JSON line to
ledger/costs.jsonl (--ledger or LEDGER_PATH overrides), in the line format of tools/ledger.py:
{ts, kind, provider, model, qty, unit, cost_usd, ok, ref}; this script writes them itself and imports nothing.

Money guards. Before the first call the script reads GET https://openrouter.ai/api/v1/credits and stops when
total_credits - total_usage is below $1.00 plus the estimate: OpenRouter answers 402 "requires at least $1.00 in
balance" to image output under $1.00 (2026-10-12). A dropped response is retried with a warning: on 2026-10-12
two drops after the model had run (IncompleteRead, SSL EOF) were still billed, so a retry can mean paying twice.
OPENROUTER_API_KEY comes from the environment only and is never printed.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import struct
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the Remotion project (work/remotion)
BRIEF = ROOT / "cover" / "brief.json"
TAKES = ROOT / "cover" / "takes"
CURRENT = ROOT / "public" / "assets" / "cover"
LEDGER = ROOT / "ledger" / "costs.jsonl"

API = "https://openrouter.ai/api/v1/chat/completions"
CREDITS = "https://openrouter.ai/api/v1/credits"
MODEL = "openai/gpt-5.4-image-2"
RATIOS = ("16:9", "4:3", "3:4")
DEFAULT_RATIOS = ["16:9", "3:4"]  # 4:3 reuses the 16:9 picture unless asked for (see references/covers.md)
# USD per image, the dearest measured case per size (2026-10-12): 1K $0.132, 2K $0.265 (16:9) to $0.357 (3:4)
ESTIMATE = {"1K": 0.14, "2K": 0.36}
MIN_BALANCE = 1.00  # OpenRouter refuses image output below this balance
EXTS = {"image/png": "png", "image/jpeg": "jpg"}
TONES = ("dark", "paper")
COVER_TSX = ROOT / "src" / "Cover.tsx"


def slug(ratio):
    return ratio.replace(":", "x")


def load_brief(path):
    b = json.loads(path.read_text(encoding="utf-8"))
    b["tone"] = b.get("tone") or "dark"
    if b["tone"] not in TONES:
        sys.exit(f"{path}: tone must be one of {', '.join(TONES)}, got {b['tone']!r}")
    missing = [k for k in ("subject", "style", "forbid", "layouts") if not b.get(k)]
    lay = (b.get("layouts") or {}).get(b["tone"]) or {}
    missing += [f"layouts.{b['tone']}.{r}" for r in RATIOS if not lay.get(r)]
    if missing:
        sys.exit(f"{path}: missing {', '.join(missing)}")
    return b


def layout(brief, ratio):
    return brief["layouts"][brief["tone"]][ratio]


def cover_tone():
    """COVER.tone in src/Cover.tsx, or None when it cannot be read."""
    try:
        m = re.search(r"^\s*tone:\s*'(\w+)'", COVER_TSX.read_text(encoding="utf-8"), re.M)
    except OSError:
        return None
    return m.group(1) if m else None


def placeholders(brief, ratio):
    parts = {"subject": brief["subject"], "style": brief["style"], "forbid": brief["forbid"],
             f"layouts.{brief['tone']}.{ratio}": layout(brief, ratio)}
    return [k for k, v in parts.items() if re.search(r"<[^>]+>", v)]


def prompt_for(brief, ratio):
    return " ".join(s.strip() for s in (brief["subject"], layout(brief, ratio), brief["style"], brief["forbid"]))


def request_body(model, prompt, ratio, size):
    image_config = {"aspect_ratio": ratio}
    if size != "1K":  # 1K is the model's default; the measured 1K run sent no image_size
        image_config["image_size"] = size
    return {"model": model, "messages": [{"role": "user", "content": prompt}], "modalities": ["image", "text"],
            "image_config": image_config, "max_tokens": 12000}


def existing(ratio):
    return [p for p in (CURRENT / f"ai-{slug(ratio)}.png", CURRENT / f"ai-{slug(ratio)}.jpg") if p.exists()]


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def describe(e):
    if isinstance(e, urllib.error.HTTPError):
        try:
            body = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            body = ""
        return f"HTTP {e.code} {body}".strip()
    return f"{type(e).__name__}: {e}"


def balance_verdict(data, need):
    """(remaining USD, ok) from the /credits payload {"data": {"total_credits", "total_usage"}}."""
    d = data["data"]
    left = float(d["total_credits"]) - float(d["total_usage"])
    return left, left >= MIN_BALANCE + need


def check_balance(key, need, timeout=30):
    """Stop before spending when the OpenRouter balance cannot cover the $1.00 floor plus this run's estimate."""
    req = urllib.request.Request(CREDITS, headers={"Authorization": f"Bearer {key}"})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        left, ok = balance_verdict(data, need)
    except Exception as e:  # unreadable balance: do not guess
        sys.exit(f"balance check failed ({describe(e)}); check the balance yourself, then rerun with --no-balance-check")
    if not ok:
        sys.exit(f"OpenRouter balance ${left:.2f} is below ${MIN_BALANCE:.2f} + estimate ${need:.2f}: top up first "
                 f"(image output is refused under ${MIN_BALANCE:.2f})")
    print(f"balance ${left:.2f} (needs ${MIN_BALANCE + need:.2f})", flush=True)


def append_ledger(path, model, cost, ok, ref):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {"ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), "kind": "image",
            "provider": "openrouter", "model": model, "qty": 1, "unit": "image", "cost_usd": cost, "ok": ok, "ref": ref}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def pixel_size(data):
    """(width, height) of PNG or baseline/progressive JPEG bytes, else None."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker, seg = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + seg
    return None


def decode_image(url, timeout):
    m = re.match(r"data:(image/[\w.+-]+);base64,", url)
    if m:
        return m.group(1), base64.b64decode(url[m.end():])
    with urllib.request.urlopen(url, timeout=timeout) as r:  # a hosted URL instead of inline data
        return r.headers.get_content_type(), r.read()


def retire_current(ratio, stamp):
    """Make room for the new picture without losing one: copies already kept in cover/takes/ are removed from
    public/, anything else (a picture placed by hand) is moved into cover/takes/."""
    kept = {hashlib.sha256(p.read_bytes()).hexdigest() for p in TAKES.glob(f"ai-{slug(ratio)}-*") if p.suffix in (".png", ".jpg")}
    for p in existing(ratio):
        if hashlib.sha256(p.read_bytes()).hexdigest() in kept:
            p.unlink()
        else:
            dest = TAKES / f"ai-{slug(ratio)}-{stamp}-replaced{p.suffix}"
            shutil.move(str(p), dest)
            print(f"  moved the previous {p.name} to {rel(dest)}", flush=True)
    side = CURRENT / f"ai-{slug(ratio)}.json"
    if side.exists():
        side.unlink()  # its take keeps a copy


def generate(args, brief, model, ratio, key):
    prompt = prompt_for(brief, ratio)
    body = request_body(model, prompt, ratio, args.size)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"ai-{slug(ratio)}-{stamp}-{args.size}"
    for attempt in range(1, args.attempts + 1):
        try:
            req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST", headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "motion-media-creator cover"})
            d = json.loads(urllib.request.urlopen(req, timeout=args.timeout).read())
        except urllib.error.HTTPError as e:
            msg = describe(e)
            if e.code == 402:
                sys.exit(f"{ratio}: {msg}\nOpenRouter refuses image output under ${MIN_BALANCE:.2f} of balance: top up first")
            if e.code < 500 and e.code != 429:  # the request itself is wrong: retrying will not help
                sys.exit(f"{ratio}: {msg}")
            if e.code >= 500:
                append_ledger(args.ledger, model, None, False, f"{rel(TAKES / stem)} (attempt {attempt}: HTTP {e.code})")
            print(f"WARNING {ratio} attempt {attempt}/{args.attempts}: {msg}", flush=True)
            time.sleep(4 * attempt)
            continue
        except Exception as e:  # dropped connection, TLS EOF, timeout, truncated body: the model may have run
            append_ledger(args.ledger, model, None, False, f"{rel(TAKES / stem)} (attempt {attempt}: {type(e).__name__})")
            print(f"WARNING {ratio} attempt {attempt}/{args.attempts}: {describe(e)}\n"
                  f"  the request reached OpenRouter; a dropped response may still be billed (2026-10-12: two such drops "
                  f"were). Check the activity page before running again.", flush=True)
            time.sleep(4 * attempt)
            continue
        usage = d.get("usage") or {}
        cost = usage.get("cost")
        cost = float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None
        try:
            url = d["choices"][0]["message"]["images"][0]["image_url"]["url"]
            mime, data = decode_image(url, args.timeout)
        except Exception as e:  # answered with text only (a refusal) or an unreadable image: billed all the same
            note = ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            append_ledger(args.ledger, model, cost, False, f"{rel(TAKES / stem)} (attempt {attempt}: no image)")
            print(f"WARNING {ratio} attempt {attempt}/{args.attempts}: no image in the answer ({describe(e)}) "
                  f"cost={cost} {str(note)[:200]}", flush=True)
            continue
        ext = EXTS.get(mime)
        if not ext:
            TAKES.mkdir(parents=True, exist_ok=True)
            raw = TAKES / f"{stem}.bin"
            raw.write_bytes(data)
            append_ledger(args.ledger, model, cost, False, f"{rel(raw)} ({mime})")
            sys.exit(f"{ratio}: the model returned {mime}; kept as {rel(raw)}. Convert it to PNG by hand.")
        wh = pixel_size(data)
        TAKES.mkdir(parents=True, exist_ok=True)
        take = TAKES / f"{stem}.{ext}"
        take.write_bytes(data)
        record = {"model": model, "ratio": ratio, "size": args.size, "tone": brief["tone"], "pixels": list(wh) if wh else None,
                  "prompt": prompt, "request": body, "generation_id": d.get("id"), "usage": usage,
                  "take": rel(take), "created": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")}
        (TAKES / f"{stem}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        append_ledger(args.ledger, model, cost, True, rel(take))
        CURRENT.mkdir(parents=True, exist_ok=True)
        retire_current(ratio, stamp)
        cur = CURRENT / f"ai-{slug(ratio)}.{ext}"
        shutil.copyfile(take, cur)
        (CURRENT / f"ai-{slug(ratio)}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        w, h = wh or (0, 0)
        want = {"16:9": 16 / 9, "4:3": 4 / 3, "3:4": 3 / 4}[ratio]
        off = f"  WARNING: {w}x{h} is not {ratio}" if h and abs(w / h - want) > 0.01 * want else ""
        print(f"{ratio}: {rel(cur)} {w}x{h} cost=${cost} (take {rel(take)}){off}", flush=True)
        return cost
    sys.exit(f"{ratio}: no picture after {args.attempts} attempts; every failed attempt is in {rel(args.ledger)}")


def main():
    ap = argparse.ArgumentParser(description="AI cover backgrounds (no text) for src/Cover.tsx", formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ratio", action="append", choices=RATIOS, help=f"repeatable; default {' and '.join(DEFAULT_RATIOS)}")
    ap.add_argument("--size", choices=("1K", "2K"), default="2K", help="1K only for composition tests (default 2K)")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt, the request body and the estimate; no network")
    ap.add_argument("--force", action="store_true", help="replace a current picture (it stays in cover/takes/); costs again")
    ap.add_argument("--attempts", type=int, default=2, help="tries per picture (default 2); a dropped try may be billed")
    ap.add_argument("--timeout", type=int, default=300, help="seconds per request (default 300)")
    ap.add_argument("--brief", type=Path, default=BRIEF)
    ap.add_argument("--ledger", type=Path, default=Path(os.environ.get("LEDGER_PATH") or LEDGER).expanduser())
    ap.add_argument("--no-balance-check", action="store_true", help="skip GET /credits (only after checking the balance yourself)")
    args = ap.parse_args()
    if args.attempts < 1:
        ap.error("--attempts must be at least 1")
    ratios = list(dict.fromkeys(args.ratio or DEFAULT_RATIOS))
    brief = load_brief(args.brief)
    model = brief.get("model") or MODEL

    todo = []
    for r in ratios:
        have = existing(r)
        if have and not args.force:
            print(f"{r}: {rel(have[0])} exists, skipped (--force replaces it and costs again)")
        else:
            todo.append(r)
    need = ESTIMATE[args.size] * len(todo)
    print(f"{len(todo)} picture(s) x about ${ESTIMATE[args.size]:.2f} ({args.size}) = about ${need:.2f} ({model}); "
          f"balance floor ${MIN_BALANCE:.2f}; tone {brief['tone']}", flush=True)
    ct = cover_tone()
    mismatch = f"cover/brief.json tone {brief['tone']!r} but src/Cover.tsx COVER.tone {ct!r}: make them equal" if ct and ct != brief["tone"] else ""
    if mismatch and args.dry_run:
        print(f"WARNING {mismatch}; a real run refuses", flush=True)

    if args.dry_run:
        for r in todo or ratios:
            ph = placeholders(brief, r)
            print(f"\n== {r} -> public/assets/cover/ai-{slug(r)}.png")
            if ph:
                print(f"   placeholders left in {', '.join(ph)}: a real run refuses")
            print("prompt:\n" + prompt_for(brief, r))
            print(f"request: POST {API}\n  Authorization: Bearer $OPENROUTER_API_KEY\n  Content-Type: application/json")
            print(json.dumps(request_body(model, prompt_for(brief, r), r, args.size), ensure_ascii=False, indent=1))
        return
    if not todo:
        return
    if mismatch:
        sys.exit(mismatch)
    left = {r: placeholders(brief, r) for r in todo}
    if any(left.values()):
        sys.exit("cover/brief.json still has placeholders: " + "; ".join(f"{r}: {', '.join(v)}" for r, v in left.items() if v))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set")
    if not args.no_balance_check:
        check_balance(key, need)
    spent = [generate(args, brief, model, r, key) for r in todo]
    known = [c for c in spent if isinstance(c, (int, float))]
    print(f"done: {len(spent)} picture(s), reported cost ${sum(known):.3f}; ledger {rel(args.ledger)}")
    print("next: tools/stills.sh covers (look at all three covers), then tools/deliver.sh covers <version>")


if __name__ == "__main__":
    main()
