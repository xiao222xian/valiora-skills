#!/bin/bash
# Bundle an entry once for many renders. Run from the Remotion project root (where public/ is).
# The bundler copies public/ into every bundle (about 1 GB once a film carries footage or 3D textures),
# and the render server does not follow a symlinked public dir. So: bundle against an empty public dir,
# then clone public/ in (cp -c makes APFS clones on macOS: no extra space; plain copy elsewhere).
#   tools/bundle.sh <entry> <out-dir>        e.g. tools/bundle.sh src/index.ts ../build/main-16x9
set -euo pipefail
[ $# -eq 2 ] || { echo "usage: tools/bundle.sh <entry> <out-dir>" >&2; exit 2; }
ENTRY=$1; OUT=$2
[ -d public ] || { echo "bundle.sh: run from the Remotion project root (no public/ here)" >&2; exit 1; }
case "$OUT" in "" | "/" | "." | ".." | "$HOME" | "$PWD") echo "bundle.sh: refusing out-dir '$OUT'" >&2; exit 1 ;; esac
EMPTY=$(mktemp -d "${TMPDIR:-/tmp}/empty-public_XXXXXX")
rm -rf "$OUT"
# no shared webpack cache: parallel bundles (one per chapter preview) would race on it
npx remotion bundle "$ENTRY" --out-dir "$OUT" --public-dir "$EMPTY" --bundle-cache=false --log=error >/dev/null
rmdir "$EMPTY"
rm -rf "$OUT/public"
cp -Rc public "$OUT/public" 2>/dev/null || { rm -rf "$OUT/public"; cp -R public "$OUT/public"; }
