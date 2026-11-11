import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {noise2D} from '@remotion/noise';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS} from '../timeline';
import {E, Pt, clamp01, hexA, lerp, partialPolyline, pointAt, polyLength, polyline, prog, rng} from '../lib/anim';
import {BODY, MONO, fam} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const C5 = CHAPTERS[5];
const P = C5.palette;
const GOLD = '#C9A15A';
const CREAM = '#f3e5c6';

// Route waypoints (lon, lat). Only points and the line are drawn: no coastlines, no borders.
// The Han envoys' furthest stop on this route is 安息; beyond it the line is drawn as the
// trade extension, and 大秦 carries a note that no Han envoy got there.
const ROUTE: {lon: number; lat: number; name?: string; en?: string; note?: string}[] = [
  {lon: 108.9, lat: 34.3, name: '长安', en: "CHANG'AN"},
  {lon: 102.6, lat: 37.9},
  {lon: 98.5, lat: 39.7},
  {lon: 94.7, lat: 40.1, name: '敦煌', en: 'DUNHUANG'},
  {lon: 89.2, lat: 42.9},
  {lon: 83.0, lat: 41.7},
  {lon: 76.0, lat: 39.5, name: '疏勒', en: 'KASHGAR'},
  {lon: 71.8, lat: 40.5, name: '大宛', en: 'FERGANA'},
  {lon: 67.0, lat: 39.6},
  {lon: 62.2, lat: 37.6},
  {lon: 54.4, lat: 36.2, name: '安息', en: 'PARTHIA'},
  {lon: 44.6, lat: 33.1},
  {lon: 36.2, lat: 36.2},
  {lon: 24.0, lat: 37.5},
  {lon: 12.5, lat: 41.9, name: '大秦', en: 'ROMAN EMPIRE', note: '汉使未至'},
];
const NAMED = ROUTE.map((c, i) => (c.name ? i : -1)).filter((i) => i >= 0);
const TRADE_FROM = 10; // ROUTE index of 安息
const SEG = 12; // Catmull-Rom samples per waypoint span

// Timing (local frames). The HUD year counter runs 前 139 → 前 126 across 15 → 165, holds,
// then steps to 105 over 290 → 300, so the caravan travels exactly 15 → 165 and the paper lands on 300.
const KEYF = [15, 45, 75, 90, 120, 165]; // arrival at each named stop, on the 15-frame beat
const ZOOM_AT = 165;
const ZOOM_DUR = 45;
const ROUTE_OUT = 284; // the full-route overview stays readable until here
const PAPER_AT = 300;
const SETTLE = 48;
const PRESS_AT = PAPER_AT + 48;
const PRESS_DUR = 20;
const ZHI_AT = PAPER_AT + 60;

const project = (lon: number, lat: number): Pt => [(lon - 60) * 22, -(lat - 38) * 27];

