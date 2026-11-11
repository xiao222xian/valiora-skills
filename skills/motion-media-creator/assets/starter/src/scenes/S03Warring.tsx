import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {noise2D} from '@remotion/noise';
import {Paper} from '../components/Paper';
import {Line, StaggerText} from '../components/Type';
import {CHAPTERS} from '../timeline';
import {E, clamp01, hexA, lerp, prog} from '../lib/anim';
import {BODY, fam} from '../lib/fonts';
import {useLayout} from '../lib/layout';

const C3 = CHAPTERS[3];
const P = C3.palette;
const QIN_RED = CHAPTERS[4].palette.accent; // the colour 秦 carries into the next chapter

// Right-to-left, the order bamboo slips are read in. Roughly chronological so the reading
// pass (96-186) runs with the HUD counter (-551 at 30 -> -280 at 180): 孔子 first, 韩非子 last.
const SLIPS = [
  {who: '孔子', q: '学而时习之'},
  {who: '孙子', q: '知彼知己'},
  {who: '老子', q: '道可道　非常道'},
  {who: '墨子', q: '兼相爱　交相利'},
  {who: '孟子', q: '民为贵'},
  {who: '庄子', q: '北冥有鱼'},
  {who: '荀子', q: '锲而不舍'},
  {who: '韩非子', q: '法不阿贵'},
];

// Seven states, laid out by rough relative position (west to east), each name set in a
// different typeface: 文字异形. 韩 (capital 新郑) sits south-west of 魏 (capital 大梁).
export const STATES = [
  {n: '秦', x: 0.17, y: 0.48, r: 118, font: 'ZL-Li', c: '#2b2622'},
  {n: '楚', x: 0.55, y: 0.76, r: 128, font: 'ZL-Xingkai', c: '#8a3b24'},
  {n: '齐', x: 0.83, y: 0.47, r: 100, font: 'ZL-SongBlack', c: '#4c6a78'},
  {n: '燕', x: 0.76, y: 0.2, r: 88, font: 'ZL-Weibei', c: '#6f7b4a'},
  {n: '赵', x: 0.55, y: 0.27, r: 96, font: 'ZL-KaiBlack', c: '#7a5a2c'},
  {n: '魏', x: 0.65, y: 0.49, r: 82, font: 'ZL-Baoli', c: '#5b4a6b'},
  {n: '韩', x: 0.38, y: 0.64, r: 64, font: 'ZL-HeiHeavy', c: '#9a6a3a'},
];

export const statesRect = (W: number, H: number, vertical: boolean) =>
  vertical ? {x: 70, y: 470, w: W - 140, h: 820, s: 0.78} : {x: 640, y: 150, w: 1120, h: 760, s: 1};

const mixHex = (a: string, b: string, t: number) => {
  const pa = parseInt(a.slice(1), 16);
  const pb = parseInt(b.slice(1), 16);
  const ch = (s: number) => Math.round(lerp((pa >> s) & 255, (pb >> s) & 255, clamp01(t)));
  return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
};

const READ_AT = 96;
const READ_STEP = 11;
const MORPH_AT = 196;
const PULL_AT = 318; // 秦 starts drawing the others in; the next chapter's merge picks it up

