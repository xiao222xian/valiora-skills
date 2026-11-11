import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Img, continueRender, delayRender, staticFile, useVideoConfig} from 'remotion';
import {Paper} from './components/Paper';
import {BrandSeal} from './brand/Seal';
import {ERA_CHAPTERS, TITLE} from './timeline';
import type {Chapter} from './timeline';
import {MONO, fam} from './lib/fonts';

// Covers, named by ratio (Root.tsx, tools/deliver.sh covers): Cover-16x9 1920x1080, Cover-4x3 1440x1080 (Bilibili
// home and the WeChat Channels share card), Cover-3x4 1080x1440 (the Channels profile card). Every film delivers
// all three. The picture is an AI background without any text (tools/gen_cover_bg.py ->
// public/assets/cover/ai-<16x9|4x3|3x4>.png or .jpg) that leaves a quiet title area in the cover's tone (COVER.tone:
// near-black, or the film's paper colour); title, English title, seal and logo are set here. Each cover takes its own picture. Without one, 4:3 sets the 16:9 picture full width at the
// bottom, top edge faded, with the title in the dark band above (cropping 16:9 to 4:3 under the left title put the
// title over the subject, 2026-10-12), and 3:4 sets it in its lower 62 %, cut from the right. Without any picture
// the cover falls back to the chapter spectrum on paper. No chapter names or step axis on covers: at thumbnail size
// they cannot be read and they crowd the subject (2026-10-12).

/** Per-film cover settings. The title comes from timeline.ts, the logo from public/brand/logo.png, the seal from src/brand. */
export const COVER = {
  /** Title lines; [] breaks TITLE itself: at a comma, colon or bar, else a CJK title over 6 characters in two near the middle. */
  lines: [] as string[],
  /** English title in spaced capitals: under the title on 16:9 and 4:3, above it as a kicker on 3:4; '' leaves it out. */
  titleEn: '',
  /** Typeface of the title (a family registered in lib/fonts). */
  font: 'ZL-KaiBlack',
  /** Fallback only: the glyph each chapter band shows in that chapter's headline face; '' gives plain colour bands. */
  bandGlyph: '汉',
  /** Ground of the title area, the same as "tone" in cover/brief.json (it picks the matching layout lines): 'dark' is
   * near-black with a light title (validated on the Tesla film, 2026-10-12); 'paper' is the film's paper colour with
   * a dark ink title, for a paper or ink film whose cover should not turn cinematic-dark. */
  tone: 'dark' as Tone,
};

type Tone = 'dark' | 'paper';
type Ratio = '16x9' | '4x3' | '3x4';
type Picture = {src: string; own: boolean};

/** Title ink, ground, and the RGB the shading over the picture fades from. Set paper.bg (and paper.shade) to the
 * film's ground colour, and the same hex in cover/brief.json layouts.paper. */
const TONES: Record<Tone, {ink: string; bg: string; shade: string}> = {
  dark: {ink: '#F2EFE8', bg: '#08090a', shade: '5,6,7'},
  paper: {ink: '#141210', bg: '#EEE7D8', shade: '238,231,216'},
};
const T = TONES[COVER.tone];
const shade = (a: number) => `rgba(${T.shade},${a})`;
const PAPER = TONES.paper; // the no-picture fallback is always on paper
const FADE_TOP = 'linear-gradient(180deg, transparent 0%, #000 14%)';

const ratioOf = (w: number, h: number): Ratio => (h > w ? '3x4' : w / h > 1.5 ? '16x9' : '4x3');
const files = (r: Ratio) => [`assets/cover/ai-${r}.png`, `assets/cover/ai-${r}.jpg`];
// in order: the cover's own picture, then (4:3, 3:4) the 16:9 picture in a band at the bottom
const candidates = (r: Ratio) => [...files(r).map((f) => ({f, own: true})), ...(r === '16x9' ? [] : files('16x9').map((f) => ({f, own: false})))];

