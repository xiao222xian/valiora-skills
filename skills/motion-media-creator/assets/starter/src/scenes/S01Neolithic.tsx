import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS} from '../timeline';
import {E, Pt, clamp01, hexA, lerp, partialPolyline, prog} from '../lib/anim';
import {BODY} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const P = CHAPTERS[1].palette;
const TAU = Math.PI * 2;

// Majiayao-style jar profile: radius (px at scale 1) against height fraction v (0 = lip).
const PROFILE: [number, number][] = [
  [0, 112], [0.05, 98], [0.13, 116], [0.28, 232], [0.44, 300], [0.6, 276], [0.8, 190], [1, 122],
];
const radius = (v: number) => {
  const p = PROFILE;
  let i = 0;
  while (i < p.length - 2 && v > p[i + 1][0]) i++;
  const [v0, r0] = p[i];
  const [v1, r1] = p[i + 1];
  const rm = p[Math.max(0, i - 1)][1];
  const rp = p[Math.min(p.length - 1, i + 2)][1];
  const t = clamp01((v - v0) / (v1 - v0));
  // Catmull-Rom in r
  const m0 = (r1 - rm) / 2;
  const m1 = (rp - r0) / 2;
  const t2 = t * t;
  const t3 = t2 * t;
  return (2 * t3 - 3 * t2 + 1) * r0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * r1 + (t3 - t2) * m1;
};

type SurfLine = {pts: [number, number][]; w: number; at: number; dur: number; closed?: boolean};

/** Pattern authored on the unrolled surface: θ (radians around the jar), v (height fraction). */
const buildPattern = (h: number): SurfLine[] => {
  const L: SurfLine[] = [];
  const ring = (v: number, w: number, at: number) =>
    L.push({pts: Array.from({length: 121}, (_, k) => [(k / 120) * TAU, v] as [number, number]), w, at, dur: 26, closed: true});
  ring(0.135, 7, 0);
  ring(0.158, 4, 4);
  ring(0.545, 7, 8);
  ring(0.568, 4, 12);
  // whirl band: four spirals joined by flowing double bands
  const vc = 0.335;
  const rC = radius(vc);
  for (let k = 0; k < 4; k++) {
    const thc = (k / 4) * TAU;
    const spiral: [number, number][] = [];
    const turns = 2.6;
    const N = 120;
    for (let j = 0; j <= N; j++) {
      const tau = (j / N) * turns * TAU;
      const rho = (8 + 64 * (j / N)) * 1.0;
      const dir = k % 2 === 0 ? 1 : -1;
      spiral.push([thc + (rho * Math.cos(tau * dir)) / rC, vc + (rho * Math.sin(tau * dir)) / h]);
    }
    L.push({pts: spiral, w: 13, at: 30 + k * 9, dur: 40});
    L.push({pts: [[thc, vc], [thc + 0.001, vc]], w: 20, at: 30 + k * 9, dur: 4});
  }
  // two braided wave pairs in opposite phase: they cross between whirls and wrap each one
  for (const [sign, amp, w, at] of [
    [1, 0.128, 10, 8], [1, 0.158, 6, 16], [-1, 0.128, 10, 12], [-1, 0.158, 6, 20],
  ] as [number, number, number, number][]) {
    L.push({
      pts: Array.from({length: 241}, (_, j) => {
        const th = (j / 240) * TAU;
        return [th, vc - sign * amp * Math.cos(2 * th)] as [number, number];
      }),
      w, at, dur: 60, closed: true,
    });
  }
  // lower water-wave band
  L.push({pts: Array.from({length: 241}, (_, k) => [(k / 240) * TAU, 0.625 + 0.03 * Math.sin(8 * (k / 240) * TAU)] as [number, number]), w: 6, at: 70, dur: 44, closed: true});
  L.push({pts: Array.from({length: 241}, (_, k) => [(k / 240) * TAU, 0.672 + 0.03 * Math.sin(8 * (k / 240) * TAU + 0.6)] as [number, number]), w: 4, at: 78, dur: 44, closed: true});
  // neck zigzag
  const zig: [number, number][] = [];
  for (let k = 0; k <= 48; k++) zig.push([(k / 48) * TAU, k % 2 ? 0.035 : 0.11]);
  L.push({pts: zig, w: 4, at: 88, dur: 36, closed: true});
  return L;
};

