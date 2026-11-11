import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS} from '../timeline';
import {E, clamp01, hexA, lerp, prog, rng} from '../lib/anim';
import {MONO, SERIF, fam, useFontsReady} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const C7 = CHAPTERS[7];
const P = C7.palette;
const N_POEMS = 48900; // 《全唐诗》编者自述“得诗四万八千九百余首”
const AMBER = '#D99A3A';
const GREEN = '#6E9A4E';
const CREAM = '#F1E4C6';
const NIGHT = '#1E160E'; // same as the chapter's hudAlt plate

// Local-frame beats, in step with this chapter's axisKeys in timeline.ts:
// 581 holds to 70 · 605 lands at 86 (exam line) · 605→618 over 130–170 · particles from 200 (618→907).
const T_EXAM = 84;
const T_TANG = 150; // underline "618 年唐兴" while the HUD counter climbs to 618
const T_TEXT_OUT = 174;
const T_DARK = 178; // night falls; the HUD switches ink at 192
const P_AT = 200;
const COUNT_DUR = 40; // 0 → 48,900: one dot leaves the city for every poem counted
const RISE = 16;
const ARRIVE_AT = P_AT + 24;
const ARRIVE_DUR = 56;
const ARRIVE_LAG = 18;
const CITY_OUT = P_AT + 4;
const CITY_OUT_DUR = 30;
const CITY_DROP = 80;
const SPREAD_AT = P_AT + 214;

const io3 = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (2 - 2 * t) ** 3 / 2);
const invIo3 = (y: number) => (y < 0.5 ? Math.cbrt(y / 4) : 1 - Math.cbrt(2 * (1 - y)) / 2);
/** Poems counted by local frame f. Dot i is on screen iff i < countAt(f): one dot per poem. */
const countAt = (f: number) => Math.floor(N_POEMS * io3(clamp01((f - P_AT) / COUNT_DUR)));
const cityOutAt = (f: number) => prog(f, CITY_OUT, CITY_OUT_DUR, E.inOutCubic);
const thetaAt = (f: number) => lerp(-0.22, 0.12, prog(f, 0, 230, E.inOutSine));

type Geo = {S: number; ocx: number; ocy: number};
const geoFor = (W: number, H: number, vertical: boolean): Geo =>
  vertical ? {S: 36, ocx: W / 2 + 154, ocy: H * 0.33} : {S: 48, ocx: W * 0.68, ocy: H * 0.31};
const isoAt = (g: Geo, theta: number, x: number, y: number, z: number): [number, number] => {
  const cy = y - 5;
  const c = Math.cos(theta);
  const s = Math.sin(theta);
  const rx = x * c - cy * s;
  const ry = x * s + cy * c + 5;
  return [g.ocx + (rx - ry) * 0.866 * g.S, g.ocy + (rx + ry) * 0.5 * g.S - z * g.S];
};

type Block = {gx: number; gy: number; w: number; d: number; h: number; kind: 'ward' | 'palace' | 'market' | 'gate'; delay: number};

/** Abstract Chang'an plan: a symmetric grid of walled wards around the Zhuque avenue,
 * palace city at the north centre, East and West markets. Not a survey-accurate map. */
const cityPlan = (): Block[] => {
  const r = rng(618);
  const out: Block[] = [];
  const cols = [-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6];
  for (let row = 0; row < 10; row++) {
    for (const c of cols) {
      const gx = c * 1.2 + (c > 0 ? 0.4 : -0.4);
      const gy = row * 1.0;
      if (row < 3 && Math.abs(c) <= 2) continue; // palace + imperial city
      if ((row === 4 || row === 5) && (c === -4 || c === 4)) {
        if (row === 4) out.push({gx: gx - 0.6, gy, w: 2.2, d: 1.8, h: 0.5, kind: 'market', delay: 0});
        continue;
      }
      if ((row === 4 || row === 5) && (c === -3 || c === 3)) continue;
      out.push({gx, gy, w: 0.98, d: 0.78, h: 0.22 + r() * 0.25, kind: 'ward', delay: 0});
    }
  }
  out.push({gx: -2.4, gy: 0, w: 4.8, d: 1.3, h: 1.1, kind: 'palace', delay: 0});
  out.push({gx: -2.4, gy: 1.5, w: 4.8, d: 1.3, h: 0.7, kind: 'palace', delay: 0});
  out.push({gx: -0.35, gy: 9.9, w: 0.7, d: 0.35, h: 0.9, kind: 'gate', delay: 0});
  out.forEach((b) => (b.delay = Math.hypot(b.gx, (b.gy - 9) * 1.1) * 3.2));
  return out;
};
const PLAN = cityPlan();

