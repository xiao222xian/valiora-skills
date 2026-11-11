// The CC0 surfaces the kit's materials are made of (kit.tsx, SPEC `tex`) and the HDR environments <Stage hdri>
// can light with. tools/fetch_textures.py reads this table, downloads each entry into public/ and writes its credit
// into src/credits.ts. Node imports this file (the fetch script runs it through `node`): keep it free of imports and
// of TypeScript that does not simply erase (no enums, no namespaces).

export type TexSource = 'ambientcg' | 'polyhaven';

export type TexSetSpec = {
  source: TexSource;
  /** The source's asset id: ambientCG `Metal050A`, Poly Haven `concrete_floor_painted`. */
  id: string;
  /** Rescale the roughness map's 1st-99th percentile into this range when it is fetched. three multiplies the map by
   * the material's `roughness`, so a map that is nearly black stays a mirror whatever the material says: ambientCG
   * Metal050A averages 0.06 and every brushed metal rendered as chrome (2026-10-12, the first 3D film; the fix
   * was this remap to 0.24-0.40, which keeps the brushing pattern). */
  roughness?: [number, number];
};

/** A film lists only the sets it shows: every entry is downloaded and credited. Drop a set together with the
 * material kinds in kit.tsx that use it, and its line in src/credits.ts. */
export const TEX_SETS = {
  metal050a: {source: 'ambientcg', id: 'Metal050A', roughness: [0.24, 0.4]}, // brushed steel and aluminium
  metal051a: {source: 'ambientcg', id: 'Metal051A'}, // circular-brushed (turned) aluminium
  metal047a: {source: 'ambientcg', id: 'Metal047A'}, // copper
  rubber004: {source: 'ambientcg', id: 'Rubber004'}, // rubber; its fine pebbling also serves paint and as-cast metal
  concrete: {source: 'polyhaven', id: 'concrete_floor_painted'}, // shop floor, plinths
  leather: {source: 'polyhaven', id: 'leather_white'},
} satisfies Record<string, TexSetSpec>;

export type TexSetId = keyof typeof TEX_SETS;

/** Every set ships three maps: base colour (sRGB), roughness, and a normal map in the OpenGL convention (+Y up,
 * what three expects; ambientCG `NormalGL`, Poly Haven `nor_gl`). */
export const TEX_MAPS = ['color', 'roughness', 'normal'] as const;
export type TexMap = (typeof TEX_MAPS)[number];

/** Path under public/ (pass it to staticFile). */
export const texFile = (set: string, map: TexMap) => `assets/tex3d/${set}/${map}.jpg`;

/** Poly Haven HDRIs at 1k (about 1.5 MB each): reflections only (Stage keeps the background off), so 1k is enough. */
export const HDRIS = [{id: 'studio_small_09', res: '1k'}] as const;

/** Path under public/assets/hdri/ (the `hdri` prop of <Stage>). */
export const hdriFile = (id: string, res: string) => `${id}_${res}.hdr`;
