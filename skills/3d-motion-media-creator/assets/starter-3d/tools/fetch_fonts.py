#!/usr/bin/env python3
"""Fetch the film's SIL OFL typefaces and make the static weights that tools/fonts.py subsets.

  python3 tools/fetch_fonts.py --dry-run          # what would be fetched and instanced: no network, no writes
  python3 tools/fetch_fonts.py                    # download what is missing from Google Fonts' repository
  python3 tools/fetch_fonts.py --from <dir>       # take the files from a local folder instead (found by file name)
  python3 tools/fetch_fonts.py --force            # fetch and instance again

Faces: Noto Serif SC and Noto Sans SC (Google's builds of Source Han Serif / Sans: 思源宋体、思源黑体) and IBM Plex
Mono, all SIL OFL 1.1. The two CJK families come as variable fonts; their weights are instanced with fontTools into
fonts-ofl/static/<family>.ttf (about 20 s of CPU each, 2-3 min wall on a busy machine, 2026-10-13), the families tools/fonts.py lists (scripts/bootstrap_3d.py writes
that list into it). fonts-ofl/sources.json records URL, SHA-256, size and date of every file and each licence text
sits next to its font. OFL fonts need no on-screen credit; name them with their licence in the delivery report.
A file whose SHA-256 differs from the one checked on 2026-10-12 is kept with a warning: look at its glyph coverage
(tools/fonts.py subset fails on a missing glyph) and its licence before delivery. Needs fontTools. Honours HTTPS_PROXY.
"""
import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "fonts-ofl"
STATIC = OUT / "static"
UA = {"User-Agent": "Mozilla/5.0 (fetch_fonts.py; OFL font fetch)"}
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl"

# file -> source; sha256 and bytes as downloaded on 2026-10-12 for the first 3D film
FILES: Dict[str, dict] = {
    "NotoSerifSC[wght].ttf": {
        "name": "Noto Serif SC (Source Han Serif SC, 思源宋体)",
        "url": f"{GF}/notoserifsc/NotoSerifSC%5Bwght%5D.ttf",
        "licence_url": f"{GF}/notoserifsc/OFL.txt",
        "project": "https://github.com/notofonts/noto-cjk",
        "sha256": "050080d9255a86808f2945bffac582b31ef32bc36411ce29563b4961670c66f9",
        "bytes": 25125512,
    },
    "NotoSansSC[wght].ttf": {
        "name": "Noto Sans SC (Source Han Sans SC, 思源黑体)",
        "url": f"{GF}/notosanssc/NotoSansSC%5Bwght%5D.ttf",
        "licence_url": f"{GF}/notosanssc/OFL.txt",
        "project": "https://github.com/notofonts/noto-cjk",
        "sha256": "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da",
        "bytes": 17772300,
    },
    "IBMPlexMono-Regular.ttf": {
        "name": "IBM Plex Mono Regular",
        "url": f"{GF}/ibmplexmono/IBMPlexMono-Regular.ttf",
        "licence_url": f"{GF}/ibmplexmono/OFL.txt",
        "project": "https://github.com/IBM/plex",
        "sha256": "6a3412f058c7d8dfd9170c41e85ade48e5156ecb89356110ca57a0a27734af46",
        "bytes": 135580,
    },
    "IBMPlexMono-Medium.ttf": {
        "name": "IBM Plex Mono Medium",
        "url": f"{GF}/ibmplexmono/IBMPlexMono-Medium.ttf",
        "licence_url": f"{GF}/ibmplexmono/OFL.txt",
        "project": "https://github.com/IBM/plex",
        "sha256": "a9b4c49bb299e05b5f6c481e7fb5e78943d2793249a0c8874ab574a2d1ea6755",
        "bytes": 136704,
    },
}
# css family -> (file, weight to instance or None for a static file): the FACES of tools/fonts.py
FACES: Dict[str, Tuple[str, Optional[int]]] = {
    "OFL-Serif": ("NotoSerifSC[wght].ttf", 600),
    "OFL-SerifHeavy": ("NotoSerifSC[wght].ttf", 900),
    "OFL-Sans": ("NotoSansSC[wght].ttf", 400),
    "OFL-SansMedium": ("NotoSansSC[wght].ttf", 500),
    "OFL-Mono": ("IBMPlexMono-Regular.ttf", None),
    "OFL-MonoMedium": ("IBMPlexMono-Medium.ttf", None),
}


