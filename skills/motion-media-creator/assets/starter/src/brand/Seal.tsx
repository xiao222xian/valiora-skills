import React from 'react';
import {useCurrentFrame} from 'remotion';
import {E, prog} from '../lib/anim';
import {fam} from '../lib/fonts';
import type {SealProps} from './types';

// Placeholder seal: replace with the brand's own seal design. Text comes from the brand profile.
export const SEAL_TEXT = '印章';

export const BrandSeal: React.FC<SealProps> = ({at, size, color = '#B8322A', paper = '#EEE7D8', style}) => {
  const frame = useCurrentFrame();
  const p = prog(frame, at, 9, E.outCubic);
  const chars = Array.from(SEAL_TEXT);
  return (
    <div style={{width: size, height: size, position: 'relative', opacity: p > 0 ? Math.min(1, p * 1.6) : 0, transform: `scale(${1.25 - 0.25 * p})`, ...style}}>
      <div style={{position: 'absolute', inset: size * 0.04, background: color, borderRadius: size * 0.05}} />
      <div style={{position: 'absolute', inset: size * 0.14, display: 'grid', gridTemplateColumns: `repeat(${chars.length > 2 ? 2 : chars.length}, 1fr)`, alignItems: 'center', justifyItems: 'center', fontFamily: fam('ZL-Li'), fontSize: size * (chars.length > 1 ? 0.32 : 0.5), lineHeight: 1, color: paper}}>
        {chars.map((ch, i) => (
          <span key={i}>{ch}</span>
        ))}
      </div>
    </div>
  );
};