export const S01Neolithic: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();

  const scale = vertical ? 1.05 : 1;
  const jh = 620 * scale;
  const cx = vertical ? W / 2 : W * 0.66;
  const top = vertical ? H * 0.38 : H * 0.18;
  const tilt = 0.14;
  const rot = frame * 0.011 + 0.4;
  const R = (v: number) => radius(v) * scale;

  const pattern = useMemo(() => buildPattern(jh), [jh]);

  const project = (th: number, v: number): [number, number, number] => {
    const a = th + rot;
    const r = R(v);
    return [cx + r * Math.sin(a), top + v * jh + r * tilt * Math.cos(a), Math.cos(a)];
  };

  // silhouette: left edge down, front base arc, right edge up, back rim arc
  const sil: string[] = [];
  for (let k = 0; k <= 60; k++) {
    const v = k / 60;
    sil.push(`${(cx - R(v)).toFixed(1)},${(top + v * jh).toFixed(1)}`);
  }
  for (let k = 0; k <= 40; k++) {
    const a = -Math.PI / 2 + (k / 40) * Math.PI;
    sil.push(`${(cx + R(1) * Math.sin(a)).toFixed(1)},${(top + jh + R(1) * tilt * Math.cos(a)).toFixed(1)}`);
  }
  for (let k = 60; k >= 0; k--) {
    const v = k / 60;
    sil.push(`${(cx + R(v)).toFixed(1)},${(top + v * jh).toFixed(1)}`);
  }
  for (let k = 0; k <= 40; k++) {
    const a = Math.PI / 2 + (k / 40) * Math.PI;
    sil.push(`${(cx + R(0) * Math.sin(a)).toFixed(1)},${(top + R(0) * tilt * Math.cos(a)).toFixed(1)}`);
  }
  const silD = `M${sil.join('L')}Z`;

  // build-up: clay -> paint (no construction mesh on screen)
  const wireDraw = prog(frame, 0, 24, E.outCubic);
  const wire = 0;
  const clay = prog(frame, 0, 24, E.inOutCubic);
  const enter = prog(frame, -6, 16, E.outExpo);
  const push = lerp(1, 1.05, prog(frame, 0, 380, E.inOutSine));
  const paint0 = 58;

  /** Visible pieces of a surface polyline, chunked so each chunk carries its facing (1 = toward us). */
  const chunks = (pts: [number, number][], t: number, size = 7) => {
    const part = partialPolyline(pts as Pt[], t);
    const out: {d: string; f: number}[] = [];
    let cur: [number, number, number][] = [];
    const flush = () => {
      if (cur.length > 1) out.push({d: 'M' + cur.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join('L'), f: cur.reduce((s, q) => s + q[2], 0) / cur.length});
    };
    for (const [th, v] of part) {
      const q = project(th, v);
      if (q[2] > -0.02) {
        cur.push(q);
        if (cur.length > size) {
          flush();
          cur = [cur[cur.length - 1]];
        }
      } else {
        flush();
        cur = [];
      }
    }
    flush();
    return out;
  };
  const line = (pts: [number, number][], t: number) => chunks(pts, t, 1e9).map((c) => c.d).join('');
  const smooth = (x: number) => {
    const u = clamp01(x);
    return u * u * (3 - 2 * u);
  };

  const lon = Array.from({length: 24}, (_, k) => (k / 24) * TAU);
  const lat = Array.from({length: 11}, (_, k) => k / 10);

  // second beat: the unrolled surface (UV band) scrolls in sync with the jar; its middle half is
  // exactly what the camera sees on the jar right now
  const band = vertical ? {x: 70, y: 1408, w: W - 140, h: 120} : {x: 150, y: 776, w: 720, h: 132};
  const bandIn = prog(frame, 180, 36, E.inOutCubic);
  const vMin = 0.02;
  const vMax = 0.72;
  const wrap = (a: number) => {
    let x = (a + Math.PI) % TAU;
    if (x < 0) x += TAU;
    return x - Math.PI;
  };
  // a still 纹饰展开图: the band does not track the pot's rotation
  const BAND_ROT = 2.6;
  const flat = (th: number, v: number): Pt => [band.x + band.w / 2 + (wrap(th + BAND_ROT) / Math.PI) * (band.w / 2), band.y + ((v - vMin) / (vMax - vMin)) * band.h];
  const flatPath = (pts: [number, number][], t: number) => {
    const part = partialPolyline(pts as Pt[], t);
    let d = '';
    let prev: Pt | null = null;
    for (const [th, v] of part) {
      const q = flat(th, v);
      d += prev && Math.abs(q[0] - prev[0]) < band.w / 2 ? `L${q[0].toFixed(1)},${q[1].toFixed(1)}` : `M${q[0].toFixed(1)},${q[1].toFixed(1)}`;
      prev = q;
    }
    return d;
  };
  const midV = 0.335;

  return (
    <Paper bg={P.bg}>
      <AbsoluteFill style={{transform: `scale(${push})`, transformOrigin: `${cx}px ${top + jh / 2}px`}}>
        <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
          <defs>
            <linearGradient id="clay" x1={cx - R(0.44)} x2={cx + R(0.44)} y1={0} y2={0} gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="#6A3117" />
              <stop offset="0.16" stopColor="#A4532B" />
              <stop offset="0.36" stopColor="#DE9561" />
              <stop offset="0.55" stopColor="#C46C3D" />
              <stop offset="0.82" stopColor="#8C4421" />
              <stop offset="1" stopColor="#552811" />
            </linearGradient>
            <linearGradient id="clayV" x1={0} x2={0} y1={top} y2={top + jh} gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="#000" stopOpacity={0.15} />
              <stop offset="0.45" stopColor="#000" stopOpacity={0} />
              <stop offset="1" stopColor="#000" stopOpacity={0.32} />
            </linearGradient>
            <linearGradient id="limb" x1={cx - R(0.44)} x2={cx + R(0.44)} y1={0} y2={0} gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="rgb(40,18,8)" stopOpacity={0.45} />
              <stop offset="0.22" stopColor="rgb(40,18,8)" stopOpacity={0} />
              <stop offset="0.78" stopColor="rgb(40,18,8)" stopOpacity={0} />
              <stop offset="1" stopColor="rgb(40,18,8)" stopOpacity={0.45} />
            </linearGradient>
            <clipPath id="jar">
              <path d={silD} />
            </clipPath>
            <clipPath id="band-reveal">
              <rect x={band.x - 4} y={band.y - 30} width={(band.w + 8) * bandIn} height={band.h + 60} />
            </clipPath>
            <filter id="brush">
              <feTurbulence type="fractalNoise" baseFrequency="0.08" numOctaves={2} seed={12} />
              <feDisplacementMap in="SourceGraphic" scale={3.5} />
            </filter>
            <radialGradient id="shadow">
              <stop offset="0" stopColor="#3b2414" stopOpacity={0.45} />
              <stop offset="1" stopColor="#3b2414" stopOpacity={0} />
            </radialGradient>
          </defs>

          <ellipse cx={cx + 20} cy={top + jh + R(1) * tilt + 6} rx={R(1) * 2.1 * enter} ry={R(1) * 0.32 * enter} fill="url(#shadow)" />

          <g opacity={enter} transform={`translate(0 ${(1 - enter) * 40})`}>
            <path d={silD} fill="url(#clay)" opacity={clay} />
            <ellipse cx={cx} cy={top} rx={R(0)} ry={R(0) * tilt} fill="#3a1d0e" opacity={clay} />
            <ellipse cx={cx} cy={top} rx={R(0)} ry={R(0) * tilt} fill="none" stroke="#e7a77a" strokeWidth={2} opacity={clay * 0.6} />

            {wire > 0.01 && (
              <g stroke={P.ink} strokeWidth={1.1} fill="none" opacity={wire * 0.75}>
                {lon.map((th, k) => {
                  const pts: [number, number][] = Array.from({length: 31}, (_, j) => [th, j / 30]);
                  return <path key={`lo${k}`} d={line(pts, wireDraw)} />;
                })}
                {lat.map((v, k) => {
                  const pts: [number, number][] = Array.from({length: 73}, (_, j) => [(j / 72) * TAU, v]);
                  return <path key={`la${k}`} d={line(pts, clamp01(wireDraw * 1.6 - k * 0.06))} />;
                })}
                <path d={silD} strokeWidth={1.6} />
              </g>
            )}

            {/* paint thins and fades as it turns away, then takes the same body shading as the clay */}
            <g clipPath="url(#jar)" filter="url(#brush)" stroke="#24150d" fill="none" strokeLinecap="round" strokeLinejoin="round">
              {pattern.map((ln, k) => {
                const t = prog(frame, paint0 + ln.at, ln.dur, E.inOutSine);
                if (t <= 0) return null;
                return chunks(ln.pts, t).map((c, j) => (
                  <path key={`${k}-${j}`} d={c.d} strokeWidth={ln.w * scale * (0.35 + 0.65 * Math.max(0, c.f))} opacity={0.9 * smooth(c.f / 0.35)} />
                ));
              })}
            </g>
            <path d={silD} fill="url(#clayV)" opacity={clay} />
            <path d={silD} fill="url(#limb)" opacity={clay} style={{mixBlendMode: 'multiply'}} />
          </g>

          {/* unrolled band */}
          {bandIn > 0 && (
            <g clipPath="url(#band-reveal)">
              <rect x={band.x} y={band.y - 8} width={band.w} height={band.h + 16} rx={6} fill="#C9814F" />
              <rect x={band.x} y={band.y - 8} width={band.w} height={band.h + 16} rx={6} fill="none" stroke="#7A3B1E" strokeWidth={1.5} />
              <g stroke="#24150d" fill="none" strokeLinecap="round" strokeLinejoin="round" filter="url(#brush)">
                {pattern.map((ln, k) => {
                  const t = prog(frame, paint0 + ln.at, ln.dur, E.inOutSine);
                  return t > 0 ? <path key={k} d={flatPath(ln.pts, t)} strokeWidth={ln.w * (vertical ? 0.32 : 0.42)} opacity={0.85} /> : null;
                })}
              </g>
            </g>
          )}
        </svg>
      </AbsoluteFill>

      <AbsoluteFill>
        <div style={{position: 'absolute', left: vertical ? 70 : 150, top: 300, width: vertical ? W - 140 : 760}}>
          <StaggerText text="纹，先于字" at={4} step={5} dur={18} font={CHAPTERS[1].font} size={vertical ? 110 : 132} color={P.ink} mode="rise" letterSpacing={10} />
          <div style={{height: 2, width: 120 * prog(frame, 40, 24, E.outCubic), background: P.accent, margin: vertical ? '24px 0 22px' : '34px 0 30px'}} />
          <Line at={52} color={P.ink} size={vertical ? 38 : 36}>
            从仰韶的回旋勾连纹，
          </Line>
          <Line at={62} color={P.ink} size={vertical ? 38 : 36}>
            到马家窑的旋涡与水波。
          </Line>
          <Line at={96} color={hexA(P.ink, 0.78)} size={vertical ? 34 : 30} style={{marginTop: vertical ? 14 : 22}}>
            成熟的文字出现之前，纹样已流传了数千年。
          </Line>
        </div>
        {bandIn > 0 && (
          <>
            <div
              style={{
                position: 'absolute',
                left: band.x,
                top: band.y - (vertical ? 50 : 44),
                fontFamily: BODY,
                fontSize: vertical ? 20 : 18,
                letterSpacing: 2,
                color: P.hud,
                opacity: 0.85 * prog(frame, 196, 16, E.outCubic),
              }}
            >
              纹饰展开图 · 示意
            </div>
          </>
        )}
        {!vertical && (
          <div
            style={{
              position: 'absolute',
              left: cx - 260,
              width: 520,
              top: top + jh + 66,
              textAlign: 'center',
              fontFamily: BODY,
              fontSize: 22,
              letterSpacing: 3,
              color: P.hud,
              opacity: 0.8 * prog(frame, 120, 20, E.outCubic),
            }}
          >
            马家窑类型旋涡纹 · 示意
          </div>
        )}
      </AbsoluteFill>
    </Paper>
  );
};
