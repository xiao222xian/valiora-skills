import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {E, prog} from '../lib/anim';
import {BODY, MONO, SERIF, fam} from '../lib/fonts';
import {LEADER_W, TYPE_FLOOR, useLayout} from '../lib/layout';

type Mode = 'rise' | 'ink' | 'stamp' | 'drop';

/** Per-character reveal. `out` (absolute local frame) fades the whole line away. */
export const StaggerText: React.FC<{
  text: string;
  at: number;
  step?: number;
  dur?: number;
  font: string;
  size: number;
  color: string;
  mode?: Mode;
  out?: number;
  outDur?: number;
  letterSpacing?: number;
  vertical?: boolean;
  style?: React.CSSProperties;
  charStyle?: (i: number, ch: string) => React.CSSProperties;
}> = ({
  text,
  at,
  step = 3,
  dur = 16,
  font,
  size,
  color,
  mode = 'rise',
  out,
  outDur = 12,
  letterSpacing = 0,
  vertical = false,
  style,
  charStyle,
}) => {
  const frame = useCurrentFrame();
  const fadeOut = out === undefined ? 1 : 1 - prog(frame, out, outDur, E.inCubic);
  const chars = Array.from(text);
  return (
    <div
      style={{
        fontFamily: fam(font),
        fontSize: size,
        color,
        letterSpacing,
        lineHeight: 1.15,
        whiteSpace: 'pre',
        display: 'flex',
        flexDirection: vertical ? 'column' : 'row',
        alignItems: vertical ? 'center' : 'baseline',
        opacity: fadeOut,
        ...style,
      }}
    >
      {chars.map((ch, i) => {
        const p = prog(frame, at + i * step, dur, mode === 'stamp' ? E.outBack : E.outCubic);
        let s: React.CSSProperties = {opacity: p};
        if (mode === 'rise') s = {opacity: p, transform: `translateY(${(1 - p) * size * 0.35}px)`};
        if (mode === 'ink') s = {opacity: p, filter: `blur(${((1 - p) * size * 0.06).toFixed(2)}px)`, transform: `scale(${1 + (1 - p) * 0.06})`};
        if (mode === 'stamp') s = {opacity: Math.min(1, p * 2), transform: `scale(${1.6 - 0.6 * p})`};
        if (mode === 'drop') s = {opacity: p, transform: `translateY(${-(1 - p) * size * 0.8}px)`};
        return (
          <span key={i} style={{display: 'inline-block', ...s, ...(charStyle ? charStyle(i, ch) : {})}}>
            {ch === ' ' ? ' ' : ch}
          </span>
        );
      })}
    </div>
  );
};

/** Quiet body copy line: fades and slides in, optional fade out. Data blocks, checklists and lists built from
 * it stay at or above TYPE_FLOOR.data (26 px at 1920x1080). */
export const Line: React.FC<{
  at: number;
  out?: number;
  size?: number;
  color: string;
  font?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
  dy?: number;
}> = ({at, out, size = 34, color, font, children, style, dy = 14}) => {
  const frame = useCurrentFrame();
  const p = prog(frame, at, 16, E.outCubic);
  const o = out === undefined ? 1 : 1 - prog(frame, out, 12, E.inCubic);
  return (
    <div
      style={{
        fontFamily: font ? fam(font) : BODY,
        fontSize: size,
        color,
        letterSpacing: 1.5,
        lineHeight: 1.5,
        ...style,
        opacity: p * o * ((style?.opacity as number | undefined) ?? 1),
        transform: `translateY(${(1 - p) * dy}px)`,
      }}
    >
      {children}
    </div>
  );
};

/** Leader line from a point on the subject to a small label, like a note on an engineering drawing. Points are
 * in screen pixels; the label sits at `to`. Label 22 px and a 1.5 px leader at 1920x1080 (TYPE_FLOOR.callout,
 * LEADER_W), scaled by the layout. */
export const Callout: React.FC<{
  from: [number, number];
  to: [number, number];
  label: string;
  at: number;
  out?: number;
  color: string;
  align?: 'left' | 'right';
  shadow?: boolean; // light labels over busy pictures
}> = ({from, to, label, at, out, color, align = 'left', shadow = false}) => {
  const frame = useCurrentFrame();
  const {W, H, ts} = useLayout();
  const draw = prog(frame, at, 10, E.outCubic);
  const o = out === undefined ? 1 : 1 - prog(frame, out - 8, 8, E.inCubic);
  if (draw <= 0 || o <= 0) return null;
  const ex = from[0] + (to[0] - from[0]) * draw;
  const ey = from[1] + (to[1] - from[1]) * draw;
  const labelO = prog(frame, at + 6, 8, E.linear);
  return (
    <AbsoluteFill style={{opacity: o, pointerEvents: 'none'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <circle cx={from[0]} cy={from[1]} r={3 * ts} fill={color} fillOpacity={0.9} />
        <line x1={from[0]} y1={from[1]} x2={ex} y2={ey} stroke={color} strokeOpacity={0.8} strokeWidth={LEADER_W * ts} />
      </svg>
      <div
        style={{
          position: 'absolute',
          left: to[0],
          top: to[1],
          transform: `translate(${align === 'right' ? 'calc(-100% - 8px)' : '8px'}, -50%)`,
          fontFamily: MONO,
          fontSize: TYPE_FLOOR.callout * ts,
          letterSpacing: 0.5,
          color,
          opacity: labelO * 0.9,
          whiteSpace: 'nowrap',
          textShadow: shadow ? '0 1px 8px rgba(0,0,0,0.5)' : 'none',
        }}
      >
        {label}
      </div>
    </AbsoluteFill>
  );
};

/** Large figure (4,416 · 1:10,000,000). 120-160 px at 1920x1080 (default 140); tabular figures, so counting
 * changes digits only: no scale, no bounce. `unit` is a small mono label under the figure. */
export const BigNumber: React.FC<{
  text: string;
  x: number;
  y: number; // top
  size?: number;
  at: number;
  out?: number;
  color: string;
  font?: string; // default: the serif at weight 700
  align?: 'left' | 'center' | 'right';
  unit?: string;
}> = ({text, x, y, size = 140, at, out, color, font, align = 'left', unit}) => {
  const frame = useCurrentFrame();
  const {ts} = useLayout();
  const pIn = prog(frame, at, 12, E.outCubic);
  const o = Math.min(pIn, out === undefined ? 1 : 1 - prog(frame, out - 10, 10, E.inCubic));
  if (o <= 0) return null;
  const px = Math.max(size, TYPE_FLOOR.bigNumber) * ts;
  const tx = align === 'center' ? '-50%' : align === 'right' ? '-100%' : '0';
  return (
    <div style={{position: 'absolute', left: x, top: y, transform: `translate(${tx}, ${(1 - pIn) * 8}px)`, opacity: o, textAlign: align, color}}>
      <div style={{fontFamily: font ? fam(font) : SERIF, fontWeight: font ? undefined : 700, fontSize: px, lineHeight: 1, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap'}}>{text}</div>
      {unit && <div style={{fontFamily: MONO, fontSize: Math.max(TYPE_FLOOR.callout * ts, px * 0.16), letterSpacing: '0.12em', opacity: 0.7, marginTop: px * 0.12}}>{unit}</div>}
    </div>
  );
};

/** Format an integer with thousands separators (4416 -> "4,416"). */
export const thousands = (n: number) => Math.round(n).toLocaleString('en-US');
