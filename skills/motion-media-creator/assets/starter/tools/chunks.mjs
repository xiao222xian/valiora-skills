// Print the render chunks for tools/deliver.sh as "a-b,c-d,..." (inclusive frame ranges).
// Cuts fall on chapter starts only; consecutive chapters share a chunk up to CHUNK_FRAMES
// (default 1500), and the last chapter (the outro, which mounts every scene as a thumbnail)
// always renders alone. A chapter longer than CHUNK_FRAMES gets a chunk of its own.
import {CHAPTERS, TOTAL_FRAMES} from '../src/timeline.ts'; // Node 24 strips the types

const max = Number(process.env.CHUNK_FRAMES || 1500);
const starts = [...new Set(CHAPTERS.map((c) => c.start))].sort((a, b) => a - b);
const last = starts.at(-1);
const ranges = [];
let a = 0;
let prev = 0;
for (const b of [...starts.filter((s) => s > 0 && s < last), last]) {
  if (b - a > max && prev > a) {
    ranges.push([a, prev - 1]);
    a = prev;
  }
  prev = b;
}
if (last > a) ranges.push([a, last - 1]);
ranges.push([last, TOTAL_FRAMES - 1]);
console.log(ranges.map(([x, y]) => `${x}-${y}`).join(','));
