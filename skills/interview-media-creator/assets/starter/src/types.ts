export type Face = { cx: number; cy: number; w: number } | null;
export type Piece = { src: [number, number]; start: number; frames: number; file?: string; face?: Face };

export type Item =
  | { kind: 'speech'; id: string; part: string; speaker: 'G' | 'Q'; start: number; frames: number; pieces: Piece[]; text: string }
  | { kind: 'chapter'; chapter: string; index: number; title: string; start: number; frames: number }
  | { kind: 'title'; id: string; start: number; frames: number; src: [number, number] }
  | { kind: 'outro'; start: number; frames: number };

// en: the English line under the Chinese one (bilingual captions; work/subs-en.json attached by scripts/subs_en.py)
export type Sub = { seg: string; speaker: 'G' | 'Q'; part: string; text: string; start: number; end: number; hl?: string | null; en?: string };

// equation steps: the step with op '=' is highlighted; hl highlights the final step of an arrow sequence without '='
export type Callout =
  | { kind: 'equation'; start: number; end: number; steps: { at: number; text: string; op: string; hl?: boolean }[] }
  | { kind: 'stamp'; start: number; end: number; text: string }
  | { kind: 'number'; start: number; end: number; value: string; unit: string; label: string }
  | { kind: 'arrow'; start: number; end: number; from: string; to: string; label: string };

// ref: reference material for a concept someone names (show, product, technology): the picture with its name,
// a one-line description and the image credit (licence attribution); ar = image width / height
// video: img is a full-screen B-roll clip (1080×1920, e.g. the guest's own product footage) played from `from` seconds
// album: the guest's own photos dropped one by one onto a pile of cards; ar = width / height of each photo, focus =
// centre of its slow push-in; decorate.py copies the first photo into img
export type Insert = { kind: 'photo'; img: string; start: number; end: number; focus?: [number, number]; flash?: boolean;
  video?: boolean; from?: number; ref?: { name: string; sub?: string; desc: string; credit: string; ar: number };
  album?: { img: string; ar: number; focus?: [number, number] }[] };

export type Timeline = {
  version: string;
  fps: number;
  frames: number;
  chapters: { id: string; title: string; short?: string; basis?: string }[];
  items: Item[];
  callouts?: Callout[];
  inserts?: Insert[];
  nametag?: { start: number; end: number; name: string; en?: string; desc: string };
  location?: { start: number; end: number; text: string };
  title?: { lines: string[]; byline?: string };
  logo_frames?: number;
  media: { video: string; audio: string | null };
};

export type CoverSpec = {
  base: { img: string; top: number }; // 1080-wide frame, shifted up by `top` px inside the 3:4 canvas
  series: string; // series label on the bottom strip, next to the official logo
  wide?: { img: string }; // optional landscape base for the 4:3 / 16:9 cards; otherwise base.img is reused
  variants: Record<string, { small: string[]; big: string[]; tail?: string[]; bigTop?: number }>;
};
