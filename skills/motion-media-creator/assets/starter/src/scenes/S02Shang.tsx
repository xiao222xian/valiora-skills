import React, {useId, useMemo} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS} from '../timeline';
import {E, Pt, hexA, lerp, partialPolyline, polyline, prog, rng, smoothPath, window01} from '../lib/anim';
import {BODY, MONO, SERIF} from '../lib/fonts';
import {ORACLE, squareSpiral} from '../lib/glyphs';
import {useLayout} from '../lib/layout';

const C2 = CHAPTERS[2];
const P = C2.palette;
const BONE = '#D9CBA6';
const INCISE = '#4A3420';
const VERD = '#6E9C86';
const VERD_MID = '#5d8573';
const VERD_HI = '#A9CDB8';
const CAST_INK = '#0c0f0c';

type Crack = {pts: Pt[]; at: number; dur: number; w: number};

/** Branching heat cracks. The first crack of each pit is the 卜 shape: a stem plus one side branch. */
const growCracks = (seed: number, ox: number, oy: number, at: number, scale: number, upLen = 70): Crack[] => {
  const r = rng(seed);
  const out: Crack[] = [];
  const walk = (x: number, y: number, ang: number, len: number, t0: number, depth: number, w: number) => {
    const n = 7;
    const pts: Pt[] = [[x, y]];
    let a = ang;
    for (let i = 1; i <= n; i++) {
      a += (r() - 0.5) * 0.45;
      x += Math.cos(a) * (len / n);
      y += Math.sin(a) * (len / n);
      pts.push([x, y]);
    }
    const dur = 10 + len * 0.12;
    out.push({pts, at: t0, dur, w});
    if (depth > 0) {
      const kids = 1 + Math.floor(r() * 2);
      for (let k = 0; k < kids; k++) {
        const f = 0.3 + r() * 0.6;
        const idx = Math.floor(f * n);
        const [bx, by] = pts[idx];
        const side = r() < 0.5 ? -1 : 1;
        walk(bx, by, ang + side * (0.5 + r() * 0.7), len * (0.38 + r() * 0.3), t0 + dur * f, depth - 1, w * 0.62);
      }
    }
  };
  // 卜: vertical stem upward, then one branch to the right
  const stem: Pt[] = [];
  for (let i = 0; i <= 6; i++) stem.push([ox + (r() - 0.5) * 4, oy - (i / 6) * 96 * scale]);
  out.push({pts: stem, at, dur: 12, w: 3.2});
  const bx = stem[3][0];
  const by = stem[3][1];
  out.push({pts: [[bx, by], [bx + 26 * scale, by - 20 * scale], [bx + 52 * scale, by - 34 * scale]], at: at + 9, dur: 9, w: 2.8});
  // walk() always draws the same number of random values, so upLen only rescales this branch
  walk(ox, oy - 96 * scale, -Math.PI / 2 - 0.3, upLen * scale, at + 20, 2, 2);
  walk(bx + 52 * scale, by - 34 * scale, -0.4, 60 * scale, at + 22, 2, 1.8);
  walk(ox, oy, Math.PI / 2 + 0.2, 60 * scale, at + 24, 1, 1.8);
  return out;
};

const plastronPath = (cx: number, cy: number, s: number) => {
  const half: Pt[] = [
    [0, -380], [110, -372], [196, -346], [232, -300], [222, -252], [252, -214], [272, -150], [278, -60],
    [270, 40], [250, 118], [264, 168], [242, 232], [204, 300], [150, 350], [86, 376], [40, 388], [0, 368],
  ];
  const pts: Pt[] = [...half, ...half.slice(1, -1).reverse().map(([x, y]) => [-x, y] as Pt)];
  return smoothPath(pts.map(([x, y]) => [cx + x * s * 1.22, cy + y * s] as Pt), true, 0.45);
};

