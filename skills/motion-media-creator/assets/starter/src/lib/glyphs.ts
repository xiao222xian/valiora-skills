// Stylised oracle-bone forms (字形示意), drawn by hand in a 100x100 box as open strokes.
// They follow the well-known pictographic shapes; they are not traced from rubbings.
export const ORACLE: Record<string, string> = {
  日: 'M24,16 C14,30 14,72 26,86 L74,86 C86,72 86,30 76,16 Z M38,50 L62,50',
  月: 'M64,6 C26,20 20,74 58,96 M64,6 C46,34 46,70 58,96 M46,48 L58,52',
  山: 'M8,86 L92,86 M8,86 L22,44 L36,86 M36,86 L50,10 L64,86 M64,86 L78,44 L92,86',
  水: 'M50,6 C36,26 64,42 50,58 C38,72 60,84 50,96 M26,22 L34,30 M20,52 L30,58 M76,26 L68,34 M80,60 L70,64',
  人: 'M62,8 C54,40 44,62 30,94 M53,42 L76,60',
  雨: 'M10,12 L90,12 M18,26 L82,26 M50,12 L50,26 M28,40 L28,50 M28,62 L28,72 M50,40 L50,50 M50,62 L50,72 M72,40 L72,50 M72,62 L72,72',
  木: 'M50,6 L50,96 M50,40 L24,16 M50,40 L76,16 M50,68 L24,94 M50,68 L76,94',
  火: 'M18,88 L82,88 M22,88 C26,64 30,58 32,40 M50,88 C50,54 52,32 50,10 M78,88 C74,64 70,58 68,40',
};

/** Rectangular spiral (云雷纹 cell) starting at the centre, as a polyline. */
export const squareSpiral = (x: number, y: number, unit: number, segments: number, dir = 1): [number, number][] => {
  const dirs: [number, number][] = [
    [1, 0],
    [0, dir],
    [-1, 0],
    [0, -dir],
  ];
  const pts: [number, number][] = [[x, y]];
  let cx = x;
  let cy = y;
  for (let i = 0; i < segments; i++) {
    const len = unit * (Math.floor(i / 2) + 1);
    cx += dirs[i % 4][0] * len;
    cy += dirs[i % 4][1] * len;
    pts.push([cx, cy]);
  }
  return pts;
};

// Seal-script (小篆) forms drawn as even-width strokes in the same 100x100 box (字形示意).
// macOS ships no seal-script face, so the Qin chapter's "书同文" resolves to these paths.
export const SEAL: Record<string, string> = {
  文: 'M50,6 L50,20 M16,26 Q50,18 84,26 M32,34 C36,58 52,74 74,94 M68,34 C64,58 48,74 26,94',
  字: 'M50,4 L50,14 M14,38 L14,22 Q50,12 86,22 L86,38 M36,34 Q50,26 64,34 Q64,46 50,50 M26,60 Q50,52 74,60 M50,50 L50,84 Q50,96 38,92',
};

// 16x16 hand-set pixel 字 (宀 over 子): bitmap rasterising of a font merges the strokes at this size.
export const ZI16 = [
  '................',
  '.......##.......',
  '.......##.......',
  '.##############.',
  '.##..........##.',
  '.##..........##.',
  '.....######.....',
  '..........##....',
  '.........##.....',
  '.##############.',
  '.......##.......',
  '.......##.......',
  '.......##.......',
  '.......##.......',
  '.....####.......',
  '................',
].map((row) => Array.from(row).map((c) => c === '#'));

// 16x16 hand-set pixel 汉 (氵 beside 又), same pixel weight as ZI16.
export const HAN16 = [
  '................',
  '................',
  '..##............',
  '...##.########..',
  '............##..',
  '............##..',
  '.##....##...##..',
  '..##...##..##...',
  '........##.##...',
  '.........###....',
  '.........###....',
  '........##.##...',
  '...##..##...##..',
  '..##..##.....##.',
  '.##...##.....##.',
  '................',
].map((row) => Array.from(row).map((c) => c === '#'));
