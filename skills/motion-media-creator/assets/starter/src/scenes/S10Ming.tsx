import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS, CUES} from '../timeline';
import {E, Pt, clamp01, hexA, lerp, partialPolyline, pointAt, polyLength, polyline, prog} from '../lib/anim';
import {BODY, SERIF, fam} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const C10 = CHAPTERS[10];
const P = C10.palette;
const GOLD = '#E0A526';
const CREAM = '#F2E7D0';
const PALACE = CUES.mingPalace - C10.start;

// Stops named in Ming records of the voyages. Several voyages are merged into one schematic
// track; only points and lines are drawn (no coastlines).
const MAIN: {n: string; lon: number; lat: number}[] = [
  {n: '刘家港', lon: 121.2, lat: 31.6},
  {n: '占城', lon: 109.2, lat: 13.8},
  {n: '爪哇', lon: 112.7, lat: -7.2},
  {n: '满剌加', lon: 102.2, lat: 2.2},
  {n: '锡兰山', lon: 80.2, lat: 6.0},
  {n: '古里', lon: 75.8, lat: 11.2},
  {n: '忽鲁谟斯', lon: 56.4, lat: 27.1},
];
const BRANCH_FROM = 5; // 古里
const BRANCH_TO = {n: '木骨都束', lon: 45.3, lat: 2.0};

/** Side-view treasure ship: never rolled onto its side; it faces its heading and pitches a little. */
const Ship: React.FC<{x: number; y: number; s: number; a: number; frame: number}> = ({x, y, s, a, frame}) => {
  const right = Math.cos(a) >= 0;
  const pitch = Math.max(-8, Math.min(8, (Math.atan2(Math.sin(a), Math.abs(Math.cos(a))) * 180) / Math.PI * 0.25)) * (right ? 1 : -1);
  return (
    <g transform={`translate(${x} ${y + Math.sin(frame / 7) * 3}) rotate(${pitch + Math.sin(frame / 9) * 1.5}) scale(${(right ? 1 : -1) * s} ${s})`}>
      <path d="M-40,0 Q0,16 44,-2 L36,-10 L-34,-10 Z" fill={CREAM} />
      {[-22, -4, 14, 28].map((mx, k) => (
        <g key={k}>
          <line x1={mx} x2={mx} y1={-10} y2={-44 + Math.abs(k - 1.5) * 6} stroke={CREAM} strokeWidth={2} />
          <path d={`M${mx + 1},${-40 + Math.abs(k - 1.5) * 6} L${mx + 12},${-38 + Math.abs(k - 1.5) * 6} L${mx + 12},${-14} L${mx + 1},${-14} Z`} fill={hexA(GOLD, 0.9)} />
        </g>
      ))}
    </g>
  );
};

type Hall = {z: number; w: number; h: number; kind: 'gate' | 'hall' | 'grand'; name: string};
// Yongle-era names; today's names in brackets.
const AXIS: Hall[] = [
  {z: 0, w: 900, h: 300, kind: 'gate', name: '午门'},
  {z: 1, w: 700, h: 260, kind: 'gate', name: '奉天门（今太和门）'},
  {z: 2, w: 980, h: 380, kind: 'grand', name: '奉天殿（今太和殿）'},
  {z: 3, w: 520, h: 260, kind: 'hall', name: '华盖殿（今中和殿）'},
  {z: 4, w: 760, h: 320, kind: 'hall', name: '谨身殿（今保和殿）'},
];

