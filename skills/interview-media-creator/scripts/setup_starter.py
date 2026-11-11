#!/usr/bin/env python3
"""Copy the Remotion starter into a project and wire fonts, logo and media folders.

usage: setup_starter.py work/remotion --sans-font PATH --title-font PATH --logo PATH
                        [--node-modules PATH] [--cover-spec PATH] [--series 系列名]

- Run it right after the EDL is written (start of Step 5), before build_timeline.py, so public/{data,media,
  audio,img} exist when the pipeline fills them. Placeholder timeline.json / subs.json are written only when
  missing; Film shows black while media.video is empty.
- Copies assets/starter (Film, Cover, CoverWide, layout, render scripts) into the target; refuses to overwrite
  an existing src/ so a project's edits are never lost.
- Fonts are copied (APFS clone when possible) to public/fonts/sans.ttf and public/fonts/title.ttf: a heavy
  CJK sans for captions (variable Noto Sans SC works) and a display face for titles. Check the licence of
  any font that ships in a published video.
- --logo is the official white logo on transparency (Profile brand logo); it is copied to public/img/logo.png.
  Never draw or generate a logo.
- --node-modules links an existing node_modules with the same Remotion version (saves ~500 MB); otherwise
  run `npm install` in the target.
- --cover-spec is copied to public/data/cover.json. Without it a neutral skeleton is written (series from
  --series or "", variants a/b with placeholder lines) to be filled in Step 10. A solid dark 1080x1920
  public/img/cover-base.jpg is written when missing; replace it with the fx_pieces.py --photo frame.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
STARTER = HERE.parent / "assets" / "starter"


def clone(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if subprocess.run(["cp", "-c", str(src), str(dst)], capture_output=True).returncode != 0:
        shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target")
    ap.add_argument("--sans-font", required=True)
    ap.add_argument("--title-font", required=True)
    ap.add_argument("--logo", required=True)
    ap.add_argument("--node-modules")
    ap.add_argument("--cover-spec")
    ap.add_argument("--series", default="", help="series label for the skeleton cover.json (Profile records.series_name)")
    a = ap.parse_args()
    t = pathlib.Path(a.target).resolve()
    if (t / "src").exists():
        raise SystemExit(f"{t / 'src'} already exists; not overwriting project code")
    t.mkdir(parents=True, exist_ok=True)
    for p in STARTER.rglob("*"):
        if p.is_file():
            clone(p, t / p.relative_to(STARTER))
    for sub in ("data", "media", "audio", "img", "fonts"):
        (t / "public" / sub).mkdir(parents=True, exist_ok=True)
    clone(pathlib.Path(a.sans_font), t / "public" / "fonts" / "sans.ttf")
    clone(pathlib.Path(a.title_font), t / "public" / "fonts" / "title.ttf")
    clone(pathlib.Path(a.logo), t / "public" / "img" / "logo.png")
    if a.cover_spec:
        clone(pathlib.Path(a.cover_spec), t / "public" / "data" / "cover.json")
    else:
        skeleton = {"small": ["主标题第一行"], "big": ["重音词"]}
        (t / "public" / "data" / "cover.json").write_text(json.dumps(
            {"base": {"img": "img/cover-base.jpg", "top": 0}, "series": a.series, "variants": {"a": skeleton, "b": skeleton}},
            ensure_ascii=False, indent=1))
    base = t / "public" / "img" / "cover-base.jpg"
    if not base.exists():
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x16181F:s=1080x1920",
                        "-frames:v", "1", "-q:v", "3", str(base)], check=True)
    for name in ("timeline.json", "subs.json"):
        f = t / "public" / "data" / name
        if not f.exists():
            f.write_text('{"version": "v0.0", "fps": 30, "frames": 30, "chapters": [], "items": [], "media": {"video": "", "audio": null}}'
                         if name == "timeline.json" else "[]")
    if a.node_modules:
        os.symlink(pathlib.Path(a.node_modules).resolve(), t / "node_modules")
    (t / "render-chunks.sh").chmod(0o755)
    print(f"starter ready at {t}; next: {'(node_modules linked)' if a.node_modules else 'npm install'}, then build_timeline.py -> "
          f"fx_pieces.py --copy-to {t / 'public' / 'media'} -> subs_from_lines.py -> decorate.py -> check_timeline.py")


if __name__ == "__main__":
    main()
