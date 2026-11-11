import React from 'react';
import {useCurrentFrame} from 'remotion';
import {E, hexA, prog} from '../lib/anim';
import {MONO} from '../lib/fonts';
import {TYPE_FLOOR, useLayout} from '../lib/layout';
import {MEDIA, type MediaItem, type MediaKey} from '../media';

/** What a shot is: our 3D reconstruction, real material about the subject, real material of the same process
 * elsewhere, or a generated picture (used only when the user chose one). */
export type ShotKind = 'model' | 'archival' | 'stock' | 'ai';

/** The corner note's text. `note || …`, not `??`: an empty string is a value, and on the first 3D film a shot table
 * with note '' rendered an empty corner instead of the default (2026-10-12). Archival notes take the credit from the
 * media catalogue (src/media.ts), the same record the end credits read, so the two cannot disagree. */
export const shotNoteText = (kind: ShotKind, note?: string, key?: MediaKey): string => {
  const credit = key ? (MEDIA[key] as MediaItem).credit : '';
  switch (kind) {
    case 'model':
      return note || '示意';
    case 'archival':
      return ['资料', note, credit].filter(Boolean).join(' · ');
    case 'stock':
      return ['资料 · 同类工序', note, credit].filter(Boolean).join(' · ');
    case 'ai':
      return '生成画面 · 示意';
  }
};

/** The small fixed note every shot carries: 「示意」 (or what the reconstruction stands for: 「车型为示意」,
 * 「慢放 · 示意」) on 3D shots, 「资料 · 说明 · 作者 · 许可」 on archival ones. 16:9 top right, on the HUD header's line;
 * 9:16 at the foot of the stage band. 14 px at 1920x1080 on purpose (TYPE_FLOOR.annotation: the user's standing
 * preference keeps these notes small). Mount one per shot, in the shot's Sequence. */
export const ShotNote: React.FC<{kind?: ShotKind; note?: string; media?: MediaKey; at?: number; out?: number; ink?: string}> = ({
  kind = 'model',
  note,
  media,
  at = 0,
  out,
  ink = '#F2EFE8',
}) => {
  const frame = useCurrentFrame();
  const {W, vertical, stageBottom, ts} = useLayout();
  const o = Math.min(prog(frame, at, 8, E.linear), out === undefined ? 1 : 1 - prog(frame, out - 8, 8, E.linear));
  if (o <= 0) return null;
  const pos: React.CSSProperties = vertical ? {left: 70, top: stageBottom - 44} : {right: 96, top: 62, textAlign: 'right'};
  return (
    <div style={{position: 'absolute', ...pos, maxWidth: W * 0.4, fontFamily: MONO, fontSize: TYPE_FLOOR.annotation * ts, letterSpacing: 1, color: hexA(ink, 0.6), opacity: o, whiteSpace: 'nowrap', pointerEvents: 'none'}}>
      {shotNoteText(kind, note, media)}
    </div>
  );
};
