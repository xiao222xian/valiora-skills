import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {rulerGeometry} from '../components/HUD';
import {CHAPTERS, ERA_CHAPTERS} from '../timeline';
import {E, hexA, lerp, prog, rng} from '../lib/anim';
import {BODY, fam, useFontsReady} from '../lib/fonts';
import {bitmap} from '../lib/bitmap';
import {HAN16, ORACLE} from '../lib/glyphs';
import {SEAL_HAN} from '../lib/glyphs-han';
import {useLayout} from '../lib/layout';

const C13 = CHAPTERS[13];
const P = C13.palette;
const RED = P.accent;

/** Squares fly in and lock to a grid: either a hand-set grid or a font raster. */
const PixelText: React.FC<{grid: boolean[][]; px: number; at: number; color: string; seed: number; scatter?: number}> = ({grid, px, at, color, seed, scatter = 1}) => {
  const frame = useCurrentFrame();
  const r = rng(seed);
  const rows = grid.length;
  const cols = grid[0]?.length ?? 0;
  const cells: React.ReactNode[] = [];
  grid.forEach((row, y) =>
    row.forEach((on, x) => {
      const ox = (r() - 0.5) * 900 * scatter;
      const oy = (r() - 0.5) * 700 * scatter;
      const d = r() * 10 * scatter + x * 0.5 * scatter;
      if (!on) return;
      const t = prog(frame, at + d, 18, E.outCubic);
      cells.push(
        <rect
          key={`${x}-${y}`}
          x={x * px + ox * (1 - t)}
          y={y * px + oy * (1 - t)}
          width={px - Math.max(1, px * 0.08)}
          height={px - Math.max(1, px * 0.08)}
          fill={color}
          opacity={t}
          transform={`rotate(${(1 - t) * 90} ${x * px + px / 2} ${y * px + px / 2})`}
        />,
      );
    }),
  );
  return (
    <svg width={cols * px} height={rows * px} style={{overflow: 'visible', display: 'block'}}>
      {cells}
    </svg>
  );
};

