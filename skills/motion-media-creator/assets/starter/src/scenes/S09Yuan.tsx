import React, {useMemo} from 'react';
import {useCurrentFrame} from 'remotion';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS} from '../timeline';
import {E, Pt, clamp01, hexA, lerp, polyline, prog, rng} from '../lib/anim';
import {BODY} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const C9 = CHAPTERS[9];
const P = C9.palette;
const COBALT = '#1E3A8C';
const WASH = '#3C5DB6';
const TAU = Math.PI * 2;

const polar = (r: number, a: number): Pt => [r * Math.cos(a), r * Math.sin(a)];

/** One broad, rounded lotus petal pointing up (local coordinates). */
const petal = (len: number, width: number) =>
  `M0,0 C${-width},${-len * 0.25} ${-width * 0.9},${-len * 0.8} 0,${-len} C${width * 0.9},${-len * 0.8} ${width},${-len * 0.25} 0,0 Z`;
const leafPath = (s: number) => `M0,0 Q${10 * s},${-14 * s} ${32 * s},${-6 * s} Q${14 * s},${5 * s} 0,0 Z`;
const curl = (dir: number, s: number) => `M0,0 C${-18 * dir * s},${8 * s} ${-30 * dir * s},${-6 * s} ${-22 * dir * s},${-18 * s} C${-16 * dir * s},${-26 * s} ${-6 * dir * s},${-20 * s} ${-10 * dir * s},${-14 * s}`;

const VINE_START = 30;
const VINE_DUR = 210;

