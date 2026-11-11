import {createContext, useContext} from 'react';
import {useVideoConfig} from 'remotion';

// Shared layout constants. Vertical (WeChat Channels 1080x1920) keeps critical content out of
// the top 160 px (status bar / notch / app chrome) and bottom 260 px (caption, actions).

/** Lets a parent render a scene at another size, e.g. the outro's 16:9 thumbnails (Freeze + scene)
 * inside a 9:16 frame. Only scenes that read their size from useLayout() follow it. */
export const LayoutOverride = createContext<{W: number; H: number} | null>(null);

export const useLayout = () => {
  const cfg = useVideoConfig();
  const o = useContext(LayoutOverride);
  const W = o ? o.W : cfg.width;
  const H = o ? o.H : cfg.height;
  const vertical = H > W;
  const safe = vertical ? {top: 160, bottom: 260, left: 46, right: 46} : {top: 56, bottom: 56, left: 96, right: 96};
  // stage = the region scenes compose into (vertical: under the HUD header, above the ruler)
  const stage = vertical
    ? {x: 0, y: 330, w: W, h: H - 330 - 380}
    : {x: 0, y: 0, w: W, h: H};
  // vertical: content must end above the HUD year counter (~H-346) and ruler (H-300)
  const stageBottom = stage.y + stage.h;
  // text scale against the 1920x1080 floors below: the short side over 1080; 9:16 is watched on a phone, so x1.15
  const ts = (Math.min(W, H) / 1080) * (vertical ? 1.15 : 1);
  return {W, H, vertical, safe, stage, stageBottom, cx: W / 2, cy: H / 2, ts};
};

/** Text size floors at 1920x1080, in px; multiply by `ts` from useLayout() for other sizes. Text the viewer
 * must take in at a glance never goes below these (a film with footage and heavy animation, 2026-10-12:
 * "文字部分太小导致不够一眼 get 信息"). The corner annotation is the one deliberate exception: it stays small
 * (the user's standing preference, Profile records.annotation). */
export const TYPE_FLOOR = {
  subtitleZh: 46,
  subtitleEn: 27,
  callout: 22, // leader-line label; the leader is LEADER_W wide
  data: 26, // data blocks, checklists, lists, tick labels
  hudReadout: 16,
  hudSegment: 15,
  bigNumber: 120, // big figures 120-160; the chapter card's name uses the same size
  annotation: 14, // corner 示意 / source note: stays this small on purpose
} as const;
export const LEADER_W = 1.5;

export type Layout = ReturnType<typeof useLayout>;