export const S02Shang: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  // SVG ids are document-global and the outro index mounts this scene again: keep them unique
  const uid = useId().replace(/[^A-Za-z0-9_-]/g, '');
  const ref = (name: string) => `s02-${name}-${uid}`;

  // ---------- Part A layout ----------
  const s = vertical ? 0.8 : 1;
  const pcx = vertical ? W / 2 : W * 0.33;
  const pcy = vertical ? H * 0.37 : H * 0.515;

  // pits (钻凿) in rows; three are fired in sequence
  const pits = useMemo(() => {
    const out: {x: number; y: number}[] = [];
    for (let row = 0; row < 6; row++) {
      for (const side of [-1, 1]) {
        for (let col = 0; col < 2; col++) {
          out.push({x: pcx + side * (78 + col * 112) * s, y: pcy + (-250 + row * 104) * s});
        }
      }
    }
    return out;
  }, [pcx, pcy, s]);
  const fired = [8, 3, 17, 20, 13];
  const fireAt = [16, 70, 96, 118, 140];
  const cracks = useMemo(
    // pit 3 sits close to the rim: its upward branch is shortened so the clip never shows a hard cut
    () => fired.flatMap((pi, k) => growCracks(100 + k, pits[pi].x, pits[pi].y - 18 * s, fireAt[k] + 10, k === 0 ? 1.05 * s : 0.8 * s, k === 1 ? 40 : 70)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pits, s],
  );

  // glyph columns carved on the right half, read right-to-left
  const glyphs = ['日', '月', '山', '水', '人', '雨', '木', '火'];
  const gSize = 70 * s;
  const glyphPos = glyphs.map((g, k) => {
    const col = Math.floor(k / 4);
    const row = k % 4;
    return {g, x: pcx + (232 - col * 116) * s - gSize / 2, y: pcy + (-200 + row * 112) * s - gSize / 2, at: 120 + k * 9};
  });

  // count lands by local 184, so any still taken after that (e.g. the outro index) reads 4,500
  const count = Math.round(interpolate(frame, [136, 184], [0, 4500], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E.outCubic}));

  // ---------- A -> B: hard-edged mirror wipe opening from the central flange ----------
  const partB = 228; // bronze half begins
  const t0 = partB - 12;
  const wipe = prog(frame, t0, 28, E.outCubic);
  const boneOut = prog(frame, partB - 4, 22, E.inCubic);
  const showBone = frame < t0 + 30; // the wipe has fully covered it by t0 + 28
  const showBronze = frame >= t0;

  // ---------- Part B layout ----------
  const END = 408;
  const bcx = W / 2;
  const bcy = vertical ? 800 : H * 0.47;
  const bs = vertical ? 0.72 : 1;
  const zoneTop = vertical ? 330 : 130;
  const zoneBottom = vertical ? 1530 : 930;
  const field = useMemo(() => {
    const cells: {pts: Pt[]; d: number}[] = [];
    const unit = 9 * bs;
    const step = 64 * bs;
    const cols = Math.ceil(W / 2 / step) + 1;
    const up = Math.ceil((bcy - zoneTop) / step) + 1;
    const down = Math.ceil((zoneBottom - bcy) / step) + 1;
    let maxD = 1;
    for (let y = -up; y <= down; y++) {
      for (let x = -cols; x <= cols; x++) {
        const d = Math.hypot(x, y * 1.4);
        maxD = Math.max(maxD, d);
        cells.push({pts: squareSpiral(bcx + x * step, bcy + y * step, unit, 9, (x + y) % 2 === 0 ? 1 : -1), d});
      }
    }
    return cells.map((c) => ({...c, d: c.d / maxD}));
  }, [W, bcx, bcy, bs, zoneTop, zoneBottom]);
  // keep the ground pattern clear of the HUD header and the ruler
  const fieldMask = `linear-gradient(to bottom, transparent 0px, transparent ${zoneTop}px, #000 ${zoneTop + 100}px, #000 ${zoneBottom - 110}px, transparent ${zoneBottom}px)`;

  // angular relief, the way bronze casts read: square-cut horn, almond 臣 eye, kui-dragon body, hooked jaw
  const half = (sx: number) => {
    const k = (x: number) => (bcx + sx * x * bs).toFixed(1);
    const y = (v: number) => (bcy + v * bs).toFixed(1);
    const pl = (pts: [number, number][]) => 'M' + pts.map(([x, v]) => `${k(x)},${y(v)}`).join('L');
    return [
      pl([[44, -96], [44, -214], [398, -214], [398, -116], [314, -116], [314, -172], [356, -172]]),
      `M${k(104)},${y(-40)} Q${k(200)},${y(-118)} ${k(296)},${y(-40)} Q${k(200)},${y(26)} ${k(104)},${y(-40)} Z M${k(104)},${y(-40)} L${k(70)},${y(-6)}`,
      pl([[296, -40], [488, -40], [488, 92], [404, 92], [404, 22], [446, 22]]),
      pl([[56, 44], [56, 150], [314, 150], [314, 74], [226, 74], [226, 112], [268, 112]]),
      pl([[540, -214], [540, 150], [600, 150]]),
    ];
  };
  const reliefPaths = [1, -1].flatMap((sx) => half(sx).map((d, k) => ({d, k, sx})));
  const flange = Array.from({length: 9}, (_, k) => ({x: bcx - 16 * bs, y: bcy + (-230 + k * 52) * bs, w: 32 * bs, h: 34 * bs, at: t0 + k * 1.5}));

  // continuous motion to the end of the chapter: slow push on the mask, counter-drift on the ground, one raking glint
  const push = lerp(1, 1.05, prog(frame, t0, END - t0, E.linear));
  const drift = Math.max(0, frame - t0);
  const sheenOn = window01(frame, 300, 380, 14, 18);
  const sheenX = lerp(bcx - 820 * bs, bcx + 820 * bs, prog(frame, 300, 80, E.inOutSine));
  const textBack = prog(frame, partB + 30, 24, E.outCubic);

  return (
    <Paper bg={P.bg} dark vignette={0.45}>
      {/* ---------- Part A: oracle bone ---------- */}
      {showBone && (
        <AbsoluteFill style={{opacity: 1 - 0.5 * boneOut, transform: `scale(${1 - 0.04 * boneOut})`}}>
          <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
            <defs>
              <radialGradient id={ref('bone')} cx="45%" cy="40%" r="70%">
                <stop offset="0" stopColor="#E8DDBF" />
                <stop offset="0.7" stopColor={BONE} />
                <stop offset="1" stopColor="#A89A74" />
              </radialGradient>
              <filter id={ref('bone-tex')}>
                <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={4} result="n" />
                <feColorMatrix in="n" type="matrix" values="0 0 0 0 0.35  0 0 0 0 0.28  0 0 0 0 0.18  0 0 0 0.22 0" result="spots" />
                <feComposite in="spots" in2="SourceGraphic" operator="in" result="sp" />
                <feMerge>
                  <feMergeNode in="SourceGraphic" />
                  <feMergeNode in="sp" />
                </feMerge>
              </filter>
              <radialGradient id={ref('heat')}>
                <stop offset="0" stopColor="#FFE2A0" />
                <stop offset="0.35" stopColor="#F08A2A" />
                <stop offset="1" stopColor="#B33A10" stopOpacity={0} />
              </radialGradient>
              {/* cracks stay on the shell: same user space as the crack group (inside the slide-in translate) */}
              <clipPath id={ref('plastron')}>
                <path d={plastronPath(pcx, pcy, s * 0.97)} />
              </clipPath>
            </defs>
            <g transform={`translate(0 ${(1 - prog(frame, 0, 24, E.outCubic)) * 30})`}>
              <path d={plastronPath(pcx + 10, pcy + 14, s)} fill="#000" opacity={0.35} style={{filter: 'blur(14px)'}} />
              <path d={plastronPath(pcx, pcy, s)} fill={`url(#${ref('bone')})`} filter={`url(#${ref('bone-tex')})`} />
              {/* scute seams */}
              <g stroke={hexA('#7a6a48', 0.55)} strokeWidth={1.6} fill="none">
                <path d={polyline([[pcx, pcy - 372 * s], [pcx + 4, pcy - 200 * s], [pcx - 3, pcy], [pcx + 3, pcy + 200 * s], [pcx, pcy + 366 * s]])} />
                {[-262, -128, 34, 196, 300].map((yy, k) => (
                  <path key={k} d={smoothPath([[pcx - 250 * s, pcy + (yy + 14) * s], [pcx, pcy + yy * s], [pcx + 250 * s, pcy + (yy + 14) * s]])} />
                ))}
              </g>
              {/* pits */}
              {pits.map((p, k) => (
                <ellipse key={k} cx={p.x} cy={p.y} rx={13 * s} ry={22 * s} fill={hexA('#5a4528', 0.35)} stroke={hexA('#3b2c18', 0.4)} strokeWidth={1} />
              ))}
              {/* heat glow */}
              {fired.map((pi, k) => {
                const g = prog(frame, fireAt[k], 8, E.outCubic) * (1 - prog(frame, fireAt[k] + 14, 26, E.inCubic));
                if (g <= 0) return null;
                const flick = 0.85 + 0.15 * Math.sin(frame * 1.7 + k);
                return <circle key={k} cx={pits[pi].x} cy={pits[pi].y} r={48 * s * flick} fill={`url(#${ref('heat')})`} opacity={g} />;
              })}
              {/* cracks */}
              <g stroke="#2E2012" fill="none" strokeLinecap="round" strokeLinejoin="round" clipPath={`url(#${ref('plastron')})`}>
                {cracks.map((c, k) => {
                  const t = prog(frame, c.at, c.dur, E.outCubic);
                  if (t <= 0) return null;
                  return <path key={k} d={polyline(partialPolyline(c.pts, t))} strokeWidth={c.w * s} />;
                })}
              </g>
              {/* carved glyphs: dark cut + light lip to read as incised */}
              {glyphPos.map(({g, x, y, at}) => {
                const t = prog(frame, at, 22, E.inOutSine);
                if (t <= 0) return null;
                const tr = `translate(${x} ${y}) scale(${gSize / 100})`;
                return (
                  <g key={g}>
                    <path d={ORACLE[g]} transform={`translate(${x + 1.4} ${y + 1.6}) scale(${gSize / 100})`} fill="none" stroke={hexA('#fff6dc', 0.7)} strokeWidth={4.4} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - t} />
                    <path d={ORACLE[g]} transform={tr} fill="none" stroke={INCISE} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - t} />
                  </g>
                );
              })}
            </g>
          </svg>

          <div style={{position: 'absolute', left: vertical ? 70 : W * 0.58, top: vertical ? 1080 : 236, width: vertical ? W - 140 : 680}}>
            <div style={{display: 'flex', alignItems: 'flex-end', gap: vertical ? 22 : 28}}>
              <StaggerText text="卜" at={34} font={C2.font} size={vertical ? 130 : 240} color={P.ink} mode="stamp" />
              <div style={{paddingBottom: vertical ? 18 : 30, opacity: prog(frame, 46, 14), fontFamily: BODY, fontSize: vertical ? 30 : 26, color: P.hud, letterSpacing: 2, whiteSpace: 'nowrap'}}>
                <span style={{fontFamily: MONO, letterSpacing: 3}}>BǓ</span> · 字形取自卜兆
              </div>
            </div>
            <Line at={52} color={P.ink} size={34}>
              商代人灼烧龟甲兽骨占卜，
            </Line>
            <Line at={60} color={P.ink} size={34}>
              裂开的兆纹，就是「卜」字的样子。
            </Line>
            <div style={{marginTop: vertical ? 24 : 46, opacity: prog(frame, 132, 14), display: 'flex', alignItems: 'baseline', gap: 16}}>
              <span style={{fontFamily: BODY, fontSize: vertical ? 34 : 30, color: P.ink}}>约</span>
              <span style={{fontFamily: SERIF, fontSize: vertical ? 80 : 104, color: P.accent, fontVariantNumeric: 'tabular-nums', letterSpacing: -1}}>
                {count.toLocaleString('en-US')}
              </span>
              <span style={{fontFamily: BODY, fontSize: vertical ? 34 : 30, color: P.ink}}>个甲骨文单字</span>
            </div>
            <Line at={156} color={hexA(P.ink, 0.78)} size={vertical ? 30 : 26}>
              公认释读的约 1,500 个 · 图中字形为示意
            </Line>
          </div>
        </AbsoluteFill>
      )}

      {/* ---------- Part B: bronze ---------- */}
      {showBronze && (
        <AbsoluteFill style={{clipPath: `inset(0 ${lerp(50, 0, wipe)}% 0 ${lerp(50, 0, wipe)}%)`}}>
          <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, #2a3029 0%, #161a17 70%)'}} />

          {/* thunder-spiral ground (云雷纹): own layer, masked off the HUD, drifting against the push */}
          <svg width={W} height={H} style={{position: 'absolute', inset: 0, maskImage: fieldMask, WebkitMaskImage: fieldMask}}>
            <defs>
              <filter id={ref('cast-field')}>
                <feTurbulence type="fractalNoise" baseFrequency="0.6" numOctaves={2} seed={9} />
                <feDisplacementMap in="SourceGraphic" scale={2.2} />
              </filter>
            </defs>
            <g transform={`translate(${(-drift * 0.15 * bs).toFixed(2)} ${(drift * 0.04 * bs).toFixed(2)})`}>
              <g stroke={VERD} fill="none" strokeWidth={4.5 * bs} strokeLinecap="square" opacity={0.28} filter={`url(#${ref('cast-field')})`}>
                {field.map((c, k) => {
                  const t = prog(frame, t0 + 4 + c.d * 34, 20, E.outCubic);
                  if (t <= 0) return null;
                  return <path key={k} d={polyline(partialPolyline(c.pts, t))} />;
                })}
              </g>
            </g>
          </svg>

          {/* mirrored taotie relief */}
          <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
            <defs>
              <filter id={ref('cast')}>
                <feTurbulence type="fractalNoise" baseFrequency="0.6" numOctaves={2} seed={9} />
                <feDisplacementMap in="SourceGraphic" scale={2.2} />
              </filter>
              <linearGradient id={ref('sheen')} x1="0" y1="0" x2="1" y2="0">
                <stop offset="0" stopColor="#ffffff" stopOpacity={0} />
                <stop offset="0.5" stopColor="#F2FFF6" stopOpacity={0.5} />
                <stop offset="1" stopColor="#ffffff" stopOpacity={0} />
              </linearGradient>
              {/* the glint only lands on raised metal */}
              <mask id={ref('relief')} maskUnits="userSpaceOnUse" x={-W} y={-H} width={3 * W} height={3 * H}>
                <g stroke="#fff" fill="none" strokeLinejoin="miter" strokeLinecap="square">
                  {reliefPaths.map(({d, k, sx}) => (
                    <path key={`${sx}${k}`} d={d} strokeWidth={26 * bs} />
                  ))}
                </g>
                {flange.map((f, k) => (
                  <rect key={k} x={f.x} y={f.y} width={f.w} height={f.h} fill="#fff" />
                ))}
              </mask>
            </defs>
            <g transform={`translate(${bcx} ${bcy}) scale(${push.toFixed(5)}) translate(${-bcx} ${-bcy})`}>
              <g filter={`url(#${ref('cast')})`} strokeLinecap="round" fill="none">
                {/* central flange (扉棱): the seam the wipe opens from */}
                {flange.map((f, k) => {
                  const t = prog(frame, f.at, 10, E.outCubic);
                  return <rect key={k} x={f.x} y={f.y + (f.h * (1 - t)) / 2} width={f.w} height={f.h * t} fill="#A8874F" opacity={0.95} />;
                })}
                {reliefPaths.map(({d, k, sx}) => {
                  const t = prog(frame, t0 + 6 + k * 6, 30, E.inOutCubic);
                  return (
                    <g key={`${sx}${k}`} strokeLinejoin="miter" strokeLinecap="square">
                      <path d={d} stroke={CAST_INK} strokeWidth={40 * bs} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - t} opacity={0.92} />
                      <path d={d} stroke={VERD_MID} strokeWidth={24 * bs} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - t} />
                      <path d={d} stroke={VERD_HI} strokeWidth={9 * bs} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - t} transform={`translate(${-2 * bs} ${-2.5 * bs})`} opacity={0.85} />
                    </g>
                  );
                })}
                {[1, -1].map((sx) => {
                  const t = prog(frame, partB + 30, 14, E.outBack);
                  return <circle key={sx} cx={bcx + sx * 200 * bs} cy={bcy - 40 * bs} r={Math.max(0, 24 * bs * t)} fill={CAST_INK} stroke={VERD_HI} strokeWidth={7 * bs} />;
                })}
              </g>
              {sheenOn > 0 && (
                <g mask={`url(#${ref('relief')})`} style={{mixBlendMode: 'screen'}} opacity={sheenOn}>
                  <rect
                    x={sheenX - 170 * bs}
                    y={bcy - 420 * bs}
                    width={340 * bs}
                    height={840 * bs}
                    fill={`url(#${ref('sheen')})`}
                    transform={`rotate(20 ${sheenX.toFixed(1)} ${bcy})`}
                  />
                </g>
              )}
            </g>
          </svg>

          <div style={{position: 'absolute', left: vertical ? 70 : 150, bottom: vertical ? 440 : 150, isolation: 'isolate'}}>
            {/* soft dark bed so the copy never sits directly on the pattern */}
            <div
              style={{
                position: 'absolute',
                left: -150,
                right: -170,
                top: -100,
                bottom: -60,
                zIndex: -1,
                opacity: textBack,
                background: 'radial-gradient(ellipse at 42% 55%, rgba(14,17,15,0.86) 0%, rgba(14,17,15,0.64) 40%, rgba(14,17,15,0) 72%)',
              }}
            />
            <StaggerText text="铸鼎象物" at={partB + 36} step={5} font={C2.font} size={vertical ? 96 : 104} color={'#E3D6B2'} mode="rise" letterSpacing={12} />
            <Line at={partB + 52} color={hexA('#E3D6B2', 0.78)} size={vertical ? 30 : 26} style={{marginTop: 6}}>
              ——《左传 · 宣公三年》　原指夏铸九鼎
            </Line>
            <Line at={partB + 64} color={hexA('#E3D6B2', 0.9)} size={vertical ? 34 : 30} style={{marginTop: 14}}>
              商代青铜礼器上，兽面纹与云雷纹层层回旋。
            </Line>
          </div>
        </AbsoluteFill>
      )}

      {/* bright edges of the wipe, mirrored about the flange */}
      {showBronze &&
        wipe < 1 &&
        [-1, 1].map((sd) => (
          <div
            key={sd}
            style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              left: bcx + sd * (W / 2) * wipe - 1,
              width: 2,
              background: VERD_HI,
              boxShadow: `0 0 18px 3px ${hexA(VERD_HI, 0.55)}`,
              opacity: 0.85 * (1 - wipe * wipe),
            }}
          />
        ))}
    </Paper>
  );
};
