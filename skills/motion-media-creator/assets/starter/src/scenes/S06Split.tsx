import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS} from '../timeline';
import {E, Pt, hexA, lerp, prog, rng} from '../lib/anim';
import {MONO, fam} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const C6 = CHAPTERS[6];
const P = C6.palette;

// Local anchors. The HUD year keys in timeline.ts hold on the same frames:
// 88 → 316 (the triptych shatters), 158 → 353 (永和九年), 296 → 589 (隋灭陈).
const BOOM = 88;
const LANTING = 158;
const CARD2_OUT = 212; // the counter leaves 353 at local 210
const BACK = 238; // shards start home
const RET = 46; // flight time home
const RET_SPREAD = 12; // centre seats first, rim last
const LOCK = BACK + RET_SPREAD + RET; // 296: last shard seats, 589 enters

const SEAM = '#4d4840';
const STONE_BG = [
  'radial-gradient(ellipse 38% 30% at 22% 30%, rgba(255,255,255,0.10), rgba(255,255,255,0) 70%)',
  'radial-gradient(ellipse 30% 42% at 80% 64%, rgba(58,50,42,0.10), rgba(58,50,42,0) 70%)',
  'radial-gradient(ellipse 46% 24% at 60% 16%, rgba(58,50,42,0.07), rgba(58,50,42,0) 70%)',
  'radial-gradient(ellipse 34% 28% at 34% 84%, rgba(255,255,255,0.08), rgba(255,255,255,0) 70%)',
  'radial-gradient(ellipse 80% 70% at 50% 46%, #C9C2B4 0%, #BCB5A7 65%, #ADA698 100%)',
].join(',');

/** Keep the part of a convex polygon on one side of the line through p with normal n. */
const clipHalf = (poly: Pt[], p: Pt, n: Pt, sign: number): Pt[] => {
  const out: Pt[] = [];
  const side = (q: Pt) => sign * ((q[0] - p[0]) * n[0] + (q[1] - p[1]) * n[1]);
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i];
    const b = poly[(i + 1) % poly.length];
    const sa = side(a);
    const sb = side(b);
    if (sa >= 0) out.push(a);
    if (sa * sb < 0) {
      const t = sa / (sa - sb);
      out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
    }
  }
  return out;
};

/** Interior edges of a shard as an SVG path (edges lying on the frame border are not cracks). */
const seamPath = (poly: Pt[], W: number, H: number) => {
  const on = (v: number, edge: number) => Math.abs(v - edge) < 0.5;
  let d = '';
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i];
    const b = poly[(i + 1) % poly.length];
    const border = (on(a[0], 0) && on(b[0], 0)) || (on(a[0], W) && on(b[0], W)) || (on(a[1], 0) && on(b[1], 0)) || (on(a[1], H) && on(b[1], H));
    if (!border) d += `M${a[0].toFixed(1)},${a[1].toFixed(1)}L${b[0].toFixed(1)},${b[1].toFixed(1)}`;
  }
  return d;
};

const shatter = (W: number, H: number, seed: number) => {
  const r = rng(seed);
  let polys: Pt[][] = [0, 1, 2].map((k) => [
    [(k * W) / 3, 0],
    [((k + 1) * W) / 3, 0],
    [((k + 1) * W) / 3, H],
    [(k * W) / 3, H],
  ]);
  for (let depth = 0; depth < 4; depth++) {
    const next: Pt[][] = [];
    for (const poly of polys) {
      const cx = poly.reduce((s, q) => s + q[0], 0) / poly.length;
      const cy = poly.reduce((s, q) => s + q[1], 0) / poly.length;
      const ang = r() * Math.PI;
      const p: Pt = [cx + (r() - 0.5) * 80, cy + (r() - 0.5) * 80];
      const n: Pt = [Math.cos(ang), Math.sin(ang)];
      const a = clipHalf(poly, p, n, 1);
      const b = clipHalf(poly, p, n, -1);
      if (a.length >= 3 && b.length >= 3 && depth < 3 + (r() < 0.5 ? 1 : 0)) next.push(a, b);
      else next.push(poly);
    }
    polys = next;
  }
  const raw = polys.map((poly) => {
    const cx = poly.reduce((s, q) => s + q[0], 0) / poly.length;
    const cy = poly.reduce((s, q) => s + q[1], 0) / poly.length;
    const dx = cx - W / 2;
    const dy = cy - H / 2;
    const d = Math.hypot(dx, dy) || 1;
    // shards near the top and bottom edge travel less vertically, keeping them out of the HUD bands
    const edge = Math.abs(dy) > H * 0.3 ? 0.55 : 1;
    return {
      poly,
      cx,
      cy,
      d,
      vx: (dx / d) * (90 + r() * 160),
      vy: (dy / d) * (70 + r() * 120) * edge,
      rot: (r() - 0.5) * 34,
      s: 0.86 + r() * 0.12,
      delay: r() * 10,
      z: 0.85 + r() * 0.3, // depth: scales drift, size and shade
      spin: (r() < 0.5 ? -1 : 1) * (0.03 + r() * 0.06), // deg per frame of drift
      clip: `polygon(${poly.map(([x, y]) => `${x.toFixed(1)}px ${y.toFixed(1)}px`).join(',')})`,
      seam: seamPath(poly, W, H),
    };
  });
  const dMax = Math.max(...raw.map((s) => s.d));
  // back-to-front so nearer shards (larger z) overlap farther ones
  return raw.map((s) => ({...s, rdelay: (s.d / dMax) * RET_SPREAD})).sort((a, b) => a.z - b.z);
};