def get(url: str, attempts: int = 3) -> bytes:
    for k in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read()
        except Exception as e:  # network errors of every kind get the same retry
            if k == attempts - 1:
                raise RuntimeError(f"{url}: {e}") from e
            time.sleep(2 * (k + 1))
    raise AssertionError


def licence_name(file: str) -> str:
    return f"{Path(file).stem.split('-')[0].split('[')[0]}-OFL.txt"


def find_local(folder: Path, name: str) -> Optional[Path]:
    # compared by name, not globbed: "[wght]" in a file name is a character class to glob
    hits = sorted(p for p in folder.rglob("*") if p.name == name and p.is_file())
    return hits[0] if hits else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog="\n\n".join(__doc__.split("\n\n")[1:]))
    ap.add_argument("--from", dest="src", type=Path, help="a local folder that holds the font files (searched by file name, subfolders too)")
    ap.add_argument("--force", action="store_true", help="fetch and instance again even when present")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; no network, no writes")
    a = ap.parse_args()
    if a.src and not a.src.is_dir():
        sys.exit(f"--from {a.src}: not a folder")

    record_path = OUT / "sources.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {"files": {}, "faces": {}}
    todo = [f for f in FILES if a.force or not (OUT / f).is_file()]
    faces = [fam for fam, (f, _) in FACES.items() if a.force or f in todo or not (STATIC / f"{fam}.ttf").is_file()]
    for f, s in FILES.items():
        how = "present" if f not in todo else (f"from {a.src}" if a.src else f"download {s['url']} ({s['bytes'] / 1e6:.1f} MB)")
        print(f"font     {f}: {how}")
    for fam in faces:
        f, w = FACES[fam]
        print(f"face     {fam}: {'instance wght ' + str(w) + ' of' if w else 'copy'} {f} -> fonts-ofl/static/{fam}.ttf")
    if a.dry_run:
        print("dry run: nothing fetched or written")
        return 0

    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
    except ImportError:
        sys.exit("needs fontTools: python3 -m pip install fonttools")
    OUT.mkdir(parents=True, exist_ok=True)
    STATIC.mkdir(parents=True, exist_ok=True)
    changed = []
    for f in todo:
        s = FILES[f]
        if a.src:
            hit = find_local(a.src, f)
            if not hit:
                sys.exit(f"{f} is not in {a.src}; fetch it without --from, or put it there")
            data, origin = hit.read_bytes(), str(hit)
            lic = hit.parent / "OFL.txt"
            lic_data = lic.read_bytes() if lic.is_file() else None
        else:
            data, origin = get(s["url"]), s["url"]
            lic_data = get(s["licence_url"])
        digest = hashlib.sha256(data).hexdigest()
        if digest != s["sha256"]:
            changed.append(f)
            print(f"warning: {f} differs from the file checked on 2026-10-12 (sha256 {digest[:12]}..., {len(data)} bytes): check glyphs and licence", file=sys.stderr)
        (OUT / f).write_bytes(data)
        if lic_data:
            (OUT / licence_name(f)).write_bytes(lic_data)
        record["files"][f] = {
            "name": s["name"],
            "licence": "SIL OFL 1.1",
            "licence_text": licence_name(f) if lic_data else None,
            "licence_url": s["licence_url"],
            "project": s["project"],
            "from": origin,
            "sha256": digest,
            "bytes": len(data),
            "fetched": date.today().isoformat(),
        }
        print(f"fetched  {f} ({len(data) / 1e6:.1f} MB){'' if lic_data else '; licence text not found next to it: ' + s['licence_url']}")

    for fam in faces:
        f, w = FACES[fam]
        out = STATIC / f"{fam}.ttf"
        if w is None:
            shutil.copyfile(OUT / f, out)
        else:
            t0 = time.time()
            font = TTFont(OUT / f)
            instancer.instantiateVariableFont(font, {"wght": w}, inplace=True)
            font.save(out)
            print(f"face     {fam}: wght {w} of {f}, {out.stat().st_size / 1e6:.1f} MB in {time.time() - t0:.0f} s")
        record["faces"][fam] = {"file": f, "wght": w}
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote fonts-ofl/sources.json; {len(FACES)} faces in fonts-ofl/static/")
    print("delivery report: typefaces Noto Serif SC, Noto Sans SC (Source Han Serif / Sans) and IBM Plex Mono, SIL OFL 1.1 (fonts-ofl/sources.json)")
    # tools/bootstrap.sh extracts into fonts-src/ only when a face is missing there
    print("next: tools/bootstrap.sh" if not (ROOT / "fonts-src").is_dir() else "next: python3 tools/fonts.py extract && python3 tools/fonts.py subset")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
