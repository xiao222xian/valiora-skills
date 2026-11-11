import React from 'react';
import { AbsoluteFill, Img, staticFile } from 'remotion';
import { C, FONT } from './layout';
import { useFonts } from './fonts';
import type { CoverSpec } from './types';

// WeChat Channels 3:4 (1080×1440) card. Base: an on-camera frame of the guest with headroom (beautified like the film),
// placed 1080 wide and shifted up by spec.base.top. Flat heavy glyphs + one outline + hard shadow; only the 1–2
// semantic accent words are big and amber; the series strip keeps a stable baseline and never joins the broken rhythm.
export const stroke = (px: number) => ({ WebkitTextStroke: `${px}px ${C.ink}`, paintOrder: 'stroke fill' as const });

// Series label + official logo. Every glyph comes from the fonts wired by setup_starter (licence-checked).
// bottom: wide cards lift the strip above the bottom band that list views cover with play count and duration.
export const SeriesStrip: React.FC<{ series: string; bottom?: number }> = ({ series, bottom = 0 }) => (
  <div style={{ position: 'absolute', left: 0, right: 0, bottom, height: 108, background: C.ink, clipPath: 'polygon(0 22%, 100% 0, 100% 100%, 0 100%)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 28, padding: '20px 46px 0 46px' }}>
    {series && <div style={{ fontFamily: FONT.sans, fontWeight: 900, fontSize: 44, color: C.white, letterSpacing: 6 }}>{series}</div>}
    <Img src={staticFile('img/logo.png')} style={{ height: 58 }} />
  </div>
);

export const Cover: React.FC<{ spec: CoverSpec; variant: string }> = ({ spec, variant }) => {
  useFonts();
  const v = spec.variants[variant];
  return (
    <AbsoluteFill style={{ backgroundColor: C.ink }}>
      <Img src={staticFile(spec.base.img)} style={{ position: 'absolute', width: 1080, height: 1920, top: -spec.base.top, left: 0 }} />
      <AbsoluteFill style={{ background: 'linear-gradient(90deg, rgba(10,13,36,0.55) 0%, rgba(10,13,36,0) 55%), linear-gradient(180deg, rgba(10,13,36,0.25) 0%, rgba(10,13,36,0) 30%, rgba(10,13,36,0) 75%, rgba(10,13,36,0.5) 100%)' }} />
      <div style={{ position: 'absolute', left: 46, top: 64, transform: 'rotate(-3deg)', transformOrigin: 'left top' }}>
        {v.small.map((t, i) => (
          <div key={i} style={{ fontFamily: FONT.title, fontSize: 104, color: C.white, lineHeight: 1.12, ...stroke(12), textShadow: `7px 8px 0 ${C.ink}` }}>{t}</div>
        ))}
      </div>
      <div style={{ position: 'absolute', left: 30, top: v.bigTop ?? 610, transform: 'rotate(-4deg)', transformOrigin: 'left top' }}>
        {v.big.map((t, i) => (
          <div key={i} style={{ fontFamily: FONT.title, fontSize: 212, color: C.amber, lineHeight: 1.0, marginLeft: i * 70, ...stroke(16), textShadow: `11px 13px 0 ${C.ink}` }}>{t}</div>
        ))}
        {(v.tail ?? []).map((t, i) => (
          <div key={i} style={{ fontFamily: FONT.title, fontSize: 112, color: C.white, lineHeight: 1.1, marginLeft: 20, marginTop: 10, ...stroke(12), textShadow: `7px 8px 0 ${C.ink}` }}>{t}</div>
        ))}
      </div>
      <SeriesStrip series={spec.series} />
    </AbsoluteFill>
  );
};
