#!/usr/bin/env python3
"""Fetch the CC0 texture sets and HDRIs that src/three/textures.ts names into public/, and credit each in
src/credits.ts. Safe to re-run: what is present is skipped (its credit is checked again).

  python3 tools/fetch_textures.py               # whatever is missing
  python3 tools/fetch_textures.py --dry-run     # what would be fetched and credited: no network, no writes
  python3 tools/fetch_textures.py --offline     # no network: neutral placeholders for whatever is missing
  python3 tools/fetch_textures.py --only metal050a --force   # one set again
  python3 tools/fetch_textures.py --res 2k      # 2K texture sets (HDRIs keep the table's resolution)

Texture sets land in public/assets/tex3d/<set>/{color,roughness,normal}.jpg, HDRIs in public/assets/hdri/<id>_<res>.hdr,
each with a source.json (source, page, author, licence, SHA-256, date). Sources: ambientCG (zip per set) and Poly Haven
(its files API, MD5-checked). A set with `roughness: [lo, hi]` has its roughness map's 1st-99th percentile rescaled into
that range (ffmpeg decodes and encodes; the arithmetic is stdlib). Placeholders are flat grey, are never credited and
are replaced by the next online run. Needs node (reads the TypeScript table) and, for remaps and placeholders, ffmpeg.
Honours HTTPS_PROXY.
"""
import argparse
import hashlib
import io
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
CREDITS_TS = ROOT / "src" / "credits.ts"
UA = {"User-Agent": "Mozilla/5.0 (fetch_textures.py; CC0 texture fetch)"}
AMBIENTCG_MAP = {"color": "_Color.jpg", "roughness": "_Roughness.jpg", "normal": "_NormalGL.jpg"}
POLYHAVEN_MAP = {"color": "Diffuse", "roughness": "Rough", "normal": "nor_gl"}
PLACEHOLDER = {"color": "0x808080", "roughness": "0x8c8c8c", "normal": "0x8080ff"}


def table() -> dict:
    """The table in src/three/textures.ts, with every output path, through node (Node 22.18+ strips the types)."""
    js = (
        "import('./src/three/textures.ts').then(m=>console.log(JSON.stringify({"
        "sets:Object.entries(m.TEX_SETS).map(([k,v])=>({...v,key:k,files:Object.fromEntries(m.TEX_MAPS.map(x=>[x,m.texFile(k,x)]))})),"
        "hdris:m.HDRIS.map(h=>({...h,key:h.id,file:'assets/hdri/'+m.hdriFile(h.id,h.res)}))})))"
    )
    r = subprocess.run(["node", "--disable-warning=MODULE_TYPELESS_PACKAGE_JSON", "-e", js], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"cannot read src/three/textures.ts with node:\n{r.stderr.strip()}")
    return json.loads(r.stdout)


def get(url: str, attempts: int = 3) -> bytes:
    for k in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return r.read()
        except Exception as e:  # network errors of every kind get the same retry
            if k == attempts - 1:
                raise RuntimeError(f"{url}: {e}") from e
            time.sleep(2 * (k + 1))
    raise AssertionError


def get_json(url: str) -> dict:
    return json.loads(get(url).decode("utf-8"))


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        sys.exit(f"needs {tool} on PATH (remapping roughness maps and writing placeholders use it)")
    return path


# ---- sources -----------------------------------------------------------------------------------------------------

def fetch_ambientcg(item: dict, res: str) -> dict:
    url = f"https://ambientcg.com/get?file={item['id']}_{res.upper()}-JPG.zip"
    z = zipfile.ZipFile(io.BytesIO(get(url)))
    maps = {}
    for m, suffix in AMBIENTCG_MAP.items():
        names = [n for n in z.namelist() if n.endswith(suffix)]
        if not names:
            raise RuntimeError(f"{url}: no *{suffix} in the archive ({', '.join(z.namelist())})")
        maps[m] = z.read(names[0])
    return {"maps": maps, "author": "ambientCG", "title": item["id"], "page": f"https://ambientcg.com/view?id={item['id']}", "download": url}


def polyhaven_file(files: dict, key: str, res: str, fmt: str) -> bytes:
    try:
        f = files[key][res][fmt]
    except KeyError:
        raise RuntimeError(f"Poly Haven has no {key} at {res} as {fmt}")
    b = get(f["url"])
    if f.get("md5") and hashlib.md5(b).hexdigest() != f["md5"]:
        raise RuntimeError(f"{f['url']}: MD5 mismatch")
    return b


def polyhaven_meta(pid: str) -> dict:
    info = get_json(f"https://api.polyhaven.com/info/{pid}")
    return {"author": "、".join(info.get("authors", {}).keys()) or "Poly Haven", "title": info.get("name") or pid, "page": f"https://polyhaven.com/a/{pid}"}


def fetch_polyhaven(item: dict, res: str) -> dict:
    files = get_json(f"https://api.polyhaven.com/files/{item['id']}")
    maps = {m: polyhaven_file(files, key, res, "jpg") for m, key in POLYHAVEN_MAP.items()}
    return {"maps": maps, **polyhaven_meta(item["id"]), "download": f"https://api.polyhaven.com/files/{item['id']}"}


