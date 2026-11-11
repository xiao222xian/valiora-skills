import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {noise2D} from '@remotion/noise';
import {E, clamp01, lerp} from '../lib/anim';
import {useLayout} from '../lib/layout';
import type {TransitionKind} from '../timeline';

/** Incoming-scene transition: masks this scene in over `frames` while the previous scene's
 * tail keeps rendering underneath (its Sequence is extended by the same amount). */
export const Reveal: React.FC<{kind: TransitionKind; frames: number; seed?: number; edge?: string; children: React.ReactNode}> = ({
  kind,
  frames,
  seed = 1,
  edge = '#141210',
  children,
}) => {
  const frame = useCurrentFrame();
  const {W, H} = useLayout();
  if (kind === 'none' || frames <= 0 || frame >= frames) return <AbsoluteFill>{children}</AbsoluteFill>;
  const t = clamp01(frame / frames);
  const diag = Math.hypot(W, H);
  let style: React.CSSProperties = {};
  let overlay: React.ReactNode = null;

  const noisyPoints = (cx: number, cy: number, r: number, amp: number, n = 160) => {
    const pts: [number, number][] = [];
    for (let k = 0; k < n; k++) {
      const a = (k / n) * Math.PI * 2;
      const wob =
        noise2D(`ink${seed}`, Math.cos(a) * 1.6, Math.sin(a) * 1.6 + t * 0.8) * amp +
        noise2D(`ink2${seed}`, Math.cos(a) * 6, Math.sin(a) * 6) * amp * 0.35;
      const rr = Math.max(0, r * (1 + wob));
      pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
    }
    return pts;
  };

  switch (kind) {
    case 'ink':
    case 'bloom': {
      // the clip edge gets a visible wet rim so the reveal reads as ink, not a soft circle
      const r = lerp(0, diag * 0.62, E.inOutCubic(t));
      const pts = noisyPoints(W / 2, H / 2, r, kind === 'bloom' ? 0.16 : 0.11);
      style = {clipPath: `polygon(${pts.map(([x, y]) => `${x.toFixed(1)}px ${y.toFixed(1)}px`).join(',')})`};
      const d = 'M' + pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join('L') + 'Z';
      const rim = Math.sin(Math.PI * t);
      overlay = (
        <svg width={W} height={H} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
          <path d={d} fill="none" stroke={edge} strokeWidth={kind === 'bloom' ? 26 : 18} opacity={0.5 * rim} style={{filter: 'blur(6px)'}} />
          <path d={d} fill="none" stroke={edge} strokeWidth={3} opacity={0.75 * rim} />
        </svg>
      );
      break;
    }
    case 'iris': {
      const r = lerp(0, diag * 0.56, E.inOutQuint(t));
      style = {clipPath: `circle(${r.toFixed(1)}px at 50% 50%)`};
      break;
    }
    case 'slats': {
      const n = 16;
      const w = W / n;
      let d = '';
      for (let k = 0; k < n; k++) {
        const order = n - 1 - k; // right-to-left, like reading bamboo slips
        const local = clamp01((t * (1 + n * 0.06) - order * 0.06) / 1);
        const h = H * E.outCubic(local);
        const x = k * w;
        if (h > 0) d += `M${x.toFixed(1)},0H${(x + w + 0.6).toFixed(1)}V${h.toFixed(1)}H${x.toFixed(1)}Z`;
      }
      style = {clipPath: d ? `path('${d}')` : 'inset(100%)'};
      break;
    }
    case 'wipe': {
      // diagonal sweep from right to left
      const p = E.inOutCubic(t);
      const skew = H * 0.35;
      const x = lerp(W + skew, -skew, p);
      style = {clipPath: `polygon(${x}px 0px, ${W + skew}px 0px, ${W + skew}px ${H}px, ${x - skew}px ${H}px)`};
      break;
    }
    case 'shards': {
      // jagged tear travelling left to right
      const p = E.inOutCubic(t);
      const edge = lerp(-W * 0.15, W * 1.15, p);
      const pts: string[] = ['0px 0px'];
      const steps = 14;
      for (let k = 0; k <= steps; k++) {
        const yy = (k / steps) * H;
        const jag = (k % 2 === 0 ? 1 : -1) * 70 + noise2D('shard', k * 0.7, seed) * 60;
        pts.push(`${(edge + jag).toFixed(1)}px ${yy.toFixed(1)}px`);
      }
      pts.push(`0px ${H}px`);
      style = {clipPath: `polygon(${pts.join(',')})`};
      break;
    }
    case 'wave': {
      const p = E.inOutCubic(t);
      const base = lerp(H + 120, -120, p);
      let d = `M0,${H}`;
      for (let x = 0; x <= W; x += 24) {
        const yy = base + Math.sin(x / 140 + t * 9) * 46 + Math.sin(x / 57 - t * 5) * 14;
        d += `L${x},${yy.toFixed(1)}`;
      }
      d += `L${W},${H}Z`;
      style = {clipPath: `path('${d}')`};
      break;
    }
    case 'wipeRight': {
      // hard-edged left-to-right wipe, the direction the next chapter's bar fills
      const p = E.inOutCubic(t);
      style = {clipPath: `inset(0 ${((1 - p) * 100).toFixed(2)}% 0 0)`};
      overlay = <div style={{position: 'absolute', top: 0, bottom: 0, left: `${(p * 100).toFixed(2)}%`, width: 6, marginLeft: -6, background: edge, opacity: p < 1 ? 0.9 : 0}} />;
      break;
    }
    case 'flash':
    case 'dipBlack': {
      const a = 1 - E.outCubic(t);
      overlay = <AbsoluteFill style={{backgroundColor: kind === 'flash' ? '#fff8ec' : '#000', opacity: a * 0.9}} />;
      break;
    }
    case 'white': {
      overlay = <AbsoluteFill style={{backgroundColor: '#ffffff', opacity: 1 - E.outCubic(t)}} />;
      break;
    }
  }
  return (
    <AbsoluteFill style={style}>
      {children}
      {overlay}
    </AbsoluteFill>
  );
};
