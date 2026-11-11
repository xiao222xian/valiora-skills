import React from 'react';
import {useCurrentFrame} from 'remotion';
import {CARD_OUT, CHAPTERS, ERA_CHAPTERS} from '../timeline';
import {E, hexA, prog} from '../lib/anim';
import {MONO, SERIF, fam} from '../lib/fonts';
import {TYPE_FLOOR, useLayout} from '../lib/layout';
import {currentChapterIndex, hudInkAt} from './HUD';

/** Rough rendered width of a line in em: CJK and full-width forms count 1, everything else 0.6. */
const ems = (t: string) => Array.from(t).reduce((s, ch) => s + (/[⺀-￿]/.test(ch) ? 1 : 0.6), 0);

/** Chapter opener: the chapter's number and name, large, at the HUD header's anchor (top left), from the
 * middle of the incoming transition until CARD_OUT (~1.7 s); then it gives way to the HUD's small header,
 * which fades in as this fades out. The card is the header, large: the scene does not repeat the name. */
export const ChapterCard: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, vertical, ts} = useLayout();
  const i = currentChapterIndex(frame);
  const c = CHAPTERS[i];
  if (!ERA_CHAPTERS.includes(c)) return null;
  const lf = frame - c.start;
  const pIn = prog(lf, Math.ceil(c.transitionFrames / 2), 8, E.outCubic);
  const pOut = prog(lf, CARD_OUT, 10, E.inCubic);
  const o = Math.min(pIn, 1 - pOut);
  if (o <= 0) return null;
  const {ink, plate} = hudInkAt(frame);
  const k = vertical ? 1.15 : 1;
  const left = vertical ? 70 : 96;
  // the name stays on one line: a long one shrinks to the frame width instead of wrapping
  const spacing = 8 * k;
  const nameSize = Math.min(TYPE_FLOOR.bigNumber * ts, (W - 2 * left - spacing * Array.from(c.era).length) / (ems(c.era) * 1.04));
  const no = String(c.no).padStart(2, '0');
  // scenes keep this corner clear of their own text until the card has left (CARD_OUT + 10)
  return (
    <>
      {/* a soft plate in the chapter's own background colour keeps the card legible over busy pictures */}
      <div style={{position: 'absolute', inset: 0, opacity: o * 0.9, background: `radial-gradient(ellipse at 0% 0%, ${hexA(plate, 0.7)} 0%, ${hexA(plate, 0.4)} 28%, ${hexA(plate, 0)} 52%)`, pointerEvents: 'none'}} />
      <div
        style={{
          position: 'absolute',
          // the HUD header's anchor: the card is the header, large, before it settles
          left,
          top: vertical ? 172 : 50,
          color: ink,
          opacity: o,
          transform: `translateY(${(1 - pIn) * 10 - pOut * 6}px)`,
          pointerEvents: 'none',
        }}
      >
        {/* the HUD header's own order: number, "/ total", name, axis range */}
        <div style={{display: 'flex', alignItems: 'center', gap: 14 * k}}>
          <span style={{fontFamily: SERIF, fontSize: 34 * k, fontWeight: 500, letterSpacing: 2, fontVariantNumeric: 'tabular-nums'}}>{no}</span>
          <span style={{fontFamily: MONO, fontSize: TYPE_FLOOR.callout * ts, opacity: 0.7, letterSpacing: 2}}>{`/ ${ERA_CHAPTERS.length}`}</span>
          <span style={{display: 'inline-block', width: 56 * k, height: 2, marginLeft: 6 * k, background: ink, opacity: 0.8}} />
        </div>
        <div style={{fontFamily: fam(c.font), fontSize: nameSize, lineHeight: 1.05, letterSpacing: spacing, marginTop: 6 * k, whiteSpace: 'nowrap'}}>{c.era}</div>
        {c.yearsLabel && <div style={{fontFamily: MONO, fontSize: 24 * k, letterSpacing: '0.2em', opacity: 0.75, marginTop: 8 * k}}>{c.yearsLabel}</div>}
      </div>
    </>
  );
};
