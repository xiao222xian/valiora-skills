// Render several stills from one bundle with one browser (each still is a fresh tab).
//   node tools/stills.mjs <serveUrl> <compId> <outPrefix> <scale> <absFrame[:label]>...
// Writes <outPrefix><label>.jpg (label defaults to the frame number). Env GL picks the OpenGL renderer
// (e.g. GL=angle for WebGL scenes; unset = Remotion's default). FORMATS=png,jpeg writes every still in each listed
// format (covers: tools/deliver.sh covers), JPEG_QUALITY sets the JPG quality (default 88). Exits 1 when any still fails.
import {createRequire} from 'node:module';
const req = createRequire(import.meta.url);
// @remotion/renderer comes with @remotion/cli (pnpm does not hoist it to the top level)
const R = createRequire(req.resolve('@remotion/cli'))('@remotion/renderer');

const [serveUrl, id, prefix, scaleArg, ...frames] = process.argv.slice(2);
if (!serveUrl || !id || !prefix || !scaleArg || frames.length === 0) {
  console.error('usage: node tools/stills.mjs <serveUrl> <compId> <outPrefix> <scale> <absFrame[:label]>...');
  process.exit(2);
}
const EXT = {jpeg: 'jpg', png: 'png'};
const formats = (process.env.FORMATS || 'jpeg').split(',').map((s) => s.trim()).filter(Boolean);
if (!formats.length || formats.some((f) => !EXT[f])) {
  console.error(`FORMATS must list jpeg and/or png, got "${process.env.FORMATS}"`);
  process.exit(2);
}
const jpegQuality = Number(process.env.JPEG_QUALITY || 88);
const chromiumOptions = process.env.GL ? {gl: process.env.GL} : {};
const browser = await R.openBrowser('chrome', {chromiumOptions});
let failed = 0;
try {
  const composition = await R.selectComposition({serveUrl, id, puppeteerInstance: browser, chromiumOptions, timeoutInMilliseconds: 120000, logLevel: 'error'});
  for (const spec of frames) {
    const [f, label] = spec.split(':');
    for (const imageFormat of formats) {
      const output = `${prefix}${label || f}.${EXT[imageFormat]}`;
      const t0 = Date.now();
      try {
        await R.renderStill({composition, serveUrl, frame: Number(f), output, imageFormat, ...(imageFormat === 'jpeg' ? {jpegQuality} : {}), scale: Number(scaleArg), puppeteerInstance: browser, chromiumOptions, timeoutInMilliseconds: 120000, overwrite: true, logLevel: 'error'});
        console.log(`${output} (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
      } catch (e) {
        failed++;
        console.error(`FAILED frame ${f} (${imageFormat}): ${String(e?.message ?? e).split('\n').slice(0, 6).join('\n')}`);
      }
    }
  }
} finally {
  await browser.close({silent: true});
}
process.exit(failed ? 1 : 0);