const exists = async (file: string) => {
  try {
    const res = await fetch(staticFile(file), {method: 'HEAD'});
    return res.ok && !(res.headers.get('content-type') ?? '').includes('text/html');
  } catch {
    return false;
  }
};

/** The picture this cover uses (null: none, fall back), undefined while looking; the frame is held until known. */
const usePicture = (r: Ratio): Picture | null | undefined => {
  const [handle] = useState(() => delayRender(`Cover ${r}: looking for the AI picture`));
  const [pic, setPic] = useState<Picture | null | undefined>(undefined);
  useEffect(() => {
    let live = true;
    (async () => {
      for (const c of candidates(r)) if (await exists(c.f)) return {src: staticFile(c.f), own: c.own};
      return null;
    })().then((p) => live && setPic(p));
    return () => {
      live = false;
    };
  }, [r]);
  // released after the commit that mounts the picture, so its <Img> already holds the frame until it has loaded
  useEffect(() => {
    if (pic !== undefined) continueRender(handle);
  }, [pic, handle]);
  return pic;
};

const titleLines = (): string[] => {
  if (COVER.lines.length) return COVER.lines;
  const parts = TITLE.split(/[，,：:｜|]/).map((s) => s.trim()).filter(Boolean);
  if (parts.length > 1) return parts;
  const cs = Array.from(TITLE);
  if (cs.length <= 6 || /[A-Za-z]/.test(TITLE)) return [TITLE];
  const k = Math.floor(cs.length / 2); // the second line is the longer one
  return [cs.slice(0, k).join(''), cs.slice(k).join('')];
};

/** Width in em: CJK glyphs 1, anything else about 0.6. */
const ems = (s: string) => Array.from(s).reduce((a, c) => a + (c.charCodeAt(0) > 0x2e80 ? 1 : 0.6), 0);
const TRACK = 0.05; // title letter spacing, em
const SEAL = 0.7; // seal size / title size (landscape)
const SEAL_GAP = 0.18;

/** Landscape: the largest title size whose widest line (the last one with its seal) fits `budget` px, at most `cap`. */
const fitTitle = (lines: string[], budget: number, cap: number) => {
  const widest = Math.max(...lines.map((l, i) => ems(l) * (1 + TRACK) + (i === lines.length - 1 ? SEAL + SEAL_GAP : 0)));
  return Math.min(cap, budget / widest);
};

const Logo: React.FC<{height: number; style?: React.CSSProperties}> = ({height, style}) => (
  <Img src={staticFile('brand/logo.png')} style={{position: 'absolute', height, ...style}} />
);

/** Title lines with the seal after the last one, and the English title under them (or above them as a kicker). */
const Title: React.FC<{size: number; ink: string; center?: boolean; kicker?: boolean; sealK?: number}> = ({size, ink, center = false, kicker = false, sealK = SEAL}) => {
  const lines = titleLines();
  const en = COVER.titleEn ? (
    <div
      style={{
        fontFamily: MONO,
        fontSize: Math.round(size * 0.19),
        letterSpacing: '0.32em',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
        opacity: 0.7,
        ...(center ? {paddingLeft: '0.32em'} : {}), // tracking trails the last letter: balance it when centred
        ...(kicker ? {marginBottom: size * 0.15} : {marginTop: size * 0.22}),
      }}
    >
      {COVER.titleEn}
    </div>
  ) : null;
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: center ? 'center' : 'flex-start', color: ink}}>
      {kicker && en}
      {lines.map((l, i) => {
        const last = i === lines.length - 1;
        const fs = center && !last ? size * 0.8 : size; // centred titles put the weight on the last line
        return (
          <div key={i} style={{position: 'relative', fontFamily: fam(COVER.font), fontSize: fs, lineHeight: 1.14, letterSpacing: fs * TRACK, marginRight: center ? -fs * TRACK : 0, whiteSpace: 'nowrap'}}>
            {l}
            {last && <BrandSeal at={-100} size={size * sealK} style={{position: 'absolute', left: '100%', marginLeft: size * SEAL_GAP, bottom: size * 0.17}} />}
          </div>
        );
      })}
      {!kicker && en}
    </div>
  );
};