const HallShape: React.FC<{w: number; h: number; kind: Hall['kind']; o: number}> = ({w, h, kind, o}) => {
  const roofH = h * 0.36;
  const bodyH = h * (kind === 'grand' ? 0.34 : 0.4);
  const base = h * (kind === 'grand' ? 0.3 : 0.2);
  const eave = w * 0.08;
  const by = 0;
  const steps = kind === 'grand' ? 3 : 1;
  return (
    <g opacity={o}>
      {Array.from({length: steps}, (_, k) => (
        <rect key={k} x={-w / 2 - 30 + k * 26} y={by - base + (k * base) / steps} width={w + 60 - k * 52} height={base / steps} fill="#E8DFCB" stroke="#9c8c70" strokeWidth={1.5} />
      ))}
      <rect x={-w / 2 + 30} y={by - base - bodyH} width={w - 60} height={bodyH} fill="#A3201D" />
      {Array.from({length: 11}, (_, k) => (
        <line key={k} x1={-w / 2 + 40 + (k * (w - 80)) / 10} x2={-w / 2 + 40 + (k * (w - 80)) / 10} y1={by - base - bodyH} y2={by - base} stroke="#6e1512" strokeWidth={3} />
      ))}
      {kind === 'gate' && <path d={`M${-50},${by - base} L${-50},${by - base - bodyH * 0.6} Q0,${by - base - bodyH * 0.9} 50,${by - base - bodyH * 0.6} L50,${by - base} Z`} fill="#3d0c0a" />}
      {/* double-eaved hip roof */}
      <path
        d={`M${-w / 2 - eave},${by - base - bodyH} Q${-w / 2},${by - base - bodyH - roofH * 0.28} ${-w / 2 + w * 0.12},${by - base - bodyH - roofH * 0.42} L${w / 2 - w * 0.12},${by - base - bodyH - roofH * 0.42} Q${w / 2},${by - base - bodyH - roofH * 0.28} ${w / 2 + eave},${by - base - bodyH} Z`}
        fill="#E0A526"
        stroke="#8a5e0c"
        strokeWidth={2}
      />
      <path
        d={`M${-w * 0.38},${by - base - bodyH - roofH * 0.42} Q${-w * 0.3},${by - base - bodyH - roofH * 0.8} ${-w * 0.2},${by - base - bodyH - roofH} L${w * 0.2},${by - base - bodyH - roofH} Q${w * 0.3},${by - base - bodyH - roofH * 0.8} ${w * 0.38},${by - base - bodyH - roofH * 0.42} Z`}
        fill="#E8B23A"
        stroke="#8a5e0c"
        strokeWidth={2}
      />
    </g>
  );
};

