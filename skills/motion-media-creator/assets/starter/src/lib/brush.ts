import {lerp} from './anim';

/** Closed brush silhouette: an ellipse that, as `taper` rises, becomes a horizontal stroke
 * with a pressed start (顿笔) on the left and a thinning, lifting tail on the right. */
export const brushPath = (cx: number, cy: number, rx: number, ry: number, taper: number, n = 220) => {
  let d = '';
  for (let k = 0; k <= n; k++) {
    const th = (k / n) * Math.PI * 2;
    const u = Math.cos(th);
    const press = 1 + 0.32 * Math.exp(-(((u + 0.78) / 0.16) ** 2));
    const lift = 1 - 0.72 * ((u + 1) / 2) ** 2.4;
    const shape = lerp(1, press * lift, taper);
    const x = cx + rx * u;
    const y = cy + ry * Math.sin(th) * shape + taper * ry * 0.18 * u; // slight upward slant
    d += `${k ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
  }
  return d + 'Z';
};
