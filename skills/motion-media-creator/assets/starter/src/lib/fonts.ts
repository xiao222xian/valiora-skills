import {useLayoutEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender, staticFile} from 'remotion';

// Subset files are produced by tools/fonts.py from macOS system faces.
export const FONT_FAMILIES = [
  'ZL-Kai',
  'ZL-KaiBlack',
  'ZL-Li',
  'ZL-Baoli',
  'ZL-Weibei',
  'ZL-Xingkai',
  'ZL-SongBlack',
  'ZL-SongBold',
  'ZL-Song',
  'ZL-SongLight',
  'ZL-HeiHeavy',
  'ZL-Hei',
  'ZL-HeiLight',
  'ZL-Fangsong',
  'ZL-Serif',
  'ZL-Mono',
] as const;

let loaded: Promise<void> | null = null;
export let fontsReady = false;

export const ensureFonts = () => {
  if (loaded) return loaded;
  const handle = delayRender('Loading era typefaces', {timeoutInMilliseconds: 60000, retries: 1});
  loaded = Promise.all(
    FONT_FAMILIES.map((fam) => {
      // New York and SF Mono are variable fonts: declare the weight range so 400-800 use the real axis
      const ff = new FontFace(fam, `url(${staticFile(`fonts/${fam}.ttf`)}) format('truetype')`, fam === 'ZL-Serif' || fam === 'ZL-Mono' ? {weight: '1 1000'} : {});
      // Register before loading so document.fonts.check() reports false until the face is real.
      (document.fonts as unknown as Set<FontFace>).add(ff);
      return ff.load();
    }),
  )
    .then(() => {
      fontsReady = true;
      continueRender(handle);
    })
    .catch((err) => cancelRender(err));
  return loaded;
};

/** For canvas/bitmap drawing: re-render once every face is loaded, and hold the frame until then. */
export const useFontsReady = () => {
  const [ok, setOk] = useState(fontsReady);
  useLayoutEffect(() => {
    if (ok) return;
    const h = delayRender('Canvas waits for fonts');
    ensureFonts().then(() => {
      setOk(true);
      continueRender(h);
    });
  }, [ok]);
  return ok;
};

// Body copy and annotations share one quiet voice across eras; headlines change per era.
export const BODY = "'ZL-Fangsong', 'ZL-Song', serif";
export const SERIF = "'ZL-Serif', 'ZL-Song', serif";
export const MONO = "'ZL-Mono', 'ZL-Hei', monospace";
export const fam = (f: string) => `'${f}', 'ZL-Song', serif`;
// Voice-over subtitles: one legible sans across every chapter.
export const SUBTITLE_FONT = "'ZL-Hei', 'ZL-Song', sans-serif";

// CSS background textures are not tracked by Remotion's asset waiting, so decode them up front
// and keep the decoded images referenced for the life of the page.
const keep: HTMLImageElement[] = [];
let tex: Promise<void> | null = null;
export const ensureTextures = () => {
  if (tex) return tex;
  const handle = delayRender('Decoding paper textures', {timeoutInMilliseconds: 60000, retries: 1});
  const files = ['tex/paper.png', ...[0, 1, 2, 3, 4, 5].map((i) => `tex/grain${i}.png`)];
  tex = Promise.all(
    files.map((f) => {
      const img = new Image();
      img.src = staticFile(f);
      keep.push(img);
      return img.decode();
    }),
  )
    .then(() => continueRender(handle))
    .catch((err) => cancelRender(err));
  return tex;
};