// ---------- lacquer cloud scrolls (云气纹) ----------
// Filled brush ribbons: a centreline is offset by a width that swells quickly and tapers into the curl.
const spiralPts = (cx: number, cy: number, r0: number, r1: number, a0: number, a1: number, n: number): Pt[] =>
  Array.from({length: n}, (_, i) => {
    const t = i / (n - 1);
    const a = lerp(a0, a1, t);
    const r = lerp(r0, r1, t);
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  });
const ribbon = (pts: Pt[], w0: number) => {
  const n = pts.length;
  const L = [0];
  for (let i = 1; i < n; i++) L.push(L[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const tot = L[n - 1];
  const left: Pt[] = [];
  const right: Pt[] = [];
  for (let i = 0; i < n; i++) {
    const a = pts[Math.max(0, i - 1)];
    const b = pts[Math.min(n - 1, i + 1)];
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const d = Math.hypot(dx, dy) || 1;
    const s = L[i] / tot;
    const w = (w0 * Math.pow(Math.sin(Math.PI * Math.pow(s, 0.7)), 0.6) + 0.8) / 2;
    left.push([pts[i][0] - (dy / d) * w, pts[i][1] + (dx / d) * w]);
    right.push([pts[i][0] + (dy / d) * w, pts[i][1] - (dx / d) * w]);
  }
  return polyline([...left, ...right.reverse()], true);
};
const tailPts = (len: number, arch: number, n: number): Pt[] =>
  Array.from({length: n}, (_, i): Pt => {
    const u = i / (n - 1);
    return [u * len, -Math.sin(Math.PI * u) * arch];
  });
const MOTIFS = [
  // 单钩: a long tail rolling into one curl
  {
    d: ribbon([...tailPts(150, 16, 22), ...spiralPts(150, -32, 32, 7, Math.PI / 2, Math.PI / 2 - Math.PI * 2.4, 40).slice(1)], 10),
    dots: [[150, -32]] as Pt[],
    box: [0, -64, 182, 0],
  },
  // 双钩: two opposed curls joined by a tail
  {
    d: ribbon(
      [
        ...spiralPts(0, 24, 6, 24, -Math.PI / 2 - Math.PI * 1.8, -Math.PI / 2, 30),
        ...tailPts(170, 22, 22).slice(1),
        ...spiralPts(170, -28, 28, 6, Math.PI / 2, Math.PI / 2 - Math.PI * 2.2, 36).slice(1),
      ],
      9,
    ),
    dots: [
      [0, 24],
      [170, -28],
    ] as Pt[],
    box: [-24, -56, 198, 48],
  },
];
// Two deterministic bands, six scrolls each, spaced on a fixed rhythm.
const CLOUDS = [0, 1].flatMap((band) =>
  [0, 1, 2, 3, 4, 5].map((k) => ({
    band,
    k,
    slot: (k + [0.08, -0.05, 0.12, 0, -0.1, 0.06][k] + band * 0.5) / 6,
    m: (k + band) % 2,
    s: [0.78, 0.62, 0.9, 0.7, 0.84, 0.66][(k + 2 * band) % 6],
    f: (k + band) % 3 === 0 ? -1 : 1,
    dy: [-14, 8, -4, 12, -10, 4][(k * 5 + band * 3) % 6],
  })),
);

type Box = {x0: number; y0: number; x1: number; y1: number; w: number};
// 1 when the scroll is clear of every keep-out box, fading to 0 as it touches one.
const clearOf = (b: Omit<Box, 'w'>, boxes: Box[]) => {
  let o = 1;
  for (const r of boxes) {
    const gap = Math.max(r.x0 - b.x1, b.x0 - r.x1, r.y0 - b.y1, b.y0 - r.y1);
    o = Math.min(o, 1 - r.w * (1 - clamp01((gap - 6) / 50)));
  }
  return o;
};

export const S05Han: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();

  const world = useMemo(() => ROUTE.map((p) => project(p.lon, p.lat)), []);
  const curve = useMemo(() => {
    // densify with a Catmull-Rom pass so the route reads as a road, not a polyline
    const out: Pt[] = [];
    for (let i = 0; i < world.length - 1; i++) {
      const p0 = world[Math.max(0, i - 1)];
      const p1 = world[i];
      const p2 = world[i + 1];
      const p3 = world[Math.min(world.length - 1, i + 2)];
      for (let k = 0; k < SEG; k++) {
        const t = k / SEG;
        const t2 = t * t;
        const t3 = t2 * t;
        const f = (a: number, b: number, c: number, d: number) =>
          0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
        out.push([f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])]);
      }
    }
    out.push(world[world.length - 1]);
    return out;
  }, [world]);
  const total = useMemo(() => polyLength(curve), [curve]);
  // arc-length fraction of each named stop (the curve passes exactly through every waypoint)
  const cityT = useMemo(() => ROUTE.map((_, i) => (i === 0 ? 0 : polyLength(curve.slice(0, i * SEG + 1)) / total)), [curve, total]);
  const stops = useMemo(() => NAMED.map((i) => cityT[i]), [cityT]);
  // label side: away from where the route runs around the stop
  const sides = useMemo(
    () =>
      ROUTE.map((_, i) => {
        const near = curve.slice(Math.max(0, i * SEG - 6), i * SEG + 7);
        const avg = near.reduce((s, q) => s + q[1], 0) / near.length;
        return avg > world[i][1] ? 'above' : 'below';
      }),
    [curve, world],
  );
  const hanCurve = useMemo(() => curve.slice(0, TRADE_FROM * SEG + 1), [curve]);
  const tradeCurve = useMemo(() => curve.slice(TRADE_FROM * SEG), [curve]);
  const tA = cityT[TRADE_FROM];

  // ---------- camera ----------
  // time is spent per stop, not per arc length: the caravan eases into each stop on the beat
  const soft = (t: number) => lerp(t, E.inOutSine(t), 0.8);
  const travelAt = (f: number) => interpolate(f, KEYF, stops, {easing: soft, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const travel = travelAt(frame);
  const camHead = pointAt(curve, travelAt(frame - 7)).p; // the camera trails the caravan a little
  const speed = ((travelAt(frame + 1) - travelAt(frame - 1)) * total) / 2;
  const zoomOut = prog(frame, ZOOM_AT, ZOOM_DUR, E.inOutCubic);
  const drift = prog(frame, ZOOM_AT + ZOOM_DUR - 10, 110, E.inOutSine); // slow push-in while the overview holds
  const xs = curve.map((p) => p[0]);
  const ys = curve.map((p) => p[1]);
  const bx = [Math.min(...xs), Math.max(...xs)];
  const by = [Math.min(...ys), Math.max(...ys)];
  const fitS = Math.min((W - (vertical ? 140 : 380)) / (bx[1] - bx[0]), (H * 0.5) / (by[1] - by[0]));
  const followS = (vertical ? 1.05 : 1.35) * (1 - 0.18 * clamp01(speed / 30));
  const camS = lerp(followS, fitS, zoomOut) * (1 + 0.025 * drift);
  const center: Pt = [(bx[0] + bx[1]) / 2, (by[0] + by[1]) / 2];
  const focus: Pt = [lerp(camHead[0], center[0], zoomOut), lerp(camHead[1], center[1], zoomOut)];
  // follow: the caravan sits right of centre with lead room to the west; overview: under the text column
  const anchorA: Pt = vertical ? [W * 0.6, 1080] : [W * 0.58, H * 0.55];
  const anchorB: Pt = vertical ? [W / 2, 1090] : [W / 2, H * 0.7];
  const screen: Pt = [lerp(anchorA[0], anchorB[0], zoomOut), lerp(anchorA[1], anchorB[1], zoomOut)];
  const tx = (p: Pt): Pt => [screen[0] + (p[0] - focus[0]) * camS, screen[1] + (p[1] - focus[1]) * camS];

  const full = curve.map(tx);
  const drawnHan = partialPolyline(hanCurve, clamp01(travel / tA)).map(tx);
  const drawnTrade = travel > tA ? partialPolyline(tradeCurve, clamp01((travel - tA) / (1 - tA))).map(tx) : [];

  const routeOut = prog(frame, ROUTE_OUT, 18, E.inCubic);
  const paperIn = prog(frame, PAPER_AT, 18, E.outCubic);

  // ---------- text blocks ----------
  const textA = vertical
    ? {left: 70, top: 340, title: [60, 335, 370, 485], lines: [60, 480, 1030, 690]}
    : {left: 140, top: 140, title: [130, 135, 520, 318], lines: [130, 312, 820, 510]};
  const textB = vertical ? {left: 70, top: 1200, box: [60, 1190, 1030, 1440]} : {left: 150, top: 390, box: [140, 380, 830, 700]};

  // ---------- city labels ----------
  const nameSize = vertical ? 44 : 46;
  const EN = 22;
  const margin = vertical ? 50 : 100;
  const labels = ROUTE.map((c, i) => {
    if (!c.name) return null;
    const k = NAMED.indexOf(i);
    const popAt = k === 0 ? 6 : KEYF[k] - 3;
    const p = tx(world[i]);
    const h = nameSize * 1.2 + 2 + EN * 1.3 + (c.note ? EN * 1.4 : 0);
    const w = Math.max(Array.from(c.name).length * (nameSize + 6), (c.en ?? '').length * (EN * 0.6 + 2), c.note ? 4 * (EN + 2) : 0);
    const gap = 28; // ring radius 14 + 14 clear
    const top = sides[i] === 'below' ? p[1] + gap : p[1] - gap - h;
    const cx = lerp(p[0], Math.min(Math.max(p[0], margin + w / 2), W - margin - w / 2), zoomOut);
    const ring = prog(frame, popAt, 12, E.outBack);
    const o = prog(frame, popAt + 2, 14, E.outCubic);
    return {c, i, k, p, h, w, top, cx, ring, o};
  });

  // ---------- clouds ----------
  const keepOut: Box[] = [
    {x0: textA.title[0], y0: textA.title[1], x1: textA.title[2], y1: textA.title[3], w: 1 - routeOut},
    {x0: textA.lines[0], y0: textA.lines[1], x1: textA.lines[2], y1: textA.lines[3], w: 1 - routeOut},
    {x0: textB.box[0], y0: textB.box[1], x1: textB.box[2], y1: textB.box[3], w: paperIn},
    ...labels.flatMap((l) => (l ? [{x0: l.cx - l.w / 2, y0: l.top, x1: l.cx + l.w / 2, y1: l.top + l.h, w: l.o * (1 - routeOut)}] : [])),
  ];
  const bandY = vertical ? [400, 1450] : [205, 860];
  const bandL = W + 520;
  const wrap = (v: number) => ((((v + 260) % bandL) + bandL) % bandL) - 260;
  const cloudMask = vertical
    ? 'linear-gradient(to bottom, transparent 0px, transparent 320px, #000 390px, #000 1450px, transparent 1540px)'
    : 'linear-gradient(to bottom, transparent 0px, transparent 130px, #000 210px, #000 860px, transparent 950px)';
  const clouds = CLOUDS.map((c) => {
    const mo = MOTIFS[c.m];
    const px = wrap(c.slot * bandL - frame * (c.band ? 0.9 : 0.6) - focus[0] * (c.band ? 0.14 : 0.08));
    const py = bandY[c.band] + c.dy * c.s - ((mo.box[1] + mo.box[3]) / 2) * c.s + noise2D('cl', c.k + 6 * c.band, frame / 200) * 6;
    const xa = px + (c.f > 0 ? mo.box[0] : -mo.box[2]) * c.s;
    const xb = px + (c.f > 0 ? mo.box[2] : -mo.box[0]) * c.s;
    const o = clearOf({x0: xa, y0: py + mo.box[1] * c.s, x1: xb, y1: py + mo.box[3] * c.s}, keepOut);
    return {c, mo, px, py, o};
  });

  // ---------- paper (part B) ----------
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sheet = vertical ? {x: 90, y: 470, w: W - 180, h: 700} : {x: W * 0.44, y: H * 0.2, w: W * 0.44, h: H * 0.6};
  const fibres = useMemo(() => {
    const r = rng(105);
    return Array.from({length: 4200}, () => {
      const x = sheet.x + r() * sheet.w;
      const y = sheet.y + r() * sheet.h;
      return {x, y, a: r() * Math.PI, l: 6 + r() * 26, t: r(), w: 0.6 + r() * 1.2, sx: (r() - 0.5) * 900, sy: -300 - r() * 700};
    });
  }, [sheet.x, sheet.y, sheet.w, sheet.h]);
  const settle = prog(frame, PAPER_AT + 4, SETTLE, E.linear);
  const press = prog(frame, PRESS_AT, PRESS_DUR, E.inOutCubic);
  const clipTop = vertical ? 330 : 125; // fibres never cross the HUD header

  useLayoutEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx = cv.getContext('2d')!;
    ctx.clearRect(0, 0, W, H);
    if (frame < PAPER_AT) return;
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, clipTop, W, H - clipTop);
    ctx.clip();
    ctx.lineCap = 'round';
    // once pressed, the fibres darken into the sheet as its texture
    const cr = Math.round(lerp(236, 150, press));
    const cg = Math.round(lerp(224, 128, press));
    const cb = Math.round(lerp(196, 92, press));
    for (const f of fibres) {
      const t = clamp01((settle - f.t * 0.6) / 0.4);
      if (t <= 0) continue;
      const e = 1 - (1 - t) ** 3;
      const x = lerp(f.x + f.sx, f.x, e);
      const y = lerp(f.y + f.sy, f.y, e);
      const a = f.a + (1 - e) * 2.4;
      const alpha = lerp(0.35 + 0.4 * e, 0.32, press) * clamp01((y - clipTop) / 90);
      if (alpha <= 0) continue;
      ctx.strokeStyle = `rgba(${cr},${cg},${cb},${alpha.toFixed(3)})`;
      ctx.lineWidth = f.w;
      ctx.beginPath();
      ctx.moveTo(x - Math.cos(a) * f.l * 0.5, y - Math.sin(a) * f.l * 0.5);
      ctx.lineTo(x + Math.cos(a) * f.l * 0.5, y + Math.sin(a) * f.l * 0.5);
      ctx.stroke();
    }
    ctx.restore();
  }, [frame, fibres, settle, press, clipTop, W, H]);

  // the finished sheet breathes: a slow push plus a small swell, so the hold never freezes
  const breathIn = prog(frame, ZHI_AT, 30, E.inOutSine);
  const breath = 1 + 0.012 * prog(frame, PRESS_AT, 90, E.inOutSine) + 0.005 * breathIn * Math.sin(((frame - ZHI_AT) / 75) * Math.PI * 2);
  const sheetOrigin = `${sheet.x + sheet.w / 2}px ${sheet.y + sheet.h / 2}px`;
  const zhi = prog(frame, ZHI_AT, 16, E.outCubic);
  const dateSize = vertical ? 100 : 130;

  const holeRect = vertical ? {x: 50, y: 325, w: 990, h: 375} : {x: 120, y: 125, w: 720, h: 400};

  return (
    <Paper bg={P.bg} dark vignette={0.5}>
      {/* lacquer clouds: two bands, masked away from the HUD header and ruler, faded near text */}
      <svg
        width={W}
        height={H}
        style={{position: 'absolute', inset: 0, opacity: 0.75 * (1 - routeOut * 0.6), maskImage: cloudMask, WebkitMaskImage: cloudMask}}
      >
        {clouds.map(({c, mo, px, py, o}) =>
          o <= 0.01 ? null : (
            <g key={`${c.band}-${c.k}`} transform={`translate(${px.toFixed(1)},${py.toFixed(1)}) scale(${(c.s * c.f).toFixed(3)},${c.s})`} opacity={0.8 * o}>
              <path d={mo.d} fill={P.accent} />
              {mo.dots.map((d, j) => (
                <circle key={j} cx={d[0]} cy={d[1]} r={3.4} fill={GOLD} opacity={0.7} />
              ))}
            </g>
          ),
        )}
      </svg>

      {/* route */}
      <AbsoluteFill style={{opacity: 1 - routeOut}}>
        <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
          <defs>
            <filter id="han-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation={6} />
            </filter>
            <filter id="han-soft" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation={24} />
            </filter>
            {/* keeps map furniture and the not-yet-travelled route out from under the text column */}
            <mask id="han-text-hole" maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
              <rect x={0} y={0} width={W} height={H} fill="white" />
              <rect x={holeRect.x} y={holeRect.y} width={holeRect.w} height={holeRect.h} rx={40} fill="black" filter="url(#han-soft)" />
            </mask>
          </defs>
          <g mask="url(#han-text-hole)" style={{maskImage: cloudMask, WebkitMaskImage: cloudMask}}>
            {/* graticule: meridians every 10°, parallels every 5° — the only map furniture drawn */}
            <g stroke={hexA(GOLD, 0.1)} strokeWidth={1}>
              {Array.from({length: 13}, (_, k) => {
                const lon = 0 + k * 10;
                const a = tx(project(lon, 60));
                const b = tx(project(lon, 15));
                return <line key={`m${k}`} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} />;
              })}
              {Array.from({length: 9}, (_, k) => {
                const lat = 20 + k * 5;
                const a = tx(project(-5, lat));
                const b = tx(project(125, lat));
                return <line key={`p${k}`} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} />;
              })}
            </g>
            <path d={polyline(full)} fill="none" stroke={hexA(GOLD, 0.16)} strokeWidth={2} strokeDasharray="4 10" />
          </g>
          {/* Han envoys' road: solid gold */}
          <path d={polyline(drawnHan)} fill="none" stroke={GOLD} strokeWidth={9} opacity={0.45} filter="url(#han-glow)" />
          <path d={polyline(drawnHan)} fill="none" stroke="#f0d79c" strokeWidth={3.6} strokeLinecap="round" strokeLinejoin="round" />
          {/* beyond 安息: trade extension, dashed and dimmer, dashes flowing west */}
          {drawnTrade.length > 1 && (
            <path
              d={polyline(drawnTrade)}
              fill="none"
              stroke={hexA('#f0d79c', 0.6)}
              strokeWidth={3}
              strokeLinecap="round"
              strokeDasharray="10 12"
              strokeDashoffset={-frame * 0.6}
            />
          )}
          {/* caravan: beads trailing the head by a few frames, so they bunch up at each stop */}
          {[0, 3, 6, 9].map((lag, k) => {
            const tk = travelAt(frame - lag);
            const p = tx(pointAt(curve, tk).p);
            const moving = travel > 0 && travel < 1;
            const dim = tk > tA ? 0.65 : 1;
            return (
              <circle key={k} cx={p[0]} cy={p[1]} r={k === 0 ? 9 : 5} fill={k === 0 ? '#fff1cf' : GOLD} opacity={(moving ? 1 : k === 0 ? 0.9 : 0) * dim} />
            );
          })}
          {labels.map((l) =>
            !l ? null : (
              <g key={l.c.name} opacity={l.ring > 0 ? 1 : 0}>
                <circle
                  cx={l.p[0]}
                  cy={l.p[1]}
                  r={14 * l.ring * (1 + 0.1 * drift * Math.sin((frame + l.k * 11) / 8))}
                  fill="none"
                  stroke="#f0d79c"
                  strokeWidth={2}
                  opacity={l.i > TRADE_FROM ? 0.7 : 1}
                />
                <circle cx={l.p[0]} cy={l.p[1]} r={6 * l.ring} fill="#f0d79c" />
              </g>
            ),
          )}
        </svg>
        {labels.map((l) => {
          if (!l) return null;
          const below = sides[l.i] === 'below';
          return (
            <div
              key={l.c.name}
              style={{
                position: 'absolute',
                left: l.cx - 150,
                width: 300,
                top: l.top,
                textAlign: 'center',
                opacity: l.o,
                transform: `translateY(${(1 - l.o) * (below ? -8 : 8)}px)`,
              }}
            >
              <div style={{fontFamily: fam(C5.font), fontSize: nameSize, lineHeight: 1.2, color: CREAM, letterSpacing: 6, paddingLeft: 6}}>{l.c.name}</div>
              <div style={{fontFamily: MONO, fontSize: EN, lineHeight: 1.3, marginTop: 2, color: hexA(CREAM, 0.72), letterSpacing: 2, paddingLeft: 2}}>{l.c.en}</div>
              {l.c.note && <div style={{fontFamily: BODY, fontSize: EN, lineHeight: 1.4, color: hexA(CREAM, 0.72), letterSpacing: 2, paddingLeft: 2}}>{l.c.note}</div>}
            </div>
          );
        })}
        <div style={{position: 'absolute', left: textA.left, top: textA.top, width: vertical ? W - 140 : 700}}>
          <StaggerText text="凿空" at={8} step={8} font={C5.font} size={vertical ? 120 : 150} color={CREAM} mode="ink" letterSpacing={18} />
          <StaggerText
            text="然张骞凿空"
            at={30}
            step={4}
            font={C5.font}
            size={vertical ? 46 : 44}
            color={CREAM}
            mode="ink"
            letterSpacing={8}
            style={{marginTop: vertical ? 10 : 6}}
          />
          <Line at={46} color={hexA(CREAM, 0.72)} size={vertical ? 28 : 26}>
            ——《史记 · 大宛列传》
          </Line>
          <Line at={58} color={CREAM} size={vertical ? 34 : 32} style={{marginTop: 10}}>
            张骞出使西域，汉与西域自此通使往来。
          </Line>
          <Line at={72} color={hexA(CREAM, 0.72)} size={vertical ? 26 : 22}>
            路线与地名为示意 · 张骞亲至大宛、康居、大月氏、大夏
          </Line>
        </div>
      </AbsoluteFill>

      {/* paper */}
      {frame >= PAPER_AT - 2 && (
        <AbsoluteFill style={{opacity: paperIn}}>
          <AbsoluteFill style={{transform: `scale(${breath})`, transformOrigin: sheetOrigin}}>
            <AbsoluteFill style={{transform: `scale(${lerp(1.03, 1, press)})`, transformOrigin: sheetOrigin}}>
              <div
                style={{
                  position: 'absolute',
                  left: sheet.x - 6,
                  top: sheet.y - 6,
                  width: sheet.w + 12,
                  height: sheet.h + 12,
                  boxShadow: `0 30px 80px rgba(0,0,0,${0.5 * press})`,
                }}
              />
              <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
                <defs>
                  {/* deckled edge: the sheet is pulled from a mould, not cut */}
                  <filter id="han-deckle" x="-4%" y="-4%" width="108%" height="108%">
                    <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves={3} seed={3} result="n" />
                    <feDisplacementMap in="SourceGraphic" in2="n" scale={12} xChannelSelector="R" yChannelSelector="G" />
                  </filter>
                </defs>
                <rect
                  x={sheet.x - 10}
                  y={sheet.y - 10}
                  width={sheet.w + 20}
                  height={sheet.h + 20}
                  fill="#ece2c8"
                  opacity={press * 0.96}
                  filter="url(#han-deckle)"
                />
              </svg>
            </AbsoluteFill>
            <canvas ref={canvasRef} width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 1 - press * 0.3}} />
            <div
              style={{
                position: 'absolute',
                left: sheet.x,
                top: sheet.y,
                width: sheet.w,
                height: sheet.h,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: fam(C5.font),
                fontSize: vertical ? 360 : 340,
                color: '#2a1d16',
                opacity: zhi,
                filter: `blur(${(1 - zhi) * 6}px)`,
              }}
            >
              纸
            </div>
          </AbsoluteFill>
          <div style={{position: 'absolute', left: textB.left, top: textB.top, width: vertical ? W - 140 : 670}}>
            <StaggerText
              text="公元 105"
              at={PAPER_AT + 8}
              step={4}
              font="ZL-Serif"
              size={dateSize}
              color={GOLD}
              mode="rise"
              charStyle={(_, ch) => (/[0-9 ]/.test(ch) ? {} : {fontFamily: fam(C5.font), fontSize: dateSize * 0.66, marginRight: 4})}
            />
            <Line at={PAPER_AT + 22} color={CREAM} size={vertical ? 36 : 34} style={{marginTop: 10}}>
              蔡伦改进造纸术。
            </Line>
            <Line at={PAPER_AT + 34} color={hexA(CREAM, 0.8)} size={vertical ? 34 : 30}>
              {vertical ? (
                '此后数百年间，文字从竹简、缣帛渐渐落到纸上。'
              ) : (
                <>
                  此后数百年间，
                  <br />
                  文字从竹简、缣帛渐渐落到纸上。
                </>
              )}
            </Line>
          </div>
        </AbsoluteFill>
      )}
    </Paper>
  );
};
