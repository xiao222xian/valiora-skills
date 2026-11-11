// One source of truth for the film's structure. Chapter starts are snapped to the chosen
// BGM (Lyria candidate A, 120 BPM, beat phase 0.023 s): see audio/snaps.json and
// the section analysis in audio/structure.json. Changing a start here re-times
// picture, HUD ruler and year counter together.

// Film title and tagline: opening, outro card and covers all read these.
export const TITLE = '字里中国';
export const SUBTITLE = '从陶纹，到像素';

// Subtitles of the voice-over (src/narration.ts): Chinese only by default; 'zh+en' adds an English
// line under each Chinese one, only when the user asks for bilingual subtitles.
export const SUBTITLE_LANGS: 'zh' | 'zh+en' = 'zh';

export const FPS = 30;
export const TOTAL_FRAMES = 5265; // 175.5 s; music is 175.41 s
export const BEAT = 15; // frames per beat at 120 BPM
// Each chapter opens on its card (components/ChapterCard: number and name, large, at the HUD header's
// anchor); at this local frame (~1.7 s) the card leaves and the HUD's small header fades in.
export const CARD_OUT = 50;

export type TransitionKind =
  | 'none'
  | 'ink'
  | 'slats'
  | 'flash'
  | 'wipe'
  | 'wipeRight'
  | 'shards'
  | 'iris'
  | 'bloom'
  | 'wave'
  | 'dipBlack'
  | 'white';

export type Palette = {
  bg: string;
  ink: string;
  accent: string;
  hud: string; // HUD text colour on this chapter's background
  ruler: string; // this chapter's colour on the bottom ruler
};

/** [local frame, year]: the HUD year counter interpolates between these, holding on
 * the years the picture is showing. Negative = BCE. */
export type AxisKey = [number, number];

export type Chapter = {
  id: string;
  no: number; // 0 = opening, 14 = outro, 1..13 = eras
  era: string; // display name
  short: string; // ruler label
  yearsLabel: string;
  years: [number, number]; // nominal range of the chapter
  axisKeys: AxisKey[];
  motif: string; // outro recap caption: what the chapter shows (content only)
  font: string; // headline typeface for this era
  palette: Palette;
  start: number;
  transition: TransitionKind;
  transitionFrames: number;
  hudAlt?: {from: number; color: string; bg: string}; // local frame after which the HUD switches ink
};

const C = (c: Omit<Chapter, 'transitionFrames' | 'axisKeys'> & {transitionFrames?: number; axisKeys?: AxisKey[]}): Chapter => ({
  transitionFrames: 18,
  axisKeys: [
    [0, c.years[0]],
    [10000, c.years[1]],
  ],
  ...c,
});

// Near-instant step between two years at local frame f (used where the picture cuts).
const step = (f: number, from: number, to: number): AxisKey[] => [
  [f - 1, from],
  [f, to],
];

export const MODERN_EVENTS: {y: number; t: string; sub?: string}[] = [
  {y: 1861, t: '洋务运动'},
  {y: 1894, t: '甲午战争'},
  {y: 1898, t: '戊戌变法'},
  {y: 1911, t: '辛亥革命'},
  {y: 1912, t: '中华民国成立', sub: '清帝退位，两千多年帝制终结'},
  {y: 1919, t: '五四运动'},
  {y: 1921, t: '中国共产党成立'},
  {y: 1931, t: '九一八事变'},
  {y: 1937, t: '全面抗战'},
  {y: 1945, t: '抗战胜利'},
  {y: 1949, t: '中华人民共和国成立'},
];

