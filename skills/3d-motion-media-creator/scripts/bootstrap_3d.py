#!/usr/bin/env python3
"""Start a 3D motion-atlas Remotion project: a copy of lov-motion-media-creator's starter with this Skill's 3D overlay
(assets/starter-3d) laid on top and the 3D dependencies merged into package.json.

  python3 scripts/bootstrap_3d.py <project>/work/remotion
  python3 scripts/bootstrap_3d.py <dir> --base ~/repo/skills/motion-media-creator-skill
  python3 scripts/bootstrap_3d.py <dir> --dry-run          # every file it would add, overwrite or keep; writes nothing
  python3 scripts/bootstrap_3d.py <dir> --force            # update an existing project: the kit and tools, not the film
  python3 scripts/bootstrap_3d.py <dir> --force --overwrite-film   # also put the example film back

The base starter is found at --base, else $MOTION_MEDIA_CREATOR_DIR, else ~/.agents/skills/lov-motion-media-creator
(the Skill root or its assets/starter). The base's example film is left out: its scenes (src/scenes/S*.tsx) and glyph
tables (src/lib/glyphs*.ts) would put its characters into the font subsets; the overlay brings its own timeline, scene
registry and example chapters. node_modules, public/ and other generated directories are never copied, and nothing in
the target is deleted.

A few base files are patched as they are copied (a warning names any patch that no longer matches the base):
src/Cover.tsx (the example's title face, plain colour bands), tools/fonts.py and src/lib/fonts.ts (the SIL OFL faces
of tools/fetch_fonts.py instead of macOS system faces), src/components/HUD.tsx (the ruler appears whole at the first
chapter's first frame, where the opening's light line hands over to it) and audio/chapters/briefs.json (one music
brief per chapter id of src/timeline.ts).

With --force the film's own files are kept when they differ from the starter's (FILM_FILES, plus any --keep
pattern): the timeline, scenes, credits, narration, covers, media catalogue, texture table, music and cover briefs,
the lock file. package.json is merged: the 3D dependencies are set in the target's own file.
"""
import argparse
import json
import os
import re
import shutil
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

SKILL = Path(__file__).resolve().parent.parent
OVERLAY = SKILL / "assets" / "starter-3d"
DEPS = OVERLAY / "deps-3d.json"
SKIP_DIRS = {"node_modules", "public", "out", "fonts-src", "fonts-ofl", "build", ".git", "__pycache__"}
# the base's example film, not part of the 3D starter
SKIP_BASE = ["src/scenes/S*.tsx", "src/lib/glyphs*.ts", "src/dev/entry-*.tsx"]
SKIP_OVERLAY = ["deps-3d.json"]
# a film's own files: --force keeps them when they differ (fnmatch: * also matches /)
FILM_FILES = [
    "src/timeline.ts",
    "src/scenes/*",
    "src/credits.ts",
    "src/narration.ts",
    "src/Cover.tsx",
    "src/cover3d.tsx",
    "src/media.ts",
    "src/three/textures.ts",
    "audio/chapters/briefs.json",
    "cover/brief.json",
    "pnpm-lock.yaml",
]

Patch = Tuple[str, "re.Pattern[str]", str, bool]  # (what, pattern, replacement, required)
OFL_FACES = '''OFL = ROOT / "fonts-ofl" / "static"
# css family -> (font file, face index or None). The 3D starter (lov-3d-motion-media-creator) uses SIL OFL faces only:
# static weights that tools/fetch_fonts.py instances from Noto Serif SC / Noto Sans SC (Source Han Serif / Sans) and
# takes from IBM Plex Mono, so the film carries no system font whose licence does not cover publishing.
FACES = {
    "OFL-Serif": (str(OFL / "OFL-Serif.ttf"), None),  # Noto Serif SC 600: chapter names, titles
    "OFL-SerifHeavy": (str(OFL / "OFL-SerifHeavy.ttf"), None),  # Noto Serif SC 900: film title, settled big numbers
    "OFL-Sans": (str(OFL / "OFL-Sans.ttf"), None),  # Noto Sans SC 400: body, HUD segment names
    "OFL-SansMedium": (str(OFL / "OFL-SansMedium.ttf"), None),  # Noto Sans SC 500: subtitles, counting numbers
    "OFL-Mono": (str(OFL / "OFL-Mono.ttf"), None),  # IBM Plex Mono 400: readouts, notes, callouts
    "OFL-MonoMedium": (str(OFL / "OFL-MonoMedium.ttf"), None),  # IBM Plex Mono 500
}
LATIN_ONLY = {"OFL-Mono", "OFL-MonoMedium"}'''
OFL_FONT_CONSTANTS = '''// The 3D film's one set of SIL OFL faces (lov-3d-motion-media-creator): body and subtitles in the sans, chapter
// names and titles in the serif, readouts and notes in the mono (CJK in a mono string falls back to the sans).
export const BODY = "'OFL-Sans', sans-serif";
export const SERIF = "'OFL-Serif', serif";
export const MONO = "'OFL-Mono', 'OFL-Sans', monospace";
export const fam = (f: string) => `'${f}', 'OFL-Sans', sans-serif`;
export const SUBTITLE_FONT = "'OFL-SansMedium', 'OFL-Sans', sans-serif";'''

