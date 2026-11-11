import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {noise2D} from '@remotion/noise';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS, CUES} from '../timeline';
import {E, clamp01, hexA, lerp, prog} from '../lib/anim';
import {BODY, MONO, SERIF, fam} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const C11 = CHAPTERS[11];
const P = C11.palette;
const BREAK = CUES.qingBreak - C11.start;
const CRACK = CUES.qingCrack - C11.start;

// Imperial China from the First Emperor (221 BCE) to the Qing abdication (1912): 2,132 years
// (there is no year 0). Segments are schematic dynastic spans, coloured like the film's ruler.
const pos = (y: number) => (y < 0 ? y + 221 : y + 220);
const SPAN = pos(1912);
const SEGS: {n: string; a: number; b: number; c: string; f: string}[] = [
  {n: '秦', a: -221, b: -207, c: '#B3261E', f: 'ZL-Li'},
  {n: '汉', a: -207, b: 220, c: '#C9A15A', f: 'ZL-Li'},
  {n: '魏晋南北朝', a: 220, b: 581, c: '#46677A', f: 'ZL-Weibei'},
  {n: '隋', a: 581, b: 618, c: '#D9A85A', f: 'ZL-KaiBlack'},
  {n: '唐', a: 618, b: 907, c: '#C4832A', f: 'ZL-KaiBlack'},
  {n: '五代', a: 907, b: 960, c: '#9a948a', f: 'ZL-Kai'},
  {n: '宋', a: 960, b: 1271, c: '#9DB5B9', f: 'ZL-Fangsong'},
  {n: '元', a: 1271, b: 1368, c: '#2443A0', f: 'ZL-Xingkai'},
  {n: '明', a: 1368, b: 1644, c: '#7B2D3A', f: 'ZL-SongBold'},
  {n: '清', a: 1644, b: 1912, c: '#D58E86', f: 'ZL-Song'},
];