const KINGDOMS = [
  {n: '魏', y: '220 — 265', bg: '#BBB3A3'},
  {n: '蜀', y: '221 — 263', bg: '#A89F8E'},
  {n: '吴', y: '222 — 280', bg: '#C8C0B1'},
];

export const S06Split: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const shards = useMemo(() => shatter(W, H, 589), [W, H]);
  const allSeams = useMemo(() => shards.map((s) => s.seam).join(''), [shards]);

  const split = prog(frame, 4, 26, E.outCubic); // panels slide apart
  const glyphT = Math.min(frame, BOOM); // glyphs stop sliding once they are carried by shards
  const labelO = prog(frame, 18, 14, E.outCubic) * (1 - prog(frame, BOOM - 10, 8, E.inCubic));

  const panels = (
    <AbsoluteFill>
      {KINGDOMS.map((k, i) => {
        const dir = i % 2 === 0 ? -1 : 1;
        return (
          <div key={k.n} style={{position: 'absolute', left: (i * W) / 3, top: 0, width: W / 3, height: H, background: k.bg, overflow: 'hidden'}}>
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: fam(C6.font),
                fontSize: vertical ? 300 : 410,
                color: hexA(P.ink, 0.88),
                transform: `translateY(${dir * (1 - split) * 260 + dir * glyphT * 0.25}px)`,
              }}
            >
              {k.n}
            </div>
            {labelO > 0 && (
              <div
                style={{
                  position: 'absolute',
                  top: vertical ? H / 2 + 190 : 158,
                  width: '100%',
                  textAlign: 'center',
                  fontFamily: MONO,
                  fontSize: vertical ? 26 : 24,
                  letterSpacing: 4,
                  color: hexA(P.ink, 0.8),
                  opacity: labelO,
                }}
              >
                {k.y}
              </div>
            )}
          </div>
        );
      })}
      {[1, 2].map((k) => (
        <div key={k} style={{position: 'absolute', left: (k * W) / 3 - 3, top: 0, width: 6, height: H * split, background: P.ink}} />
      ))}
    </AbsoluteFill>
  );

  // the one stone the shards return as: a single surface carrying a faint 隋
  const stone = (
    <AbsoluteFill style={{background: STONE_BG, alignItems: 'center', justifyContent: 'center'}}>
      <div style={{fontFamily: fam(C6.font), fontSize: vertical ? 760 : 820, lineHeight: 1, color: hexA(P.ink, 0.17)}}>隋</div>
    </AbsoluteFill>
  );

  // grotto niches (千佛龛) revealed behind the shards; rows fill the frame height
  const niches = useMemo(() => {
    const r = rng(353);
    const out: {x: number; y: number; w: number; h: number; eroded: boolean; tone: number}[] = [];
    const w = vertical ? 74 : 92;
    const h = w * 1.42;
    const rows = Math.ceil((H - 40) / (h + 16)) + 1;
    for (let row = 0; row < rows; row++) {
      for (let col = -1; col < W / w + 1; col++) {
        out.push({x: col * w + (row % 2) * (w / 2) + (r() - 0.5) * 12, y: 40 + row * (h + 16), w: w - 14, h, eroded: r() < 0.16, tone: r()});
      }
    }
    return out;
  }, [W, H, vertical]);
  const nicheMask = vertical
    ? 'linear-gradient(180deg, transparent 0, transparent 190px, #000 330px, #000 1480px, transparent 1600px)'
    : 'linear-gradient(180deg, transparent 0, transparent 110px, #000 200px, #000 900px, transparent 990px)';

  const shadow = prog(frame, BOOM, 24, E.outCubic) * (1 - prog(frame, BACK + 20, 30, E.inCubic));
  const crackIn = prog(frame, BOOM - 8, 7, E.outCubic);
  const push = lerp(1, 1.03, prog(frame, LOCK, 112, E.linear));
  const heal = prog(frame, LOCK + 10, 80, E.inOutCubic);
  const flash = 1 - prog(frame, LOCK, 14, E.outCubic);

  const card1In = prog(frame, 6, 14, E.outCubic);
  const card1Out = prog(frame, BOOM - 6, 10, E.inCubic);
  const card2In = prog(frame, BOOM + 20, 14, E.outCubic);
  const card2Out = prog(frame, CARD2_OUT, 14, E.inCubic);

  return (
    <Paper bg="#8f887b" vignette={0.4}>
      {/* behind: niches, masked away from the HUD header and ruler */}
      {frame >= BOOM && frame < LOCK && (
        <AbsoluteFill style={{opacity: prog(frame, BOOM, 30, E.outCubic), maskImage: nicheMask, WebkitMaskImage: nicheMask}}>
          <svg width={W} height={H} style={{position: 'absolute', inset: 0, transform: `scale(${lerp(1, 1.05, prog(frame, BOOM, 200, E.linear))})`, transformOrigin: '50% 50%'}}>
            <defs>
              <linearGradient id="s06-recess" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#6f685d" />
                <stop offset="1" stopColor="#8a8377" />
              </linearGradient>
            </defs>
            {niches.map((n, k) => (
              <g key={k} transform={`translate(${n.x.toFixed(1)} ${n.y.toFixed(1)})`} opacity={0.82 + n.tone * 0.18}>
                <path d={`M0,${n.h} L0,${n.w / 2} A${n.w / 2},${n.w / 2} 0 0 1 ${n.w},${n.w / 2} L${n.w},${n.h} Z`} fill="url(#s06-recess)" stroke="#6d675c" strokeWidth={1.2} />
                {!n.eroded && (
                  <>
                    <circle cx={n.w / 2} cy={n.w * 0.52} r={n.w * 0.13} fill="#978f82" />
                    <path d={`M${n.w * 0.24},${n.h - 6} Q${n.w / 2},${n.w * 0.62} ${n.w * 0.76},${n.h - 6} Z`} fill="#978f82" />
                  </>
                )}
              </g>
            ))}
          </svg>
        </AbsoluteFill>
      )}

      {/* the triptych, whole, until it cracks */}
      {frame < BOOM && (
        <AbsoluteFill>
          {panels}
          {crackIn > 0 && (
            <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
              <path d={allSeams} pathLength={1} fill="none" stroke={SEAM} strokeWidth={3} strokeDasharray="1 1" strokeDashoffset={1 - crackIn} />
            </svg>
          )}
        </AbsoluteFill>
      )}

      {/* shards: one shared drop-shadow on the parent, none per shard */}
      {frame >= BOOM && frame < LOCK && (
        <AbsoluteFill style={{filter: shadow > 0.02 ? `drop-shadow(0 ${(16 * shadow).toFixed(1)}px ${(22 * shadow).toFixed(1)}px rgba(0,0,0,${(0.34 * shadow).toFixed(3)}))` : undefined}}>
          {shards.map((sh, k) => {
            const out = prog(frame, BOOM + sh.delay, 46, E.outQuint);
            const ret = prog(frame, BACK + sh.rdelay, RET, E.inCubic);
            const e = out * (1 - ret);
            const live = Math.max(0, frame - BOOM) * (1 - ret) * sh.z;
            const tx = sh.vx * (e + 0.0035 * live);
            const ty = sh.vy * (e + 0.0035 * live);
            const rot = sh.rot * e + sh.spin * live;
            const sc = lerp(1, sh.s, e) * (1 + (sh.z - 1) * 0.12 * e);
            const u = prog(frame, BACK + sh.rdelay + 4, 20, E.inOutCubic); // panels → unified stone
            const shade = ((1.15 - sh.z) / 0.3) * 0.16 * Math.min(1, e * 1.5);
            return (
              <AbsoluteFill
                key={k}
                style={{
                  clipPath: sh.clip,
                  transform: `translate(${tx.toFixed(2)}px, ${ty.toFixed(2)}px) rotate(${rot.toFixed(3)}deg) scale(${sc.toFixed(4)})`,
                  transformOrigin: `${sh.cx.toFixed(1)}px ${sh.cy.toFixed(1)}px`,
                }}
              >
                {u < 1 && panels}
                {u > 0 && <AbsoluteFill style={{opacity: u}}>{stone}</AbsoluteFill>}
                {shade > 0.004 && <AbsoluteFill style={{background: `rgba(24,21,18,${shade.toFixed(3)})`}} />}
                <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
                  <path d={sh.seam} fill="none" stroke={SEAM} strokeWidth={3} />
                </svg>
              </AbsoluteFill>
            );
          })}
        </AbsoluteFill>
      )}

      {/* reassembled: one stone; the seams flash once, then heal */}
      {frame >= LOCK && (
        <AbsoluteFill style={{transform: `scale(${push.toFixed(4)})`}}>
          {stone}
          {heal < 1 && (
            <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
              <path d={allSeams} fill="none" stroke={SEAM} strokeWidth={lerp(3, 1.2, heal)} opacity={1 - heal} />
              {flash > 0 && <path d={allSeams} fill="none" stroke={P.accent} strokeWidth={3} opacity={0.9 * flash} />}
            </svg>
          )}
        </AbsoluteFill>
      )}

      {/* copy */}
      <AbsoluteFill>
        {/* card 1: a lintel across the triptych, gone before the break */}
        {card1Out < 1 && (
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: vertical ? 420 : 150,
              display: 'flex',
              justifyContent: 'center',
              opacity: 1 - card1Out,
              transform: `translateY(${card1Out * 12}px)`,
            }}
          >
            <div
              style={{
                background: '#E9E3D6',
                padding: vertical ? '22px 40px 26px' : '20px 44px 22px',
                boxShadow: '0 16px 40px rgba(0,0,0,0.18)',
                clipPath: `inset(0 ${((1 - card1In) * 100).toFixed(2)}% 0 0)`,
                display: 'flex',
                flexDirection: vertical ? 'column' : 'row',
                alignItems: vertical ? 'center' : 'baseline',
                gap: vertical ? 10 : 40,
              }}
            >
              <StaggerText text="三国鼎立" at={12} step={5} font={C6.font} size={vertical ? 86 : 76} color={P.ink} letterSpacing={6} />
              <Line at={30} color={P.ink} size={vertical ? 34 : 32}>
                220 年汉亡，魏、蜀、吴相继立国。
              </Line>
            </div>
          </div>
        )}

        {/* card 2: the span, then 353 */}
        {card2In > 0 && card2Out < 1 && (
          <div style={{position: 'absolute', left: vertical ? 70 : 120, top: vertical ? 350 : 200, opacity: card2In * (1 - card2Out)}}>
            <div style={{background: '#E9E3D6', padding: vertical ? '26px 36px 30px 40px' : '26px 40px 30px 44px', boxShadow: '0 22px 50px rgba(0,0,0,0.24)', borderLeft: `5px solid ${P.accent}`}}>
              <StaggerText text="分合三百余年" at={BOOM + 24} step={4} font={C6.font} size={vertical ? 76 : 86} color={P.ink} letterSpacing={6} />
              <Line at={BOOM + 44} color={P.ink} size={vertical ? 34 : 30} style={{marginTop: 12}}>
                也是民族交融、佛教兴盛、书法走向成熟的年代。
              </Line>
              <div style={{marginTop: 18}}>
                <StaggerText text="永和九年，岁在癸丑" at={LANTING} step={4} font="ZL-Xingkai" size={vertical ? 48 : 54} color={P.accent} mode="ink" />
              </div>
              <Line at={LANTING + 14} color={hexA(P.ink, 0.75)} size={vertical ? 28 : 26} style={{marginTop: 10}}>
                353 · 王羲之《兰亭集序》开篇
              </Line>
            </div>
          </div>
        )}

        {/* 589 lands with the last shard and stays to the end */}
        {frame >= LOCK - 1 && (
          <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', transform: `scale(${lerp(1, 1.035, prog(frame, LOCK, 112, E.linear)).toFixed(4)})`}}>
            <StaggerText text="589" at={LOCK} step={5} font="ZL-Serif" size={vertical ? 200 : 250} color={P.ink} mode="rise" />
            <Line at={LOCK + 16} color={P.ink} size={36} style={{marginTop: 8}}>
              隋灭陈，南北重归一统。
            </Line>
          </AbsoluteFill>
        )}
      </AbsoluteFill>
    </Paper>
  );
};
