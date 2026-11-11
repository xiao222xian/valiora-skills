import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {noise2D} from '@remotion/noise';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS, CUES} from '../timeline';
import {E, Pt, clamp01, hexA, lerp, partialPolyline, polyLength, polyline, prog} from '../lib/anim';
import {BODY, MONO, fam} from '../lib/fonts';
import {SEAL} from '../lib/glyphs';
import {useLayout} from '../lib/layout';
import {STATES, statesRect} from './S03Warring';

const C4 = CHAPTERS[4];
const P = C4.palette;
const SLAM = CUES.qinSlam - C4.start; // local frame of the 48.0 s downbeat (60)
const CREAM = '#efe6d2';
const GREY = '#5a534b';
const EARTH = '#d8cfbc'; // rammed earth (夯土)
const LAYER = '#3a2f24'; // tamping-layer line

// Order in which Qin annexed the six states (Shiji): 韩 230, 赵 228, 魏 225, 楚 223, 燕 222, 齐 221 BCE.
const CONQUEST: [string, number][] = [
  ['韩', 230], ['赵', 228], ['魏', 225], ['楚', 223], ['燕', 222], ['齐', 221],
];
// The ticker row k (and the HUD year step in timeline.ts) lands at local 20 + k*7.5.
const tickerAt = (k: number) => 20 + k * 7.5;
// Each annexation: approach (decelerate onto the rim) -> neck (stuck to the rim) -> absorb (pulled to the centre).
// Absorption k completes 2.5 frames after its ticker row; the last one (齐) lands on the SLAM.
const ABSORB = 7;
const NECK = 7;
const APPROACH = 14;
const absorbedAt = (k: number) => SLAM - (CONQUEST.length - 1 - k) * 7.5;

const mixHex = (a: string, b: string, t: number) => {
  const pa = parseInt(a.slice(1), 16);
  const pb = parseInt(b.slice(1), 16);
  const m = (s: number) => Math.round(lerp((pa >> s) & 255, (pb >> s) & 255, clamp01(t)));
  return `rgb(${m(16)},${m(8)},${m(0)})`;
};

// 小篆「文」 split into its four strokes, written in order.
const SEAL_WEN = SEAL['文'].split('M').filter(Boolean).map((s) => `M${s.trim()}`);

