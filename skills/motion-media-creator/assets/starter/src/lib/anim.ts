import {Easing, interpolate} from 'remotion';

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const mix = lerp;

export const E = {
  outCubic: Easing.out(Easing.cubic),
  inCubic: Easing.in(Easing.cubic),
  inOutCubic: Easing.inOut(Easing.cubic),
  outExpo: Easing.out(Easing.exp),
  inOutExpo: Easing.inOut(Easing.exp),
  outQuint: Easing.out(Easing.poly(5)),
  inOutQuint: Easing.inOut(Easing.poly(5)),
  outBack: Easing.out(Easing.back(1.6)),
  inOutSine: Easing.inOut(Easing.sin),
  linear: (t: number) => t,
};

/** 0..1 progress of `frame` through [start, start+dur], eased and clamped. */
export const prog = (frame: number, start: number, dur: number, ease: (t: number) => number = E.inOutCubic) =>
  interpolate(frame, [start, start + Math.max(1, dur)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: ease,
  });

/** Fade in over [a, a+inDur], hold, fade out over [b-outDur, b]. */
export const window01 = (frame: number, a: number, b: number, inDur = 10, outDur = 10) =>
  Math.min(prog(frame, a, inDur, E.outCubic), 1 - prog(frame, b - outDur, outDur, E.inCubic));

/** Deterministic PRNG (mulberry32). */
export const rng = (seed: number) => {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

export type Pt = [number, number];

export const polyline = (pts: Pt[], close = false) =>
  pts.length ? `M${pts.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('L')}${close ? 'Z' : ''}` : '';

/** Catmull-Rom spline through points as a cubic Bezier path. */
export const smoothPath = (pts: Pt[], close = false, tension = 0.5) => {
  if (pts.length < 2) return '';
  const p = close ? [pts[pts.length - 1], ...pts, pts[0], pts[1]] : [pts[0], ...pts, pts[pts.length - 1]];
  let d = `M${p[1][0].toFixed(1)},${p[1][1].toFixed(1)}`;
  for (let i = 1; i < p.length - 2; i++) {
    const [x0, y0] = p[i - 1];
    const [x1, y1] = p[i];
    const [x2, y2] = p[i + 1];
    const [x3, y3] = p[i + 2];
    const c1x = x1 + ((x2 - x0) / 6) * tension * 2;
    const c1y = y1 + ((y2 - y0) / 6) * tension * 2;
    const c2x = x2 - ((x3 - x1) / 6) * tension * 2;
    const c2y = y2 - ((y3 - y1) / 6) * tension * 2;
    d += `C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`;
  }
  return close ? d + 'Z' : d;
};

export const polyLength = (pts: Pt[]) => {
  let L = 0;
  for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  return L;
};

/** Leading fraction t of a polyline (by arc length). */
export const partialPolyline = (pts: Pt[], t: number): Pt[] => {
  if (t >= 1) return pts;
  if (t <= 0 || pts.length < 2) return pts.slice(0, 1);
  const total = polyLength(pts);
  let target = total * t;
  const out: Pt[] = [pts[0]];
  for (let i = 1; i < pts.length; i++) {
    const seg = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    if (seg >= target) {
      const k = seg === 0 ? 0 : target / seg;
      out.push([lerp(pts[i - 1][0], pts[i][0], k), lerp(pts[i - 1][1], pts[i][1], k)]);
      return out;
    }
    target -= seg;
    out.push(pts[i]);
  }
  return out;
};

/** Point and tangent angle at fraction t along a polyline. */
export const pointAt = (pts: Pt[], t: number): {p: Pt; a: number} => {
  const total = polyLength(pts);
  let target = total * clamp01(t);
  for (let i = 1; i < pts.length; i++) {
    const dx = pts[i][0] - pts[i - 1][0];
    const dy = pts[i][1] - pts[i - 1][1];
    const seg = Math.hypot(dx, dy);
    if (seg >= target || i === pts.length - 1) {
      const k = seg === 0 ? 0 : Math.min(1, target / seg);
      return {p: [pts[i - 1][0] + dx * k, pts[i - 1][1] + dy * k], a: Math.atan2(dy, dx)};
    }
    target -= seg;
  }
  return {p: pts[0], a: 0};
};

/** Dash props that reveal a stroke of known length to fraction t. */
export const drawOn = (length: number, t: number) => ({
  strokeDasharray: `${length} ${length}`,
  strokeDashoffset: length * (1 - clamp01(t)),
});

export const hexA = (hex: string, a: number) => {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};