def fetch_hdri(item: dict) -> dict:
    files = get_json(f"https://api.polyhaven.com/files/{item['id']}")
    return {"data": polyhaven_file(files, "hdri", item["res"], "hdr"), **polyhaven_meta(item["id"]), "download": f"https://api.polyhaven.com/files/{item['id']}"}


# ---- image work ----------------------------------------------------------------------------------------------------

def remap_roughness(data: bytes, lo_t: float, hi_t: float) -> Tuple[bytes, str]:
    """Rescale the 1st-99th percentile of a grey JPEG into [lo_t, hi_t]; returns the new JPEG and a summary."""
    ffmpeg, ffprobe = need("ffmpeg"), need("ffprobe")
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "in.jpg"
        dst = Path(d) / "out.jpg"
        src.write_bytes(data)
        wh = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(src)], capture_output=True, text=True, check=True).stdout.strip()
        raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        counts = Counter(raw)
        n = len(raw)

        def pct(p: float) -> int:
            acc = 0
            for v in range(256):
                acc += counts.get(v, 0)
                if acc >= p * n:
                    return v
            return 255

        lo, hi = pct(0.01), max(pct(0.99), pct(0.01) + 1)
        lut = bytes(round(255 * (lo_t + (hi_t - lo_t) * min(1.0, max(0.0, (v - lo) / (hi - lo))))) for v in range(256))
        out = raw.translate(lut)
        mean = lambda b: sum(v * c for v, c in Counter(b).items()) / len(b) / 255
        subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", wh, "-i", "-", "-pix_fmt", "yuvj444p", "-q:v", "2", str(dst)], input=out, check=True)
        return dst.read_bytes(), f"roughness mean {mean(raw):.2f} -> {mean(out):.2f} (p1 {lo / 255:.2f}, p99 {hi / 255:.2f} -> {lo_t:.2f}..{hi_t:.2f})"


def flat_jpeg(color: str) -> bytes:
    ffmpeg = need("ffmpeg")
    with tempfile.TemporaryDirectory() as d:
        dst = Path(d) / "flat.jpg"
        subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=64x64", "-frames:v", "1", "-pix_fmt", "yuvj444p", "-q:v", "2", str(dst)], check=True)
        return dst.read_bytes()


def flat_hdr(w: int = 64, h: int = 32) -> bytes:
    """Radiance RGBE, uncompressed: dark grey, a soft overhead band and a dimmer horizon band (studio-like reflections)."""
    def rgbe(v: float) -> bytes:
        if v < 1e-32:
            return b"\x00\x00\x00\x00"
        m, e = math.frexp(v)
        c = int(m * 256)
        return bytes((c, c, c, e + 128))

    rows = []
    for y in range(h):
        el = 90 - 180 * (y + 0.5) / h
        v = 0.03 + 3.0 * math.exp(-(((el - 70) / 10) ** 2)) + 0.4 * math.exp(-(((el - 8) / 6) ** 2))
        rows.append(rgbe(v) * w)
    return f"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y {h} +X {w}\n".encode() + b"".join(rows)


# ---- credits -------------------------------------------------------------------------------------------------------

def ts_str(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def credit(meta: dict, changed: Optional[str] = None) -> dict:
    c = {"author": meta["author"], "title": meta["title"], "license": "CC0", "url": meta["page"]}
    if changed:
        c["changed"] = changed
    return c


def add_credits(entries: List[dict], write: bool) -> List[dict]:
    """Append the entries src/credits.ts does not list yet (matched by source URL); returns those added."""
    src = CREDITS_TS.read_text(encoding="utf-8")
    m = re.search(r"(export const CREDITS: Credit\[\] = \[)(.*?)(\n?\];)", src, re.S)
    if not m:
        sys.exit(f"{CREDITS_TS.relative_to(ROOT)}: no `export const CREDITS: Credit[] = [...];` to add to")
    body = m.group(2)
    new = [e for e in entries if f"url: {ts_str(e['url'])}" not in body and e["url"] not in body]
    if new and write:
        lines = "".join("\n  {" + ", ".join(f"{k}: {ts_str(v)}" for k, v in e.items()) + "}," for e in new)
        src = src[: m.start()] + m.group(1) + body.rstrip() + lines + "\n];" + src[m.end():]
        CREDITS_TS.write_text(src, encoding="utf-8")
    return new


# ---- main ----------------------------------------------------------------------------------------------------------

def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)


def sidecar_of(item: dict) -> Path:
    return (PUBLIC / item["file"]).with_suffix(".json") if item["kind"] == "hdri" else PUBLIC / Path(next(iter(item["files"].values()))).parent / "source.json"


