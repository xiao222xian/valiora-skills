import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {CARD_OUT, CHAPTERS, CUES, ERA_CHAPTERS, chapterDur, chapterEnd, AXIS} from '../timeline';
import {E, clamp01, hexA, lerp, prog} from '../lib/anim';
import {BODY, MONO, SERIF, fam} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const RULER_START = ERA_CHAPTERS[0].start;
const RULER_END = chapterEnd(CHAPTERS.indexOf(ERA_CHAPTERS[ERA_CHAPTERS.length - 1]));

export const currentChapterIndex = (frame: number) => {
  let idx = 0;
  CHAPTERS.forEach((c, i) => {
    if (frame >= c.start) idx = i;
  });
  return idx;
};

/** HUD ink and the plate it sits on at an absolute frame: the chapter palette, or its hudAlt after
 * `from`; the switch happens halfway through the incoming transition. Subtitles follow the same ink. */
export const hudInkAt = (frame: number) => {
  const i = currentChapterIndex(frame);
  const c = CHAPTERS[i];
  const swap = frame - c.start < c.transitionFrames / 2 && i > 1 ? CHAPTERS[i - 1] : c;
  const alt = swap.hudAlt && frame - swap.start >= swap.hudAlt.from ? swap.hudAlt : null;
  return {ink: alt ? alt.color : swap.palette.hud, plate: alt ? alt.bg : swap.palette.bg};
};

/** Year shown by the playhead: piecewise through the chapter's axisKeys, so it holds on
 * the year the picture is showing and eases between events. */
export const axisAt = (frame: number) => {
  const i = currentChapterIndex(frame);
  const c = CHAPTERS[i];
  const lf = frame - c.start;
  // default keys end on a 10000 sentinel meaning "the end of this chapter"
  const keys = c.axisKeys.map(([f, y]): [number, number] => [f >= 10000 ? chapterDur(i) : f, y]);
  if (lf <= keys[0][0]) return keys[0][1];
  for (let k = 1; k < keys.length; k++) {
    const [f1, y1] = keys[k];
    const [f0, y0] = keys[k - 1];
    if (lf <= f1) return lerp(y0, y1, E.inOutSine(clamp01((lf - f0) / Math.max(1, f1 - f0))));
  }
  return keys[keys.length - 1][1];
};

/** The ruler the opening brush stroke turns into: one segment per era, width ∝ screen time
 * (not ∝ years — the outro credits say so). */
export const rulerGeometry = (W: number, H: number, vertical: boolean) => {
  const x0 = vertical ? 70 : 96;
  const x1 = W - (vertical ? 70 : 96);
  const y = vertical ? H - 300 : H - 66;
  const total = RULER_END - RULER_START;
  const segs = ERA_CHAPTERS.map((c) => {
    const i = CHAPTERS.indexOf(c);
    const a = x0 + ((c.start - RULER_START) / total) * (x1 - x0);
    const b = x0 + ((chapterEnd(i) - RULER_START) / total) * (x1 - x0);
    return {c, a, b};
  });
  const xAt = (frame: number) => x0 + clamp01((frame - RULER_START) / total) * (x1 - x0);
  return {x0, x1, y, segs, xAt};
};

