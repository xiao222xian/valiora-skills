import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {MEDIA, type MediaKey, type MediaItem} from '../media';
import {lerp} from '../lib/anim';
import {useLayout} from '../lib/layout';

// Real photographs and footage are shown one of two ways (style-grammar-3d「资料」): a full-frame window here, or a
// physical print inside a 3D scene (useTexture(mediaUrl(key)) on a thin box). Full frame: cover-fit, a slow constant
// push of at most 6 % per 3 s, nothing else moves. 9:16: a landscape source sits in a full-width 1080x608 window in
// the middle of the stage band ('box'); satellite views and skylines may fill the frame and pan slowly ('fill').
// Every item comes from src/media.ts (tools/conform.py), so the corner note (ShotNote kind="archival") and the end
// credits read the same record.

export const media = (key: MediaKey): MediaItem => MEDIA[key] as MediaItem;
export const mediaUrl = (key: MediaKey) => staticFile(media(key).file);

type Common = {
  media: MediaKey;
  /** frames this window is on screen; sets the push rate */
  dur: number;
  /** start and end scale; keep (end - start) <= 0.06 per 90 frames */
  push?: [number, number];
  /** point of the source kept still while pushing / cropping, 0..1 */
  focus?: [number, number];
  /** focus at the end of the window (a slow pan); defaults to focus */
  focusTo?: [number, number];
  vertical?: 'box' | 'fill';
  fit?: 'cover' | 'contain';
  bg?: string;
  /** 0..1 brightness, e.g. 0.3 behind a quote */
  dim?: number;
};

const Window: React.FC<Common & {children: (style: React.CSSProperties) => React.ReactNode}> = ({
  media: key,
  dur,
  push = [1, 1.03],
  focus = [0.5, 0.5],
  focusTo,
  vertical: vmode = 'box',
  fit = 'cover',
  bg = '#0b0b0c',
  dim = 1,
  children,
}) => {
  const frame = useCurrentFrame();
  const {W, vertical, stage} = useLayout();
  const t = Math.min(1, Math.max(0, frame / Math.max(1, dur)));
  const s = lerp(push[0], push[1], t);
  const f = focusTo ? [lerp(focus[0], focusTo[0], t), lerp(focus[1], focusTo[1], t)] : focus;
  const boxed = vertical && vmode === 'box';
  const box = boxed ? {left: 0, top: stage.y + (stage.h - 608) / 2, width: W, height: 608} : {left: 0, top: 0, width: '100%', height: '100%'};
  const style: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: fit,
    objectPosition: `${f[0] * 100}% ${f[1] * 100}%`,
    transform: `scale(${s})`,
    transformOrigin: `${f[0] * 100}% ${f[1] * 100}%`,
    filter: dim < 1 ? `brightness(${dim})` : undefined,
  };
  return (
    <AbsoluteFill style={{background: bg}}>
      <div style={{position: 'absolute', overflow: 'hidden', ...box}} data-media={media(key).file}>
        {children(style)}
      </div>
    </AbsoluteFill>
  );
};

/** A still photograph in a full-frame window. */
export const Photo: React.FC<Common> = (p) => <Window {...p}>{(style) => <Img src={mediaUrl(p.media)} style={style} />}</Window>;

/** Footage in a full-frame window, muted (the film's sound is one premixed track); `from` in seconds into the clip. */
export const Footage: React.FC<Common & {from?: number; rate?: number}> = ({from = 0, rate = 1, ...p}) => {
  const {fps} = useVideoConfig();
  return <Window {...p}>{(style) => <OffthreadVideo src={mediaUrl(p.media)} muted trimBefore={Math.round(from * fps)} playbackRate={rate} style={style} />}</Window>;
};
