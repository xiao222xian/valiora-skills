import * as THREE from 'three';

// Procedural parts of a small single-stage gearbox, in metres: an involute spur-gear pair (module 4 mm, 14 and 34
// teeth, centre distance 96 mm), a split cast housing, shafts, bearings, bolts. Every hard edge has a bevel or a
// chamfer, so it catches the light. Shafts run along Z; the split plane is y = SPLIT.

export const MODULE = 0.004;
export const PINION = {teeth: 14, x: -0.048, width: 0.028, bore: 0.009};
export const WHEEL = {teeth: 34, x: 0.048, width: 0.024, bore: 0.012};
export const SPLIT = 0.09; // shaft axis height = split plane of the housing
// top clears the large gear's tip circle (0.09 + 0.072) by 14 mm
export const HOUSING = {x0: -0.1, x1: 0.14, z: 0.05, wall: 0.01, floor: 0.012, top: 0.176, r: 0.012};
export const SHAFT = {pinion: {r: 0.009, z0: -0.065, z1: 0.125}, wheel: {r: 0.012, z0: -0.125, z1: 0.065}};
export const BEARING = {pinion: 0.022, wheel: 0.026, width: 0.016, z: 0.052};
export const BOSS = {pinion: 0.03, wheel: 0.034, depth: 0.012, clearance: 0.0005};

const pitchR = (teeth: number) => (teeth * MODULE) / 2;
export const outerR = (teeth: number) => pitchR(teeth) + MODULE;

const inv = (a: number) => Math.tan(a) - a;
const polar = (r: number, a: number) => new THREE.Vector2(r * Math.cos(a), r * Math.sin(a));

/** Outline of an involute spur gear (20 degree pressure angle) as points, counter-clockwise. */
const gearOutline = (teeth: number) => {
  const rp = pitchR(teeth);
  const alpha = (20 * Math.PI) / 180;
  const rb = rp * Math.cos(alpha);
  const ra = rp + MODULE;
  const rf = rp - 1.25 * MODULE;
  const r0 = Math.max(rb, rf);
  // half the tooth's angular thickness at radius r, less 0.2 mm of backlash per flank: zero-backlash flanks of a
  // meshing pair coincide and z-fight along the contact line
  const half = (r: number) => Math.PI / (2 * teeth) + inv(alpha) - inv(Math.acos(Math.min(1, rb / r))) - 0.0002 / rp;
  const S = 8;
  const pts: THREE.Vector2[] = [];
  for (let i = 0; i < teeth; i++) {
    const c = (i / teeth) * Math.PI * 2;
    const h0 = half(r0);
    pts.push(polar(rf, c - h0));
    for (let k = 0; k <= S; k++) {
      const r = r0 + ((ra - r0) * k) / S;
      pts.push(polar(r, c - half(r)));
    }
    for (let k = S; k >= 0; k--) {
      const r = r0 + ((ra - r0) * k) / S;
      pts.push(polar(r, c + half(r)));
    }
    pts.push(polar(rf, c + h0));
    // root arc to the next tooth
    const next = ((i + 1) / teeth) * Math.PI * 2 - h0;
    for (let k = 1; k < 4; k++) pts.push(polar(rf, c + h0 + ((next - c - h0) * k) / 4));
  }
  return pts;
};

const circle = (r: number, x = 0, y = 0) => {
  const p = new THREE.Path();
  p.absarc(x, y, r, 0, Math.PI * 2, true);
  return p;
};

// The bevel is cut into the outline (bevelOffset = -bevelSize), not added around it: three grows the outline by
// bevelSize by default, and meshing teeth or a bearing in its seat would then overlap and z-fight.
const extrude = (shape: THREE.Shape, depth: number, bevel: number, curveSegments = 24) => {
  const size = bevel * 0.8;
  const g = new THREE.ExtrudeGeometry(shape, {depth: depth - 2 * bevel, bevelEnabled: true, bevelThickness: bevel, bevelSize: size, bevelOffset: -size, bevelSegments: 2, curveSegments});
  g.translate(0, 0, -(depth - 2 * bevel) / 2);
  return g;
};

/** Spur gear centred on the origin, axis along Z, `width` thick, with a bore and (on large gears) lightening holes. */
export const gearGeometry = (teeth: number, width: number, bore: number) => {
  const s = new THREE.Shape(gearOutline(teeth));
  s.holes.push(circle(bore));
  const rp = pitchR(teeth);
  if (rp > 0.05) {
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2 + Math.PI / 6;
      s.holes.push(circle(rp * 0.15, Math.cos(a) * rp * 0.58, Math.sin(a) * rp * 0.58));
    }
  }
  return extrude(s, width, 0.0008);
};

