import React, {useMemo} from 'react';
import {staticFile} from 'remotion';
import {MeshReflectorMaterial, RoundedBox, useTexture} from '@react-three/drei';
import * as THREE from 'three';
import {TEX_MAPS, texFile, type TexSetId} from './textures';
import type {V3} from './camera';
import {FLOOR_Y} from './GroundShadow';

// Shared 3D kit: physically based materials with a real micro-surface (CC0 texture sets from textures.ts, self-hosted
// under public/assets/tex3d by tools/fetch_textures.py), floors, and bevelled boxes.

// ---------------------------------------------------------------------------------------------
// Materials

export type MatKind =
  | 'brushedAlu' // linear brushed aluminium (trays, housings)
  | 'circularAlu' // turned / circular-brushed aluminium (caps, end plates)
  | 'steel' // brushed stainless, bright steel (shafts, gears)
  | 'galvanized' // zinc-coated sheet steel
  | 'bareSteel' // raw sheet steel, body-in-white
  | 'darkSteel' // black-oxide or machined cast iron, tooling, fasteners
  | 'chrome' // hydraulic rods, tie bars
  | 'castAlu' // as-cast aluminium, matte
  | 'moltenAlu' // liquid aluminium: mirror silver; add a dull red emissive in the scene
  | 'copper' // foil, windings, busbars
  | 'rubber' // seals, tyres, cable jackets
  | 'machinePaint' // off-white machine enamel
  | 'safetyYellow' // safety paint on guards
  | 'graphitePaint' // dark machine paint
  | 'anodized' // dark anodised aluminium
  | 'leather'
  | 'concrete'
  | 'glass';

type Spec = {tex?: TexSetId; color: string; metalness: number; roughness: number; useMap?: boolean; normal?: number; clearcoat?: number; clearcoatRoughness?: number; anisotropy?: number};

/** `roughness` multiplies the set's roughness map (three reads the map's green channel), so it is a scale, not the
 * final value: metal050a's map is remapped to 0.24-0.40, and 0.9 on it gives a satin 0.22-0.36. Kinds without `tex`
 * (molten metal, glass) are the only untextured surfaces the art direction allows. */
const SPEC: Record<MatKind, Spec> = {
  brushedAlu: {tex: 'metal050a', color: '#d4d8dc', metalness: 1, roughness: 0.9, normal: 0.6, anisotropy: 0.7},
  circularAlu: {tex: 'metal051a', color: '#d9dde1', metalness: 1, roughness: 0.85, normal: 0.6},
  steel: {tex: 'metal050a', color: '#b9bfc5', metalness: 1, roughness: 0.75, normal: 0.5, anisotropy: 0.4},
  galvanized: {tex: 'metal050a', color: '#aeb6bc', metalness: 0.9, roughness: 1.1, normal: 0.35},
  bareSteel: {tex: 'metal050a', color: '#a9b0b6', metalness: 1, roughness: 1.0, normal: 0.4},
  darkSteel: {tex: 'metal050a', color: '#3d4247', metalness: 0.9, roughness: 1.25, normal: 0.8},
  chrome: {tex: 'metal051a', color: '#e8ecef', metalness: 1, roughness: 0.18, normal: 0.15},
  // the rubber set's fine pebbling reads as sand-cast grain; the concrete set (the first 3D film's choice) showed its
  // chipped-paint marks repeating tile by tile on a large casting (2026-10-13)
  castAlu: {tex: 'rubber004', color: '#b5bac0', metalness: 0.85, roughness: 1.15, normal: 0.3},
  moltenAlu: {color: '#dfe4ea', metalness: 1, roughness: 0.06},
  copper: {tex: 'metal047a', color: '#ffffff', metalness: 1, roughness: 0.8, useMap: true, normal: 0.4},
  rubber: {tex: 'rubber004', color: '#1a1a1a', metalness: 0, roughness: 1, normal: 0.6},
  machinePaint: {tex: 'rubber004', color: '#d6d2c9', metalness: 0.05, roughness: 0.75, normal: 0.12, clearcoat: 0.35, clearcoatRoughness: 0.35},
  safetyYellow: {tex: 'rubber004', color: '#d7a514', metalness: 0.05, roughness: 0.8, normal: 0.15, clearcoat: 0.2, clearcoatRoughness: 0.4},
  graphitePaint: {tex: 'rubber004', color: '#2a2d31', metalness: 0.2, roughness: 0.8, normal: 0.15, clearcoat: 0.3, clearcoatRoughness: 0.35},
  anodized: {tex: 'metal050a', color: '#2b2f35', metalness: 0.85, roughness: 0.9, normal: 0.35},
  leather: {tex: 'leather', color: '#ffffff', metalness: 0, roughness: 1, useMap: true, normal: 0.8},
  concrete: {tex: 'concrete', color: '#ffffff', metalness: 0, roughness: 1, useMap: true, normal: 1},
  glass: {color: '#0e1114', metalness: 0, roughness: 0.03},
};

type TexMaps = {map: THREE.Texture; roughnessMap: THREE.Texture; normalMap: THREE.Texture};

const urls = (set: TexSetId) => {
  const [color, roughness, normal] = TEX_MAPS.map((m) => staticFile(texFile(set, m)));
  return {map: color, roughnessMap: roughness, normalMap: normal};
};

