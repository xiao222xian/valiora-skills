// Batch stills with one bundle: node render-stills.mjs <compositionId> <outDir> <frame,frame,...>
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';
const root = process.cwd();
const [id, outDir, frames] = process.argv.slice(2);
fs.mkdirSync(outDir, {recursive: true});
const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.ts'), publicDir: path.join(root, 'public')});
try {
  const composition = await selectComposition({serveUrl, id});
  for (const f of frames.split(',').map(Number)) {
    const out = path.resolve(outDir, `${id}-${String(f).padStart(5, '0')}.png`);
    await renderStill({serveUrl, composition, output: out, frame: f, imageFormat: 'png', overwrite: true});
    console.log('still', f);
  }
} finally {
  // the bundle is a full copy of public/; remove it even when a still fails
  fs.rmSync(serveUrl, {recursive: true, force: true});
}
