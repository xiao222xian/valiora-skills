import React from 'react';
import { AbsoluteFill, Img, staticFile } from 'remotion';
import { C, FONT } from './layout';
import { useFonts } from './fonts';
import { SeriesStrip, stroke } from './Cover';
import type { CoverSpec } from './types';

// 4:3 (1440×1080) share card and 16:9 (1920×1080) card from the same cover.json variant as the 3:4 card.
// Picture: spec.wide.img full-bleed (object-fit cover, focus right) when given; otherwise the vertical base.img is
// reused at full height on the right (object-fit cover, left edge feathered) over a blurred copy of itself.
// Title on the left: small lines, then the accent words (one row on 16:9, stacked on 4:3), then the tail.
// The bottom ~17 % of wide cards (y > 896) is covered by play count and duration in list views, so the series strip
// sits above that line and nothing important goes below it.
export type WideRatio = '43' | '169';

const SIZE: Record<WideRatio, { w: number; h: number }> = { '43': { w: 1440, h: 1080 }, '169': { w: 1920, h: 1080 } };
const STRIP_BOTTOM = 184;
const STRIP_H = 108;
const PHOTO_W = 648; // 1080×1920 base at 0.6: 648 wide, top-aligned

// CJK glyphs are ~1 em wide; Latin letters, digits and ASCII punctuation ~0.58 em
const ems = (s: string) => [...s].reduce((n, ch) => n + (ch.charCodeAt(0) < 0x2e80 ? 0.58 : 1), 0);
const widest = (xs: string[]) => Math.max(1, ...xs.map(ems));

export const CoverWide: React.FC<{ spec: CoverSpec; variant: string; ratio: WideRatio }> = ({ spec, variant, ratio }) => {
  useFonts();
  const v = spec.variants[variant];
  const tail = v.tail ?? [];
  const { w, h } = SIZE[ratio];
  const one = ratio === '169';
  const rows = one ? [v.big.join(' ')] : v.big;
  const L = one ? { small: 70, big: 48, top: 130, indent: 0 } : { small: 50, big: 34, top: 70, indent: 70 };
  const textW = w - L.big - PHOTO_W * 0.45 - L.indent * (rows.length - 1);
  let small = Math.min(one ? 110 : 104, Math.floor((w * 0.62) / widest(v.small)));
  let big = Math.min(one ? 250 : 200, Math.floor(textW / widest(rows)));
  let tailSize = Math.min(Math.round(big * 0.53), Math.floor(textW / widest(tail)));
  const gap = 44;
  const need = v.small.length * small * 1.12 + gap + rows.length * big + tail.length * (tailSize * 1.1 + 10);
  const k = Math.min(1, (h - STRIP_BOTTOM - STRIP_H - L.top) / need);
  [small, big, tailSize] = [small, big, tailSize].map((x) => Math.floor(x * k));
  const bigTop = L.top + v.small.length * small * 1.12 + gap * k;
  const bg = spec.wide?.img;
  return (
    <AbsoluteFill style={{ backgroundColor: C.ink }}>
      {bg ? (
        <>
          <Img src={staticFile(bg)} style={{ position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'right center' }} />
          <AbsoluteFill style={{ background: 'linear-gradient(90deg, rgba(10,13,36,0.72) 0%, rgba(10,13,36,0.35) 45%, rgba(10,13,36,0) 70%)' }} />
        </>
      ) : (
        <>
          <AbsoluteFill style={{ transform: 'scale(1.1)', filter: 'blur(40px) brightness(0.42) saturate(1.1)' }}>
            <Img src={staticFile(spec.base.img)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </AbsoluteFill>
          <AbsoluteFill style={{ background: 'linear-gradient(90deg, rgba(10,13,36,0.72) 0%, rgba(10,13,36,0.35) 60%, rgba(10,13,36,0.15) 100%)' }} />
          <Img src={staticFile(spec.base.img)} style={{
            position: 'absolute', top: 0, right: 0, width: PHOTO_W, height: h, objectFit: 'cover', objectPosition: '50% 0%',
            WebkitMaskImage: 'linear-gradient(90deg, transparent 0, #000 160px)', maskImage: 'linear-gradient(90deg, transparent 0, #000 160px)',
          }} />
        </>
      )}
      <div style={{ position: 'absolute', left: L.small, top: L.top, transform: 'rotate(-3deg)', transformOrigin: 'left top' }}>
        {v.small.map((t, i) => (
          <div key={i} style={{ fontFamily: FONT.title, fontSize: small, color: C.white, lineHeight: 1.12, whiteSpace: 'nowrap', ...stroke(12), textShadow: `7px 8px 0 ${C.ink}` }}>{t}</div>
        ))}
      </div>
      <div style={{ position: 'absolute', left: L.big, top: bigTop, transform: 'rotate(-4deg)', transformOrigin: 'left top' }}>
        {rows.map((t, i) => (
          <div key={i} style={{ fontFamily: FONT.title, fontSize: big, color: C.amber, lineHeight: 1.0, marginLeft: i * L.indent, whiteSpace: 'pre', ...stroke(16), textShadow: `11px 13px 0 ${C.ink}` }}>{t}</div>
        ))}
        {tail.map((t, i) => (
          <div key={i} style={{ fontFamily: FONT.title, fontSize: tailSize, color: C.white, lineHeight: 1.1, marginLeft: 20, marginTop: 10, whiteSpace: 'nowrap', ...stroke(12), textShadow: `7px 8px 0 ${C.ink}` }}>{t}</div>
        ))}
      </div>
      <SeriesStrip series={spec.series} bottom={STRIP_BOTTOM} />
    </AbsoluteFill>
  );
};