// Per-dot data: start x/y (a random point on a ward's roof at P_AT, lowered by the city's sink at
// the dot's own departure), departure frame, rise height, phase, arrival lag, colour.
const STRIDE = 7;
const buildDots = (g: Geo, vertical: boolean): Float32Array => {
  const th = thetaAt(P_AT);
  // 16:9: wards that sit under the left text column do not emit
  const wards = PLAN.filter((b) => b.kind === 'ward' && (vertical || isoAt(g, th, b.gx + b.w / 2, b.gy + b.d / 2, b.h)[0] > 770));
  const r = rng(48900);
  const d = new Float32Array(N_POEMS * STRIDE);
  for (let i = 0; i < N_POEMS; i++) {
    const b = wards[Math.floor(r() * wards.length)];
    const [x, y] = isoAt(g, th, b.gx + (0.1 + r() * 0.8) * b.w, b.gy + (0.1 + r() * 0.8) * b.d, b.h);
    const te = P_AT + COUNT_DUR * invIo3((i + 1) / N_POEMS);
    const o = i * STRIDE;
    d[o] = x;
    d[o + 1] = y + CITY_DROP * cityOutAt(te);
    d[o + 2] = te;
    d[o + 3] = (vertical ? 0.8 : 1) * (40 + r() * 80);
    d[o + 4] = r() * Math.PI * 2;
    d[o + 5] = r();
    d[o + 6] = r();
  }
  return d;
};

// Sampled only once the era faces are loaded (useFontsReady), and cached only then.
let glyphCache: Float32Array | null = null;
const sampleGlyph = (ch: string, font: string): Float32Array => {
  if (glyphCache) return glyphCache;
  const S = 600;
  const cv = document.createElement('canvas');
  cv.width = S;
  cv.height = S;
  const ctx = cv.getContext('2d')!;
  ctx.fillStyle = '#000';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = `${S * 0.86}px '${font}'`;
  ctx.fillText(ch, S / 2, S * 0.53);
  const data = ctx.getImageData(0, 0, S, S).data;
  const hits: number[] = [];
  for (let y = 0; y < S; y += 2) for (let x = 0; x < S; x += 2) if (data[(y * S + x) * 4 + 3] > 120) hits.push(x / S, y / S);
  const r = rng(907);
  const out = new Float32Array(N_POEMS * 2);
  const n = hits.length / 2;
  for (let i = 0; i < N_POEMS; i++) {
    const k = Math.floor(r() * n);
    out[i * 2] = hits[k * 2] + (r() - 0.5) * 0.004;
    out[i * 2 + 1] = hits[k * 2 + 1] + (r() - 0.5) * 0.004;
  }
  if (n > 1000 && document.fonts.check(`100px '${font}'`)) glyphCache = out;
  return out;
};

const GROUPS: [string, number, number][] = [
  [AMBER, 0, 0.5],
  [GREEN, 0.5, 0.78],
  [CREAM, 0.78, 1],
];