PATCHES: Dict[str, List[Patch]] = {
    "src/Cover.tsx": [
        ("COVER.font", re.compile(r"(\n  font: )'[^']*',"), r"\1'OFL-SerifHeavy',", True),
        ("COVER.bandGlyph", re.compile(r"(\n  bandGlyph: )'[^']*',"), r"\1'',", True),
    ],
    "tools/fonts.py": [
        ("FACES and LATIN_ONLY", re.compile(r"(?:# [^\n]*\n)*FACES = \{\n.*?\n\}\nLATIN_ONLY = \{[^\n]*\}", re.S), OFL_FACES.replace("\\", "\\\\"), True),
        ("FALLBACK_OK", re.compile(r"\nFALLBACK_OK = \{[^\n]*\}"), "\nFALLBACK_OK = set()", True),
    ],
    "src/lib/fonts.ts": [
        ("comment", re.compile(r"// Subset files are produced by tools/fonts\.py from macOS system faces\."), "// Subset files are produced by tools/fonts.py from the SIL OFL faces of tools/fetch_fonts.py.", False),
        ("FONT_FAMILIES", re.compile(r"export const FONT_FAMILIES = \[.*?\] as const;", re.S),
         "export const FONT_FAMILIES = ['OFL-Serif', 'OFL-SerifHeavy', 'OFL-Sans', 'OFL-SansMedium', 'OFL-Mono', 'OFL-MonoMedium'] as const;", True),
        # each family is one static face: declaring it for every weight stops the browser from faking bold on it
        ("FontFace weight", re.compile(r"fam === 'ZL-Serif' \|\| fam === 'ZL-Mono' \? \{weight: '1 1000'\} : \{\}"), "{weight: '1 1000'}", True),
        ("BODY .. SUBTITLE_FONT", re.compile(r"(?:// [^\n]*\n)?export const BODY = .*?\nexport const SUBTITLE_FONT = [^\n]*;", re.S), OFL_FONT_CONSTANTS.replace("\\", "\\\\"), True),
    ],
    # the opening's light line becomes the ruler at the first frame of chapter 01: a fade-in there shows a half-drawn
    # ruler and the opening's readout (工序 00) for two frames
    "src/components/HUD.tsx": [
        ("ruler fade-in", re.compile(r"prog\(frame, RULER_START - 2, 4, E\.linear\)"), "(frame < RULER_START ? 0 : 1)", True),
    ],
}


def find_base(arg: Optional[str]) -> Path:
    tried = []
    for label, cand in (("--base", arg), ("$MOTION_MEDIA_CREATOR_DIR", os.environ.get("MOTION_MEDIA_CREATOR_DIR")), ("default", str(Path.home() / ".agents/skills/lov-motion-media-creator"))):
        if not cand:
            continue
        p = Path(cand).expanduser()
        for d in (p / "assets" / "starter", p):
            if (d / "src" / "timeline.ts").is_file() and (d / "tools" / "bootstrap.sh").is_file() and (d / "package.json").is_file():
                return d.resolve()
        tried.append(f"{label} {p}")
        if label == "--base":
            break  # an explicit --base that is wrong is an error, not a reason to fall back
    sys.exit("cannot find lov-motion-media-creator's starter (assets/starter with src/timeline.ts, tools/bootstrap.sh); tried: " + ("; ".join(tried) or "nothing") + ". Pass --base <skill dir> or set MOTION_MEDIA_CREATOR_DIR.")


