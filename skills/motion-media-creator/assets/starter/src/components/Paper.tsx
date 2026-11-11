import React from 'react';
import {AbsoluteFill, staticFile, useCurrentFrame} from 'remotion';
import {rng} from '../lib/anim';

/** Era background: flat colour + rice-paper fibres + live film grain + vignette. */
export const Paper: React.FC<{
  bg: string;
  dark?: boolean;
  fibre?: number;
  grain?: number;
  vignette?: number;
  children?: React.ReactNode;
}> = ({bg, dark = false, fibre = 0.32, grain = 0.07, vignette = 0.28, children}) => {
  const frame = Math.floor(useCurrentFrame()); // Freeze can hand a fractional frame; grain files are per integer
  const r = rng(frame * 7919 + 13);
  const gx = Math.floor(r() * 512);
  const gy = Math.floor(r() * 512);
  return (
    <AbsoluteFill style={{backgroundColor: bg, overflow: 'hidden'}}>
      <AbsoluteFill
        style={{
          backgroundImage: `url(${staticFile('tex/paper.png')})`,
          backgroundSize: '1400px 1400px',
          mixBlendMode: dark ? 'screen' : 'multiply',
          opacity: dark ? fibre * 0.22 : fibre,
          filter: dark ? 'invert(1)' : undefined,
        }}
      />
      {children}
      <AbsoluteFill
        style={{
          backgroundImage: `url(${staticFile(`tex/grain${frame % 6}.png`)})`,
          backgroundPosition: `${gx}px ${gy}px`,
          mixBlendMode: 'overlay',
          opacity: grain,
          pointerEvents: 'none',
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0) 55%, rgba(0,0,0,${vignette}) 100%)`,
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};

