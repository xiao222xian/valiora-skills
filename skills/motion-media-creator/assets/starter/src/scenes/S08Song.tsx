import React, {useMemo} from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS} from '../timeline';
import {E, hexA, lerp, prog, rng} from '../lib/anim';
import {MONO, fam} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const C8 = CHAPTERS[8];
const P = C8.palette;
const INK = P.ink;
const TYPE_FACE = 'ZL-SongBold'; // Songti SC Black has no 昇

// 《梦溪笔谈 · 技艺》: 庆历中，有布衣毕昇，又为活板。 Three vertical columns, read right to left.
const COLS = ['庆历中有', '布衣毕昇', '又为活板'];

// Part A (scroll + official jiaozi, 1024) then part B (movable type, Qingli era 1041-1048):
// these local frames match the chapter's axisKeys in timeline.ts.
const B_START = 154;

const House: React.FC<{x: number; y: number; w: number; h: number; k: number}> = ({x, y, w, h, k}) => {
  const eave = w * 0.18;
  const roofH = h * 0.42;
  return (
    <g>
      <path d={`M${x},${y} L${x},${y - h + roofH} L${x + w},${y - h + roofH} L${x + w},${y} Z`} fill={hexA('#f4f1e6', 0.92)} stroke={INK} strokeWidth={1.6} />
      <path
        d={`M${x - eave},${y - h + roofH + 4} Q${x + w * 0.1},${y - h + roofH - 2} ${x + w * 0.2},${y - h} L${x + w * 0.8},${y - h} Q${x + w * 0.9},${y - h + roofH - 2} ${x + w + eave},${y - h + roofH + 4} Z`}
        fill={hexA(INK, 0.78)}
      />
      {k % 3 === 0 && <rect x={x + w * 0.38} y={y - h * 0.4} width={w * 0.24} height={h * 0.4} fill="none" stroke={INK} strokeWidth={1.4} />}
      {k % 4 === 1 && <line x1={x + w * 0.7} x2={x + w * 0.7} y1={y - h + roofH} y2={y - h - 26} stroke={INK} strokeWidth={1.4} />}
      {k % 4 === 1 && <rect x={x + w * 0.7} y={y - h - 26} width={16} height={22} fill={P.accent} opacity={0.85} />}
    </g>
  );
};

