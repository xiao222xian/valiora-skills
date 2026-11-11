#!/usr/bin/env python3
"""Conform the film's approved archival photos and footage to one look and write the media catalogue src/media.ts.

  python3 tools/conform.py --dry-run               # what would be converted; checks the register, writes nothing
  python3 tools/conform.py                         # convert what is missing, then rewrite src/media.ts
  python3 tools/conform.py --force                 # convert everything again
  python3 tools/conform.py --register <file.json>  # another register (default ../licenses/assets.json)

Photos: long side <= 3840 (--long-edge), JPEG q90, sRGB. Footage: H.264 CRF 18, 30 fps (--fps), no audio track, long
side <= 1920, or 3840 for an entry marked "wide" (the 9:16 cut pans or crops into it). One light grade for every
colour source (--contrast 1.04, --saturation 0.88: tuned next to AgX-toned 3D on the first 3D film, 2026-10-12) so
film from decades apart sits together with the 3D; black-and-white sources stay grey and are not graded.

The register is a JSON list, one entry per item, as assets-and-licensing.md「登记」 describes. This script reads the
entries whose "kind" is "photo" or "video" and whose "use" is not false:
  files[0].path   the source file, relative to the register's parent folder's parent (the project's work/)
  key             catalogue key (default: the file's folder name), used as <ShotNote kind="archival" media="key">
  license_id      one of ALLOWED, checked here; "license" keeps the page's own wording
  onscreen        the corner note after 「资料 · 」: short, author and licence, e.g. "摄影 Steve Jurvetson · CC BY 2.0"
  credit, title, page_url, is_brand, wide, bw     full credit, title, page, brand marks in frame, keep 3840 px,
                  a black-and-white source stored as colour (kept grey, not graded)
Output: public/media/photo/<key>.jpg, public/media/video/<key>.mp4. Needs Pillow and ffmpeg/ffprobe.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # work/remotion
OUT = ROOT / "public" / "media"
CAT_TS = ROOT / "src" / "media.ts"
ALLOWED = {"CC0", "PD", "CC BY 2.0", "CC BY 3.0", "CC BY 4.0", "Pexels", "Copernicus"}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd[:6])}...: {r.stderr[-800:]}")
    return r.stdout


def probe(path: Path):
    j = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-show_entries", "format=duration", "-of", "json", str(path)]))
    s = j["streams"][0]
    return int(s["width"]), int(s["height"]), float(j["format"]["duration"])


def conform_photo(src: Path, dst: Path, long_edge: int, contrast: float, saturation: float, bw: bool):
    from PIL import Image, ImageEnhance, ImageOps

    im = ImageOps.exif_transpose(Image.open(src))
    bw = bw or im.mode in ("1", "L", "LA", "I;16")
    im = im.convert("L" if bw else "RGB")
    s = long_edge / max(im.size)
    if s < 1:
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    if not bw:
        im = ImageEnhance.Contrast(im).enhance(contrast)
        im = ImageEnhance.Color(im).enhance(saturation)
    im.save(dst, "JPEG", quality=90, optimize=True, progressive=True)
    return im.width, im.height, bw


def conform_video(src: Path, dst: Path, long_edge: int, fps: int, contrast: float, saturation: float, grade: bool):
    # scale the long side, whichever it is; -2 keeps the other side even for yuv420p
    scale = f"scale='if(gt(iw,ih),min({long_edge},iw),-2)':'if(gt(iw,ih),-2,min({long_edge},ih))':flags=lanczos"
    vf = f"fps={fps},{scale}" + (f",eq=contrast={contrast}:saturation={saturation}" if grade else "") + ",format=yuv420p"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an", "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-g", str(fps), "-movflags", "+faststart", str(dst)])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog="\n\n".join(__doc__.split("\n\n")[1:]))
    ap.add_argument("--register", type=Path, default=ROOT.parent / "licenses" / "assets.json")
    ap.add_argument("--force", action="store_true", help="convert again even when the output exists")
    ap.add_argument("--dry-run", action="store_true", help="check the register and print the plan; write nothing")
    ap.add_argument("--long-edge", type=int, default=3840, help="photos and wide footage")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--contrast", type=float, default=1.04)
    ap.add_argument("--saturation", type=float, default=0.88)
    a = ap.parse_args()

    if not a.register.is_file():
        sys.exit(f"no register at {a.register}: write one entry per item first (assets-and-licensing.md「登记」), or pass --register")
    work = a.register.resolve().parent.parent
    entries = [e for e in json.loads(a.register.read_text(encoding="utf-8")) if e.get("kind") in ("photo", "video") and e.get("use", True) is not False]
    errors, cat, plan = [], {}, []
    for e in entries:
        if not e.get("files"):
            errors.append(f"{e.get('title', '?')}: no files[0].path")
            continue
        src = work / e["files"][0]["path"]
        key = e.get("key") or src.parent.name
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", key):
            errors.append(f"{key}: a key may hold letters, digits, '.', '_' and '-' (set \"key\")")
        if key in cat:
            errors.append(f"{key}: two entries share this key (set \"key\")")
        if e.get("license_id") not in ALLOWED:
            errors.append(f"{key}: license_id {e.get('license_id')!r} is not one of {', '.join(sorted(ALLOWED))}")
        if not e.get("onscreen"):
            errors.append(f"{key}: no \"onscreen\" credit for the corner note")
        if not src.is_file():
            errors.append(f"{key}: source file missing: {src}")
        ext = "jpg" if e["kind"] == "photo" else "mp4"
        dst = OUT / e["kind"] / f"{key}.{ext}"
        cat[key] = (e, src, dst)
        plan.append(f"{e['kind']:5s} {key}: {'convert' if a.force or not dst.exists() else 'present'} -> public/media/{e['kind']}/{key}.{ext}")
    print("\n".join(plan) or "no photo or video entries in the register")
    if errors:
        sys.exit("register problems:\n  " + "\n  ".join(errors))
    if a.dry_run:
        print("dry run: nothing written")
        return 0

    (OUT / "photo").mkdir(parents=True, exist_ok=True)
    (OUT / "video").mkdir(parents=True, exist_ok=True)
    items = {}
    for key, (e, src, dst) in cat.items():
        if e["kind"] == "photo":
            if a.force or not dst.exists():
                w, h, bw = conform_photo(src, dst, a.long_edge, a.contrast, a.saturation, bool(e.get("bw")))
            else:
                from PIL import Image

                im = Image.open(dst)
                w, h, bw = im.width, im.height, im.mode == "L"
            item = {"file": f"media/photo/{key}.jpg", "type": "photo", "w": w, "h": h, "bw": bw}
        else:
            if a.force or not dst.exists():
                print(f"video {key} ...", flush=True)
                conform_video(src, dst, a.long_edge if e.get("wide") else 1920, a.fps, a.contrast, a.saturation, not e.get("bw"))
            w, h, dur = probe(dst)
            item = {"file": f"media/video/{key}.mp4", "type": "video", "w": w, "h": h, "dur": round(dur, 3)}
        item.update({
            "credit": e["onscreen"],
            "license": e["license_id"],
            "title": e.get("title", ""),
            "fullCredit": e.get("credit", ""),
            "pageUrl": e.get("page_url", ""),
            "brand": bool(e.get("is_brand")),
        })
        items[key] = item
        print(f"{item['type']:5s} {w}x{h} {key}", flush=True)
    body = json.dumps(items, ensure_ascii=False, indent=2)
    CAT_TS.write_text(
        "// The film's archival photos and footage. Written by tools/conform.py from the licence register\n"
        f"// ({a.register.name}). Do not edit by hand.\n"
        "export type MediaItem = {file: string; type: 'photo' | 'video'; w: number; h: number; dur?: number; bw?: boolean;\n"
        "  credit: string; license: string; title: string; fullCredit: string; pageUrl: string; brand: boolean};\n\n"
        f"export const MEDIA = {body} as const satisfies Record<string, MediaItem>;\n\n"
        "export type MediaKey = keyof typeof MEDIA;\n",
        encoding="utf-8",
    )
    print(f"wrote {CAT_TS.relative_to(ROOT)} ({len(items)} items); CC BY items also go into src/credits.ts for the end credits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