export const S09Yuan: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const R = vertical ? 400 : 410;
  const cx = W / 2;
  const cy = vertical ? H * 0.56 : H * 0.5;
  const spin = frame * 0.2;
  const enter = prog(frame, 0, 26, E.outCubic);
  const push = lerp(1, 1.32, prog(frame, 268, 100, E.inOutSine)); // second beat: into the centre lotus

  // scrolling stem: an undulating ring; nodes alternate inside/outside, each with its own habit
  const vine = useMemo(() => {
    const pts: Pt[] = [];
    for (let k = 0; k <= 720; k++) {
      const a = (k / 720) * TAU;
      pts.push(polar(262 + 34 * Math.sin(6 * a), a));
    }
    const r = rng(1271);
    const nodes = Array.from({length: 12}, (_, k) => {
      const t = k / 12 + 1 / 48;
      const a = t * TAU;
      return {
        a,
        t,
        rad: 262 + 34 * Math.sin(6 * a),
        out: k % 2 === 0 ? 1 : -1,
        size: 1.5 + r() * 0.5,
        leaves: 1 + Math.floor(r() * 3),
        curlDir: r() < 0.5 ? 1 : -1,
        branch: r() < 0.5 ? 40 + r() * 20 : 0,
        branchAng: (r() - 0.5) * 1.2,
      };
    });
    return {pts, nodes};
  }, []);
  const stemT = prog(frame, VINE_START, VINE_DUR, E.linear);
  const nStem = Math.floor(vine.pts.length * stemT);
  const nodeLocal = (t: number) => frame - (VINE_START + VINE_DUR * t);

  const ring = (r: number, w: number, at: number, dur = 30) => {
    const t = prog(frame, at, dur, E.inOutCubic);
    return <circle cx={0} cy={0} r={r} fill="none" stroke={COBALT} strokeWidth={w} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - t} transform="rotate(-90)" />;
  };

  const waves = useMemo(() => {
    const out: string[] = [];
    for (let row = 0; row < 2; row++) {
      const r = 344 + row * 18;
      const n = 64;
      for (let k = 0; k < n; k++) {
        const a0 = (k / n) * TAU + (row ? TAU / (2 * n) : 0);
        const a1 = a0 + TAU / n;
        const [x0, y0] = polar(r, a0);
        const [x1, y1] = polar(r, a1);
        out.push(`M${x0.toFixed(1)},${y0.toFixed(1)} A${(r * Math.PI) / n},${(r * Math.PI) / n} 0 0 0 ${x1.toFixed(1)},${y1.toFixed(1)}`);
      }
    }
    return out;
  }, []);

  // centre medallion closes the chapter once the vine has gone round
  const medallion = (count: number, r0: number, len: number, wid: number, at: number, rot: number) =>
    Array.from({length: count}, (_, k) => {
      const a = (k / count) * 360 + rot;
      const t = prog(frame, at + k * 1.5, 18, E.outBack);
      if (t <= 0) return null;
      return (
        <g key={k} transform={`rotate(${a}) translate(0 ${-r0})`}>
          <path d={petal(len * t, wid)} fill={hexA(WASH, 0.72)} stroke={COBALT} strokeWidth={2.4} />
        </g>
      );
    });

  const textSize = vertical ? 38 : 34;

  return (
    <Paper bg={P.bg} vignette={0.18}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <radialGradient id="s09-glaze" cx="42%" cy="38%" r="70%">
            <stop offset="0" stopColor="#ffffff" />
            <stop offset="0.6" stopColor="#f2f1ec" />
            <stop offset="1" stopColor="#d9dbe0" />
          </radialGradient>
          {/* cobalt under the glaze: a soft bleed plus slight displacement ("heaping and piling") */}
          <filter id="s09-cobalt" x="-10%" y="-10%" width="120%" height="120%">
            <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves={3} seed={13} result="n" />
            <feDisplacementMap in="SourceGraphic" in2="n" scale={4} result="d" />
            <feGaussianBlur in="d" stdDeviation={1.8} result="bleed" />
            <feMerge>
              <feMergeNode in="bleed" />
              <feMergeNode in="d" />
            </feMerge>
          </filter>
        </defs>
        <g transform={`translate(${cx} ${cy}) scale(${lerp(0.94, 1, enter) * push})`} opacity={enter}>
          <ellipse cx={14} cy={R * 0.08 + 18} rx={R * 1.02} ry={R * 1.0} fill="rgba(30,40,70,0.18)" style={{filter: 'blur(18px)'}} />
          <circle r={R} fill="url(#s09-glaze)" />
          <circle r={R} fill="none" stroke="#c9ccd4" strokeWidth={3} />
          <g transform={`rotate(${spin})`} filter="url(#s09-cobalt)">
            {ring(R - 10, 6, 4)}
            {ring(R - 22, 2.4, 8)}
            {ring(330, 2.4, 12)}
            {ring(320, 6, 16)}
            {ring(200, 4, 22)}
            {ring(188, 1.8, 26)}
            <g fill="none" stroke={COBALT} strokeWidth={2.2}>
              {waves.map((d, k) => (
                <path key={k} d={d} opacity={prog(frame, 20 + (k % 64) * 0.6, 10, E.outCubic)} />
              ))}
            </g>
            <path d={polyline(vine.pts.slice(0, Math.max(2, nStem)))} fill="none" stroke={COBALT} strokeWidth={6} strokeLinecap="round" />
            {vine.nodes.map((n, k) => {
              const lf = nodeLocal(n.t);
              if (lf <= 0) return null;
              const [x, y] = polar(n.rad, n.a);
              const rot = (n.a * 180) / Math.PI + 90 + (n.out > 0 ? 0 : 180);
              const stalk = clamp01(lf / 10);
              const open = (j: number) => clamp01((lf - 6 - j * 3) / 14);
              const leaf = (j: number) => clamp01((lf - 10 - j * 4) / 16);
              const tendril = clamp01((lf - 14) / 18);
              const branch = clamp01((lf - 18) / 20);
              const s = n.size;
              const angles = [-0.95, -0.48, 0, 0.48, 0.95];
              return (
                <g key={k} transform={`translate(${x} ${y}) rotate(${rot})`}>
                  {/* stalk drawn out, then the bloom opens petal by petal */}
                  <path d={`M0,0 Q8,-14 0,-26`} fill="none" stroke={COBALT} strokeWidth={3.4} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - stalk} />
                  <g transform={`translate(0 -26) scale(${0.7 + 0.3 * s / 2})`}>
                    {angles.map((ang, j) => {
                      const o = open(j);
                      if (o <= 0) return null;
                      const len = (j === 2 ? 36 : 30 - Math.abs(ang) * 6) * s * 0.62;
                      return (
                        <g key={j} transform={`rotate(${(ang * o * 180) / Math.PI})`}>
                          <path d={petal(len * (0.35 + 0.65 * o), 9 * s * 0.6)} fill={hexA(WASH, 0.78)} stroke={COBALT} strokeWidth={2.2} />
                        </g>
                      );
                    })}
                    {open(0) > 0 && <circle r={5 * open(0)} fill={COBALT} />}
                  </g>
                  {Array.from({length: n.leaves}, (_, j) => {
                    const t = leaf(j);
                    if (t <= 0) return null;
                    const base = j === 0 ? 62 : j === 1 ? 128 : 96;
                    return (
                      <g key={j} transform={`rotate(${base * t}) scale(${(j % 2 ? -1 : 1) * t} ${t})`}>
                        <path d={leafPath(1.3 + 0.2 * j)} fill={hexA(WASH, 0.68)} stroke={COBALT} strokeWidth={2} />
                      </g>
                    );
                  })}
                  {tendril > 0 && <path d={curl(n.curlDir, 1.1)} fill="none" stroke={COBALT} strokeWidth={2.2} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - tendril} />}
                  {n.branch > 0 && branch > 0 && (
                    <g transform={`rotate(${(n.branchAng * 180) / Math.PI + 150})`}>
                      <path d={`M0,0 Q${n.branch * 0.3},${-n.branch * 0.4} ${n.branch * 0.15},${-n.branch}`} fill="none" stroke={COBALT} strokeWidth={2.6} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - branch} />
                      {branch > 0.9 && <g transform={`translate(${n.branch * 0.15} ${-n.branch})`}><path d={leafPath(0.9)} fill={hexA(WASH, 0.7)} stroke={COBALT} strokeWidth={1.8} /></g>}
                    </g>
                  )}
                </g>
              );
            })}
            {medallion(12, 44, 116, 34, 236, 0)}
            {medallion(8, 30, 80, 30, 252, 360 / 24)}
            <circle r={34 * prog(frame, 262, 16, E.outBack)} fill={COBALT} />
            <circle r={18 * prog(frame, 268, 16, E.outBack)} fill="#f2f1ec" />
          </g>
          <ellipse cx={-R * 0.32} cy={-R * 0.42} rx={R * 0.32} ry={R * 0.12} fill="#fff" opacity={0.35} transform="rotate(-30)" style={{filter: 'blur(10px)'}} />
        </g>
      </svg>

      {vertical ? (
        <div style={{position: 'absolute', left: 70, top: 340, width: W - 140}}>
          <StaggerText text="青花" at={8} step={8} font={C9.font} size={110} color={COBALT} mode="ink" letterSpacing={18} />
          <Line at={30} color={P.ink} size={textSize} style={{marginTop: 10}}>
            1271 年，忽必烈定国号「大元」。
          </Line>
          <Line at={42} color={P.ink} size={textSize}>
            钴蓝在釉下晕开，青花走向成熟。
          </Line>
        </div>
      ) : (
        <>
          {/* breaks the left-text template: title stands vertically on the left, copy on the right */}
          <div style={{position: 'absolute', left: 250, top: 230}}>
            <StaggerText text="青花" at={8} step={8} font={C9.font} size={170} color={COBALT} mode="ink" vertical letterSpacing={0} />
          </div>
          <div
            style={{
              position: 'absolute',
              right: 200,
              top: 210,
              height: 700,
              writingMode: 'vertical-rl',
              textOrientation: 'upright',
              display: 'flex',
              flexDirection: 'column', // in vertical-rl a column runs right to left
              gap: 18,
            }}
          >
            <Line at={30} color={P.ink} size={textSize} style={{letterSpacing: 4}}>
              一二七一年　忽必烈定国号「大元」
            </Line>
            <Line at={42} color={P.ink} size={textSize} style={{letterSpacing: 4}}>
              钴蓝在釉下晕开　青花走向成熟
            </Line>
          </div>
        </>
      )}
      <div
        style={{
          position: 'absolute',
          left: vertical ? 0 : 150,
          right: vertical ? 0 : undefined,
          top: vertical ? cy + R + 20 : 880,
          textAlign: vertical ? 'center' : 'left',
          fontFamily: BODY,
          fontSize: vertical ? 24 : 22,
          letterSpacing: 4,
          color: P.hud,
          opacity: 0.85 * prog(frame, 70, 16, E.outCubic) * (1 - prog(frame, 268, 16, E.inCubic)),
        }}
      >
        缠枝花卉纹 · 示意
      </div>
    </Paper>
  );
};