/** 16:9, and 4:3 with its own picture: the picture fills the frame, the title sits in its quiet left side. */
const LandscapeFull: React.FC<{src: string}> = ({src}) => {
  const {width: W, height: H} = useVideoConfig();
  const lines = titleLines();
  const left = W * 0.057;
  const size = fitTitle(lines, W * 0.48 - left, H * (lines.length > 1 ? 0.125 : 0.17));
  return (
    <AbsoluteFill style={{background: T.bg}}>
      <Img src={src} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', objectPosition: '100% 50%'}} />
      <AbsoluteFill style={{background: `linear-gradient(90deg, ${shade(0.8)} 0%, ${shade(0.45)} 30%, ${shade(0)} 52%)`}} />
      <div style={{position: 'absolute', left, top: 0, bottom: H * 0.1, display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <Title size={size} ink={T.ink} />
      </div>
      <Logo height={H * 0.054} style={{right: H * 0.06, top: H * 0.048}} />
    </AbsoluteFill>
  );
};

/** 4:3 without its own picture: the 16:9 picture full width at the bottom, top edge faded, the title in the band above. */
const LandscapeBand: React.FC<{src: string}> = ({src}) => {
  const {width: W, height: H} = useVideoConfig();
  const lines = titleLines();
  const left = W * 0.057;
  const picH = (W * 9) / 16;
  const size = fitTitle(lines, W * 0.5 - left, H * (lines.length > 1 ? 0.097 : 0.13));
  return (
    <AbsoluteFill style={{background: T.bg}}>
      <Img src={src} style={{position: 'absolute', left: 0, top: H - picH, width: '100%', height: picH, objectFit: 'cover', objectPosition: '100% 50%', maskImage: FADE_TOP, WebkitMaskImage: FADE_TOP}} />
      <div style={{position: 'absolute', left, top: H * 0.055}}>
        <Title size={size} ink={T.ink} />
      </div>
      <Logo height={H * 0.054} style={{right: H * 0.06, top: H * 0.048}} />
    </AbsoluteFill>
  );
};

/** 3:4 title size: centred lines (all but the last at 0.8), the seal right of the last one, 3 % side margins. */
const portraitSize = (W: number) => {
  const lines = titleLines();
  const fits = lines.map((l, i) => {
    const last = i === lines.length - 1;
    // a centred line with the seal hanging off its right end: reserve seal and gap on both sides
    return (W * 0.94) / (ems(l) * (1 + TRACK) * (last ? 1 : 0.8) + (last ? 2 * (0.62 + SEAL_GAP) : 0));
  });
  return Math.min(W * (lines.length > 1 ? 0.14 : 0.17), ...fits);
};

/** 3:4: English kicker above the title in the quiet top, the picture below (its own, or the 16:9 one in a band). */
const Portrait: React.FC<{pic: Picture}> = ({pic}) => {
  const {width: W, height: H} = useVideoConfig();
  const size = portraitSize(W);
  // the 16:9 picture in the lower 62 %, cut from its right side: its empty left 40 % is the part that goes
  const picH = H * 0.62;
  return (
    <AbsoluteFill style={{background: T.bg}}>
      {pic.own ? (
        <>
          {/* shifted down so the title block clears the subject (64 px at 1440, 2026-10-12) */}
          <Img src={pic.src} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', transform: `translateY(${H * 0.0444}px)`}} />
          <AbsoluteFill style={{background: `linear-gradient(180deg, ${shade(0.85)} 0%, ${shade(0.45)} 20%, ${shade(0)} 30%, ${shade(0)} 86%, ${shade(0.4)} 100%)`}} />
          <div style={{position: 'absolute', left: 0, right: 0, top: H * 0.05, display: 'flex', justifyContent: 'center'}}>
            <Title size={size} ink={T.ink} center kicker sealK={0.62} />
          </div>
        </>
      ) : (
        <>
          <Img src={pic.src} style={{position: 'absolute', left: 0, top: H - picH, width: '100%', height: picH, objectFit: 'cover', objectPosition: '100% 50%', maskImage: FADE_TOP, WebkitMaskImage: FADE_TOP}} />
          <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: H - picH * 0.86, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <Title size={size} ink={T.ink} center kicker sealK={0.62} />
          </div>
        </>
      )}
      <Logo height={H * 0.04} style={{right: W * 0.065, bottom: H * 0.042, opacity: 0.95}} />
    </AbsoluteFill>
  );
};

/** One chapter of the fallback spectrum: its background colour, optionally one glyph in its headline face. */
const Band: React.FC<{c: Chapter; w: number; h: number}> = ({c, w, h}) => (
  <div style={{width: w, height: h, background: c.palette.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0}}>
    {COVER.bandGlyph ? <span style={{fontFamily: fam(c.font), fontSize: Math.min(w, h) * 0.66, color: c.palette.ink, lineHeight: 1}}>{COVER.bandGlyph}</span> : null}
  </div>
);

/** No AI picture: the chapter spectrum on paper where the picture would be, the same title layout in ink. */
const Fallback: React.FC<{r: Ratio}> = ({r}) => {
  const {width: W, height: H} = useVideoConfig();
  const lines = titleLines();
  const n = ERA_CHAPTERS.length;
  if (r === '3x4') {
    const top = H * 0.42;
    return (
      <Paper bg={PAPER.bg} vignette={0.16} grain={0.04}>
        <div style={{position: 'absolute', left: 0, top, display: 'flex'}}>
          {ERA_CHAPTERS.map((c) => (
            <Band key={c.id} c={c} w={W / n + 0.5} h={H - top} />
          ))}
        </div>
        <div style={{position: 'absolute', left: 0, right: 0, top: top - 10, height: 10, background: PAPER.ink}} />
        <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: top - 10, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <Title size={portraitSize(W)} ink={PAPER.ink} center kicker sealK={0.62} />
        </div>
        <Logo height={H * 0.04} style={{left: W * 0.06, top: H * 0.04}} />
      </Paper>
    );
  }
  const bandsW = W * (r === '16x9' ? 0.46 : 0.42);
  const left = W * 0.055;
  const size = fitTitle(lines, W - bandsW - left - W * 0.04, H * (lines.length > 1 ? 0.125 : 0.17));
  return (
    <Paper bg={PAPER.bg} vignette={0.16} grain={0.04}>
      <div style={{position: 'absolute', top: 0, right: 0, display: 'flex', height: H}}>
        {ERA_CHAPTERS.map((c) => (
          <Band key={c.id} c={c} w={bandsW / n + 0.5} h={H} />
        ))}
      </div>
      <div style={{position: 'absolute', top: 0, right: bandsW, width: 10, height: H, background: PAPER.ink}} />
      <div style={{position: 'absolute', left, top: 0, bottom: H * 0.1, display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <Title size={size} ink={PAPER.ink} />
      </div>
      <Logo height={H * 0.055} style={{left, top: H * 0.06}} />
    </Paper>
  );
};

export const Cover: React.FC = () => {
  const {width: W, height: H} = useVideoConfig();
  const r = ratioOf(W, H);
  const pic = usePicture(r);
  if (pic === undefined) return <AbsoluteFill style={{background: T.bg}} />; // still looking; the frame is held
  if (pic === null) return <Fallback r={r} />;
  if (r === '3x4') return <Portrait pic={pic} />;
  return pic.own ? <LandscapeFull src={pic.src} /> : <LandscapeBand src={pic.src} />;
};