export const S10Ming: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();

  // ---------- voyage ----------
  const map = vertical ? {x0: 80, y0: 640, w: W - 160, h: 640} : {x0: 820, y0: 236, w: 950, h: 480};
  const proj = (lon: number, lat: number): Pt => [map.x0 + ((lon - 40) / 84) * map.w, map.y0 + ((33 - lat) / 38) * map.h];
  const route = useMemo(() => MAIN.map((st) => proj(st.lon, st.lat)), [map.x0, map.y0, map.w, map.h]); // eslint-disable-line react-hooks/exhaustive-deps
  const branch = useMemo(() => [route[BRANCH_FROM], proj(BRANCH_TO.lon, BRANCH_TO.lat)] as Pt[], [route]); // eslint-disable-line react-hooks/exhaustive-deps
  const sail = prog(frame, 14, 186, E.inOutSine);
  const stopShort = 1 - 70 / polyLength(route);
  const ship = pointAt(route, sail * stopShort);
  const branchT = prog(frame, 150, 50, E.inOutCubic);
  const voyageOut = prog(frame, PALACE - 14, 18, E.inOutCubic);
  const waveRows = vertical ? 7 : 7;
  const waveTop = vertical ? 1320 : H * 0.7;

  // labels sit outside the bend of the track, on a dark halo
  const labelPos = (k: number): Pt => {
    const p = route[k];
    const unit = (a: Pt, b: Pt): Pt => {
      const dx = b[0] - a[0];
      const dy = b[1] - a[1];
      const d = Math.hypot(dx, dy) || 1;
      return [dx / d, dy / d];
    };
    const prev = k > 0 ? unit(p, route[k - 1]) : null;
    const next = k < route.length - 1 ? unit(p, route[k + 1]) : null;
    let n: Pt;
    if (prev && next) {
      const sx = prev[0] + next[0];
      const sy = prev[1] + next[1];
      const d = Math.hypot(sx, sy);
      n = d > 0.3 ? [-sx / d, -sy / d] : [-next[1], next[0]];
    } else {
      const u = (prev ?? next)!;
      n = [-u[0], -u[1]];
    }
    return [p[0] + n[0] * 52, p[1] + n[1] * 52];
  };
  const halo = '0 0 8px #0F2A3B, 0 0 3px #0F2A3B, 0 0 14px #0F2A3B';

  // ---------- axis fly-through ----------
  const fly = prog(frame, PALACE, 140, E.inOutSine);
  const camZ = lerp(-1.4, 1.05, fly);
  const palaceIn = prog(frame, PALACE - 6, 16, E.outCubic);
  const horizon = vertical ? 780 : H * 0.45;
  const reach = vertical ? 520 : 700;
  const hs = vertical ? 0.7 : 1;
  const focus = AXIS.reduce((best, h) => (Math.abs(h.z - camZ - 1.2) < Math.abs(best.z - camZ - 1.2) ? h : best), AXIS[0]);

  return (
    <Paper bg={P.bg} dark vignette={0.5}>
      {voyageOut < 1 && (
        <AbsoluteFill style={{opacity: 1 - voyageOut}}>
          <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
            <g fill="none" stroke={hexA(CREAM, 0.32)} strokeWidth={2.2} strokeLinecap="round">
              {Array.from({length: waveRows}, (_, row) => {
                const y = waveTop + row * 34;
                const off = ((frame * (1.2 + row * 0.35) + row * 70) % 160) - 160;
                let d = '';
                for (let x = off; x < W + 160; x += 160) d += `M${x},${y} q40,-36 80,0 q-26,-16 -40,0 M${x + 80},${y} q40,-28 80,0`;
                return <path key={row} d={d} opacity={0.4 + row * 0.08} />;
              })}
            </g>
            <g stroke={hexA(CREAM, 0.08)} strokeWidth={1}>
              {Array.from({length: 9}, (_, k) => {
                const [x] = proj(120 - k * 10, 0);
                return <line key={k} x1={x} x2={x} y1={map.y0 - 30} y2={map.y0 + map.h + 30} />;
              })}
              {Array.from({length: 5}, (_, k) => {
                const [, y] = proj(0, 30 - k * 10);
                return <line key={k} x1={map.x0 - 30} x2={map.x0 + map.w + 30} y1={y} y2={y} />;
              })}
            </g>
            <path d={polyline(route)} fill="none" stroke={hexA(GOLD, 0.2)} strokeWidth={2} strokeDasharray="3 9" />
            <path d={polyline(partialPolyline(route, sail))} fill="none" stroke={GOLD} strokeWidth={3.4} strokeDasharray="10 8" />
            {branchT > 0 && <path d={polyline(partialPolyline(branch, branchT))} fill="none" stroke={hexA(GOLD, 0.85)} strokeWidth={2.4} strokeDasharray="4 7" />}
            {route.map(([x, y], k) => {
              const r = prog(frame, 14 + 186 * (k / (route.length - 1)) * 0.97, 10, E.outBack);
              return <circle key={k} cx={x} cy={y} r={7 * r} fill={GOLD} />;
            })}
            {branchT >= 1 && <circle cx={branch[1][0]} cy={branch[1][1]} r={6} fill="none" stroke={GOLD} strokeWidth={2} />}
            <Ship x={ship.p[0]} y={ship.p[1] - 6} s={vertical ? 1.1 : 1.2} a={ship.a} frame={frame} />
          </svg>
          {route.map((_, k) => {
            const reachT = prog(frame, 16 + 186 * (k / (route.length - 1)) * 0.97, 12, E.outCubic);
            const [lx, ly] = labelPos(k);
            return (
              <div key={k} style={{position: 'absolute', left: lx - 110, width: 220, top: ly - 20, textAlign: 'center', fontFamily: fam(C10.font), fontSize: vertical ? 32 : 30, color: CREAM, opacity: reachT, textShadow: halo}}>
                {MAIN[k].n}
              </div>
            );
          })}
          <div
            style={{
              position: 'absolute',
              left: branch[1][0] - 110,
              width: 220,
              top: branch[1][1] + 14,
              textAlign: 'center',
              opacity: prog(frame, 196, 12, E.outCubic),
              textShadow: halo,
            }}
          >
            <div style={{fontFamily: fam(C10.font), fontSize: vertical ? 30 : 28, color: CREAM}}>{BRANCH_TO.n}</div>
            <div style={{fontFamily: BODY, fontSize: vertical ? 22 : 22, color: hexA(GOLD, 0.95)}}>分船队</div>
          </div>
          <div style={{position: 'absolute', left: vertical ? 70 : 150, top: vertical ? 340 : 260, width: vertical ? W - 140 : 600}}>
            <StaggerText text="下西洋" at={8} step={7} font={C10.font} size={vertical ? 110 : 136} color={CREAM} mode="rise" letterSpacing={12} />
            <div style={{fontFamily: SERIF, fontSize: vertical ? 50 : 54, color: GOLD, marginTop: 14, opacity: prog(frame, 26, 14, E.outCubic)}}>1405 — 1433</div>
            <Line at={36} color={CREAM} size={vertical ? 34 : 32} style={{marginTop: 8}}>
              郑和七次远航，分船队到过东非沿岸。
            </Line>
            <Line at={50} color={hexA(CREAM, 0.75)} size={vertical ? 24 : 22}>
              多次航程合并示意，点位为近似
            </Line>
          </div>
        </AbsoluteFill>
      )}

      {frame >= PALACE - 6 && (
        <AbsoluteFill style={{opacity: palaceIn, background: '#F2E9D8'}}>
          <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 70%, #f7f0e2 0%, #e6d9bf 100%)'}} />
          {/* raised camera: farther roofs step up above nearer ones; nothing enters the ruler band */}
          <svg
            width={W}
            height={H}
            style={{
              position: 'absolute',
              inset: 0,
              maskImage: vertical ? 'linear-gradient(to bottom, #000 0, #000 1500px, transparent 1560px)' : 'linear-gradient(to bottom, #000 0, #000 900px, transparent 985px)',
              WebkitMaskImage: vertical ? 'linear-gradient(to bottom, #000 0, #000 1500px, transparent 1560px)' : 'linear-gradient(to bottom, #000 0, #000 900px, transparent 985px)',
            }}
          >
            <polygon points={`${W / 2 - 40},${horizon} ${W / 2 + 40},${horizon} ${W / 2 + 420},${H} ${W / 2 - 420},${H}`} fill="#d8c9a8" />
            {AXIS.slice()
              .reverse()
              .map((h) => {
                const dz = h.z - camZ;
                if (dz <= 0.15) return null;
                const sc = 0.9 / dz;
                const o = clamp01((dz - 0.15) / 0.15) * clamp01((6 - dz) / 1.5);
                return (
                  <g key={h.name} transform={`translate(${W / 2} ${horizon + reach * sc * 0.42}) scale(${sc * hs})`}>
                    <HallShape w={h.w} h={h.h} kind={h.kind} o={o} />
                  </g>
                );
              })}
          </svg>
          {(() => {
            const dz = focus.z - camZ;
            if (dz <= 0.5) return null;
            const sc = 0.9 / dz;
            const y = horizon + reach * sc * 0.42 - focus.h * sc * hs;
            return (
              <div
                key={focus.name}
                style={{
                  position: 'absolute',
                  left: vertical ? 70 : W / 2 + Math.min(520, focus.w * sc * hs * 0.5 + 40),
                  right: vertical ? 70 : undefined,
                  top: vertical ? 1470 : Math.max(150, y - 10),
                  textAlign: vertical ? 'center' : 'left',
                  fontFamily: fam('ZL-Kai'),
                  fontSize: vertical ? 36 : 34,
                  color: '#5a1a12',
                  textShadow: '0 0 10px #f7f0e2, 0 0 4px #f7f0e2',
                  whiteSpace: 'nowrap',
                }}
              >
                {focus.name}
              </div>
            );
          })()}
          <div
            style={{
              position: 'absolute',
              left: vertical ? 46 : 120,
              top: vertical ? 330 : 200,
              width: vertical ? W - 92 : 720,
              padding: vertical ? '14px 24px 18px' : '22px 30px 24px',
              background: 'rgba(247,240,226,0.9)',
              boxShadow: '0 18px 40px rgba(60,30,10,0.18)',
              opacity: prog(frame, PALACE + 4, 14, E.outCubic),
            }}
          >
            <StaggerText text="紫禁城" at={PALACE + 8} step={6} font={C10.font} size={vertical ? 100 : 120} color="#7a1712" mode="rise" letterSpacing={10} />
            <div style={{fontFamily: SERIF, fontSize: vertical ? 44 : 46, color: '#7a1712', marginTop: 10, opacity: prog(frame, PALACE + 24, 12, E.outCubic)}}>1420</div>
            <Line at={PALACE + 34} color="#3b2418" size={vertical ? 34 : 30}>
              郑和首航、紫禁城落成、《永乐大典》成书，
            </Line>
            <Line at={PALACE + 42} color="#3b2418" size={vertical ? 34 : 30}>
              都在永乐年间。
            </Line>
            <div style={{marginTop: 22, display: 'flex', alignItems: 'baseline', gap: 12, opacity: prog(frame, PALACE + 56, 12, E.outCubic)}}>
              <span style={{fontFamily: SERIF, fontSize: vertical ? 56 : 64, color: '#B92B22'}}>22,877</span>
              <span style={{fontFamily: fam('ZL-Fangsong'), fontSize: vertical ? 28 : 26, color: '#3b2418'}}>卷 ·《永乐大典》正文</span>
            </div>
            <div style={{fontFamily: BODY, fontSize: vertical ? 24 : 22, letterSpacing: 2, color: hexA('#3b2418', 0.75), marginTop: 8, opacity: prog(frame, PALACE + 60, 12, E.outCubic)}}>
              中轴线建筑为示意，殿名用永乐时旧称
            </div>
          </div>
        </AbsoluteFill>
      )}
    </Paper>
  );
};

