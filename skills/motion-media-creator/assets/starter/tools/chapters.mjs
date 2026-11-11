// Print the chapter timeline for video descriptions (B站 简介, YouTube chapters) from src/timeline.ts and
// write it to a text file, one chapter a line: "MM:SS 名称" (HH:MM:SS once the film passes an hour), first 00:00.
//   node tools/chapters.mjs [--names era|short|<field>[,<field>...]] [--out <file>] [--timeline <file>]
// Timestamps are floored to whole seconds, the way they are displayed, and a chapter's length is measured between
// displayed timestamps (the last one runs to the floored film length): that is what the platform reads.
// YouTube chapters need the first at 00:00, at least 3 chapters and each at least 10 s. Exits 1 on fewer than 3
// chapters, starts out of order, or any displayed length under 10 s, and then writes nothing; warns under 11 s
// (design chapters >= 11 s: 《如何打造一款特斯拉》 had three chapters displayed at exactly 10 s, 2026-10-12).
// The list goes to stdout (paste or pipe it); warnings and the summary go to stderr.
import {writeFileSync, mkdirSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';

const MIN_S = 10; // platform floor (YouTube)
const DESIGN_S = 11; // design floor: one second of slack over the platform floor

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let opt;
try {
  ({values: opt} = parseArgs({
    options: {
      names: {type: 'string', default: 'era'},
      out: {type: 'string', default: path.join(root, '..', 'manifest', 'chapters.txt')},
      timeline: {type: 'string', default: path.join(root, 'src', 'timeline.ts')},
      help: {type: 'boolean', short: 'h', default: false},
    },
  }));
} catch (e) {
  console.error(String(e?.message ?? e));
  process.exit(2);
}
if (opt.help) {
  console.log('usage: node tools/chapters.mjs [--names era|short|<field>[,<field>...]] [--out <file>] [--timeline <file>]');
  process.exit(0);
}

// Same import as tools/chunks.mjs and tools/manifest.mjs (Node 24 strips the types); a path so a scratch copy works too.
const {CHAPTERS, TOTAL_FRAMES, FPS} = await import(pathToFileURL(path.resolve(opt.timeline)).href);

const fields = opt.names.split(',').map((f) => f.trim()).filter(Boolean);
const unknown = fields.filter((f) => !CHAPTERS.some((c) => typeof c[f] === 'string' || typeof c[f] === 'number'));
if (!fields.length || unknown.length) {
  console.error(`--names: no chapter field ${unknown.join(', ') || '(empty)'}; try era or short`);
  process.exit(2);
}

const filmS = Math.floor(TOTAL_FRAMES / FPS);
const long = filmS >= 3600;
const two = (n) => String(n).padStart(2, '0');
const stamp = (s) => (long ? `${two(Math.floor(s / 3600))}:${two(Math.floor((s % 3600) / 60))}:${two(s % 60)}` : `${two(Math.floor(s / 60))}:${two(s % 60)}`);

const problems = [];
const warnings = [];
const rows = CHAPTERS.map((c, i) => {
  const from = Math.floor(c.start / FPS);
  const end = i + 1 < CHAPTERS.length ? CHAPTERS[i + 1].start : TOTAL_FRAMES;
  const to = i + 1 < CHAPTERS.length ? Math.floor(end / FPS) : filmS;
  const name = fields.map((f) => String(c[f] ?? '').trim()).filter(Boolean).join(' ');
  return {i, id: c.id, name, from, shown: to - from, actual: (end - c.start) / FPS};
});

if (rows.length < 3) problems.push(`${rows.length} chapters: YouTube needs at least 3`);
if (rows.length && rows[0].from !== 0) problems.push(`first chapter starts at ${stamp(rows[0].from)}, not 00:00`);
for (const r of rows) {
  const at = `${two(r.i)} ${r.name || r.id} ${stamp(r.from)}`;
  if (!r.name) problems.push(`${at}: empty name in --names ${fields.join(',')}`);
  if (r.actual <= 0) problems.push(`${at}: starts at or after the next chapter`);
  else if (r.shown < MIN_S) problems.push(`${at}: displayed ${r.shown} s (actual ${r.actual.toFixed(2)} s), under ${MIN_S} s`);
  else if (r.shown < DESIGN_S) warnings.push(`${at}: displayed ${r.shown} s (actual ${r.actual.toFixed(2)} s), under the ${DESIGN_S} s design floor`);
}

const lines = rows.map((r) => `${stamp(r.from)} ${r.name}`);
console.log(lines.join('\n'));
for (const w of warnings) console.error('WARN', w);
for (const p of problems) console.error('PROBLEM', p);
const shortest = rows.length ? Math.min(...rows.map((r) => r.shown)) : 0;
const summary = `${rows.length} chapters, film ${(TOTAL_FRAMES / FPS).toFixed(1)} s, shortest displayed ${shortest} s`;
if (problems.length) {
  console.error(`${summary}; not written`);
  process.exit(1);
}
mkdirSync(path.dirname(path.resolve(opt.out)), {recursive: true});
writeFileSync(path.resolve(opt.out), lines.join('\n') + '\n');
console.error(`${summary}; wrote ${path.resolve(opt.out)}`);