export const S03Warring: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {W, H, vertical} = useLayout();

  const slipW = 104;
  const gap = vertical ? 10 : 22;
  const slipH = vertical ? 740 : 720;
  const totalW = SLIPS.length * slipW + (SLIPS.length - 1) * gap;
  const x0 = vertical ? (W - totalW) / 2 : W - 150 - totalW;
  const y0 = vertical ? 604 : 196;
  const liftPx = vertical ? 20 : 30;
  const cell = 56; // one quote character per cell, top to bottom
  const qTop = 128;

  const sr = statesRect(W, H, vertical);
  const cord = prog(frame, 70, 30, E.inOutCubic) * (1 - prog(frame, MORPH_AT - 6, 10, E.linear));

  // where 秦 is pulled: the centroid of the other six
  const centre = (st: (typeof STATES)[number]) => [sr.x + st.x * sr.w, sr.y + st.y * sr.h];
  const others = STATES.slice(1).map(centre);
  const [qx, qy] = centre(STATES[0]);
  const gx = others.reduce((s, p) => s + p[0], 0) / others.length;
  const gy = others.reduce((s, p) => s + p[1], 0) / others.length;
  const gl = Math.hypot(gx - qx, gy - qy) || 1;
  const pull = prog(frame, PULL_AT, 14, E.inCubic);

  return (
    <Paper bg={P.bg}>
      {/* binding cords */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[y0 + 110, y0 + slipH - 110].map((yy, k) => (
          <line key={k} x1={x0 + totalW + 30} x2={x0 + totalW + 30 - (totalW + 60) * cord} y1={yy} y2={yy + 4} stroke="#4f381e" strokeWidth={3.4} opacity={cord > 0 ? 0.85 : 0} />
        ))}
      </svg>

      {SLIPS.map((sl, i) => {
        const order = i; // index 0 is the right-most slip
        const sx = x0 + totalW - slipW - order * (slipW + gap);
        const drop = spring({frame: frame - 4 - order * 6, fps, config: {damping: 12, stiffness: 140, mass: 0.9}});
        const rot = (1 - drop) * (order % 2 ? 7 : -6);

        // reading pass: the slip springs up, then settles back with a small bounce
        const readAt = READ_AT + order * READ_STEP;
        const lift =
          spring({frame: frame - readAt, fps, config: {damping: 10, stiffness: 190, mass: 0.6}}) -
          spring({frame: frame - readAt - 8, fps, config: {damping: 9, stiffness: 150, mass: 0.7}});

        const st = STATES[Math.min(i, STATES.length - 1)];
        const m = prog(frame, MORPH_AT + order * 3, 30, E.inOutQuint);
        const gone = i >= STATES.length ? prog(frame, MORPH_AT, 14, E.inCubic) : 0;
        const [cx, cy] = centre(st);
        const d = st.r * 2 * sr.s;

        // settled discs keep drifting on a slow noise field
        const settle = i < STATES.length ? prog(frame, MORPH_AT + order * 3 + 22, 24, E.inOutSine) : 0;
        const nT = frame / 45;
        let jx = noise2D(`wx${i}`, nT, 0.5) * 5 * settle;
        let jy = noise2D(`wy${i}`, 0.5, nT) * 5 * settle;
        let sc = 1 + 0.018 * noise2D(`ws${i}`, nT * 0.8, 3.1) * settle;
        let col = st.c;
        if (i === 0) {
          jx += ((gx - qx) / gl) * 34 * pull;
          jy += ((gy - qy) / gl) * 34 * pull;
          sc *= 1 + 0.06 * pull;
          col = mixHex(st.c, QIN_RED, pull);
        } else if (i < STATES.length) {
          const dx = qx - cx;
          const dy = qy - cy;
          const dl = Math.hypot(dx, dy) || 1;
          jx += (dx / dl) * 10 * pull;
          jy += (dy / dl) * 10 * pull;
          sc *= 1 - 0.03 * pull;
        }

        const left = lerp(sx, cx - d / 2, m) + jx;
        const top = lerp(y0 + (1 - drop) * -980 - liftPx * lift * (1 - m), cy - d / 2, m) + jy;
        const w = lerp(slipW, d, m);
        const h = lerp(slipH, d, m);
        const radius = lerp(6, d / 2, m);
        const tilt = lift * (order % 2 ? 0.8 : -0.8);
        const textQ = 1 - prog(frame, MORPH_AT - 4, 14, E.inCubic);
        const textS = prog(frame, MORPH_AT + 18 + order * 3, 16, E.outCubic);
        const up = Math.max(0, lift);
        return (
          <div
            key={sl.who}
            style={{
              position: 'absolute',
              left,
              top,
              width: w,
              height: h,
              borderRadius: radius,
              transform: `rotate(${lerp(rot + tilt, 0, m)}deg) scale(${sc})`,
              background:
                m < 1
                  ? `linear-gradient(90deg, ${hexA('#9c7a3f', 1 - m)} 0%, ${hexA('#e9d6a4', 1 - m)} 28%, ${hexA('#f0e0b4', 1 - m)} 52%, ${hexA('#c9a764', 1 - m)} 100%), ${col}`
                  : col,
              boxShadow: `0 ${lerp(10 + 16 * up, 18, m)}px ${lerp(18 + 22 * up, 40, m)}px rgba(60,40,10,${0.28 - 0.06 * up})`,
              opacity: 1 - gone,
              overflow: 'hidden',
            }}
          >
            {m < 1 && (
              <div style={{position: 'absolute', left: 0, right: 0, top: slipH * 0.36, height: 3, background: hexA('#7d5c2c', 0.35 * (1 - m))}} />
            )}
            {textQ > 0 && (
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  right: 0,
                  top: qTop,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  fontFamily: fam('ZL-Baoli'),
                  fontSize: 50,
                  lineHeight: 1,
                  opacity: textQ,
                }}
              >
                {Array.from(sl.q).map((ch, k) => {
                  // each character falls in on its own spring, two frames behind the last
                  const s = spring({frame: frame - (18 + order * 6 + k * 2), fps, config: {damping: 11, stiffness: 170, mass: 0.7}});
                  const hiAt = readAt + 2 + k * 2;
                  const hi = prog(frame, hiAt, 4, E.outCubic) * (1 - prog(frame, hiAt + 8, 22, E.inOutSine));
                  return (
                    <div
                      key={k}
                      style={{
                        height: cell,
                        color: mixHex(P.ink, P.accent, hi),
                        opacity: clamp01(s * 4),
                        transform: `translateY(${(1 - s) * -170}px) scale(${1 + 0.14 * hi})`,
                      }}
                    >
                      {ch}
                    </div>
                  );
                })}
              </div>
            )}
            <div
              style={{
                position: 'absolute',
                bottom: 40,
                left: '50%',
                transform: 'translateX(-50%)',
                writingMode: 'vertical-rl',
                fontFamily: fam('ZL-Kai'),
                fontSize: 26,
                letterSpacing: 4,
                color: '#f4e6c4',
                background: P.accent,
                padding: '10px 6px',
                borderRadius: 3,
                opacity: textQ * prog(frame, 34 + order * 6, 12, E.outCubic),
              }}
            >
              {sl.who}
            </div>
            {i < STATES.length && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: fam(st.font),
                  fontSize: d * 0.5,
                  color: '#f3e8cc',
                  opacity: textS,
                  transform: `scale(${0.7 + 0.3 * textS})`,
                }}
              >
                {st.n}
              </div>
            )}
          </div>
        );
      })}

      {/* phase 1: thinkers */}
      <div
        style={{
          position: 'absolute',
          left: vertical ? 70 : 150,
          top: vertical ? 334 : 300,
          width: vertical ? W - 140 : 560,
          opacity: 1 - prog(frame, MORPH_AT - 10, 14, E.inCubic),
        }}
      >
        <StaggerText text="百家争鸣" at={10} step={5} font={C3.font} size={vertical ? 100 : 118} color={P.ink} mode="rise" letterSpacing={8} />
        <Line at={40} color={P.ink} size={34} style={{marginTop: vertical ? 24 : 30}}>
          诸侯纷争的五百余年，
        </Line>
        <Line at={48} color={P.ink} size={34}>
          也是思想空前活跃的年代。
        </Line>
      </div>

      {/* phase 2: states */}
      <div style={{position: 'absolute', left: vertical ? 70 : 150, top: vertical ? 1250 : 300, width: vertical ? W - 140 : 560}}>
        <div style={{display: 'flex', alignItems: 'flex-end', gap: 22}}>
          <StaggerText text="七国" at={MORPH_AT + 10} step={6} font={C3.font} size={vertical ? 100 : 118} color={P.ink} mode="rise" letterSpacing={8} />
          <div
            style={{
              marginBottom: vertical ? 20 : 24,
              padding: '3px 10px',
              border: `1.5px solid ${hexA(P.ink, 0.55)}`,
              borderRadius: 3,
              fontFamily: BODY,
              fontSize: vertical ? 28 : 24,
              letterSpacing: 3,
              color: P.ink,
              opacity: 0.8 * prog(frame, MORPH_AT + 28, 14, E.outCubic),
            }}
          >
            方位示意
          </div>
        </div>
        <StaggerText
          text="言语异声，文字异形"
          at={MORPH_AT + 26}
          step={3}
          font="ZL-Kai"
          size={46}
          color={P.accent}
          mode="ink"
          letterSpacing={4}
          style={{marginTop: 30}}
        />
        <Line at={MORPH_AT + 50} color={hexA(P.ink, 0.78)} size={vertical ? 26 : 24} style={{marginTop: 14}}>
          ——许慎《说文解字 · 叙》
        </Line>
      </div>
    </Paper>
  );
};
