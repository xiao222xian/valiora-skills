// Write the description credits blocks from src/credits.ts, the catalogue the end card reads, so the card and the
// blocks list the same items in the same order.
//   node tools/credits.mjs [--out-dir <dir>] [--catalogue <file>]
// credits-full.txt     one line per item that needs attribution: author，《title》（changed），licence（licence URL），
//                      source URL; then CREDITS_CHANGED and one line for the material that needs none (YouTube)
// credits-compact.txt  the same items without the per-item licence URL, the licence URLs on one line, and the
//                      material that needs none pointed back to the end card, where it is listed (Bilibili, ≤ 2000)
// (2026-10-12, 《如何打造一款特斯拉》: 11 CC BY items took 2273 characters in full and 1676 compact; the full block made
// the Bilibili description 2646 characters, over 2000.)
// Prints each block's length in Python characters (code points, newlines included, final newline left out: the
// count references/publish-handoff.md and check_copy.py use) and flags < and > (YouTube refuses them). Exits 1 and
// writes nothing when an attributed item lacks an author, a licence or a source URL, a licence has no known URL,
// or an item is listed twice. An empty catalogue writes nothing.
import {writeFileSync, mkdirSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let opt;
try {
  ({values: opt} = parseArgs({
    options: {
      'out-dir': {type: 'string', default: path.join(root, '..', 'manifest')},
      catalogue: {type: 'string', default: path.join(root, 'src', 'credits.ts')},
      help: {type: 'boolean', short: 'h', default: false},
    },
  }));
} catch (e) {
  console.error(String(e?.message ?? e));
  process.exit(2);
}
if (opt.help) {
  console.log('usage: node tools/credits.mjs [--out-dir <dir>] [--catalogue <file>]');
  process.exit(0);
}

// Node 24 strips the types, as for timeline.ts in tools/chapters.mjs; a path so a scratch copy works too.
const cat = await import(pathToFileURL(path.resolve(opt.catalogue)).href);
const {CREDITS, CREDITS_CHANGED, licenseUrl, needsCredit, otherLine} = cat;

if (!CREDITS.length) {
  console.error(`${path.relative(process.cwd(), path.resolve(opt.catalogue))} lists no third-party material: no credits blocks to write`);
  process.exit(0);
}

const problems = [];
const seen = new Set();
CREDITS.forEach((c, i) => {
  const at = `#${i + 1} ${c.author || '(no author)'}${c.title ? ` · ${c.title}` : ''}`;
  const key = (c.url || `${c.author}|${c.title ?? ''}`).trim();
  if (seen.has(key)) problems.push(`${at}: listed twice (once each, in film order)`);
  seen.add(key);
  if (!String(c.author ?? '').trim()) problems.push(`${at}: no author`);
  if (!String(c.license ?? '').trim()) problems.push(`${at}: no licence`);
  else if (needsCredit(c) && !licenseUrl(c.license)) problems.push(`${at}: no known URL for licence "${c.license}" (write e.g. "CC BY 4.0", or extend licenseUrl in src/credits.ts)`);
  if (needsCredit(c) && !String(c.url ?? '').trim()) problems.push(`${at}: no source URL`);
});
if (problems.length) {
  for (const p of problems) console.error('PROBLEM', p);
  console.error(`${CREDITS.length} items; not written`);
  process.exit(1);
}

const named = CREDITS.filter(needsCredit);
const item = (c, withLicenseUrl) => {
  const title = c.title ? `，《${c.title}》` : '';
  const changed = c.changed ? `（${c.changed}）` : '';
  const lic = withLicenseUrl ? `${c.license}（https://${licenseUrl(c.license)}/）` : c.license;
  return `- ${c.author}${title}${changed}，${lic}，${c.url}`;
};
const CC = 'creativecommons.org/licenses';
const urls = [...new Set(named.map((c) => licenseUrl(c.license)))];
const urlLine = urls.length
  ? '许可协议：' + urls.map((u, i) => (i && u.startsWith(CC) && urls[0].startsWith(CC) ? u.slice(CC.length) : u)).join(' 、')
  : '';
const other = otherLine();

const head = named.length ? ['素材署名：'] : [];
const changed = named.length && CREDITS_CHANGED ? [CREDITS_CHANGED] : [];
const full = [...head, ...named.map((c) => item(c, true)), ...changed, other].filter(Boolean).join('\n');
// the compact block points the no-attribution material back to the card, which lists it; alone, it keeps the line
const compact = [...head, ...named.map((c) => item(c, false)), ...changed, urlLine, other && named.length ? '其余素材署名见片尾。' : other].filter(Boolean).join('\n');

const outDir = path.resolve(opt['out-dir']);
mkdirSync(outDir, {recursive: true});
for (const [name, text] of [['credits-full.txt', full], ['credits-compact.txt', compact]]) {
  writeFileSync(path.join(outDir, name), text + '\n');
  const flag = /[<>]/.test(text) ? '  has < or >: YouTube refuses it' : '';
  console.log(`${[...text].length}\t${name}${flag}`);
}
console.error(`${named.length} attributed, ${CREDITS.length - named.length} without attribution; wrote ${outDir}`);