// Sample timing from the first film, older than the 11 s chapter floor (references/pipeline.md, section 1): qing and
// the outro display 9 s, opening and today 10 s, so `node tools/chapters.mjs` exits 1 on this table (2026-10-12).
// It stays as it was because the sample scenes, CUES and music were cut to it. A new film re-times every chapter
// (opening and outro included) to at least 22 beats (330 frames), every start on the same 15-frame grid.
export const CHAPTERS: Chapter[] = [
  C({
    id: 'opening', no: 0, era: '序', short: '序', yearsLabel: '', years: [-10000, -10000],
    motif: '',
    font: 'ZL-KaiBlack',
    palette: {bg: '#EEE7D8', ink: '#141210', accent: '#B8322A', hud: '#3a342c', ruler: '#141210'},
    start: 0, transition: 'none', transitionFrames: 0,
  }),
  C({
    id: 'neolithic', no: 1, era: '新石器时代', short: '新石器', yearsLabel: '约前 10000 — 前 2070', years: [-10000, -2070],
    motif: '彩陶',
    font: 'ZL-SongBlack',
    palette: {bg: '#E4CFAC', ink: '#2B1D14', accent: '#B5542E', hud: '#4a3424', ruler: '#B5542E'},
    start: 301, transition: 'none', transitionFrames: 0,
  }),
  C({
    id: 'shang', no: 2, era: '夏 · 商 · 西周', short: '夏商西周', yearsLabel: '约前 2070 — 前 771', years: [-2070, -771],
    axisKeys: [[0, -2070], [40, -1300], [200, -1250], [228, -1046], [390, -771]],
    motif: '甲骨与青铜',

    font: 'ZL-Baoli',
    palette: {bg: '#1B201D', ink: '#D9CBA6', accent: '#6E9C86', hud: '#bfb393', ruler: '#6E9C86'},
    start: 661, transition: 'ink', transitionFrames: 20,
  }),
  C({
    id: 'warring', no: 3, era: '春秋 · 战国', short: '春秋战国', yearsLabel: '前 770 — 前 221', years: [-770, -221],
    axisKeys: [[0, -770], [30, -551], [180, -280], [300, -230], [330, -230]],
    motif: '百家争鸣',
    font: 'ZL-Baoli',
    palette: {bg: '#D8C496', ink: '#1E1A14', accent: '#9A2E1C', hud: '#4b3d22', ruler: '#B08A3E'},
    start: 1051, transition: 'slats', transitionFrames: 18,
  }),
  C({
    id: 'qin', no: 4, era: '秦', short: '秦', yearsLabel: '前 221 — 前 207', years: [-221, -207],
    // the conquest ticker reveals 230, 228, 225, 223, 222, 221 at local 20 + k*7.5; the slam lands on 221
    axisKeys: [[0, -230], [20, -230], ...step(28, -230, -228), ...step(35, -228, -225), ...step(43, -225, -223), ...step(50, -223, -222), ...step(58, -222, -221), [150, -221], [360, -207]],
    motif: '书同文与长城',
    font: 'ZL-Li',
    palette: {bg: '#0D0C0B', ink: '#EAE3D2', accent: '#B3261E', hud: '#a39b8b', ruler: '#B3261E'},
    start: 1381, transition: 'flash', transitionFrames: 8,
  }),
  C({
    id: 'han', no: 5, era: '汉', short: '汉', yearsLabel: '前 202 — 公元 220', years: [-202, 220],
    // Zhang Qian's first mission 139-126 BCE while the route draws; Cai Lun presents paper in 105 when the sheet forms
    axisKeys: [[0, -202], [15, -139], [165, -126], [290, -126], [300, 105], [420, 105]],
    motif: '西域与纸',

    font: 'ZL-Li',
    palette: {bg: '#170F0D', ink: '#EBDCC4', accent: '#A8301F', hud: '#a8907a', ruler: '#C9A15A'},
    start: 1741, transition: 'wipe', transitionFrames: 20,
  }),
  C({
    id: 'split', no: 6, era: '三国 · 两晋 · 南北朝', short: '魏晋南北朝', yearsLabel: '220 — 589', years: [220, 589],
    axisKeys: [[0, 220], [88, 316], [158, 353], [210, 353], [296, 589], [390, 589]],
    motif: '分合三百余年',
    font: 'ZL-Weibei',
    palette: {bg: '#CBC5B9', ink: '#22201E', accent: '#46677A', hud: '#3f3b36', ruler: '#46677A'},
    start: 2161, transition: 'shards', transitionFrames: 20,
  }),
  C({
    id: 'tang', no: 7, era: '隋 · 唐', short: '隋唐', yearsLabel: '581 — 907', years: [581, 907],
    axisKeys: [[0, 581], [70, 581], [86, 605], [130, 605], [170, 618], [210, 618], [430, 907], [450, 907]],
    motif: '长安与唐诗',
    font: 'ZL-KaiBlack',
    palette: {bg: '#F0E4CB', ink: '#33230F', accent: '#C4832A', hud: '#5a4528', ruler: '#C4832A'},
    start: 2551, transition: 'iris', transitionFrames: 18, hudAlt: {from: 192, color: '#d9c8a6', bg: '#1E160E'},
  }),
  C({
    id: 'song', no: 8, era: '宋', short: '宋', yearsLabel: '960 — 1279', years: [960, 1279],
    // part A: Bianjing scroll + the official jiaozi (1024); part B: movable type (Qingli era, 1041-1048)
    axisKeys: [[0, 960], [40, 1024], [140, 1024], [176, 1041], [300, 1048], [330, 1048]],
    motif: '长卷与活字',
    font: 'ZL-Fangsong',
    palette: {bg: '#DCE4DE', ink: '#26322F', accent: '#A13A2B', hud: '#42504c', ruler: '#9DB5B9'},
    start: 3001, transition: 'wipe', transitionFrames: 22,
  }),
  C({
    id: 'yuan', no: 9, era: '元', short: '元', yearsLabel: '1271 — 1368', years: [1271, 1368],
    motif: '青花',
    font: 'ZL-Xingkai',
    palette: {bg: '#F3F0E8', ink: '#1C2F73', accent: '#2443A0', hud: '#3a4a7a', ruler: '#2443A0'},
    start: 3331, transition: 'bloom', transitionFrames: 22,
  }),
  C({
    id: 'ming', no: 10, era: '明', short: '明', yearsLabel: '1368 — 1644', years: [1368, 1644],
    // voyages begin 1405; the palace is completed 1420 (Yongle 18)
    axisKeys: [[0, 1368], [14, 1405], [212, 1419], [255, 1420], [375, 1420]],
    motif: '下西洋与紫禁城',

    font: 'ZL-SongBold', // 明体: the Song-style face took its printed form in Ming books
    palette: {bg: '#0F2A3B', ink: '#F2E7D0', accent: '#E0A526', hud: '#a9bcc4', ruler: '#7B2D3A'},
    start: 3676, transition: 'wave', transitionFrames: 22, hudAlt: {from: 252, color: '#5a3a2a', bg: '#F2E9D8'},
  }),
  C({
    id: 'qing', no: 11, era: '清', short: '清', yearsLabel: '1644 — 1912', years: [1644, 1840],
    axisKeys: [[0, 1644], [200, 1830], [210, 1840], [270, 1840]],
    motif: '帝制与鸦片战争',
    font: 'ZL-Song',
    palette: {bg: '#F2E7E1', ink: '#2A2422', accent: '#2C5F8A', hud: '#5d524e', ruler: '#D58E86'},
    start: 4051, transition: 'wipeRight', transitionFrames: 20,
  }),
  C({
    id: 'modern', no: 12, era: '近代', short: '近代', yearsLabel: '1840 — 1949', years: [1840, 1949],
    axisKeys: MODERN_EVENTS.flatMap((e, k): AxisKey[] => (k === 0 ? [[0, e.y]] : step(k * 2 * BEAT, MODERN_EVENTS[k - 1].y, e.y))).concat([[360, 1949]]),
    motif: '从洋务到 1949',
    font: 'ZL-Hei',
    palette: {bg: '#E7E0D0', ink: '#111111', accent: '#B5231C', hud: '#3b3631', ruler: '#6F6A62'},
    start: 4321, transition: 'dipBlack', transitionFrames: 6,
  }),
  C({
    id: 'today', no: 13, era: '当代', short: '当代', yearsLabel: '1949 — 今', years: [1949, 2026],
    axisKeys: [[0, 1978], [96, 1978], [222, 2026], [300, 2026]],
    motif: '改革开放',
    font: 'ZL-HeiHeavy',
    palette: {bg: '#F6F5F1', ink: '#111111', accent: '#D7301E', hud: '#55524c', ruler: '#D7301E'},
    start: 4681, transition: 'white', transitionFrames: 10,
  }),
  C({
    id: 'outro', no: 14, era: '片名', short: '片名', yearsLabel: '', years: [2026, 2026],
    motif: '',
    font: 'ZL-KaiBlack',
    palette: {bg: '#EEE7D8', ink: '#141210', accent: '#B8322A', hud: '#3a342c', ruler: '#141210'},
    start: 4981, transition: 'ink', transitionFrames: 22,
  }),
];