export const S04Qin: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const sr = statesRect(W, H, vertical);
  const T: Pt = [W / 2, H * 0.47];

  // ---------- merge ----------
  const qin = STATES[0];
  const qStart: Pt = [sr.x + qin.x * sr.w, sr.y + qin.y * sr.h];
  const qMove = prog(frame, 0, 14, E.inOutCubic);
  const qx = lerp(qStart[0], T[0], qMove);
  const qy = lerp(qStart[1], T[1], qMove);

  const phase = (k: number) => {
    const done = absorbedAt(k);
    const absorbAt = done - ABSORB;
    const neckAt = absorbAt - NECK;
    const appAt = Math.max(0, neckAt - APPROACH);
    return {
      app: prog(frame, appAt, neckAt - appAt, E.outCubic),
      neck: prog(frame, neckAt, NECK, E.linear),
      abs: prog(frame, absorbAt, ABSORB, E.inCubic),
    };
  };

  const geo = STATES.slice(1).map((st) => {
    const k = CONQUEST.findIndex(([n]) => n === st.n);
    return {st, k, r: st.r * sr.s, o: [sr.x + st.x * sr.w, sr.y + st.y * sr.h] as Pt, ...phase(k)};
  });
  // the disc swells by each state's area as it is drawn in
  const area = geo.reduce((a, g) => a + g.r ** 2 * g.abs, (qin.r * sr.s) ** 2);
  const R = Math.sqrt(area);
  const slam = prog(frame, SLAM, 12, E.outBack);
  const qR = R * (frame >= SLAM ? lerp(1.35, 1.2, slam) : 1);

  const blobs = geo.map((g) => {
    const {st, r, o, app, neck, abs} = g;
    // waiting: drift in place, and get shouldered aside if the growing disc comes too close
    const idle = 1 - app;
    const rest: Pt = [o[0] + idle * 5 * noise2D(`bx${st.n}`, frame / 36, 0), o[1] + idle * 5 * noise2D(`by${st.n}`, frame / 36, 0)];
    const vx = rest[0] - qx;
    const vy = rest[1] - qy;
    const vd = Math.hypot(vx, vy) || 1;
    const keepOff = R + r + 36;
    const restP: Pt = vd < keepOff ? [qx + (vx / vd) * keepOff, qy + (vy / vd) * keepOff] : rest;
    // approach target: on the rim, along the line from the centre to the state's home
    const d0 = Math.hypot(o[0] - T[0], o[1] - T[1]) || 1;
    const dir: Pt = [(o[0] - T[0]) / d0, (o[1] - T[1]) / d0];
    const cd = R + r * 0.55;
    const contact: Pt = [qx + dir[0] * cd, qy + dir[1] * cd];
    const x = lerp(lerp(restP[0], contact[0], app), qx, abs);
    const y = lerp(lerp(restP[1], contact[1], app), qy, abs);
    // stuck to the rim: the ball stretches toward the disc, then is drawn in and shrinks
    const pull = Math.sin(Math.PI * neck) * (1 - abs);
    return {
      st,
      x,
      y,
      r: r * (1 - 0.72 * abs),
      stretch: 1 + 0.14 * pull + 0.25 * abs,
      ang: (Math.atan2(dir[1], dir[0]) * 180) / Math.PI,
      tint: clamp01(neck * 0.3 + abs),
      label: clamp01(1 - abs * 1.8) * (1 - 0.2 * neck),
      gone: abs >= 1,
    };
  });
  const discOut = prog(frame, 96, 22, E.inOutCubic);

  // ---------- three standards ----------
  const stdAt = 108;
  const stdOut = prog(frame, 222, 18, E.inCubic);
  const cols = vertical ? [T[0], T[0], T[0]] : [W * 0.25, W * 0.5, W * 0.75];
  const rows = vertical ? [H * 0.295, H * 0.495, H * 0.695] : [H * 0.47, H * 0.47, H * 0.47];
  const ringR = vertical ? 140 : 225;
  const gs = vertical ? 0.75 : 1; // gauge / ruler scale
  const conv = prog(frame, stdAt + 34, 34, E.inOutCubic);
  const fonts = ['ZL-Li', 'ZL-Xingkai', 'ZL-SongBlack', 'ZL-Weibei', 'ZL-KaiBlack', 'ZL-Baoli', 'ZL-HeiHeavy'];
  const stdZoom = 1 + (vertical ? 0.008 : 0.02) * prog(frame, stdAt, 132, E.linear);
  const sealAt = stdAt + 54;
  const sealSize = vertical ? 150 : 210;
  const labelDy = vertical ? 150 : 250;
  const labelSize = vertical ? 44 : 58;

  // ---------- great wall ----------
  const wallAt = 232;
  const base = vertical ? H * 0.6 : H * 0.66;
  const ridge = useMemo(() => {
    const pts: Pt[] = [];
    for (let x = -40; x <= W + 240; x += 8) {
      const y = base - 150 * (noise2D('ridge', x / 520, 0.3) * 0.6 + noise2D('ridge2', x / 190, 1.1) * 0.3 + 0.3);
      pts.push([x, y]);
    }
    return pts;
  }, [W, base]);
  // watchtowers stand upright, only on local summits of the ridge
  const towers = useMemo(() => {
    const total = polyLength(ridge);
    const cum = [0];
    for (let i = 1; i < ridge.length; i++) cum.push(cum[i - 1] + Math.hypot(ridge[i][0] - ridge[i - 1][0], ridge[i][1] - ridge[i - 1][1]));
    const out: {x: number; y: number; f: number}[] = [];
    const win = 9;
    for (let i = win; i < ridge.length - win; i++) {
      const y = ridge[i][1];
      const around = ridge.slice(i - win, i + win + 1);
      if (around.some((p, j) => j !== win && p[1] < y)) continue;
      if (Math.max(...around.map((p) => p[1])) - y < 10) continue;
      if (out.length && ridge[i][0] - out[out.length - 1].x < 150) continue;
      if (ridge[i][0] < 60) continue;
      out.push({x: ridge[i][0], y, f: cum[i] / total});
    }
    return out;
  }, [ridge]);
  const wallDraw = prog(frame, wallAt + 6, 96, E.inOutSine);
  const wallPts = partialPolyline(ridge, wallDraw);
  const tip = wallPts[wallPts.length - 1];
  const pan = -1.1 * Math.max(0, frame - (wallAt - 6));
  const mountains = (layer: number) => {
    const pts: Pt[] = [[-40, H]];
    const mb = base - 30 + layer * 80;
    const drift = frame * (0.4 + layer * 0.5);
    for (let x = -40; x <= W + 40; x += 16) {
      pts.push([x, mb - 160 * (noise2D(`m${layer}`, (x + drift) / (420 - layer * 90), layer) * 0.5 + 0.55) + layer * 30]);
    }
    pts.push([W + 40, H]);
    return polyline(pts, true);
  };
  const wallIn = prog(frame, wallAt - 6, 20, E.outCubic);
  const tw = vertical ? 0.85 : 1;

  return (
    <Paper bg={P.bg} dark vignette={0.5}>
      {/* merge */}
      {discOut < 1 && (
        <AbsoluteFill style={{opacity: 1 - discOut, transform: `scale(${1 - 0.15 * discOut})`}}>
          <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
            {/* one goo pass per state, shared only with the disc: a state can fuse with Qin but never with its neighbours */}
            {[null, ...blobs].map((b, i) => {
              if (b && b.gone) return null;
              const m = 64;
              const bx0 = Math.min(qx - qR, b ? b.x - b.r * b.stretch : Infinity) - m;
              const by0 = Math.min(qy - qR, b ? b.y - b.r * b.stretch : Infinity) - m;
              const bx1 = Math.max(qx + qR, b ? b.x + b.r * b.stretch : -Infinity) + m;
              const by1 = Math.max(qy + qR, b ? b.y + b.r * b.stretch : -Infinity) + m;
              const id = `goo${i}`;
              return (
                <g key={id}>
                  <defs>
                    <filter id={id} filterUnits="userSpaceOnUse" x={bx0} y={by0} width={bx1 - bx0} height={by1 - by0}>
                      <feGaussianBlur in="SourceGraphic" stdDeviation={18} result="b" />
                      <feColorMatrix in="b" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 28 -12" />
                    </filter>
                  </defs>
                  <g filter={`url(#${id})`}>
                    <circle cx={qx} cy={qy} r={qR} fill={P.accent} />
                    {b && (
                      <ellipse
                        cx={b.x}
                        cy={b.y}
                        rx={b.r * b.stretch}
                        ry={b.r / Math.sqrt(b.stretch)}
                        transform={`rotate(${b.ang.toFixed(2)} ${b.x.toFixed(2)} ${b.y.toFixed(2)})`}
                        fill={mixHex(GREY, P.accent, b.tint)}
                      />
                    )}
                  </g>
                </g>
              );
            })}
          </svg>
          {blobs.map(({st, x, y, r, label}) =>
            label > 0 ? (
              <div
                key={st.n}
                style={{
                  position: 'absolute',
                  left: x - r,
                  top: y - r,
                  width: r * 2,
                  height: r * 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: fam(st.font),
                  fontSize: r,
                  lineHeight: 1,
                  color: CREAM,
                  opacity: label,
                }}
              >
                {st.n}
              </div>
            ) : null,
          )}
          <div
            style={{
              position: 'absolute',
              left: qx - qR,
              top: qy - qR,
              width: qR * 2,
              height: qR * 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontFamily: fam(C4.font),
              fontSize: qR * (frame >= SLAM ? 1.15 : 0.9),
              color: frame >= SLAM ? P.bg : CREAM,
              lineHeight: 1,
            }}
          >
            秦
          </div>
          {/* conquest ticker: a column on the left (16:9), a 3 x 2 grid above the disc (9:16) */}
          {CONQUEST.map(([n, y], k) => {
            const t = prog(frame, tickerAt(k), 6, E.outCubic);
            const pos = vertical ? {left: 104 + (k % 3) * 312, top: 372 + Math.floor(k / 3) * 76} : {left: 150, top: 290 + k * 58};
            return (
              <div
                key={n}
                style={{
                  position: 'absolute',
                  ...pos,
                  opacity: t,
                  transform: `translateX(${(1 - t) * -16}px)`,
                  display: 'flex',
                  gap: 16,
                  alignItems: 'baseline',
                  whiteSpace: 'nowrap',
                  lineHeight: 1.2,
                }}
              >
                <span style={{fontFamily: MONO, fontSize: vertical ? 28 : 24, color: P.hud}}>前 {y}</span>
                <span style={{fontFamily: fam(C4.font), fontSize: vertical ? 42 : 36, color: CREAM}}>灭{n}</span>
              </div>
            );
          })}
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: T[1] + qR + 36,
              textAlign: 'center',
              opacity: prog(frame, SLAM + 2, 10, E.outCubic),
              transform: `translateY(${(1 - prog(frame, SLAM + 2, 14, E.outBack)) * 20}px)`,
            }}
          >
            <span style={{fontFamily: fam(C4.font), fontSize: vertical ? 58 : 64, color: CREAM, letterSpacing: vertical ? 12 : 16}}>前 221　六国归一</span>
          </div>
        </AbsoluteFill>
      )}

      {/* three standards */}
      {frame >= stdAt && stdOut < 1 && (
        <AbsoluteFill style={{opacity: prog(frame, stdAt, 14, E.outCubic) * (1 - stdOut), transform: `scale(${stdZoom})`}}>
          <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
            {[0, 1, 2].map((k) => (
              <circle key={k} cx={cols[k]} cy={rows[k]} r={ringR} fill="none" stroke={hexA(CREAM, 0.22)} strokeWidth={1.5} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - prog(frame, stdAt + k * 5, 30, E.inOutCubic)} transform={`rotate(-90 ${cols[k]} ${rows[k]})`} />
            ))}
            {/* 车同轨: seven track gauges collapse onto one */}
            {Array.from({length: 7}, (_, k) => {
              const g0 = (80 + ((k * 37) % 110)) * gs;
              const g = lerp(g0, 130 * gs, conv);
              const off = lerp((k - 3) * 16 * gs, 0, conv);
              const x = cols[1] + off;
              const span = vertical ? 130 : 170;
              const yA = rows[1] - span;
              const yB = rows[1] + span;
              const d = prog(frame, stdAt + 8 + k * 2, 18, E.outCubic);
              return (
                <g key={k} stroke={hexA(CREAM, lerp(0.5, 0.95, conv))} strokeWidth={vertical ? 4 : 4.5}>
                  <line x1={x - g / 2} x2={x - g / 2} y1={yA} y2={lerp(yA, yB, d)} />
                  <line x1={x + g / 2} x2={x + g / 2} y1={yA} y2={lerp(yA, yB, d)} />
                </g>
              );
            })}
            {/* 度量衡: seven rulers with different units align */}
            {Array.from({length: 7}, (_, k) => {
              const len = 380 * (vertical ? 0.7 : 1);
              const u0 = (26 + ((k * 13) % 30)) * gs;
              const u = lerp(u0, 38 * gs, conv);
              const y = lerp(rows[2] - 150 * (vertical ? 0.7 : 1) + k * 50 * (vertical ? 0.7 : 1), rows[2] + 30 * gs, conv);
              const x0 = cols[2] - len / 2;
              const d = prog(frame, stdAt + 10 + k * 2, 18, E.outCubic);
              const ticks = Math.floor(len / u);
              return (
                <g key={k} stroke={hexA(CREAM, lerp(0.5, 0.95, conv))} strokeWidth={vertical ? 3 : 3.4}>
                  <line x1={x0} x2={x0 + len * d} y1={y} y2={y} />
                  {Array.from({length: ticks + 1}, (_, j) =>
                    j * u <= len * d ? <line key={j} x1={x0 + j * u} x2={x0 + j * u} y1={y} y2={y - (j % 5 === 0 ? 34 : 16) * gs} /> : null,
                  )}
                </g>
              );
            })}
            {/* 书同文 resolves to a seal-script 文, written stroke by stroke with an even, round-ended line */}
            <g
              transform={`translate(${cols[0] - sealSize / 2} ${rows[0] - sealSize / 2 - (vertical ? 6 : 12)}) scale(${sealSize / 100})`}
              fill="none"
              stroke={CREAM}
              strokeWidth={6.4}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {SEAL_WEN.map((d, i) => {
                const p = prog(frame, sealAt + i * 6, i === 0 ? 8 : 13, E.inOutSine);
                return p > 0 ? <path key={i} d={d} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - p} /> : null;
              })}
            </g>
          </svg>
          {/* seven hands of one character converge, then give way to the seal form */}
          {fonts.map((f, k) => {
            const a = (k / 7) * Math.PI * 2 - Math.PI / 2;
            const rr = lerp(vertical ? 100 : 150, 0, conv);
            const show = prog(frame, stdAt + 4 + k * 3, 12, E.outCubic);
            const keep = 1 - prog(frame, stdAt + 50, 16, E.inCubic);
            const box = vertical ? 100 : 140;
            return (
              <div
                key={f}
                style={{
                  position: 'absolute',
                  left: cols[0] + Math.cos(a) * rr - box / 2,
                  top: rows[0] + Math.sin(a) * rr - box / 2,
                  width: box,
                  height: box,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: fam(f),
                  fontSize: lerp(vertical ? 58 : 86, vertical ? 76 : 110, conv),
                  lineHeight: 1,
                  color: hexA(CREAM, k === 0 ? 0.95 : 0.75),
                  opacity: show * keep,
                }}
              >
                文
              </div>
            );
          })}
          {/* annotation beside the seal glyph */}
          <div
            style={{
              position: 'absolute',
              ...(vertical
                ? {left: 46, width: cols[0] - ringR - 18 - 46, top: rows[0] - 16, textAlign: 'right' as const}
                : {left: cols[0] - 160, width: 320, top: rows[0] + sealSize / 2 + 4, textAlign: 'center' as const}),
              fontFamily: BODY,
              fontSize: vertical ? 26 : 24,
              letterSpacing: 2,
              color: hexA(CREAM, 0.78),
              opacity: prog(frame, sealAt + 22, 14, E.outCubic),
              whiteSpace: 'nowrap',
            }}
          >
            小篆 · 字形示意
          </div>
          {[
            ['书同文', cols[0], rows[0]],
            ['车同轨', cols[1], rows[1]],
            ['统一度量衡', cols[2], rows[2]],
          ].map(([t, x, y], k) => (
            <div
              key={t as string}
              style={{
                position: 'absolute',
                left: (x as number) - 220,
                width: 440,
                top: (y as number) + labelDy,
                textAlign: 'center',
                fontFamily: fam(C4.font),
                fontSize: labelSize,
                lineHeight: 1,
                color: P.accent,
                letterSpacing: 10,
                opacity: prog(frame, stdAt + 70 + k * 6, 14, E.outCubic),
              }}
            >
              {t as string}
            </div>
          ))}
          {/* the edict behind 书同文, quoted verbatim */}
          <div
            style={{
              position: 'absolute',
              ...(vertical
                ? {left: cols[0] + ringR + 22, top: rows[0] - 46, textAlign: 'left' as const}
                : {left: cols[0] - 240, width: 480, top: rows[0] + labelDy + labelSize + 18, textAlign: 'center' as const}),
              whiteSpace: 'nowrap',
            }}
          >
            <Line at={stdAt + 92} font={C4.font} size={34} color={CREAM} style={{letterSpacing: 3, lineHeight: 1.3}}>
              罢其不与秦文合者
            </Line>
            <Line at={stdAt + 100} size={vertical ? 26 : 24} color={hexA(CREAM, 0.78)} style={{marginTop: vertical ? 10 : 6, lineHeight: 1.3}}>
              ——《说文解字 · 叙》
            </Line>
          </div>
        </AbsoluteFill>
      )}

      {/* great wall */}
      {frame >= wallAt - 6 && (
        <AbsoluteFill style={{opacity: wallIn}}>
          <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
            <defs>
              <radialGradient id="qinTip">
                <stop offset="0" stopColor="#ff6a3d" stopOpacity={0.9} />
                <stop offset="0.35" stopColor={P.accent} stopOpacity={0.55} />
                <stop offset="1" stopColor={P.accent} stopOpacity={0} />
              </radialGradient>
            </defs>
            <circle cx={W * (vertical ? 0.62 : 0.74)} cy={H * (vertical ? 0.42 : 0.34)} r={vertical ? 120 : 150} fill={P.accent} opacity={0.9 * prog(frame, wallAt, 30, E.outCubic)} />
            <path d={mountains(0)} fill="#1b1917" />
            <path d={mountains(1)} fill="#141311" />
            <g transform={`translate(${pan.toFixed(2)} 0)`}>
              {/* the ridge the wall follows */}
              <path d={polyline([[ridge[0][0], H], ...ridge, [ridge[ridge.length - 1][0], H]], true)} fill="#100f0d" />
              <g transform="translate(0 -4)">
                {/* rammed-earth wall: a pale tamped band with a darker layer line inside */}
                <path d={polyline(wallPts)} fill="none" stroke={EARTH} strokeWidth={9} strokeLinecap="round" strokeLinejoin="round" />
                <path d={polyline(wallPts)} fill="none" stroke={hexA(LAYER, 0.6)} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" transform="translate(0 0.8)" />
                {towers.map((t, k) => {
                  const g = E.outCubic(clamp01((wallDraw - t.f) / 0.025));
                  if (g <= 0) return null;
                  const bw = 13 * tw;
                  const topw = 9.5 * tw;
                  const h = 30 * tw * g;
                  const yb = t.y - 2;
                  return (
                    <g key={k}>
                      <path d={`M${t.x - bw},${yb} L${t.x + bw},${yb} L${t.x + topw},${yb - h} L${t.x - topw},${yb - h} Z`} fill={EARTH} />
                      {h > 14 && <line x1={t.x - bw + 2} x2={t.x + bw - 2} y1={yb - h * 0.45} y2={yb - h * 0.45} stroke={hexA(LAYER, 0.6)} strokeWidth={2} />}
                    </g>
                  );
                })}
                {/* vermilion brush tip at the growing end */}
                {wallDraw > 0 && wallDraw < 1 && (
                  <g opacity={Math.min(1, wallDraw * 20, (1 - wallDraw) * 20)}>
                    <circle cx={tip[0]} cy={tip[1]} r={20 + 3 * noise2D('tip', frame / 5, 0)} fill="url(#qinTip)" />
                    <circle cx={tip[0]} cy={tip[1]} r={4.5} fill="#e5432e" />
                  </g>
                )}
              </g>
            </g>
            <path d={mountains(2)} fill="#0b0a09" />
          </svg>
          <div style={{position: 'absolute', left: vertical ? 70 : 150, top: vertical ? 400 : 240}}>
            <StaggerText text="起临洮，至辽东，延袤万余里" at={wallAt + 20} step={3} font={C4.font} size={vertical ? 52 : 62} color={CREAM} mode="ink" letterSpacing={6} />
            <Line at={wallAt + 56} color={hexA(CREAM, 0.78)} size={vertical ? 26 : 24} style={{marginTop: 16}}>
              ——《史记 · 蒙恬列传》
            </Line>
            <Line at={wallAt + 68} color={hexA(CREAM, 0.92)} size={vertical ? 36 : 32} style={{marginTop: vertical ? 14 : 10}}>
              秦在燕、赵、秦旧长城基础上连接增筑。
            </Line>
          </div>
        </AbsoluteFill>
      )}
      {/* slam flash */}
      <AbsoluteFill style={{backgroundColor: '#fff4e0', opacity: 0.4 * (1 - clamp01((frame - SLAM) / 6)) * (frame >= SLAM ? 1 : 0), mixBlendMode: 'screen'}} />
    </Paper>
  );
};