export const S07Tang: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const fontsOk = useFontsReady();
  const geo = useMemo(() => geoFor(W, H, vertical), [W, H, vertical]);

  // ---------- part A: Chang'an ----------
  const textOut = prog(frame, T_TEXT_OUT, 14, E.inCubic);
  const dark = prog(frame, T_DARK, 24, E.inOutCubic);
  const cityOut = cityOutAt(frame);
  const theta = thetaAt(frame);
  const iso = (x: number, y: number, z: number) => isoAt(geo, theta, x, y, z);
  const prisms = PLAN.map((b) => {
    const rise = prog(frame, 6 + b.delay, 22, E.outBack);
    const h = b.h * rise;
    const c = [
      [b.gx, b.gy],
      [b.gx + b.w, b.gy],
      [b.gx + b.w, b.gy + b.d],
      [b.gx, b.gy + b.d],
    ] as [number, number][];
    const depth = c.reduce((s, [x, y]) => s + iso(x, y, 0)[1], 0);
    return {b, h, c, depth, rise};
  }).sort((a, z) => a.depth - z.depth);
  const pts = (arr: [number, number][]) => arr.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const colour = (k: Block['kind']) =>
    k === 'palace' ? ['#B6452C', '#8E2F1D', '#E3B04B'] : k === 'market' ? ['#7C9A55', '#5B7A3C', '#B8CC8A'] : k === 'gate' ? ['#B6452C', '#8E2F1D', '#E3B04B'] : ['#D9C49A', '#B99C66', '#F4E7C8'];

  const body = vertical ? 34 : 32;
  const examIn = prog(frame, T_EXAM, 8, E.outCubic);
  const tangLine = prog(frame, T_TANG, 18, E.outCubic);

  // ---------- part B: 48,900 poems ----------
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dots = useMemo(() => buildDots(geo, vertical), [geo, vertical]);
  const box = vertical ? {x: W / 2 - 380, y: 340, s: 760} : {x: W * 0.6 - 380, y: H * 0.5 - 400, s: 760};
  const counted = countAt(frame);

  useLayoutEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx = cv.getContext('2d')!;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.clearRect(0, 0, W, H);
    if (counted === 0 || !fontsOk) return;
    const tgt = sampleGlyph('诗', 'ZL-KaiBlack');
    const f = frame - P_AT;
    const spread = prog(frame, SPREAD_AT, 40, E.inCubic);
    const topY = vertical ? 350 : 132; // keep rising dots out of the HUD header
    const breathe = Math.sin(f * 0.031) * 3;
    ctx.globalAlpha = 1 - 0.6 * spread;
    for (const [col, lo, hi] of GROUPS) {
      ctx.fillStyle = col;
      for (let i = 0; i < counted; i++) {
        const o = i * STRIDE;
        const c = dots[o + 6];
        if (c < lo || c >= hi) continue;
        const sx = dots[o];
        const sy = dots[o + 1];
        const ph = dots[o + 4];
        const dl = dots[o + 5];
        const age = Math.max(0, frame - dots[o + 2]);
        // 1) lift off the roof  2) ease into the flow field  3) settle into the glyph
        const lift = 1 - (1 - Math.min(1, age / RISE)) ** 3;
        const fl = clamp01((age - RISE * 0.5) / 26);
        let x = sx + Math.sin(ph + age * 0.21) * 3 * lift + fl * (Math.sin(ph + f * 0.045 + sy * 0.004) * 46 + Math.sin(f * 0.02 + sx * 0.003) * 30);
        let y = sy - dots[o + 3] * lift + fl * (Math.cos(ph * 1.3 + f * 0.04 + sx * 0.004) * 40 - Math.max(0, age - RISE) * 0.5 * (0.5 + dl));
        const a = clamp01((frame - ARRIVE_AT - dl * ARRIVE_LAG) / ARRIVE_DUR);
        if (a > 0) {
          const e = io3(a);
          const tx = box.x + tgt[i * 2] * box.s + Math.sin(f * 0.07 + ph) * 1.2;
          const ty = box.y + tgt[i * 2 + 1] * box.s + Math.cos(f * 0.06 + ph) * 1.2 + breathe;
          x += (tx - x) * e;
          y += (ty - y) * e;
        }
        if (spread > 0) {
          x += Math.cos(ph) * spread * 260 * (0.3 + dl);
          y += Math.sin(ph) * spread * 260 * (0.3 + dl) - spread * 80;
        }
        if (y < topY) y = topY - (topY - y) * (0.3 + 0.7 * spread);
        ctx.fillRect(x, y, 2.1, 2.1);
      }
    }
    // keep the copy readable: dots crossing the text column are mostly erased
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'destination-out';
    if (vertical) {
      const g = ctx.createLinearGradient(0, 1086, 0, 1126);
      g.addColorStop(0, 'rgba(0,0,0,0)');
      g.addColorStop(1, 'rgba(0,0,0,0.8)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 1086, W, H - 1086);
    } else {
      const g = ctx.createLinearGradient(0, 0, 810, 0);
      g.addColorStop(0, 'rgba(0,0,0,0.8)');
      g.addColorStop(740 / 810, 'rgba(0,0,0,0.8)');
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, 810, H);
    }
    ctx.globalCompositeOperation = 'source-over';
  }, [frame, counted, fontsOk, dots, W, H, vertical, box.x, box.y, box.s]);

  return (
    <Paper bg={P.bg}>
      <AbsoluteFill style={{background: NIGHT, opacity: dark}} />
      {/* city */}
      {cityOut < 1 && (
        <AbsoluteFill style={{opacity: 1 - cityOut, transform: `translateY(${cityOut * CITY_DROP}px)`, filter: dark > 0 ? `brightness(${(1 - 0.42 * dark).toFixed(3)})` : undefined}}>
          <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
            {/* city wall footprint + Zhuque avenue */}
            <polygon points={pts([iso(-8.2, -0.5, 0), iso(8.2, -0.5, 0), iso(8.2, 10.4, 0), iso(-8.2, 10.4, 0)])} fill={hexA('#c9b58a', 0.35)} stroke="#a58a55" strokeWidth={2} />
            <polyline points={pts([iso(0, 3, 0.01), iso(0, 10.4, 0.01)])} stroke={P.accent} strokeWidth={vertical ? 6 : 7} opacity={prog(frame, 4, 24, E.outCubic)} />
            {prisms.map(({b, h, c, rise}, k) => {
              if (rise <= 0) return null;
              const [top, side, light] = colour(b.kind);
              const t = c.map(([x, y]) => iso(x, y, h));
              const g = c.map(([x, y]) => iso(x, y, 0));
              return (
                <g key={k}>
                  <polygon points={pts([g[3], g[2], t[2], t[3]])} fill={side} />
                  <polygon points={pts([g[1], g[2], t[2], t[1]])} fill={hexA(side, 0.82)} />
                  <polygon points={pts(t)} fill={b.kind === 'ward' ? top : light} stroke={hexA('#6b5634', 0.35)} strokeWidth={1} />
                </g>
              );
            })}
          </svg>
          {[
            ['宫城', 0, 0.7, 1.6],
            ['东市', 4.4, 5.0, 0.6],
            ['西市', -4.4, 5.0, 0.6],
            ['朱雀大街', 0, 7.6, 0.2],
          ].map(([t, x, y, z]) => {
            const p = iso(x as number, y as number, z as number);
            return (
              <div
                key={t as string}
                style={{
                  position: 'absolute',
                  left: p[0] - 90,
                  top: p[1] - (vertical ? 58 : 56),
                  width: 180,
                  textAlign: 'center',
                  fontFamily: fam('ZL-Kai'),
                  fontSize: vertical ? 30 : 28,
                  color: '#3b2a17',
                  textShadow: '0 0 10px #f6ead0, 0 0 4px #f6ead0',
                  opacity: prog(frame, 60, 20, E.outCubic) * (1 - textOut),
                }}
              >
                {t as string}
              </div>
            );
          })}
        </AbsoluteFill>
      )}

      {/* text column: soft paper ground so the city never sits under the copy */}
      {textOut < 1 && (
        <AbsoluteFill style={{opacity: 1 - textOut}}>
          {!vertical && (
            <div
              style={{
                position: 'absolute',
                left: -40,
                top: 130,
                width: 940,
                height: 720,
                background: `radial-gradient(ellipse 50% 50% at 50% 50%, ${hexA(P.bg, 0.94)} 0%, ${hexA(P.bg, 0.82)} 48%, ${hexA(P.bg, 0)} 100%)`,
                opacity: prog(frame, 4, 24, E.outCubic),
              }}
            />
          )}
          <div style={{position: 'absolute', left: vertical ? 70 : 150, top: vertical ? 1120 : 250, width: vertical ? W - 140 : 680}}>
            <StaggerText text="长安" at={10} step={8} font={C7.font} size={vertical ? 120 : 160} color={P.ink} mode="rise" letterSpacing={16} />
            <Line at={34} color={P.ink} size={body} style={{marginTop: vertical ? 6 : 10}}>
              581 年隋立，
              <span style={{position: 'relative', display: 'inline-block'}}>
                618 年唐兴。
                <span
                  style={{
                    position: 'absolute',
                    left: 0,
                    right: '0.9em',
                    bottom: 1,
                    height: 4,
                    background: P.accent,
                    transform: `scaleX(${tangLine})`,
                    transformOrigin: 'left center',
                  }}
                />
              </span>
            </Line>
            <Line at={44} color={P.ink} size={body}>
              坊市如棋盘，朱雀大街贯穿南北。
            </Line>
            <div
              style={{
                marginTop: vertical ? 22 : 30,
                display: 'flex',
                alignItems: 'baseline',
                gap: 12,
                lineHeight: 1.15,
                opacity: examIn,
                transform: `translateY(${(1 - examIn) * 16}px)`,
              }}
            >
              <span style={{fontFamily: MONO, fontSize: vertical ? 30 : 26, color: P.hud}}>约</span>
              <span style={{fontFamily: SERIF, fontSize: vertical ? 66 : 62, color: P.accent, letterSpacing: 1, fontVariantNumeric: 'tabular-nums'}}>605 — 1905</span>
            </div>
            <Line at={T_EXAM + 6} color={hexA(P.ink, 0.88)} size={body}>
              隋设进士科，科举由此延续约一千三百年。
            </Line>
          </div>
        </AbsoluteFill>
      )}

      {/* night ground behind the poem copy (16:9): hides what is left of the city under the counter */}
      {!vertical && frame >= P_AT - 4 && (
        <div
          style={{
            position: 'absolute',
            left: -60,
            top: 170,
            width: 900,
            height: 700,
            background: `radial-gradient(ellipse 50% 50% at 50% 50%, ${hexA(NIGHT, 0.95)} 0%, ${hexA(NIGHT, 0.8)} 45%, ${hexA(NIGHT, 0)} 100%)`,
            opacity: prog(frame, P_AT - 4, 10, E.outCubic),
          }}
        />
      )}

      {/* poems */}
      <canvas ref={canvasRef} width={W} height={H} style={{position: 'absolute', inset: 0}} />
      {frame >= P_AT && (
        <AbsoluteFill>
          <div style={{position: 'absolute', left: vertical ? 70 : 150, top: vertical ? 1120 : 290, width: vertical ? W - 140 : 600}}>
            <div style={{fontFamily: SERIF, fontSize: vertical ? 110 : 136, lineHeight: 1.12, color: AMBER, fontVariantNumeric: 'tabular-nums', opacity: prog(frame, P_AT, 8, E.outCubic)}}>
              {counted.toLocaleString('en-US')}
            </div>
            <Line at={P_AT + 22} color={CREAM} size={body}>
              《全唐诗》收诗四万八千九百余首，
            </Line>
            <Line at={P_AT + 32} color={hexA(CREAM, 0.86)} size={body}>
              每一个光点，代表其中一首。
            </Line>
            <div style={{marginTop: vertical ? 36 : 64}}>
              <StaggerText text="欲穷千里目，更上一层楼" at={P_AT + 112} step={4} font="ZL-Kai" size={vertical ? 50 : 52} color={CREAM} mode="ink" letterSpacing={6} />
              <Line at={P_AT + 152} color={hexA(CREAM, 0.78)} size={vertical ? 26 : 24} style={{marginTop: 10}}>
                ——王之涣《登鹳雀楼》
              </Line>
            </div>
          </div>
        </AbsoluteFill>
      )}
    </Paper>
  );
};
