import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Paper} from '../components/Paper';
import {StaggerText, Line} from '../components/Type';
import {BrandSeal} from '../brand/Seal';
import {rulerGeometry} from '../components/HUD';
import {CHAPTERS, SUBTITLE, TITLE} from '../timeline';
import {E, Pt, clamp01, hexA, lerp, prog, rng, smoothPath} from '../lib/anim';
import {MONO} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const P = CHAPTERS[0].palette;

const mixHex = (a: string, b: string, t: number) => {
  const na = parseInt(a.slice(1), 16);
  const nb = parseInt(b.slice(1), 16);
  const c = [16, 8, 0].map((s) => Math.round(lerp((na >> s) & 255, (nb >> s) & 255, clamp01(t))));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
};

// Same silhouette as lib/brush.ts (pressed start, lifting tail), plus `sq`, which squares the
// outline off (superellipse) so the landing stroke becomes a rule with blunt ends.
const press = (u: number) => 1 + 0.32 * Math.exp(-(((u + 0.78) / 0.16) ** 2));
const lift = (u: number) => 1 - 0.72 * ((u + 1) / 2) ** 2.4;
const shapeAt = (u: number, taper: number) => lerp(1, press(u) * lift(u), taper);
const strokeOutline = (cx: number, cy: number, rx: number, ry: number, taper: number, sq: number, n = 240) => {
  const ex = 1 - 0.96 * clamp01(sq);
  let d = '';
  for (let k = 0; k <= n; k++) {
    const th = (k / n) * Math.PI * 2;
    const c = Math.cos(th);
    const s = Math.sin(th);
    const u = Math.sign(c) * Math.abs(c) ** ex;
    const v = Math.sign(s) * Math.abs(s) ** ex;
    const x = cx + rx * u;
    const y = cy + ry * v * shapeAt(u, taper) + taper * ry * 0.18 * u;
    d += `${k ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
  }
  return d + 'Z';
};

// 飞白: dry-brush filaments, cut out of the stroke through a mask so the real paper shows.
// u runs -1 (head) .. 1 (tip); every filament lives in the back half and stops short of the tip.
// Each filament is a ribbon that starts hair-thin, swells, and breaks into 1-4 pieces.
type Filament = {oy: number; u0: number; u1: number; w: number; a: number; bow: number; wav: number; ph: number; delay: number; pieces: [number, number][]};
const FILAMENTS: Filament[] = (() => {
  const r = rng(42);
  const out: Filament[] = [];
  for (let i = 0; i < 52; i++) {
    const broad = i >= 44; // a few wide, faint scrapes for the mottled dry tone
    const side = r() * 2 - 1;
    const oy = Math.sign(side) * Math.abs(side) ** 0.75 * 0.86; // denser towards the edges
    const u0 = -0.12 + 0.72 * r() ** 0.8;
    const u1 = Math.min(0.97, u0 + 0.26 + r() * 0.6);
    const w = broad ? 5 + r() * 8 : 0.8 + r() * r() * 4.6;
    const a = broad ? 0.22 + r() * 0.2 : 0.62 + r() * 0.38;
    const bow = (r() * 2 - 1) * 0.22;
    const wav = r() * 0.05;
    const ph = r() * 6.28;
    const delay = r() * 0.45;
    const nBreaks = Math.floor(r() * 4);
    const cuts = Array.from({length: nBreaks}, () => 0.12 + r() * 0.8).sort((p, q) => p - q);
    const pieces: [number, number][] = [];
    let s = 0;
    cuts.forEach((c) => {
      if (c - s > 0.06) pieces.push([s, c]);
      s = c + 0.015 + r() * 0.07;
    });
    if (1 - s > 0.05) pieces.push([s, 1]);
    out.push({oy, u0, u1, w, a, bow, wav, ph, delay, pieces});
  }
  return out;
})();

const smooth01 = (x: number) => {
  const t = clamp01(x);
  return t * t * (3 - 2 * t);
};

/** Ribbon outline(s) of one filament, revealed up to `tr` along its length. */
const filamentPath = (f: Filament, cx: number, cy: number, rx: number, ry: number, taper: number, tr: number, k: number) => {
  let d = '';
  for (const [ta, tb0] of f.pieces) {
    const tb = Math.min(tb0, tr);
    if (tb - ta < 0.008) continue;
    const N = Math.max(3, Math.ceil((tb - ta) * 36));
    const up: Pt[] = [];
    const lo: Pt[] = [];
    for (let j = 0; j <= N; j++) {
      const t = lerp(ta, tb, j / N);
      const u = lerp(f.u0, f.u1, t);
      const half = ry * Math.sqrt(Math.max(0, 1 - u * u)) * shapeAt(u, taper);
      const off = Math.max(-0.97, Math.min(0.97, f.oy + f.bow * Math.sin(Math.PI * t) + f.wav * Math.sin(t * 9 + f.ph)));
      const x = cx + rx * u;
      const y = cy + taper * ry * 0.18 * u + off * half;
      const ends = 0.3 + 0.7 * smooth01(Math.min((t - ta) / 0.05, (tb - t) / 0.05));
      const hw = 0.5 * f.w * k * (0.18 + 0.82 * smooth01(t / 0.32)) * ends;
      up.push([x, y - hw]);
      lo.push([x, y + hw]);
    }
    d += smoothPath([...up, ...lo.reverse()], true);
  }
  return d;
};

// three concentric soft rings around the bloom: [radius factor, opacity, seed]
const WASH: [number, number, number][] = [
  [1.08, 0.38, 4],
  [1.25, 0.18, 11],
  [1.45, 0.08, 23],
];

export const S00Opening: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const ruler = rulerGeometry(W, H, vertical);

  const cx = W / 2;
  const bloomY = H * (vertical ? 0.44 : 0.47);
  const strokeY = H * (vertical ? 0.52 : 0.6);

  // 1. drop (vertical: starts lower and fades in below the platform chrome)
  const fall = prog(frame, 12, 18, E.inCubic);
  const dropY = lerp(vertical ? 180 : -80, bloomY, fall);
  const dropVisible = frame >= 12 && frame < 31;
  const dropA = vertical ? clamp01((dropY - 280) / 70) : 1;

  // 2. bloom, 3. stretch into a stroke, 4. land on the ruler
  const bloom = prog(frame, 30, 54, E.outCubic);
  const R = 236 * bloom + 22 * prog(frame, 56, 40, E.linear);
  const m = prog(frame, 84, 44, E.inOutCubic);
  const land = prog(frame, 246, 40);
  const rxStroke = vertical ? 450 : 760;
  const ryStroke = vertical ? 26 : 30;
  const rulerHalf = (ruler.x1 - ruler.x0) / 2;
  let rx = lerp(R, rxStroke, m);
  let ry = lerp(R, ryStroke, m);
  let scx = cx;
  let scy = lerp(bloomY, strokeY, m);
  rx = lerp(rx, rulerHalf, land);
  ry = lerp(ry, 2, land);
  scx = lerp(scx, (ruler.x0 + ruler.x1) / 2, land);
  scy = lerp(scy, ruler.y, land);
  const taper = m * (1 - land);
  const sq = E.inOutCubic(clamp01((land - 0.3) / 0.4)); // ends square off before the rule takes over
  const disp = lerp(lerp(38, 16, m), 0, land);
  const asRule = land > 0.7;
  const outline = strokeOutline(scx, scy, Math.max(rx, 0.5), Math.max(ry, 0.5), taper, sq);

  const halo = (1 - m) * bloom;
  const dry = prog(frame, 104, 60, E.outCubic) * (1 - land);
  const wick = prog(frame, 112, 150, E.linear); // the wet edge keeps creeping into the fibres
  const wickA = 0.13 * prog(frame, 100, 24, E.outCubic) * (1 - land);
  const fScale = ry / 30;

  const splash = prog(frame, 30, 20, E.outCubic);
  const subOut = prog(frame, 246, 16, E.inOutCubic); // clears the path of the descending stroke
  const titleOut = prog(frame, 250, 22, E.inOutCubic);
  const drift = prog(frame, 124, 126, E.linear); // slow push while the card holds
  const blackIn = 1 - prog(frame, 0, 10, E.linear);

  // ticks pop along the landed rule, one per frame from 284, settling into the HUD's own ticks
  const tickXs = [...ruler.segs.map((s) => s.a), ruler.x1];
  const tickRest = hexA(P.hud, 0.55);

  const titleSize = vertical ? 170 : 200;
  const titleLs = vertical ? 14 : 34;
  const sealSize = vertical ? 76 : 88;

  return (
    <Paper bg={P.bg} vignette={0.22}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="s00-edge" x="-20%" y="-60%" width="140%" height="220%">
            <feTurbulence type="fractalNoise" baseFrequency="0.011 0.018" numOctaves={3} seed={3} />
            <feDisplacementMap in="SourceGraphic" scale={disp} xChannelSelector="R" yChannelSelector="G" />
          </filter>
          <filter id="s00-rule" x="-5%" y="-300%" width="110%" height="700%">
            <feTurbulence type="fractalNoise" baseFrequency="0.011 0.018" numOctaves={3} seed={3} />
            <feDisplacementMap in="SourceGraphic" scale={disp} xChannelSelector="R" yChannelSelector="G" />
          </filter>
          {WASH.map(([, , seed], i) => (
            <filter key={i} id={`s00-wash${i}`} x="-35%" y="-35%" width="170%" height="170%">
              <feTurbulence type="fractalNoise" baseFrequency="0.028" numOctaves={2} seed={seed} result="coarse" />
              <feDisplacementMap in="SourceGraphic" in2="coarse" scale={32} xChannelSelector="R" yChannelSelector="G" result="d1" />
              <feGaussianBlur in="d1" stdDeviation={5 + i} result="soft" />
              <feTurbulence type="fractalNoise" baseFrequency={i === 2 ? '0.11 0.07' : '0.07'} numOctaves={3} seed={seed + 40} result="fibre" />
              <feDisplacementMap in="soft" in2="fibre" scale={12 + 6 * i} xChannelSelector="R" yChannelSelector="B" />
            </filter>
          ))}
          <filter id="s00-wick" x="-10%" y="-200%" width="120%" height="500%">
            <feTurbulence type="fractalNoise" baseFrequency="0.06 0.12" numOctaves={3} seed={17} result="n" />
            <feGaussianBlur in="SourceGraphic" stdDeviation={lerp(2.5, 7, wick)} result="b" />
            <feDisplacementMap in="b" in2="n" scale={lerp(10, 26, wick)} xChannelSelector="R" yChannelSelector="G" />
          </filter>
          <radialGradient id="s00-core">
            <stop offset="0%" stopColor={mixHex('#221e1a', P.ink, m)} />
            <stop offset="78%" stopColor={P.ink} />
            <stop offset="100%" stopColor="#070605" />
          </radialGradient>
          <mask id="s00-dry" maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
            <rect x={0} y={0} width={W} height={H} fill="#fff" />
            {dry > 0.004 &&
              FILAMENTS.map((f, i) => {
                const t = clamp01((dry - f.delay) / 0.55);
                if (t <= 0.01) return null;
                const d = filamentPath(f, scx, scy, rx, ry, taper, t, fScale);
                return d ? <path key={i} d={d} fill="#000" fillOpacity={f.a} /> : null;
              })}
          </mask>
        </defs>

        {halo > 0.01 &&
          WASH.map(([k, o], i) => <circle key={i} cx={cx} cy={bloomY} r={R * k} fill={P.ink} opacity={o * halo} filter={`url(#s00-wash${i})`} />)}

        {frame >= 30 && wickA > 0.005 && <path d={outline} fill={P.ink} opacity={wickA} filter="url(#s00-wick)" mask="url(#s00-dry)" />}

        {frame >= 30 && !asRule && <path d={outline} fill="url(#s00-core)" filter="url(#s00-edge)" mask={dry > 0.004 ? 'url(#s00-dry)' : undefined} />}
        {asRule && <rect x={scx - rx} y={scy - ry} width={2 * rx} height={2 * ry} fill={P.ink} filter={land < 0.999 ? 'url(#s00-rule)' : undefined} />}

        {frame >= 284 &&
          tickXs.map((x, k) => {
            const f0 = 284 + k;
            if (frame <= f0) return null;
            const up = prog(frame, f0, 2, E.outCubic);
            const p = prog(frame, f0, 4, E.linear);
            const half = 5 * up + 8 * Math.sin(Math.PI * p);
            return (
              <line
                key={k}
                x1={x}
                x2={x}
                y1={ruler.y - half}
                y2={ruler.y + half}
                stroke={p >= 1 ? tickRest : mixHex(P.ink, P.hud, p)}
                strokeOpacity={p >= 1 ? 1 : lerp(1, 0.55, p)}
                strokeWidth={lerp(2, 1.2, p)}
              />
            );
          })}

        {frame >= 30 && frame < 52 && (
          <ellipse cx={cx} cy={bloomY} rx={20 + 120 * splash} ry={(20 + 120 * splash) * 0.92} fill="none" stroke={P.ink} strokeWidth={2} opacity={0.45 * (1 - splash)} />
        )}
        {dropVisible && dropA > 0 && <ellipse cx={cx} cy={dropY} rx={9 - 3 * fall} ry={13 + 12 * fall} fill={P.ink} opacity={dropA} />}
      </svg>

      {/* title + seal: the seal hangs off the title's right edge so the title itself sits on the axis */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: vertical ? H * 0.27 : H * 0.215,
          display: 'flex',
          justifyContent: 'center',
          opacity: 1 - titleOut,
          transform: `translateY(${-18 * titleOut}px)`,
        }}
      >
        <div style={{position: 'relative', transform: `scale(${1 + 0.014 * drift})`}}>
          <StaggerText
            text={TITLE}
            at={124}
            step={7}
            dur={20}
            font="ZL-KaiBlack"
            size={titleSize}
            color={P.ink}
            mode="ink"
            letterSpacing={titleLs}
            style={{marginRight: -titleLs}}
          />
          <BrandSeal
            at={166}
            size={sealSize}
            color={P.accent}
            paper={P.bg}
            style={{position: 'absolute', left: '100%', marginLeft: vertical ? 12 : 20, bottom: vertical ? 18 : 22}}
          />
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: strokeY + (vertical ? 80 : 92),
          textAlign: 'center',
          opacity: 1 - subOut,
          transform: `translateY(${-6 * drift - 14 * subOut}px)`,
        }}
      >
        <Line at={176} color={P.ink} size={vertical ? 40 : 44} style={{letterSpacing: 14, paddingLeft: 14}}>
          {SUBTITLE}
        </Line>
        <Line at={190} color={P.hud} size={vertical ? 34 : 30} font="ZL-Fangsong" style={{marginTop: vertical ? 16 : 12, letterSpacing: 8, paddingLeft: 8}}>
          十三个时代 · 写在纹与字里
        </Line>
        <Line
          at={198}
          color={P.hud}
          size={vertical ? 24 : 22}
          style={{fontFamily: MONO, marginTop: vertical ? 30 : 16, letterSpacing: 4, paddingLeft: 4, lineHeight: 1.6, opacity: 0.8}}
        >
          {vertical ? (
            <>
              THIRTEEN ERAS
              <br />
              WRITTEN IN PATTERN AND SCRIPT
            </>
          ) : (
            'THIRTEEN ERAS · WRITTEN IN PATTERN AND SCRIPT'
          )}
        </Line>
      </div>
      {blackIn > 0 && <AbsoluteFill style={{backgroundColor: '#000', opacity: blackIn}} />}
    </Paper>
  );
};