/** Part A: a handscroll of Bianjing streets, layers at different depths, panning with an eased push. */
const ScrollPart: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const pan = 1900 * prog(frame, 0, 158, E.inOutSine) + 0.6 * frame;
  const out = prog(frame, 144, 12, E.inCubic);
  const scene = useMemo(() => {
    const r = rng(1024);
    const houses = Array.from({length: 46}, (_, k) => ({x: k * 150 + r() * 40, w: 90 + r() * 60, h: 70 + r() * 60, row: k % 2}));
    const boats = Array.from({length: 9}, (_, k) => ({x: k * 640 + r() * 200, s: 0.8 + r() * 0.5, sail: r() < 0.6}));
    const people = Array.from({length: 140}, () => ({x: r() * 7000, row: Math.floor(r() * 3), ph: r() * 6, v: 0.3 + r() * 0.6}));
    const trees = Array.from({length: 24}, (_, k) => ({x: k * 310 + r() * 120, h: 90 + r() * 70}));
    const reeds = Array.from({length: 70}, (_, k) => ({x: k * 120 + r() * 80, h: 40 + r() * 50, lean: (r() - 0.5) * 0.6}));
    return {houses, boats, people, trees, reeds};
  }, []);
  const groundY = vertical ? 1120 : H * 0.62;
  const riverY = groundY + 90;
  const fgY = vertical ? 1520 : 930;
  const layer = (speed: number) => `translate(${(-pan * speed).toFixed(1)} 0)`;
  const cardIn = prog(frame, 36, 22, E.outBack);

  return (
    <AbsoluteFill style={{opacity: 1 - out}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <linearGradient id="s08-mist" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor={P.bg} stopOpacity={0} />
            <stop offset="1" stopColor={P.bg} stopOpacity={1} />
          </linearGradient>
        </defs>
        {/* far hills: slowest, clearly visible */}
        <g transform={layer(0.15)} opacity={0.85}>
          {Array.from({length: 18}, (_, k) => (
            <path key={k} d={`M${k * 420 - 200},${groundY - 40} Q${k * 420},${groundY - 240 - (k % 3) * 44} ${k * 420 + 260},${groundY - 40} Z`} fill={hexA('#95ada4', 0.8)} />
          ))}
          <rect x={-400} y={groundY - 120} width={9000} height={100} fill="url(#s08-mist)" />
        </g>
        <rect x={0} y={riverY - 20} width={W} height={(vertical ? 1540 : H) - riverY + 20} fill={hexA('#b9cdc5', 0.6)} />
        <g transform={layer(1.0)} stroke={hexA(INK, 0.35)} strokeWidth={1.4} fill="none">
          {Array.from({length: 120}, (_, k) => {
            const x = k * 80 + ((k * 37) % 40);
            const y = riverY + 20 + ((k * 53) % 140);
            const ph = Math.sin(frame / 12 + k) * 6;
            return <path key={k} d={`M${x},${y} q20,${-8 + ph * 0.2} 40,0 t40,0`} />;
          })}
        </g>
        {/* back row: aerial perspective */}
        <g transform={layer(0.5)} opacity={0.55}>
          {scene.houses.filter((h) => h.row === 0).map((h, k) => (
            <House key={k} x={h.x} y={groundY - 30} w={h.w * 0.8} h={h.h * 0.8} k={k} />
          ))}
        </g>
        <g transform={layer(0.75)} stroke={INK} fill="none" strokeWidth={1.6}>
          {scene.trees.map((t, k) => (
            <g key={k}>
              <path d={`M${t.x},${groundY} Q${t.x - 6},${groundY - t.h * 0.5} ${t.x + 4},${groundY - t.h}`} />
              {Array.from({length: 7}, (_, j) => (
                <path key={j} d={`M${t.x + 2},${groundY - t.h + j * 8} q${-18 + j * 3},${20 + j * 4} ${-28 + j * 5},${44 + j * 6}`} stroke={hexA('#4f6f5c', 0.8)} />
              ))}
            </g>
          ))}
        </g>
        <g transform={layer(1.0)}>
          {scene.houses.filter((h) => h.row === 1).map((h, k) => (
            <House key={k} x={h.x + 60} y={groundY + 6} w={h.w} h={h.h} k={k + 1} />
          ))}
          {/* rainbow bridges: both reachable within the pan */}
          {[1300, 2900].map((bx) => (
            <g key={bx}>
              <path d={`M${bx},${riverY + 30} Q${bx + 260},${riverY - 190} ${bx + 520},${riverY + 30}`} fill="none" stroke={INK} strokeWidth={9} />
              <path d={`M${bx + 20},${riverY + 6} Q${bx + 260},${riverY - 200} ${bx + 500},${riverY + 6}`} fill="none" stroke={INK} strokeWidth={2} />
              {Array.from({length: 14}, (_, k) => {
                const t = (k + 1) / 15;
                const x = bx + 20 + t * 480;
                const y = (1 - t) * (1 - t) * (riverY + 6) + 2 * (1 - t) * t * (riverY - 200) + t * t * (riverY + 6);
                return <line key={k} x1={x} x2={x} y1={y} y2={y - 22} stroke={INK} strokeWidth={1.6} />;
              })}
            </g>
          ))}
          {scene.people.map((p, k) => {
            const x = p.x + Math.sin(frame / 20 + p.ph) * 6 + frame * p.v * (k % 2 ? 1 : -1);
            const y = groundY + 18 + p.row * 12;
            const step = Math.sin(frame / 3 + p.ph) * 2;
            return (
              <g key={k} fill={INK}>
                <circle cx={x} cy={y - 18} r={3.4} />
                <path d={`M${x - 4},${y - 14} L${x + 4},${y - 14} L${x + 5 + step},${y} L${x - 5 - step},${y} Z`} />
              </g>
            );
          })}
        </g>
        <g transform={layer(1.15)}>
          {scene.boats.map((b, k) => {
            const bx = b.x + frame * 0.6 * (k % 2 ? 1 : -1);
            const by = riverY + 70 + (k % 3) * 46 + Math.sin(frame / 14 + k) * 3;
            return (
              <g key={k} transform={`translate(${bx} ${by}) scale(${b.s})`}>
                <path d="M-90,0 Q0,30 90,0 L70,-14 L-70,-14 Z" fill={hexA('#6d5a40', 0.85)} stroke={INK} strokeWidth={1.6} />
                <rect x={-40} y={-40} width={70} height={26} fill={hexA('#f4f1e6', 0.9)} stroke={INK} strokeWidth={1.4} />
                {b.sail && <line x1={0} x2={0} y1={-14} y2={-120} stroke={INK} strokeWidth={2} />}
                {b.sail && <path d="M2,-112 Q40,-80 4,-36 Z" fill={hexA('#e9e1cc', 0.95)} stroke={INK} strokeWidth={1.2} />}
              </g>
            );
          })}
        </g>
        {/* foreground reeds: fastest layer, kept above the ruler */}
        <g transform={layer(1.7)} stroke={hexA(INK, 0.85)} strokeWidth={2.4} strokeLinecap="round" fill="none">
          {scene.reeds.map((rd, k) => (
            <path key={k} d={`M${rd.x},${fgY} q${rd.lean * 20},${-rd.h * 0.6} ${rd.lean * 44},${-rd.h}`} />
          ))}
        </g>
      </svg>
      <div style={{position: 'absolute', left: vertical ? 70 : 150, top: vertical ? 340 : 200, width: vertical ? W - 140 : 980}}>
        <StaggerText text="市井长卷" at={8} step={5} font={C8.font} size={vertical ? 100 : 116} color={INK} mode="rise" letterSpacing={10} />
        <Line at={26} color={INK} size={vertical ? 36 : 32} style={{marginTop: 12}}>
          城郭、虹桥、舟船与商铺，宋人把日常画进了长卷。
        </Line>
      </div>
      {/* official jiaozi, 1024 */}
      <div
        style={{
          position: 'absolute',
          right: vertical ? 70 : 150,
          top: vertical ? 560 : 330,
          display: 'flex',
          alignItems: 'flex-start',
          gap: 26,
          flexDirection: vertical ? 'row' : 'row-reverse',
        }}
      >
        <div
          style={{
            width: 176,
            height: 258,
            transformOrigin: '50% 0%',
            transform: `perspective(900px) rotateX(${lerp(-92, 0, cardIn)}deg)`,
            background: '#efe6cf',
            border: `3px double ${P.accent}`,
            boxShadow: '0 16px 30px rgba(0,0,0,0.18)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 10,
          }}
        >
          <div style={{fontFamily: fam(C8.font), fontSize: 50, color: P.accent, writingMode: 'vertical-rl', letterSpacing: 8}}>官交子</div>
          <div style={{fontFamily: MONO, fontSize: 20, color: INK, letterSpacing: 2}}>1024</div>
        </div>
        <div style={{width: vertical ? 620 : 560, textAlign: vertical ? 'left' : 'right', paddingTop: 70, whiteSpace: 'nowrap'}}>
          <Line at={54} color={INK} size={vertical ? 32 : 30}>
            北宋在益州（今成都）发行官交子，
          </Line>
          <Line at={62} color={INK} size={vertical ? 32 : 30}>
            是最早的官方纸币之一。
          </Line>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Part B: set the forme, ink it, press a sheet, lift it and turn it over its left edge. */
const PrintPart: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const cell = vertical ? 100 : 120;
  const trayW = COLS.length * cell + 40;
  const trayH = 4 * cell + 40;
  const trayX = vertical ? W / 2 + 180 : W * 0.74;
  const trayY = vertical ? 900 : H * 0.5;
  const inkPass = prog(frame, 52, 22, E.inOutCubic);
  const paperDown = prog(frame, 76, 18, E.inOutCubic);
  const lift = prog(frame, 98, 14, E.outCubic);
  const flip = prog(frame, 112, 36, E.inOutCubic);
  const view = prog(frame, 140, 40, E.inOutCubic); // camera eases toward the printed sheet
  const tilt = lerp(lerp(56, 50, prog(frame, 0, 100, E.inOutSine)), 24, view);
  const spin = lerp(-8, -3, view);
  const settle = vertical ? 0 : lerp(0, -cell * 1.2, view);

  return (
    <AbsoluteFill style={{opacity: prog(frame, 0, 8, E.linear)}}>
      <div style={{position: 'absolute', left: trayX - trayW / 2 + settle, top: trayY - trayH / 2, width: trayW, height: trayH, perspective: 1500}}>
        <div style={{position: 'absolute', inset: 0, transformStyle: 'preserve-3d', transform: `rotateX(${tilt}deg) rotateZ(${spin}deg)`}}>
          <div style={{position: 'absolute', inset: -14, background: '#8a7454', borderRadius: 6, transform: 'translateZ(-2px)', boxShadow: '0 40px 80px rgba(0,0,0,0.3)'}} />
          {COLS.flatMap((col, ci) =>
            Array.from(col).map((ch, ri) => {
              const order = ci * 4 + ri;
              const drop = prog(frame, 2 + order * 4, 14, E.outBack);
              const x = 20 + ci * cell; // the forme mirrors the page: the page's right-most column sits left
              const y = 20 + ri * cell;
              return (
                <div
                  key={order}
                  style={{
                    position: 'absolute',
                    left: x + 4,
                    top: y + 4,
                    width: cell - 8,
                    height: cell - 8,
                    transformStyle: 'preserve-3d',
                    transform: `translateZ(${lerp(260, 0, drop)}px)`,
                    opacity: drop > 0 ? 1 : 0,
                  }}
                >
                  <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 46, background: '#a88c62', transformOrigin: '50% 100%', transform: 'rotateX(-90deg)'}} />
                  <div style={{position: 'absolute', top: 0, bottom: 0, right: 0, width: 46, background: '#977b52', transformOrigin: '100% 50%', transform: 'rotateY(90deg)'}} />
                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      transform: 'translateZ(46px)',
                      background: 'linear-gradient(135deg, #c9ae7f, #b89a6a)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontFamily: fam(TYPE_FACE),
                      fontSize: cell * 0.7,
                      color: inkPass > (ci + 1) / 4 ? '#141414' : '#6b5534',
                      borderRadius: 3,
                    }}
                  >
                    <span style={{transform: 'scaleX(-1)'}}>{ch}</span>
                  </div>
                </div>
              );
            }),
          )}
          {inkPass > 0 && inkPass < 1 && (
            <div style={{position: 'absolute', top: -20, bottom: -20, width: 60, left: lerp(trayW + 20, -80, inkPass), background: 'linear-gradient(90deg, #222, #555, #111)', borderRadius: 30, transform: 'translateZ(80px)'}} />
          )}
          {/* one sheet: blank face up while it is pressed, printed face up after it turns over its left edge */}
          {paperDown > 0 && (
            <div
              style={{
                position: 'absolute',
                inset: -10,
                transformStyle: 'preserve-3d',
                transformOrigin: '0% 50%',
                transform: `translateZ(${lerp(320, 50, paperDown) + 110 * lift - 60 * flip}px) rotateY(${-180 * flip}deg)`,
              }}
            >
              <div style={{position: 'absolute', inset: 0, background: '#f3eedf', backfaceVisibility: 'hidden', boxShadow: '0 10px 30px rgba(0,0,0,0.25)'}} />
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: '#f3eedf',
                  backfaceVisibility: 'hidden',
                  transform: 'rotateY(180deg)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
                }}
              >
                <div style={{writingMode: 'vertical-rl', fontFamily: fam(TYPE_FACE), fontSize: cell * 0.7, lineHeight: 1.43, letterSpacing: cell * 0.12, color: '#161616', whiteSpace: 'pre'}}>
                  {COLS.join('\n')}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      <div style={{position: 'absolute', left: vertical ? 70 : 150, top: vertical ? 1250 : 250, width: vertical ? W - 140 : 620}}>
        <StaggerText text="活字" at={6} step={8} font={C8.font} size={vertical ? 110 : 150} color={INK} mode="rise" letterSpacing={16} />
        <Line at={24} color={INK} size={vertical ? 34 : 34} style={{marginTop: 12}}>
          庆历中，有布衣毕昇，又为活板。
        </Line>
        <Line at={34} color={hexA(INK, 0.72)} size={vertical ? 24 : 24}>
          ——沈括《梦溪笔谈 · 技艺》
        </Line>
        <Line at={120} color={INK} size={vertical ? 32 : 30} style={{marginTop: vertical ? 18 : 30}}>
          比欧洲的活字印刷早约四百年。
        </Line>
      </div>
    </AbsoluteFill>
  );
};

export const S08Song: React.FC = () => (
  <Paper bg={P.bg}>
    <Sequence durationInFrames={B_START + 4} layout="none">
      <ScrollPart />
    </Sequence>
    <Sequence from={B_START - 4} layout="none">
      <PrintPart />
    </Sequence>
  </Paper>
);
