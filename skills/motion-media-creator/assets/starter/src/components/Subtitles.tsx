import React from 'react';
import {useCurrentFrame} from 'remotion';
import {SUBTITLES} from '../narration';
import {SUBTITLE_LANGS} from '../timeline';
import {E, prog} from '../lib/anim';
import {SERIF, SUBTITLE_FONT} from '../lib/fonts';
import {TYPE_FLOOR, useLayout} from '../lib/layout';
import {hudInkAt} from './HUD';

/** With a voice-over, a scene's lower-left body captions give way to these subtitles (same facts,
 * said aloud): render such captions only `if (!NARRATED)`. Titles, the HUD and the small 示意 /
 * source notes stay on screen. */
export const NARRATED = SUBTITLES.length > 0;

/** Perceived brightness (0-1) of a #rgb / #rrggbb colour. */
const brightness = (hex: string) => {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return (0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) / 255;
};

/** Subtitles of the voice-over: Chinese, or Chinese over English when SUBTITLE_LANGS is 'zh+en'.
 * Centred above the progress axis (16:9: bottom edge at H-128, clear of the moving readout; 9:16: at
 * the foot of the stage band). On bright pictures the text takes the HUD ink; elsewhere it is light
 * with a soft shadow. */
export const Subtitles: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical, stageBottom, ts} = useLayout();
  const line = SUBTITLES.find((s) => frame >= s.from && frame < s.to);
  if (!line) return null;
  const o = Math.min(prog(frame, line.from, 5, E.linear), 1 - prog(frame, line.to - 5, 5, E.linear));
  const {ink, plate} = hudInkAt(frame);
  const bright = brightness(plate) > 0.5;
  const color = bright ? ink : 'rgba(246,243,236,0.96)';
  const shadow = bright ? 'none' : '0 1px 3px rgba(0,0,0,0.65), 0 2px 18px rgba(0,0,0,0.55)';
  // an empty English line shows nothing (`en: ''` in a zh-only film)
  const en = SUBTITLE_LANGS === 'zh+en' && line.en ? line.en : '';
  return (
    <div
      style={{
        position: 'absolute',
        left: vertical ? 60 : 160,
        width: W - (vertical ? 120 : 320),
        bottom: vertical ? H - stageBottom + 40 : 128,
        textAlign: 'center',
        opacity: o,
        color,
        textShadow: shadow,
        pointerEvents: 'none',
      }}
    >
      {/* 16:9: 46 px Chinese, 27 px English (the floors); 9:16 scales them by ts */}
      <div style={{fontFamily: SUBTITLE_FONT, fontSize: TYPE_FLOOR.subtitleZh * ts, lineHeight: 1.35, letterSpacing: 1}}>{line.zh}</div>
      {en && <div style={{fontFamily: SERIF, fontSize: TYPE_FLOOR.subtitleEn * ts, lineHeight: 1.3, marginTop: 6, opacity: 0.88, letterSpacing: 0.2}}>{en}</div>}
    </div>
  );
};