const Spiral: React.FC<{size: number; color: string}> = ({size, color}) => (
  <svg width={size} height={size} viewBox="-50 -50 100 100">
    <path d={Array.from({length: 90}, (_, j) => `${j ? 'L' : 'M'}${(Math.cos(j * 0.21) * j * 0.45).toFixed(1)},${(Math.sin(j * 0.21) * j * 0.45).toFixed(1)}`).join('')} fill="none" stroke={color} strokeWidth={7} strokeLinecap="round" />
  </svg>
);
const Drawn: React.FC<{d: string; size: number; color: string}> = ({d, size, color}) => (
  <svg width={size} height={size} viewBox="0 0 100 100">
    <path d={d} fill="none" stroke={color} strokeWidth={7} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const ZOOM_AT = 96;

export const S13Today: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const ready = useFontsReady();
  const ruler = rulerGeometry(W, H, vertical);

  const partA = 1 - prog(frame, ZOOM_AT - 10, 12, E.inCubic);
  const finalIn = prog(frame, 222, 18, E.outCubic);

  // spectrum band area keeps the HUD header and ruler on plain paper
  const bandTop = vertical ? 330 : 128;
  const bandBottom = vertical ? 1540 : 974;
  const n = ERA_CHAPTERS.length;
  const bandW = W / n;
  const glyphSize = vertical ? 64 : 104;
  // zoom-out: start on the present-day pixel 汉, pull back to all thirteen eras
  const zp = prog(frame, ZOOM_AT + 4, 56, E.inOutCubic);
  const zoom = lerp(vertical ? 9 : 7.5, 1, zp);
  const originX = (n - 0.5) * bandW;
  const panX = lerp(W / 2 - originX, 0, zp); // the pixel 汉 starts centred, then the camera pulls back
  const originY = (bandBottom - bandTop) / 2;
  // then the bands fold back into the ruler they came from
  const fold = prog(frame, 204, 26, E.inOutCubic);
  const clipTop = lerp(bandTop, ruler.y - 2, fold);
  const clipH = lerp(bandBottom - bandTop, 4, fold);
  const spectrumOn = frame >= ZOOM_AT && fold < 1;

  const glyphFor = (c: (typeof ERA_CHAPTERS)[number], k: number) => {
    if (c.no === 1) return <Spiral size={glyphSize} color={c.palette.ink} />;
    if (c.no === 2) return <Drawn d={ORACLE['人']} size={glyphSize} color={c.palette.ink} />;
    // 小篆 has no simplified 汉: the Qin band shows the seal-script 漢
    if (c.no === 4) return <Drawn d={SEAL_HAN} size={glyphSize} color={c.palette.ink} />;
    if (c.no === 13) return <PixelText grid={HAN16} px={glyphSize / 16} at={ZOOM_AT - 6} color={c.palette.ink} seed={13} scatter={0.35} />;
    return <span style={{fontFamily: fam(c.font), fontSize: glyphSize, color: c.palette.ink, lineHeight: 1, opacity: prog(frame, ZOOM_AT + 20 + (n - k) * 2, 12, E.outCubic)}}>汉</span>;
  };

  return (
    <Paper bg={P.bg} vignette={0.12} fibre={0.12}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5}}>
        {Array.from({length: 13}, (_, k) => (
          <line key={k} x1={(k * W) / 12} x2={(k * W) / 12} y1={0} y2={H} stroke={hexA(P.ink, 0.05)} strokeWidth={1} />
        ))}
      </svg>

      {/* 1978, assembled from pixels */}
      {partA > 0 && (
        <AbsoluteFill style={{opacity: partA}}>
          <div style={{position: 'absolute', left: vertical ? 70 : 150, top: vertical ? 400 : 200}}>
            {ready && <PixelText grid={bitmap('1978', 'ZL-HeiHeavy', vertical ? 30 : 40, vertical ? 9 : 11)} px={vertical ? 30 : 24} at={0} color={RED} seed={1978} />}
          </div>
          <div style={{position: 'absolute', left: vertical ? 70 : 150, top: vertical ? 720 : 500, width: vertical ? W - 140 : 1100}}>
            <StaggerText text="改革开放" at={14} step={4} font={C13.font} size={vertical ? 110 : 120} color={P.ink} mode="rise" letterSpacing={10} />
            <Line at={30} color={P.ink} size={vertical ? 34 : 32} style={{marginTop: 16}}>
              1978 年 12 月，中共十一届三中全会召开，
            </Line>
            <Line at={36} color={P.ink} size={vertical ? 34 : 32}>
              改革开放由此起步。
            </Line>
            <Line at={48} color={hexA(P.ink, 0.75)} size={vertical ? 30 : 30} style={{marginTop: 10}}>
              2010 年，中国国内生产总值超过日本，居世界第二。
            </Line>
          </div>
        </AbsoluteFill>
      )}

      {spectrumOn && (
        <div style={{position: 'absolute', left: 0, right: 0, top: clipTop, height: clipH, overflow: 'hidden'}}>
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: W,
              height: bandBottom - bandTop,
              transform: `translate(${panX}px, 0) scale(${zoom})`,
              transformOrigin: `${originX}px ${originY}px`,
              display: 'flex',
            }}
          >
            {ERA_CHAPTERS.map((c, k) => (
              <div
                key={c.id}
                style={{
                  width: bandW + 0.5,
                  height: '100%',
                  background: c.palette.bg,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 18,
                }}
              >
                <div style={{height: glyphSize * 1.15, display: 'flex', alignItems: 'center'}}>{glyphFor(c, k)}</div>
                <div style={{fontFamily: BODY, fontSize: vertical ? 17 : 20, color: hexA(c.palette.ink, 0.8), writingMode: 'vertical-rl', letterSpacing: 4, opacity: prog(frame, ZOOM_AT + 40, 14, E.outCubic)}}>
                  {c.short}
                </div>
              </div>
            ))}
          </div>
          <div style={{position: 'absolute', left: 0, right: 0, top: vertical ? 30 : 26, textAlign: 'center', opacity: prog(frame, 150, 14, E.outCubic) * (1 - prog(frame, 198, 8, E.inCubic))}}>
            <div style={{display: 'inline-block', background: hexA('#ffffff', 0.9), padding: '12px 28px 14px', boxShadow: '0 10px 30px rgba(0,0,0,0.12)'}}>
              <div style={{fontFamily: fam('ZL-HeiHeavy'), fontSize: vertical ? 42 : 46, color: P.ink, letterSpacing: 8}}>十三章，十三种字的样子</div>
              <div style={{fontFamily: BODY, fontSize: vertical ? 22 : 22, color: hexA(P.ink, 0.75), letterSpacing: 3, marginTop: 6}}>字体、字形为风格示意，非各代原貌；甲骨一格为「人」字</div>
            </div>
          </div>
        </div>
      )}

      {finalIn > 0 && (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity: finalIn}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 6, marginTop: vertical ? -80 : 0}}>
            <StaggerText text="历史，仍在书写" at={224} step={5} font="ZL-Hei" size={vertical ? 76 : 96} color={P.ink} mode="rise" letterSpacing={12} />
            <div style={{width: vertical ? 6 : 8, height: vertical ? 84 : 104, background: RED, marginLeft: 10, opacity: Math.floor(frame / 15) % 2 === 0 ? 1 : 0}} />
          </div>
        </AbsoluteFill>
      )}
    </Paper>
  );
};