def files_of(root: Path, skip: List[str]) -> List[Path]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            rel = (Path(dirpath) / f).relative_to(root)
            if f == ".DS_Store" or any(fnmatch(rel.as_posix(), pat) for pat in skip):
                continue
            out.append(rel)
    return out


def merged_package(pkg_in: dict, deps: dict) -> Tuple[dict, List[str]]:
    pkg = json.loads(json.dumps(pkg_in))
    notes = []
    for section in ("dependencies", "devDependencies"):
        want = deps.get(section, {})
        have = pkg.setdefault(section, {})
        for name, ver in want.items():
            if name in have and have[name] != ver:
                notes.append(f"{section}.{name}: {have[name]} -> {ver}")
            have[name] = ver
        pkg[section] = dict(sorted(have.items()))
    remotion = pkg["dependencies"].get("remotion")
    if remotion and pkg["dependencies"].get("@remotion/three") != remotion:
        # every @remotion/* package must match remotion exactly
        notes.append(f"@remotion/three {pkg['dependencies'].get('@remotion/three')} -> {remotion} (the project's remotion version)")
        pkg["dependencies"]["@remotion/three"] = remotion
    return pkg, notes


def chapter_ids(timeline: str) -> List[str]:
    return re.findall(r"\bC\(\{id: '([^']+)'", timeline) or re.findall(r"\bid: '([^']+)'", timeline)


def briefs_for(text: str, ids: List[str]) -> str:
    """The base's music brief with one placeholder line per era chapter of this timeline, instead of its example film's
    (the opening and the outro play the full-length track, as in the base; its _readme says when to add them)."""
    b = json.loads(text)
    old = b.get("chapters", {})
    blank = next((v for k, v in old.items() if not k.startswith("_")), "<mood: lead instruments, texture, energy>")
    b["chapters"] = {k: v for k, v in old.items() if k.startswith("_")}
    b["chapters"].update({cid: blank for cid in ids[1:-1]})
    return json.dumps(b, indent=1, ensure_ascii=False) + "\n"


