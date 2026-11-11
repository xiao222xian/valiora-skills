// One source of truth for the film's structure: the 3D example film (a gearbox in four shots). Same exports as the
// motion-media-creator starter's timeline, so its HUD, chapter cards, covers, preview harness and tools read it
// unchanged. Every start sits on the 15-frame beat grid and every chapter (opening and outro included) runs at
// least 330 frames, so `node tools/chapters.mjs` passes. Node imports this file: keep it free of imports.

export const TITLE = '齿轮箱';
export const SUBTITLE = '从零件到批量';

export const SUBTITLE_LANGS: 'zh' | 'zh+en' = 'zh';

export const FPS = 30;
export const TOTAL_FRAMES = 2100; // 70.0 s
export const BEAT = 15; // frames per beat at 120 BPM
export const CARD_OUT = 50;

export type TransitionKind = 'none' | 'ink' | 'slats' | 'flash' | 'wipe' | 'wipeRight' | 'shards' | 'iris' | 'bloom' | 'wave' | 'dipBlack' | 'white';

export type Palette = {
  bg: string;
  ink: string;
  accent: string;
  hud: string;
  ruler: string;
};

export type AxisKey = [number, number];

export type Chapter = {
  id: string;
  no: number; // 0 = opening, last = outro
  era: string; // display name
  short: string; // ruler label
  yearsLabel: string; // the header's small mono line (here the step's English name)
  years: [number, number]; // axis range of the chapter (here the step number)
  axisKeys: AxisKey[];
  motif: string;
  font: string;
  palette: Palette;
  start: number;
  transition: TransitionKind;
  transitionFrames: number;
  hudAlt?: {from: number; color: string; bg: string};
};

// one dark product-film palette; chapters differ by light, not by colour plates (the 3D art direction)
const INK = '#F2EFE8';
const AMBER = '#E3B04B';
const dark = (bg: string): Palette => ({bg, ink: INK, accent: AMBER, hud: '#d9d5cc', ruler: AMBER});

const C = (c: Omit<Chapter, 'transitionFrames' | 'axisKeys'> & {transitionFrames?: number; axisKeys?: AxisKey[]}): Chapter => ({
  transitionFrames: 0,
  axisKeys: [
    [0, c.years[0]],
    [10000, c.years[1]],
  ],
  ...c,
});

// Transitions are editing cuts (the 3D art direction): hard cut, dip to black, dissolve, a white flash. The opening's
// light line becomes the HUD ruler at the first frame of chapter 01, so that join is a cut. A dissolve is 'none' with
// transitionFrames: Main keeps the previous chapter playing that long and the chapter fades itself in (DissolveIn).
export const CHAPTERS: Chapter[] = [
  C({id: 'opening', no: 0, era: '序', short: '序', yearsLabel: '', years: [0, 0], motif: '', font: 'OFL-SerifHeavy', palette: dark('#08090a'), start: 0, transition: 'none'}),
  C({id: 'explode', no: 1, era: '拆解', short: '拆解', yearsLabel: 'EXPLODED VIEW', years: [1, 1], motif: '箱体、轴、齿轮与轴承', font: 'OFL-Serif', palette: dark('#0a0b0d'), start: 330, transition: 'none'}),
  C({id: 'materials', no: 2, era: '材料', short: '材料', yearsLabel: 'MATERIALS', years: [2, 2], motif: '十种表面', font: 'OFL-Serif', palette: dark('#0b0b0c'), start: 690, transition: 'dipBlack', transitionFrames: 10}),
  C({id: 'pickplace', no: 3, era: '取放', short: '取放', yearsLabel: 'PICK AND PLACE', years: [3, 3], motif: '机械臂装入大齿轮', font: 'OFL-Serif', palette: dark('#0c0c0b'), start: 1050, transition: 'none', transitionFrames: 15}),
  C({id: 'batch', no: 4, era: '批量', short: '批量', yearsLabel: 'BATCH', years: [4, 4], motif: '一千二百台', font: 'OFL-Serif', palette: dark('#0a0b0c'), start: 1410, transition: 'flash', transitionFrames: 8}),
  C({id: 'outro', no: 5, era: '片名', short: '片名', yearsLabel: '', years: [4, 4], motif: '', font: 'OFL-SerifHeavy', palette: dark('#08090a'), start: 1770, transition: 'dipBlack', transitionFrames: 12}),
];

// The base's Reveal and Main switch over every kind, so the type keeps the masked ones (ink, slats, wipe, shards,
// iris, bloom, wave); a 3D film does not use them, and this refuses them wherever the timeline loads.
const CUTS: TransitionKind[] = ['none', 'dipBlack', 'white', 'flash'];
const masked = CHAPTERS.filter((c) => !CUTS.includes(c.transition));
if (masked.length) throw new Error(`3D chapters join by cuts (${CUTS.join(', ')}): ${masked.map((c) => `${c.id} '${c.transition}'`).join(', ')}`);

export const chapterEnd = (i: number) => (i + 1 < CHAPTERS.length ? CHAPTERS[i + 1].start : TOTAL_FRAMES);
export const chapterDur = (i: number) => chapterEnd(i) - CHAPTERS[i].start;
export const ERA_CHAPTERS = CHAPTERS.slice(1, -1);

// Music cues (absolute frames). outroDecay: the title card arrives and the HUD fades out.
export const CUES = {
  explodeHit: 330 + 90, // the first bolt lifts on a downbeat
  seatHit: 1050 + 250, // the gear seats on its spindle
  outroDecay: 1770,
};

/** The progress axis the HUD tracks: the step number, as on a process sheet. */
export const AXIS = {kind: 'step' as const, format: (v: number) => `工序 ${String(Math.round(v)).padStart(2, '0')} / ${String(ERA_CHAPTERS.length).padStart(2, '0')}`};
