// Render a frame range without audio (the approved mix is muxed afterwards):
// node render-range-log.mjs <compositionId> <out.mp4> <fromFrame> <toFrame>
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';
const root = process.cwd();
const [id, outRel, from, to] = process.argv.slice(2);
const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.ts'), publicDir: path.join(root, 'public')});
try {
  const composition = await selectComposition({serveUrl, id});
  await renderMedia({serveUrl, composition, outputLocation: path.resolve(root, outRel), codec: 'h264', muted: true, crf: 16,
    x264Preset: 'medium', pixelFormat: 'yuv420p', colorSpace: 'bt709', concurrency: 6, frameRange: [Number(from), Number(to)],
    overwrite: true,
    onProgress: ({progress}) => { const p = Math.floor(progress * 20); if (p !== globalThis.__p) { globalThis.__p = p; console.log(new Date().toISOString(), `progress ${(progress * 100).toFixed(0)}%`); } }});
  console.log('done', from, to);
} finally {
  // each bundle copies public/ (mezzanine included) into TMPDIR; remove it even when the render fails,
  // or retries fill the disk
  fs.rmSync(serveUrl, {recursive: true, force: true});
}