export const chapterEnd = (i: number) => (i + 1 < CHAPTERS.length ? CHAPTERS[i + 1].start : TOTAL_FRAMES);
export const chapterDur = (i: number) => chapterEnd(i) - CHAPTERS[i].start;
export const ERA_CHAPTERS = CHAPTERS.filter((c) => c.no >= 1 && c.no <= 13);

// Music cues inside chapters (absolute frames), from audio/snaps.json + RMS reading.
export const CUES = {
  openingHit: 301, // big entry after the 9.3-9.9 s breath
  qinSlam: 1441, // 48.023 s downbeat after the swell
  mingPalace: 3931, // 131.0 s section change
  qingBreak: 4207, // 140.2 s: music decays toward near-silence
  qingCrack: 4261, // 142.023 s: strongest hit of the track
  outroDecay: 4981, // the title card arrives (outro start); the HUD fades out
};

/** Historical years have no year 0. Before 841 BCE (the first securely dated year in
 * Chinese chronology) the counter is shown as an approximation. */
export const formatYear = (y: number) => {
  if (y < -841) {
    const r = Math.round(-y / 10) * 10;
    return `约前 ${r}`;
  }
  if (y < 0) return `前 ${Math.max(1, Math.round(-y))}`;
  return `${Math.max(1, Math.round(y))}`;
};

/** The progress axis the HUD tracks. A chronicle uses years; a map tour could use place names or km,
 * a catalogue an index, a process its step number. Chapters key their axis values in `axisKeys`. */
export const AXIS = { kind: 'year' as const, format: formatYear }
