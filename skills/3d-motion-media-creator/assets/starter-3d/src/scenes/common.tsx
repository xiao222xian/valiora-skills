import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Line} from '../components/Type';
import {NARRATED} from '../components/Subtitles';
import {E, hexA, prog} from '../lib/anim';
import {useLayout} from '../lib/layout';
import type {CamSpec} from '../three/camera';

/** Camera keyframes per aspect: 9:16 gets its own framing, never a crop of the 16:9 shot. */
export type Cams = {h: CamSpec[]; v: CamSpec[]};
export const useCams = (cams: Cams) => cams[useLayout().vertical ? 'v' : 'h'];

/** Lower-left body caption, at most three lines of what the picture shows. Gives way to the voice-over's subtitles
 * when the film is narrated (the same facts are said aloud). */
export const Caption: React.FC<{lines: string[]; at: number; out?: number; ink?: string}> = ({lines, at, out, ink = '#F2EFE8'}) => {
  const {H, vertical, stageBottom, ts} = useLayout();
  if (NARRATED) return null;
  return (
    <div style={{position: 'absolute', left: vertical ? 70 : 96, bottom: vertical ? H - stageBottom + 90 : 176, textShadow: '0 1px 12px rgba(0,0,0,0.6)'}}>
      {lines.map((t, i) => (
        <Line key={i} at={at + i * 4} out={out} color={hexA(ink, 0.92)} size={34 * ts}>
          {t}
        </Line>
      ))}
    </div>
  );
};

/** Where a callout label may sit: in the stage band, above the subtitle band (16:9 y 845-952 at 1080, base
 * style-grammar「字号下限」). A label pinned to a 3D point with project() moves with the camera, and on the first 3D
 * film it slid into the subtitles during a pull-back (2026-10-12, v0.3): clamp its y, the leader still reaches the
 * point. Check whole camera moves on a sheet, not on stills. */
export const useLabelBand = () => {
  const {vertical, stage, stageBottom, ts} = useLayout();
  const [top, bottom] = vertical ? [stage.y + 40 * ts, stageBottom - 40 - 150 * ts] : [150 * ts, 825 * ts];
  return {top, bottom, y: (v: number) => Math.min(bottom, Math.max(top, v))};
};

/** A dissolve into a chapter: its timeline entry is transition 'none' with transitionFrames, so the base Main keeps the
 * previous chapter playing underneath for that long (two Stages, the most a transition may mount), and this fades the
 * chapter in over the same frames. The base Reveal has no dissolve. */
export const DissolveIn: React.FC<{frames: number; children: React.ReactNode}> = ({frames, children}) => {
  const o = prog(useCurrentFrame(), 0, frames, E.inOutSine);
  return <AbsoluteFill style={{opacity: o}}>{children}</AbsoluteFill>;
};