export const S11Qing: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();

  const x0 = vertical ? 70 : 150;
  const x1 = W - (vertical ? 70 : 150);
  const by = vertical ? H * 0.56 : H * 0.655;
  const bh = vertical ? 70 : 92;
  const X = (y: number) => x0 + (pos(y) / SPAN) * (x1 - x0);

  const fillTo = interpolate(frame, [8, 132], [-221, 1840], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E.inOutSine});
  const years = Math.round(interpolate(frame, [8, 96], [0, SPAN], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E.outCubic}));
  const tension = prog(frame, BREAK, CRACK - BREAK, E.inCubic);
  const crack = prog(frame, CRACK, 10, E.outCubic);
  const grey = prog(frame, CRACK, 30, E.outCubic);
  const shakeAmp = frame >= CRACK ? 22 * (1 - prog(frame, CRACK, 16, E.outCubic)) : 3 * tension;
  const shx = noise2D('shx', frame * 0.9, 0) * shakeAmp;
  const shy = noise2D('shy', 0, frame * 0.9) * shakeAmp;
  const xc = X(1840);

  // a fracture that lives inside the bar: noisy polyline plus two short branches
  const top = by - bh / 2;
  const bot = by + bh / 2;
  const crackPts: [number, number][] = Array.from({length: 15}, (_, k) => {
    const y = top - 6 + (k / 14) * (bh + 12);
    const amp = 4 + 14 * Math.abs(noise2D('crk-a', k * 0.37, 1));
    return [xc + noise2D('crk', k * 0.55, 0) * amp, y];
  });
  const branches = [
    [crackPts[4], [crackPts[4][0] - 28, crackPts[4][1] - 10], [crackPts[4][0] - 40, crackPts[4][1] - 4]],
    [crackPts[10], [crackPts[10][0] + 22, crackPts[10][1] + 8], [crackPts[10][0] + 36, crackPts[10][1] + 6]],
  ];
  const pts = (arr: number[][]) => arr.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const leftPoly = pts([[x0 - 40, top - 20], ...crackPts, [crackPts[14][0], bot + 20], [x0 - 40, bot + 20]]);
  const rightPoly = pts([[crackPts[0][0], top - 20], [x1 + 60, top - 20], [x1 + 60, bot + 20], [crackPts[14][0], bot + 20], ...crackPts.slice().reverse()]);
  const split = crack;
  const label = {right: Math.max(W - (xc - 16), vertical ? 70 : 150), top: top - (vertical ? 250 : 300)};

  return (
    <Paper bg={P.bg} vignette={lerp(0.22, 0.5, grey)}>
      <AbsoluteFill style={{background: '#1a1716', opacity: 0.12 * grey}} />
      <AbsoluteFill style={{transform: `translate(${shx}px, ${shy}px)`}}>
        {/* headline */}
        <div style={{position: 'absolute', left: x0, top: vertical ? 320 : 170}}>
          <StaggerText text="帝制" at={6} step={6} font={C11.font} size={vertical ? 96 : 104} color={P.ink} mode="rise" letterSpacing={10} />
          <div style={{display: 'flex', alignItems: 'baseline', gap: 16, marginTop: 6}}>
            <span style={{fontFamily: SERIF, fontSize: vertical ? 96 : 112, color: P.accent, fontVariantNumeric: 'tabular-nums', filter: `grayscale(${grey})`}}>
              {years.toLocaleString('en-US')}
            </span>
            <span style={{fontFamily: fam('ZL-Fangsong'), fontSize: 32, color: P.ink}}>年</span>
          </div>
          <Line at={30} color={hexA(P.ink, 0.8)} size={vertical ? 32 : 30}>
            从秦始皇称帝（前 221）到清帝退位（1912），共 2,132 年。
          </Line>
        </div>

        <svg width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
          <defs>
            <pattern id="hatch" width={10} height={10} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1={0} y1={0} x2={0} y2={10} stroke={hexA(P.ink, 0.35)} strokeWidth={2} />
            </pattern>
            <clipPath id="s11-left">
              <polygon points={leftPoly} />
            </clipPath>
            <clipPath id="s11-right">
              <polygon points={rightPoly} />
            </clipPath>
            <clipPath id="filled">
              <rect x={x0} y={by - bh / 2 - 4} width={Math.max(0, X(fillTo) - x0)} height={bh + 8} />
            </clipPath>
          </defs>
          {/* left piece: everything up to the fracture */}
          <g clipPath="url(#s11-left)" transform={`translate(${-36 * split} ${4 * split}) rotate(${-0.6 * split} ${xc} ${by})`}>
            <g clipPath="url(#filled)" style={{filter: `grayscale(${grey}) brightness(${lerp(1, 0.82, grey)})`}}>
              {SEGS.map((sg) => (
                <rect key={sg.n} x={X(sg.a)} y={top} width={Math.max(0, Math.min(X(sg.b), xc) - X(sg.a))} height={bh} fill={sg.c} />
              ))}
            </g>
          </g>
          {/* right piece: the 1840-1912 stretch not yet reached, hatched */}
          <g clipPath="url(#s11-right)" transform={`translate(${28 * split} ${18 * split}) rotate(${2.5 * split} ${xc} ${by})`}>
            <rect x={xc} y={top} width={x1 - xc} height={bh} fill="url(#hatch)" stroke={hexA(P.ink, 0.35)} strokeWidth={1.5} strokeDasharray="6 5" opacity={prog(frame, 120, 16, E.outCubic)} />
            <g clipPath="url(#filled)" style={{filter: `grayscale(${grey}) brightness(${lerp(1, 0.82, grey)})`}}>
              {SEGS.map((sg) => (
                <rect key={sg.n} x={X(sg.a)} y={top} width={Math.max(0, Math.min(X(sg.b), xc) - X(sg.a))} height={bh} fill={sg.c} />
              ))}
            </g>
          </g>
          {split > 0 && (
            <g fill="none" stroke="#1a1716" strokeLinejoin="round" opacity={0.85 * split}>
              <polyline points={pts(crackPts)} strokeWidth={2} transform={`translate(${-36 * split} ${4 * split}) rotate(${-0.6 * split} ${xc} ${by})`} />
              {branches.map((br, k) => (
                <polyline key={k} points={pts(br)} strokeWidth={1.4} transform={`translate(${-36 * split} ${4 * split}) rotate(${-0.6 * split} ${xc} ${by})`} />
              ))}
            </g>
          )}
          {/* 1840 marker: a flagpole to the right of the label, never through it */}
          <line x1={xc} x2={xc} y1={label.top + 8} y2={bot + 24} stroke="#B3261E" strokeWidth={2.5} opacity={prog(frame, BREAK - 30, 14, E.outCubic)} />
          {/* ticks */}
          {[-221, 1, 500, 1000, 1500, 1912].map((y) => (
            <g key={y} opacity={prog(frame, 12, 20, E.outCubic) * 0.6}>
              <line x1={X(y)} x2={X(y)} y1={by + bh / 2 + 6} y2={by + bh / 2 + 16} stroke={P.ink} strokeWidth={1.2} />
              <text x={X(y)} y={by + bh / 2 + 40} textAnchor="middle" fontFamily={MONO} fontSize={vertical ? 18 : 15} fill={P.ink}>
                {y < 0 ? `前${-y}` : y === 1 ? '公元1' : y}
              </text>
            </g>
          ))}
        </svg>

        {/* dynasty labels, each in its own era's typeface */}
        {SEGS.map((s, k) => {
          const mid = (X(s.a) + Math.min(X(s.b), xc)) / 2;
          const show = clamp01((fillTo - s.a) / Math.max(20, (s.b - s.a) * 0.5));
          const up = k % 2 === 0;
          const narrow = X(s.b) - X(s.a) < 70;
          return (
            <div
              key={s.n}
              style={{
                position: 'absolute',
                left: mid - 100,
                width: 200,
                top: up ? by - bh / 2 - (narrow ? 96 : 70) : by + bh / 2 + (narrow ? 50 : 52),
                textAlign: 'center',
                fontFamily: fam(s.f),
                fontSize: vertical ? 30 : s.n.length > 2 ? 30 : 38,
                color: P.ink,
                opacity: show * (1 - 0.5 * grey),
                transform: `translateY(${(1 - show) * (up ? 10 : -10)}px)`,
              }}
            >
              {s.n}
            </div>
          );
        })}

        {/* 1840 */}
        <div
          style={{
            position: 'absolute',
            right: label.right,
            top: label.top,
            textAlign: 'right',
            transformOrigin: 'right center',
            opacity: prog(frame, CRACK, 6, E.outCubic),
            transform: `scale(${lerp(1.5, 1, prog(frame, CRACK, 10, E.outBack))})`,
          }}
        >
          <div style={{fontFamily: SERIF, fontSize: vertical ? 96 : 150, color: '#B3261E', lineHeight: 1}}>1840</div>
          <div style={{fontFamily: fam('ZL-SongBold'), fontSize: vertical ? 40 : 46, color: '#1a1716', letterSpacing: 12, marginTop: 8, marginRight: -12}}>鸦片战争</div>
        </div>
        <div style={{position: 'absolute', right: vertical ? 70 : 150, top: by + bh / 2 + (vertical ? 130 : 96), textAlign: 'right'}}>
          <Line at={CRACK + 18} color={P.ink} size={vertical ? 34 : 30}>
            中国近代史由此开端。
          </Line>
          <div style={{fontFamily: BODY, fontSize: vertical ? 24 : 22, color: hexA(P.ink, 0.75), letterSpacing: 2, marginTop: 6, opacity: prog(frame, CRACK + 24, 12)}}>
            朝代以起始年份分界，按年份等比例绘制 · 示意
          </div>
        </div>
      </AbsoluteFill>
      {/* hit flash */}
      <AbsoluteFill style={{background: '#fff', opacity: frame >= CRACK ? 0.7 * (1 - prog(frame, CRACK, 7, E.outCubic)) : 0}} />
    </Paper>
  );
};