/** Rounded rectangle centred on (cx, cy). */
const roundRect = (path: THREE.Shape | THREE.Path, cx: number, cy: number, w: number, h: number, r: number) => {
  const x0 = cx - w / 2;
  const y0 = cy - h / 2;
  path.moveTo(x0 + r, y0);
  path.lineTo(x0 + w - r, y0);
  path.absarc(x0 + w - r, y0 + r, r, -Math.PI / 2, 0, false);
  path.lineTo(x0 + w, y0 + h - r);
  path.absarc(x0 + w - r, y0 + h - r, r, 0, Math.PI / 2, false);
  path.lineTo(x0 + r, y0 + h);
  path.absarc(x0 + r, y0 + h - r, r, Math.PI / 2, Math.PI, false);
  path.lineTo(x0, y0 + r);
  path.absarc(x0 + r, y0 + r, r, Math.PI, Math.PI * 1.5, false);
  return path;
};

/** A plan-view outline (x, z) extruded upwards from y0 to y1. */
const upright = (shape: THREE.Shape, y0: number, y1: number, bevel: number) => {
  const g = extrude(shape, y1 - y0, bevel, 12);
  // shape (x, y) -> world (x, -z); extrusion -> +y
  g.rotateX(-Math.PI / 2);
  g.translate(0, (y0 + y1) / 2, 0);
  return g;
};

const H = HOUSING;
const cx = (H.x0 + H.x1) / 2;
const w = H.x1 - H.x0;

/** Lower housing walls: an open-topped rounded ring from the floor to the split plane. */
export const housingWalls = () => {
  const s = roundRect(new THREE.Shape(), cx, 0, w, 2 * H.z, H.r) as THREE.Shape;
  s.holes.push(roundRect(new THREE.Path(), cx, 0, w - 2 * H.wall, 2 * H.z - 2 * H.wall, H.r - H.wall + 0.002) as THREE.Path);
  return upright(s, 0, SPLIT, 0.0012);
};

/** The cover: one solid block from the split plane to the top (its underside is never seen from above). */
export const coverBlock = () => upright(roundRect(new THREE.Shape(), cx, 0, w, 2 * H.z, H.r) as THREE.Shape, SPLIT, H.top, 0.0015);

/** The whole closed housing as one block (for the instanced units of the batch shot). */
export const unitBlock = () => upright(roundRect(new THREE.Shape(), cx, 0, w, 2 * H.z, H.r) as THREE.Shape, 0.0002, H.top, 0.0015);

/** Half of a bearing boss on a wall face: an annulus half (lower half for the housing, upper for the cover) in the
 * XY plane, `depth` thick along +Z from z = 0. Closed on the cut, so the split face reads as solid metal. */
export const bossHalf = (outer: number, inner: number, upper: boolean) => {
  const s = new THREE.Shape();
  const a0 = upper ? 0 : Math.PI;
  s.moveTo(Math.cos(a0) * outer, 0);
  s.absarc(0, 0, outer, a0, a0 + Math.PI, false);
  s.lineTo(Math.cos(a0 + Math.PI) * inner, 0);
  s.absarc(0, 0, inner, a0 + Math.PI, a0, true);
  s.closePath();
  const g = extrude(s, BOSS.depth, 0.001, 32);
  g.translate(0, 0, BOSS.depth / 2);
  return g;
};

/** Ring (bearing race, washer) centred on the origin, axis along Z. */
export const ring = (outer: number, inner: number, width: number, bevel = 0.0008) => {
  const s = new THREE.Shape();
  s.absarc(0, 0, outer, 0, Math.PI * 2, false);
  s.holes.push(circle(inner));
  return extrude(s, width, bevel, 48);
};

/** Shaft along Z from z0 to z1 with chamfered ends. */
export const shaftGeometry = (r: number, z0: number, z1: number) => {
  const c = Math.min(0.0012, r * 0.15);
  const L = z1 - z0;
  const prof = [
    [0, -L / 2],
    [r - c, -L / 2],
    [r, -L / 2 + c],
    [r, L / 2 - c],
    [r - c, L / 2],
    [0, L / 2],
  ].map(([x, y]) => new THREE.Vector2(x, y));
  const g = new THREE.LatheGeometry(prof, 48);
  // lathe axis Y -> Z
  g.rotateX(Math.PI / 2);
  g.translate(0, 0, (z0 + z1) / 2);
  return g;
};

/** Hex-head bolt standing on y = 0 (head on top of the face, shank below it), axis along Y. */
export const boltGeometries = () => {
  const head = new THREE.CylinderGeometry(0.0062, 0.0062, 0.005, 6);
  head.translate(0, 0.0025, 0);
  const shank = new THREE.CylinderGeometry(0.0034, 0.0034, 0.045, 20);
  shank.translate(0, -0.0225, 0);
  return {head, shank};
};
export const BOLTS: [number, number][] = [-0.086, cx, 0.126].flatMap((x) => [-1, 1].map((s): [number, number] => [x, s * (H.z - H.wall / 2)]));
