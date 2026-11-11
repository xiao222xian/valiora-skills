#!/usr/bin/env python3
"""Render the covers' picture from the film's own 3D set (src/scenes/CoverPicture.tsx through src/cover3d.tsx) into
the picture slot the base Cover.tsx reads, so the covers come from the same set as the film and cost nothing.

  python3 tools/cover_3d.py                 # 16:9, 4:3 and 3:4 -> public/assets/cover/ai-<ratio>.png (+ .json)
  python3 tools/cover_3d.py --ratio 3x4     # one ratio
  python3 tools/cover_3d.py --dry-run       # what would be rendered and replaced
  tools/stills.sh covers                    # then look at the three covers

The slot is named ai-<ratio> by lov-motion-media-creator (tools/gen_cover_bg.py writes AI pictures there); the .json
beside each picture says source "3d-still" and ai false, so the delivery report does not list it as generated content.
A picture whose .json is not a 3d-still (a paid AI take) is kept unless --force. Needs node, the base tools/bundle.sh
and tools/stills.mjs; GL defaults to angle.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COVER = ROOT / "public" / "assets" / "cover"
BUILD = ROOT.parent / "build" / "cover3d"
RATIOS = ["16x9", "4x3", "3x4"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog="\n\n".join(__doc__.split("\n\n")[1:]))
    ap.add_argument("--ratio", action="append", choices=RATIOS, help="repeatable; default all three")
    ap.add_argument("--force", action="store_true", help="replace a picture that is not a 3d-still (e.g. a paid AI take)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; render and write nothing")
    a = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # keep our lines in order with the renderer's
    ratios = a.ratio or RATIOS

    plan = []
    for r in ratios:
        dst = COVER / f"ai-{r}.png"
        meta = COVER / f"ai-{r}.json"
        kind = "none"
        if dst.exists() or (COVER / f"ai-{r}.jpg").exists():
            try:
                kind = json.loads(meta.read_text(encoding="utf-8")).get("source", "unknown")
            except (OSError, ValueError):
                kind = "unknown"
        if kind not in ("none", "3d-still") and not a.force:
            print(f"keep     {r}: public/assets/cover/ai-{r}.* is a {kind} picture (--force replaces it)")
            continue
        plan.append(r)
        print(f"{'would render' if a.dry_run else 'render'}   {r}: CoverPic-{r} -> public/assets/cover/ai-{r}.png{' (replaces ' + kind + ')' if kind != 'none' else ''}")
    if a.dry_run or not plan:
        return 0

    env = {**os.environ, "GL": os.environ.get("GL") or "angle", "FORMATS": "png"}
    subprocess.run(["tools/bundle.sh", "src/cover3d.tsx", str(BUILD)], cwd=ROOT, check=True)
    COVER.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for r in plan:
            prefix = str(Path(tmp) / "pic-")
            subprocess.run(["node", "tools/stills.mjs", str(BUILD), f"CoverPic-{r}", prefix, "1", f"0:{r}"], cwd=ROOT, env=env, check=True)
            dst = COVER / f"ai-{r}.png"
            # an existing ai-<r>.jpg stays: Cover.tsx takes the .png first
            shutil.move(f"{prefix}{r}.png", dst)
            sha = hashlib.sha256(dst.read_bytes()).hexdigest()
            (COVER / f"ai-{r}.json").write_text(json.dumps({"source": "3d-still", "ai": False, "entry": "src/cover3d.tsx", "composition": f"CoverPic-{r}", "rendered": date.today().isoformat(), "sha256": sha}, indent=2) + "\n", encoding="utf-8")
            print(f"wrote    public/assets/cover/ai-{r}.png")
    print("next: tools/stills.sh covers   (look at all three: title, seal and logo clear of the subject)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
