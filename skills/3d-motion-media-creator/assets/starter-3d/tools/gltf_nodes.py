#!/usr/bin/env python3
"""List what a glTF / GLB contains before it goes into the film: the node tree (with mesh and material names), materials
and the images they use, animations, the licence fields of `asset`, and the extensions it needs. Use it to find the
brand marks to remove (<Model remove=...>, often a node or material named Logo, Emblem, Badge, Plate, or an image
that is one), to see whether it is Draco-compressed (<Model draco>), and to read the author and licence for
src/credits.ts. Reads the JSON only; geometry is not decoded.

  python3 tools/gltf_nodes.py public/assets/models/press.glb
  python3 tools/gltf_nodes.py model.gltf --json        # the same as JSON
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

# names that usually mean a mark to remove; "sign" and "text" left out (design, texture)
MARKS = re.compile(r"logo|emblem|badge|brand|plate|decal|sticker|label|trademark", re.I)


def load(path: Path) -> dict:
    data = path.read_bytes()
    if data[:4] == b"glTF":
        _, _, length = struct.unpack_from("<4sII", data, 0)
        clen, ctype = struct.unpack_from("<I4s", data, 12)
        if ctype != b"JSON":
            sys.exit(f"{path}: first GLB chunk is {ctype!r}, not JSON")
        return json.loads(data[20 : 20 + clen].decode("utf-8"))
    return json.loads(data.decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("file", type=Path)
    ap.add_argument("--json", action="store_true", help="print a JSON summary instead of text")
    a = ap.parse_args()
    if not a.file.is_file():
        sys.exit(f"no such file: {a.file}")
    g = load(a.file)
    nodes, meshes, mats = g.get("nodes", []), g.get("meshes", []), g.get("materials", [])
    textures, images = g.get("textures", []), g.get("images", [])

    def mat_images(m: dict) -> list:
        out = []
        for k, v in {**m.get("pbrMetallicRoughness", {}), **m}.items():
            if isinstance(v, dict) and "index" in v and k.endswith("Texture"):
                src = textures[v["index"]].get("source") if v["index"] < len(textures) else None
                img = images[src] if src is not None and src < len(images) else {}
                out.append(f"{k}={img.get('name') or img.get('uri') or f'image {src}'}")
        return out

    def node_line(i: int) -> dict:
        n = nodes[i]
        mesh = meshes[n["mesh"]] if "mesh" in n else None
        mnames = [mats[p["material"]].get("name", f"material {p['material']}") for p in (mesh or {}).get("primitives", []) if "material" in p]
        return {"node": n.get("name", f"node {i}"), "mesh": mesh.get("name") if mesh else None, "materials": mnames, "children": n.get("children", [])}

    scenes = g.get("scenes", [{"nodes": [i for i in range(len(nodes))]}])
    roots = scenes[g.get("scene", 0)].get("nodes", [])
    summary = {
        "asset": g.get("asset", {}),
        "extensionsRequired": g.get("extensionsRequired", []),
        "extensionsUsed": g.get("extensionsUsed", []),
        "draco": "KHR_draco_mesh_compression" in g.get("extensionsUsed", []),
        "tree": [],
        "materials": [{"name": m.get("name", f"material {i}"), "images": mat_images(m)} for i, m in enumerate(mats)],
        "images": [img.get("name") or img.get("uri") or f"image {i}" for i, img in enumerate(images)],
        "animations": [{"name": an.get("name", f"animation {i}"), "channels": len(an.get("channels", []))} for i, an in enumerate(g.get("animations", []))],
    }

    def walk(i: int, depth: int) -> None:
        line = node_line(i)
        summary["tree"].append({"depth": depth, **{k: v for k, v in line.items() if k != "children"}})
        for c in line["children"]:
            walk(c, depth + 1)

    for r in roots:
        walk(r, 0)

    if a.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    asset = summary["asset"]
    print(f"{a.file}  generator: {asset.get('generator', '-')}  copyright: {asset.get('copyright', '-')}")
    if asset.get("extras"):
        print(f"asset.extras: {json.dumps(asset['extras'], ensure_ascii=False)}")
    if summary["extensionsUsed"]:
        print(f"extensions: {', '.join(summary['extensionsUsed'])}{'  (Draco: <Model draco>, decoders in public/draco/)' if summary['draco'] else ''}")
    print("\nnodes (top-level ones are what <Model only> filters):")
    for t in summary["tree"]:
        names = [t["node"], t["mesh"] or "", *t["materials"]]
        flag = "  <- brand mark?" if any(MARKS.search(n or "") for n in names) else ""
        mesh = f"  mesh {t['mesh']}" if t["mesh"] else ""
        mat = f"  [{', '.join(t['materials'])}]" if t["materials"] else ""
        print(f"{'  ' * t['depth']}{t['node']}{mesh}{mat}{flag}")
    print("\nmaterials:")
    for m in summary["materials"]:
        flag = "  <- brand mark?" if MARKS.search(m["name"]) or any(MARKS.search(x.split("=", 1)[-1]) for x in m["images"]) else ""
        print(f"  {m['name']}{'  ' + ', '.join(m['images']) if m['images'] else ''}{flag}")
    if summary["animations"]:
        print("\nanimations (<Model clip={{name, t: frame / fps}}>):")
        for an in summary["animations"]:
            print(f"  {an['name']}  {an['channels']} channels")
    return 0


if __name__ == "__main__":
    sys.exit(main())