/** Loads through Suspense, which @remotion/three turns into a delayRender: the frame waits for the images. */
const useTexSet = (set: TexSetId) => useTexture(urls(set)) as TexMaps;

export type MatOpts = {
  /** Tiles per UV unit. Box, sphere and cylinder UVs run 0-1 per face; extruded shapes and planes built in metres
   * carry metres, so a 12 cm gear wants repeat ~8 to show the texture at its real scale. */
  repeat?: number | [number, number];
  color?: string;
  roughness?: number;
  metalness?: number;
  normalScale?: number;
  // no envMapIntensity: three 0.186 ignores it under scene.environment (Stage's HDRI or StudioEnv) and uses Stage's
  // envIntensity for every material; per-material control needs the material's own envMap (pitfalls-3d)
};

/** A physically based material for a real surface. Every call returns its own instance (its own texture repeat): call
 * it once per mesh type, with options that are stable from frame to frame (useMemo rebuilds on change). */
export const useMat = (kind: MatKind, o: MatOpts = {}): THREE.MeshPhysicalMaterial => {
  const s = SPEC[kind];
  // hooks run unconditionally: untextured kinds still load a set (drei caches it)
  const tex = useTexSet(s.tex ?? 'metal050a');
  const rep = Array.isArray(o.repeat) ? o.repeat : [o.repeat ?? 1, o.repeat ?? 1];
  return useMemo(() => {
    const clone = (t: THREE.Texture, srgb = false) => {
      const c = t.clone();
      c.wrapS = c.wrapT = THREE.RepeatWrapping;
      c.repeat.set(rep[0], rep[1]);
      c.anisotropy = 8;
      c.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      c.needsUpdate = true;
      return c;
    };
    const m = new THREE.MeshPhysicalMaterial({
      color: o.color ?? s.color,
      metalness: o.metalness ?? s.metalness,
      roughness: o.roughness ?? s.roughness,
      clearcoat: s.clearcoat ?? 0,
      clearcoatRoughness: s.clearcoatRoughness ?? 0,
      // brushed metal stretches its highlights across the grain (along the UV u direction)
      anisotropy: s.anisotropy ?? 0,
    });
    if (kind === 'glass') {
      m.opacity = 0.35;
      m.transparent = true;
      m.ior = 1.5;
      m.clearcoat = 1;
    }
    if (s.tex) {
      m.roughnessMap = clone(tex.roughnessMap);
      m.normalMap = clone(tex.normalMap);
      const n = (o.normalScale ?? 1) * (s.normal ?? 1);
      m.normalScale = new THREE.Vector2(n, n);
      if (s.useMap) m.map = clone(tex.map, true);
    }
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, tex, rep[0], rep[1], o.color, o.roughness, o.metalness, o.normalScale]);
};

// ---------------------------------------------------------------------------------------------
// Floors

/** Dark studio floor with a blurred reflection (product-shot look), FLOOR_Y under the contact plane so <GroundShadow>
 * fits between. 400 m wide so its edge stays beyond Stage's fog in every direction. Turn `receiveShadow` off under a
 * shadow-casting spot: variance shadow maps band across a large plane; let <GroundShadow> ground the objects instead. */
export const StudioFloor: React.FC<{size?: number; color?: string; mirror?: number; y?: number; res?: number; receiveShadow?: boolean}> = ({
  size = 400,
  color = '#0b0c0e',
  mirror = 0.45,
  y = FLOOR_Y,
  res = 1024,
  receiveShadow = true,
}) => (
  <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, y, 0]} receiveShadow={receiveShadow}>
    <planeGeometry args={[size, size]} />
    <MeshReflectorMaterial resolution={res} mirror={mirror} mixBlur={6} mixStrength={1.3} blur={[400, 120]} roughness={0.85} metalness={0.3} color={color} />
  </mesh>
);

/** Painted concrete shop floor (CC0 texture), tiled every `tile` metres, FLOOR_Y under the contact plane; 400 m wide
 * like StudioFloor, so its edge stays in the fog. */
export const ConcreteFloor: React.FC<{size?: number; tile?: number; y?: number; color?: string; receiveShadow?: boolean}> = ({size = 400, tile = 4, y = FLOOR_Y, color = '#8a8d90', receiveShadow = true}) => {
  const m = useMat('concrete', {repeat: size / tile, color});
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, y, 0]} receiveShadow={receiveShadow} material={m}>
      <planeGeometry args={[size, size]} />
    </mesh>
  );
};

// ---------------------------------------------------------------------------------------------
// Geometry

/** A box with real bevels so its edges catch the light (the art direction: no sharp-edged boxes, radius >= 1 mm at
 * real scale). Size in metres; the radius is clamped below half the thinnest side. */
export const Bevel: React.FC<{size: V3; r?: number; position?: V3; rotation?: V3; material: THREE.Material; castShadow?: boolean}> = ({
  size,
  r = 0.004,
  position,
  rotation,
  material,
  castShadow = true,
}) => (
  <RoundedBox args={size} radius={Math.min(r, Math.min(...size) / 2 - 1e-4)} smoothness={3} position={position} rotation={rotation} material={material} castShadow={castShadow} receiveShadow />
);
