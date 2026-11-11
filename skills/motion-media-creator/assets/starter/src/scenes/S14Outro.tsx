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

const I14 = CHAPTERS.length - 1;
const P = CHAPTERS[I14].palette;
const CARD = 8;

// ---- credits on the card ------------------------------------------------------------------------
// The list comes from src/credits.ts, the catalogue tools/credits.mjs also writes the description blocks from:
// author · title · licence for each item that needs attribution, then each licence with its short URL, then one
// line for the material that needs none. Empty catalogue = no credits block.

/** No line break inside a licence name or a URL. */
const nb = (s: string) => s.replace(/ /g, '\u00a0');
const creditLine = (c: Credit) => [c.author, c.title, nb(c.license)].filter(Boolean).join(' · ');
const licenseLine = (list: Credit[]) =>
  `${LICENSES_HEAD}：` +
  [...new Set(list.map((c) => c.license.trim()))].map((l) => [nb(l), licenseUrl(l)].filter(Boolean).join(' ')).join('；');

// fitted size: the block grows with the credit list (estimate: CJK and full-width 1 em, Latin 0.6 em, 8 % slack)
const isWide = (c: number) => (c >= 0x2e80 && c <= 0x9fff) || (c >= 0xf900 && c <= 0xfaff) || (c >= 0xff00 && c <= 0xffef) || (c >= 0x3000 && c <= 0x303f);
const textWidth = (s: string, size: number) => {
  let em = 0;
  for (const ch of s) em += isWide(ch.codePointAt(0)!) ? 1 : 0.6;
  return em * size * 1.08;
};
const CREDIT_LH = 1.6;
// room between the notes and the brand row; re-check the card still when the notes above change
const CREDIT_MAX_H = {h: 250, v: 360};
const CREDIT_SIZES = {h: [20, 19, 18, 17, 16, 15, 14], v: [23, 22, 21, 20, 19, 18, 17, 16]};

/** The closing chapter hands over straight to the title card. No recap grid and no transition
 * (ruler folding back into a stroke) before the card: the user found both redundant. */
export const S14Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const black = prog(frame, chapterDur(I14) - 30, 26, E.inCubic);
  const titleY = H * 0.42;
  const colW = vertical ? W - 140 : 1500;
  const named = attributed();
  const credits = (named.length ? [named.map(creditLine).join('；'), CREDITS_CHANGED, licenseLine(named)] : []).concat(otherLine()).filter(Boolean);
  const sizes = vertical ? CREDIT_SIZES.v : CREDIT_SIZES.h;
  const creditSize =
    sizes.find((s) => credits.reduce((n, t) => n + Math.ceil(textWidth(t, s) / colW), 0) * s * CREDIT_LH <= (vertical ? CREDIT_MAX_H.v : CREDIT_MAX_H.h)) ??
    sizes[sizes.length - 1];

  return (
    <Paper bg={P.bg} vignette={0.2}>
      <div style={{position: 'absolute', left: 0, right: 0, top: titleY - 170, display: 'flex', justifyContent: 'center'}}>
        <div style={{position: 'relative'}}>
          <StaggerText text={TITLE} at={CARD} step={6} font="ZL-KaiBlack" size={150} color={P.ink} mode="ink" letterSpacing={vertical ? 10 : 24} style={{marginRight: vertical ? -10 : -24}} />
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
              引文出自先秦诸子著作及《左传》《史记》
              <br />
              《说文解字》《兰亭集序》《登鹳雀楼》《梦溪笔谈》
            </>
          ) : (
            '引文出自先秦诸子著作及《左传》《史记》《说文解字》《兰亭集序》《登鹳雀楼》《梦溪笔谈》'
          )}
        </Line>
        <Line at={CARD + 46} color={hexA(P.ink, 0.72)} size={vertical ? 23 : 20} style={{marginTop: vertical ? 10 : 0, lineHeight: 1.6}}>
          {vertical ? (
            <>
              朝代年份采用通行年表；
              <br />
              地图、建筑、器物、纹样与甲骨、小篆字形均为示意；
              <br />
              各章字体为风格选用；底部标尺各段长短不按年份比例
            </>
          ) : (
            '朝代年份采用通行年表；地图、建筑、器物、纹样与甲骨、小篆字形均为示意；各章字体为风格选用；底部标尺各段长短不按年份比例'
          )}
        </Line>
        {/* credits: author · title · licence, then each licence with its short URL; small mono fine print */}
        {credits.length > 0 && (
          <div style={{marginTop: vertical ? 24 : 18}}>
            {credits.map((t, i) => (
              <Line
                key={i}
                at={CARD + 50 + i * 2}
                color={hexA(P.ink, i === 0 ? 0.66 : 0.52)}
                size={creditSize}
                dy={8}
                style={{fontFamily: MONO, letterSpacing: 0.2, lineHeight: CREDIT_LH}}
              >
                {t}
              </Line>
            ))}
          </div>
        )}
        {/* brand credit: the official brand logo, never re-typeset */}
        <div
          style={{
            marginTop: vertical ? 48 : 36,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: vertical ? 20 : 16,
            opacity: prog(frame, CARD + 56, 16, E.outCubic),
          }}
        >
          <span style={{fontFamily: fam('ZL-Song'), fontSize: vertical ? 26 : 22, color: hexA(P.ink, 0.72), letterSpacing: 6}}>出品</span>
          <Img src={staticFile('brand/logo.png')} style={{height: vertical ? 58 : 48}} />
        </div>
      </div>
      <AbsoluteFill style={{background: '#000', opacity: black}} />
    </Paper>
  );
};
