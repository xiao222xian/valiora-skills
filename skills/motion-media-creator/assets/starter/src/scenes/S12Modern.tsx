import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {noise2D} from '@remotion/noise';
import {Paper} from '../components/Paper';
import {CHAPTERS, MODERN_EVENTS} from '../timeline';
import {E, hexA, lerp, prog, rng} from '../lib/anim';
import {MONO, SERIF, fam} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const C12 = CHAPTERS[12];
const P = C12.palette;
const RED = P.accent;
const BEAT = 30; // two beats at 120 BPM

// the same table drives the HUD year counter (timeline.ts axisKeys), so both cut on the same beat
const ITEMS = MODERN_EVENTS.map((e) => ({y: String(e.y), t: e.t, sub: e.sub}));

/** Grey bars standing in for columns of newsprint (no fake words). */
const Columns: React.FC<{x: number; y: number; w: number; h: number; seed: number; o: number}> = ({x, y, w, h, seed, o}) => {
  const r = rng(seed);
  const cols = 3;
  const cw = (w - (cols - 1) * 24) / cols;
  return (
    <g opacity={o}>
      {Array.from({length: cols}, (_, c) =>
        Array.from({length: Math.floor(h / 22)}, (_, k) => (
          <rect key={`${c}-${k}`} x={x + c * (cw + 24)} y={y + k * 22} width={cw * (k % 7 === 6 ? 0.5 : 0.82 + r() * 0.18)} height={9} fill={hexA(P.ink, 0.18)} />
        )),
      )}
    </g>
  );
};

export const S12Modern: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const idx = Math.min(ITEMS.length - 1, Math.floor(frame / BEAT));
  const it = ITEMS[idx];
  const t = frame - idx * BEAT;
  const slam = prog(t, 0, 5, E.outCubic);
  const kick = (1 - prog(t, 0, 8, E.outCubic)) * 14;
  const jx = noise2D('j', frame, 1) * kick;
  const jy = noise2D('j', 1, frame) * kick;
  const last = idx === ITEMS.length - 1;
  const layout = last ? 'final' : (['left', 'center', 'right'] as const)[idx % 3];
  const yearSize = vertical ? 300 : last ? 330 : 400;

  const rule = prog(t, 2, 10, E.outCubic);
  const sub = prog(t, 6, 10, E.outCubic);

  return (
    <Paper bg={P.bg} vignette={0.3}>
      {/* halftone */}
      <AbsoluteFill style={{backgroundImage: `radial-gradient(circle, ${hexA(P.ink, 0.1)} 1.1px, transparent 1.6px)`, backgroundSize: '7px 7px', backgroundPosition: `${(frame * 0.15).toFixed(1)}px ${(frame * 0.08).toFixed(1)}px`, opacity: 0.6}} />
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* masthead rules */}
        <line x1={vertical ? 70 : 150} x2={W - (vertical ? 70 : 150)} y1={vertical ? 300 : 140} y2={vertical ? 300 : 140} stroke={P.ink} strokeWidth={3} />
        <line x1={vertical ? 70 : 150} x2={W - (vertical ? 70 : 150)} y1={vertical ? 308 : 148} y2={vertical ? 308 : 148} stroke={P.ink} strokeWidth={1} />
        <line x1={vertical ? 70 : 150} x2={W - (vertical ? 70 : 150)} y1={H - (vertical ? 420 : 150)} y2={H - (vertical ? 420 : 150)} stroke={P.ink} strokeWidth={1} />
        {!vertical && (layout === 'left' || layout === 'right') && <Columns x={layout === 'right' ? 150 : W - 150 - 520} y={H * 0.62} w={520} h={220} seed={idx + 3} o={0.9} />}
      </svg>

      {/* the 1949 card keeps breathing until the chapter ends */}
      <AbsoluteFill style={{transform: `translate(${jx}px, ${jy}px) scale(${last ? lerp(1, 1.05, prog(t, 10, 110, E.inOutSine)) : 1})`}}>
        {/* the year */}
        <div
          style={{
            position: 'absolute',
            top: vertical ? 620 : last ? 190 : 170,
            left: layout === 'left' ? (vertical ? 70 : 150) : layout === 'right' ? undefined : 0,
            right: layout === 'right' ? (vertical ? 70 : 150) : layout === 'left' ? undefined : 0,
            textAlign: layout === 'center' || layout === 'final' ? 'center' : layout,
            fontFamily: SERIF,
            fontWeight: 800,
            fontSize: yearSize,
            lineHeight: 0.92,
            letterSpacing: -8,
            color: last ? RED : P.ink,
            transform: `scale(${lerp(1.22, 1, slam)})`,
            transformOrigin: layout === 'left' ? '0% 50%' : layout === 'right' ? '100% 50%' : '50% 50%',
            opacity: slam,
            filter: `blur(${(1 - slam) * 6}px)`,
          }}
        >
          {/* misregistered red plate under the black */}
          {!last && (
            <span style={{position: 'absolute', color: hexA(RED, 0.85), transform: 'translate(7px, 5px)', zIndex: -1}}>{it.y}</span>
          )}
          <span style={{position: 'relative'}}>{it.y}</span>
        </div>
        {/* headline bar */}
        <div
          style={{
            position: 'absolute',
            top: vertical ? 960 : last ? 560 : 590,
            left: layout === 'right' ? undefined : layout === 'left' ? (vertical ? 70 : 150) : 0,
            right: layout === 'right' ? (vertical ? 70 : 150) : layout === 'left' ? undefined : 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: layout === 'left' ? 'flex-start' : layout === 'right' ? 'flex-end' : 'center',
          }}
        >
          <div
            style={{
              background: last ? RED : P.ink,
              color: P.bg,
              fontFamily: fam(C12.font),
              fontSize: vertical ? (it.t.length > 6 ? 56 : it.t.length > 5 ? 64 : 76) : last ? 84 : 92,
              whiteSpace: 'nowrap',
              letterSpacing: 10,
              padding: '10px 28px 14px',
              clipPath: `inset(0 ${(1 - rule) * 100}% 0 0)`,
            }}
          >
            {it.t}
          </div>
          {it.sub && (
            <div style={{fontFamily: fam('ZL-Song'), fontSize: vertical ? 34 : 38, color: P.ink, marginTop: 18, letterSpacing: 4, opacity: sub}}>{it.sub}</div>
          )}
        </div>
      </AbsoluteFill>

      {/* year strip */}
      <div
        style={{
          position: 'absolute',
          left: vertical ? 70 : 150,
          right: vertical ? 70 : 150,
          bottom: vertical ? 440 : 168,
          display: 'flex',
          justifyContent: 'space-between',
          fontFamily: MONO,
          fontSize: vertical ? 20 : 18,
          letterSpacing: 1,
        }}
      >
        {ITEMS.map((x, k) => (
          <span key={x.y} style={{color: k === idx ? RED : P.ink, opacity: k <= idx ? (k === idx ? 1 : 0.5) : 0.18, fontWeight: k === idx ? 700 : 400}}>
            {x.y}
          </span>
        ))}
      </div>
    </Paper>
  );
};
