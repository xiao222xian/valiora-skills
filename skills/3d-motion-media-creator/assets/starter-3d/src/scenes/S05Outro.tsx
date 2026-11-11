import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {BrandSeal} from '../brand/Seal';
import {CHAPTERS, SUBTITLE, TITLE, chapterDur} from '../timeline';
import {E, hexA, prog} from '../lib/anim';
import {MONO, fam} from '../lib/fonts';
import {useLayout} from '../lib/layout';
import {CREDITS_CHANGED, LICENSES_HEAD, attributed, licenseUrl, otherLine} from '../credits';
import type {Credit} from '../credits';

// 片名卡 on the film's near-black ground: title and seal, subtitle, what the pictures stand for, the credits from
// src/credits.ts (tools/fetch_textures.py writes the CC0 texture entries there), the brand row, then black. The
// credits block is the motion-media-creator starter's, unchanged; only the notes and the ground are this film's.

const I = CHAPTERS.length - 1;
const P = CHAPTERS[I].palette;
const CARD = 8;

const nb = (s: string) => s.replace(/ /g, ' ');
const creditLine = (c: Credit) => [c.author, c.title, nb(c.license)].filter(Boolean).join(' · ');
const licenseLine = (list: Credit[]) =>
  `${LICENSES_HEAD}：` +
  [...new Set(list.map((c) => c.license.trim()))].map((l) => [nb(l), licenseUrl(l)].filter(Boolean).join(' ')).join('；');

const isWide = (c: number) => (c >= 0x2e80 && c <= 0x9fff) || (c >= 0xf900 && c <= 0xfaff) || (c >= 0xff00 && c <= 0xffef) || (c >= 0x3000 && c <= 0x303f);
const textWidth = (s: string, size: number) => {
  let em = 0;
  for (const ch of s) em += isWide(ch.codePointAt(0)!) ? 1 : 0.6;
  return em * size * 1.08;
};
const CREDIT_LH = 1.6;
const CREDIT_MAX_H = {h: 250, v: 360};
const CREDIT_SIZES = {h: [20, 19, 18, 17, 16, 15, 14], v: [23, 22, 21, 20, 19, 18, 17, 16]};

export const S05Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const black = prog(frame, chapterDur(I) - 30, 26, E.inCubic);
  const titleY = H * 0.42;
  const colW = vertical ? W - 140 : 1500;
  const named = attributed();
  const credits = (named.length ? [named.map(creditLine).join('；'), CREDITS_CHANGED, licenseLine(named)] : []).concat(otherLine()).filter(Boolean);
  const sizes = vertical ? CREDIT_SIZES.v : CREDIT_SIZES.h;
  const creditSize =
    sizes.find((s) => credits.reduce((n, t) => n + Math.ceil(textWidth(t, s) / colW), 0) * s * CREDIT_LH <= (vertical ? CREDIT_MAX_H.v : CREDIT_MAX_H.h)) ??
    sizes[sizes.length - 1];

  return (
    <Paper bg={P.bg} dark fibre={0} vignette={0.35}>
      <div style={{position: 'absolute', left: 0, right: 0, top: titleY - 170, display: 'flex', justifyContent: 'center'}}>
        <div style={{position: 'relative'}}>
          <StaggerText text={TITLE} at={CARD} step={6} font="OFL-SerifHeavy" size={150} color={P.ink} mode="ink" letterSpacing={vertical ? 10 : 24} style={{marginRight: vertical ? -10 : -24}} />
          <BrandSeal at={CARD + 28} size={vertical ? 76 : 80} color={P.accent} paper={P.bg} style={{position: 'absolute', left: '100%', marginLeft: vertical ? 12 : 22, bottom: vertical ? 14 : 18}} />
        </div>
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: titleY + (vertical ? 40 : 30), textAlign: 'center'}}>
        <Line at={CARD + 32} color={P.ink} size={vertical ? 44 : 40} style={{letterSpacing: 14, paddingLeft: 14}}>
          {SUBTITLE}
        </Line>
      </div>
      <div style={{position: 'absolute', left: vertical ? 70 : (W - colW) / 2, width: colW, top: titleY + (vertical ? 150 : 130), textAlign: 'center'}}>
        <Line at={CARD + 40} color={hexA(P.ink, 0.72)} size={vertical ? 23 : 20} style={{lineHeight: 1.6}}>
          {vertical ? (
            <>
              齿轮箱、机械臂与产线画面均为示意；
              <br />
              尺寸、齿数与台数不代表任何具体产品
            </>
          ) : (
            '齿轮箱、机械臂与产线画面均为示意；尺寸、齿数与台数不代表任何具体产品'
          )}
        </Line>
        {credits.length > 0 && (
          <div style={{marginTop: vertical ? 24 : 18}}>
            {credits.map((t, i) => (
              <Line key={i} at={CARD + 50 + i * 2} color={hexA(P.ink, i === 0 ? 0.66 : 0.52)} size={creditSize} dy={8} style={{fontFamily: MONO, letterSpacing: 0.2, lineHeight: CREDIT_LH}}>
                {t}
              </Line>
            ))}
          </div>
        )}
        {/* brand credit: the official brand logo, never re-typeset */}
        <div style={{marginTop: vertical ? 48 : 36, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: vertical ? 20 : 16, opacity: prog(frame, CARD + 56, 16, E.outCubic)}}>
          <span style={{fontFamily: fam('OFL-Sans'), fontSize: vertical ? 26 : 22, color: hexA(P.ink, 0.72), letterSpacing: 6}}>出品</span>
          <Img src={staticFile('brand/logo.png')} style={{height: vertical ? 58 : 48}} />
        </div>
      </div>
      <AbsoluteFill style={{background: '#000', opacity: black}} />
    </Paper>
  );
};
