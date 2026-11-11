// Seal-script (小篆) 漢, drawn in the same 100x100 box and stroke style as SEAL in glyphs.ts (字形示意).
// Simplified 汉 has no seal form; 說文·水部: 漢，从水，難省聲 — 水 on the left, 難省 (the left part of 難) on the right.
// Structure follows the 說文小篆 forms on zdic.net (漢 字源字形) and Wikimedia Commons "漢-seal.svg"
// (Richard Sears data, s07913); redrawn here as centre-line strokes, not traced.
//   水: three columns; side columns break at mid-height, the upper-left sweeps out to the lower left.
//   難省: 廿 closed into a cup, open-topped 田 with the centre stroke through it, 火 (two side dots and a
//       Λ splitting off the centre stroke), 土 at the foot.
export const SEAL_HAN = [
  // 水
  'M14,10 C18,17 18,27 16,32 Q14,37 9,40',
  'M15,48 C15,62 16,76 19,90',
  'M21,5 C27,10 28,18 28,28 L27,52 C27,68 28,82 31,94',
  'M36,9 C41,17 41,29 37,38',
  'M38,48 C37,60 38,72 41,84',
  // 廿
  'M59,5 L59,22 Q59,28 69,28 Q79,28 79,22 L79,5',
  'M49,14 L89,14',
  // centre stroke, open-topped 田
  'M69,28 L69,63',
  'M52,31 L52,45 Q52,52 69,52 Q86,52 86,45 L86,31',
  'M52,40 L86,40',
  // 火
  'M57,61 L50,67',
  'M81,61 L88,67',
  'M52,77 Q62,71 69,63 Q76,71 86,77',
  // 土
  'M69,77 L69,95', // starts below the 火 apex so the two stay apart at 64px
  'M58,85 L80,85',
  'M49,95 L89,95',
].join(' ');