def patched(rel: str, text: str, warn: Callable[[str], None]) -> str:
    for what, pat, rep, required in PATCHES.get(rel, []):
        text, n = pat.subn(rep, text, count=1)
        if not n and required:
            warn(f"{rel}: the base no longer matches the patch for {what}; set it by hand (see the docstring of scripts/bootstrap_3d.py)")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog="\n\n".join(__doc__.split("\n\n")[1:]))
    ap.add_argument("target", type=Path, help="the Remotion project directory to create, e.g. <project>/work/remotion")
    ap.add_argument("--base", help="lov-motion-media-creator Skill directory (or its assets/starter)")
    ap.add_argument("--force", action="store_true", help="write into a non-empty directory: starter files are updated, the film's own files kept")
    ap.add_argument("--overwrite-film", action="store_true", help="with --force: also overwrite the film's own files (FILM_FILES) with the example's")
    ap.add_argument("--keep", action="append", default=[], metavar="PATTERN", help="with --force: keep these paths too (fnmatch, relative to the target; repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, path by path; write nothing")
    a = ap.parse_args()

    if not (OVERLAY / "src").is_dir() or not DEPS.is_file():
        sys.exit(f"this Skill's overlay is incomplete: expected {OVERLAY}/src and {DEPS}")
    base = find_base(a.base)
    target = a.target.expanduser().resolve()
    if target.exists() and not target.is_dir():
        sys.exit(f"{target} exists and is not a directory")
    if target == base or base in target.parents or target in base.parents:
        sys.exit(f"target {target} overlaps the base starter {base}")
    nonempty = target.is_dir() and any(target.iterdir())
    if nonempty and not a.force and not a.dry_run:
        sys.exit(f"{target} is not empty. --dry-run lists what --force would overwrite and keep; --force updates the kit and tools and keeps the film's own files")

    warnings: List[str] = []
    base_files = files_of(base, SKIP_BASE)
    overlay_files = files_of(OVERLAY, SKIP_OVERLAY)
    source: Dict[str, Path] = {r.as_posix(): base / r for r in base_files}
    source.update({r.as_posix(): OVERLAY / r for r in overlay_files})
    replaced = sorted(set(r.as_posix() for r in base_files) & set(r.as_posix() for r in overlay_files))
    skipped = [f for f in files_of(base, []) if f not in base_files]

    # the content each path gets: copied as is, or patched text
    ids = chapter_ids((OVERLAY / "src" / "timeline.ts").read_text(encoding="utf-8"))
    content: Dict[str, bytes] = {}
    for rel, src in source.items():
        if rel in PATCHES:
            content[rel] = patched(rel, src.read_text(encoding="utf-8"), warnings.append).encode("utf-8")
        elif rel == "audio/chapters/briefs.json":
            content[rel] = briefs_for(src.read_text(encoding="utf-8"), ids).encode("utf-8")
        else:
            content[rel] = src.read_bytes()
    pkg_target = target / "package.json"
    pkg_in = json.loads(pkg_target.read_text(encoding="utf-8")) if pkg_target.is_file() else json.loads((base / "package.json").read_text(encoding="utf-8"))
    pkg, notes = merged_package(pkg_in, json.loads(DEPS.read_text(encoding="utf-8")))
    content["package.json"] = (json.dumps(pkg, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    keep_pats = FILM_FILES + a.keep if not a.overwrite_film else a.keep
    new, same, overwrite, keep = [], [], [], []
    for rel in sorted(content):
        dst = target / rel
        if not dst.exists():
            new.append(rel)
        elif dst.read_bytes() == content[rel]:
            same.append(rel)
        elif rel != "package.json" and any(fnmatch(rel, p) for p in keep_pats):
            keep.append(rel)
        else:
            overwrite.append(rel)

    left_out = ", ".join(f"{pat} ({n})" for pat in SKIP_BASE for n in [sum(fnmatch(f.as_posix(), pat) for f in skipped)] if n)
    print(f"base     {base} ({len(base_files)} files; left out its example film: {left_out or 'nothing'})")
    print(f"overlay  {OVERLAY} ({len(overlay_files)} files; replaces {', '.join(replaced) or 'nothing'})")
    print(f"target   {target}: {len(new)} new, {len(same)} unchanged, {len(overwrite)} overwritten, {len(keep)} kept")
    for n in notes:
        print(f"package  {n}")
    for rel in overwrite:
        print(f"  {'merge     ' if rel == 'package.json' else 'overwrite '} {rel}")
    for rel in keep:
        print(f"  keep       {rel} (the film's own; --overwrite-film replaces it)")
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if a.dry_run:
        print("dry run: nothing written")
        return 0

    for rel in new + overwrite:
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if rel in source and content[rel] == source[rel].read_bytes():
            shutil.copy2(source[rel], dst)
        else:
            dst.write_bytes(content[rel])
    for f in list((target / "tools").glob("*.sh")) + list((target / "tools").glob("*.py")):
        f.chmod(f.stat().st_mode | 0o111)

    rel = os.path.relpath(target)
    print(f"\nwrote {len(new) + len(overwrite)} files; package.json has the 3D dependencies (pnpm-lock.yaml updates on install)")
    if nonempty and "src/credits.ts" in overwrite:
        print("src/credits.ts went back to the example's: run python3 tools/fetch_textures.py again to re-add the texture credits")
    print(f"""
next:
  cd {rel}
  pnpm install                          # three, @react-three/*, postprocessing, @remotion/three
  python3 tools/fetch_textures.py       # CC0 textures + HDRI into public/assets, credits into src/credits.ts
                                        #   (offline: --offline writes flat placeholders; fetch again before delivery)
  python3 tools/fetch_fonts.py          # SIL OFL faces into fonts-ofl/ (--from <dir> takes them from a local folder)
  tools/bootstrap.sh                    # base: fonts subset from src/, paper and grain, placeholder logo, silence
                                        #   FILM_LOGO=<png> FILM_SEAL_DIR=<dir> tools/bootstrap.sh for the brand's own
  export GL=angle                       # tools/stills.mjs (preview stills, deliver.sh covers) reads it; the CLI reads remotion.config.ts
  npx tsc --noEmit -p .
  node tools/chapters.mjs --out /tmp/chapters.txt
  tools/preview.sh explode stills 16x9 30 240
""")
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