export const HUD: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const i = currentChapterIndex(frame);
  const c = CHAPTERS[i];
  const {x0, x1, y, segs, xAt} = rulerGeometry(W, H, vertical);

  // visible from the end of the opening (the stroke lands on the ruler) until the music's
  // final ring-out, where the outro folds the ruler back into a brush stroke
  const show = Math.min(prog(frame, RULER_START - 2, 4, E.linear), 1 - prog(frame, CUES.outroDecay, 14, E.inCubic));
  if (show <= 0) return null;

  // switch HUD ink halfway through the incoming transition
  const {ink, plate} = hudInkAt(frame);
  const px = xAt(frame);
  const yr = axisAt(frame);
  // the chapter card (components/ChapterCard) holds the number and name large first; the header takes over as it leaves
  const labelIn = prog(frame - c.start, CARD_OUT, 12, E.linear);
  // readout 20 and segment names 17 (16:9) sit above the floors in lib/layout TYPE_FLOOR (16 / 15)
  const labelSize = vertical ? 1.15 : 1;
  const isEra = ERA_CHAPTERS.includes(c);


  // soft plates behind the header and ruler so busy pictures never swallow the HUD
  const scrimTop = vertical ? 300 : 128;
  const scrimBottom = vertical ? 420 : 150;

  return (
    <AbsoluteFill style={{opacity: show, pointerEvents: 'none'}}>
      {isEra && (
        <>
          <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: scrimTop, background: `linear-gradient(to bottom, ${hexA(plate, 0.72)}, ${hexA(plate, 0)})`, opacity: labelIn}} />
          <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: scrimBottom, background: `linear-gradient(to top, ${hexA(plate, 0.78)}, ${hexA(plate, 0)})`}} />
        </>
      )}
      {/* ruler */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <line x1={x0} x2={x1} y1={y} y2={y} stroke={hexA(ink, 0.32)} strokeWidth={1.5} />
        {segs.map(({c: sc, a, b}) => {
          const done = frame >= sc.start;
          const end = Math.min(b, px);
          return (
            <g key={sc.id}>
              <line x1={a} x2={a} y1={y - 5} y2={y + 5} stroke={hexA(ink, 0.55)} strokeWidth={1.2} />
              {done && end > a && <line x1={a} x2={end} y1={y} y2={y} stroke={sc.palette.ruler} strokeWidth={4} strokeLinecap="butt" />}
            </g>
          );
        })}
        <line x1={x1} x2={x1} y1={y - 5} y2={y + 5} stroke={hexA(ink, 0.55)} strokeWidth={1.2} />
        <line x1={px} x2={px} y1={y - 16} y2={y + 9} stroke={ink} strokeWidth={1.6} />
        <circle cx={px} cy={y} r={4.5} fill={c.palette.ruler} stroke={ink} strokeWidth={1.2} />
      </svg>
      {segs.map(({c: sc, a, b}) => {
        const active = sc.id === c.id;
        const past = frame >= chapterEnd(CHAPTERS.indexOf(sc));
        return (
          <div
            key={sc.id}
            style={{
              position: 'absolute',
              left: a,
              width: b - a,
              top: y + 12,
              textAlign: 'center',
              fontFamily: BODY,
              fontSize: (vertical ? 18 : 17) * (active ? 1.12 : 1),
              color: ink,
              opacity: active ? 1 : past ? 0.6 : 0.45,
              whiteSpace: 'nowrap',
              letterSpacing: 1,
              display: vertical && !active ? 'none' : undefined,
            }}
          >
            {sc.short}
          </div>
        );
      })}
      <div
        style={{
          position: 'absolute',
          left: Math.min(Math.max(px - 110, x0 - 40), x1 - 180),
          width: 220,
          top: y - 46,
          textAlign: 'center',
          fontFamily: MONO,
          fontSize: 20 * labelSize,
          color: ink,
          letterSpacing: 0.5,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {AXIS.format(yr)}
      </div>

      {/* chapter header */}
      {isEra && (
        <>
          <div
            style={{
              position: 'absolute',
              left: vertical ? 70 : 96,
              top: vertical ? 172 : 50,
              color: ink,
              opacity: labelIn,
              display: 'flex',
              alignItems: 'baseline',
              gap: 18,
              whiteSpace: 'nowrap',
            }}
          >
            <span style={{fontFamily: SERIF, fontSize: 30 * labelSize, fontWeight: 500, letterSpacing: 1}}>{String(c.no).padStart(2, '0')}</span>
            <span style={{fontFamily: MONO, fontSize: 15 * labelSize, opacity: 0.6}}>{`/ ${ERA_CHAPTERS.length}`}</span>
            <span style={{fontFamily: fam(c.font), fontSize: 30 * labelSize, letterSpacing: 2}}>{c.era}</span>
            <span style={{fontFamily: MONO, fontSize: 16 * labelSize, opacity: 0.75, letterSpacing: 0.5}}>{c.yearsLabel}</span>
          </div>

        </>
      )}
    </AbsoluteFill>
  );
};