def read_sidecar(item: dict) -> Optional[dict]:
    p = sidecar_of(item)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def outputs(item: dict) -> Dict[str, Path]:
    return {"hdr": PUBLIC / item["file"]} if item["kind"] == "hdri" else {k: PUBLIC / v for k, v in item["files"].items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog="\n".join(__doc__.split("\n\n")[1:]))
    ap.add_argument("--res", choices=["1k", "2k"], default="1k", help="texture set resolution (default 1k)")
    ap.add_argument("--only", action="append", default=[], metavar="KEY", help="a set key or HDRI id from textures.ts; repeatable")
    ap.add_argument("--force", action="store_true", help="fetch again even when present")
    ap.add_argument("--offline", action="store_true", help="no network: write flat placeholders for whatever is missing (not credited)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; no network, no writes")
    a = ap.parse_args()

    t = table()
    items = [{**s, "kind": "set", "res": a.res} for s in t["sets"]] + [{**h, "kind": "hdri", "source": "polyhaven"} for h in t["hdris"]]
    known = {i["key"] for i in items}
    unknown = [k for k in a.only if k not in known]
    if unknown:
        sys.exit(f"--only: not in src/three/textures.ts: {', '.join(unknown)} (known: {', '.join(sorted(known))})")
    if a.only:
        items = [i for i in items if i["key"] in a.only]

    fetched, placeholders, failed, to_credit = [], [], [], []
    for item in items:
        side = read_sidecar(item)
        outs = outputs(item)
        present = side is not None and all(p.exists() for p in outs.values())
        real = present and not side.get("placeholder")
        label = f"{item['kind']} {item['key']} ({item['source']} {item['id']}, {item['res']})"
        if real and not a.force:
            print(f"present  {label}")
            to_credit.append(credit(side, side.get("changed")))
            continue
        if a.dry_run:
            where = f"https://ambientcg.com/get?file={item['id']}_{item['res'].upper()}-JPG.zip" if item["source"] == "ambientcg" else f"https://api.polyhaven.com/files/{item['id']}"
            remap = f"; roughness -> {item['roughness'][0]}..{item['roughness'][1]}" if item.get("roughness") else ""
            print(f"{'offline ' if a.offline else 'fetch   '} {label}: {'placeholder' if a.offline else where}{remap}")
            if not a.offline:
                page = f"https://ambientcg.com/view?id={item['id']}" if item["source"] == "ambientcg" else f"https://polyhaven.com/a/{item['id']}"
                to_credit.append({"author": "ambientCG" if item["source"] == "ambientcg" else "(Poly Haven authors)", "title": item["id"], "license": "CC0", "url": page})
            continue
        if a.offline:
            if present and not a.force:
                print(f"present  {label} (placeholder)")
                continue
            data = {"hdr": flat_hdr()} if item["kind"] == "hdri" else {m: flat_jpeg(PLACEHOLDER[m]) for m in outs}
            for m, p in outs.items():
                write_atomic(p, data[m])
            write_atomic(sidecar_of(item), json.dumps({"source": item["source"], "id": item["id"], "placeholder": True, "written": date.today().isoformat()}, ensure_ascii=False, indent=2).encode())
            placeholders.append(item["key"])
            print(f"placeholder {label}")
            continue
        try:
            if item["kind"] == "hdri":
                got = fetch_hdri(item)
                data = {"hdr": got["data"]}
            else:
                got = fetch_ambientcg(item, item["res"]) if item["source"] == "ambientcg" else fetch_polyhaven(item, item["res"])
                data = dict(got["maps"])
            note = ""
            changed = None
            if item.get("roughness"):
                data["roughness"], note = remap_roughness(data["roughness"], *item["roughness"])
                changed = "粗糙度贴图重映射"
            for m, p in outs.items():
                write_atomic(p, data[m])
            meta = {
                "source": item["source"], "id": item["id"], "res": item["res"], "author": got["author"], "title": got["title"],
                "page": got["page"], "download": got["download"], "license": "CC0", "fetched": date.today().isoformat(),
                "files": {m: {"file": str(p.relative_to(PUBLIC)), "sha256": sha256(data[m])} for m, p in outs.items()},
                "placeholder": False,
            }
            if changed:
                meta["changed"] = changed
                meta["remap"] = note
            write_atomic(sidecar_of(item), json.dumps(meta, ensure_ascii=False, indent=2).encode())
            to_credit.append(credit(meta, changed))
            fetched.append(item["key"])
            print(f"fetched  {label}{': ' + note if note else ''}")
        except Exception as e:  # report every failure, then fail the run
            failed.append(item["key"])
            print(f"FAILED   {label}: {e}", file=sys.stderr)

    added = add_credits(to_credit, write=not a.dry_run) if to_credit else []
    for c in added:
        print(f"{'would credit' if a.dry_run else 'credited'} {c['author']} · {c['title']} · CC0 ({c['url']})")
    print(f"{len(fetched)} fetched, {len(placeholders)} placeholders, {len(failed)} failed, {len(added)} credits {'to add' if a.dry_run else 'added'} in src/credits.ts")
    if placeholders:
        print("placeholders are flat grey and uncredited: run again online before any delivery", file=sys.stderr)
    if failed:
        print(f"failed: {', '.join(failed)}; retry, or --offline to render with placeholders meanwhile", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
