import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Cam, Stage} from '../three/Stage';
import {GroundShadow} from '../three/GroundShadow';
import {StudioFloor} from '../three/kit';
import {AreaLight} from '../three/lights';
import {ShotNote} from '../three/ShotNote';
import {lerpCam, orbit, type CamSpec, type V3} from '../three/camera';
import {Line, StaggerText} from '../components/Type';
import {rulerGeometry} from '../components/HUD';
import {BrandSeal} from '../brand/Seal';
import {CHAPTERS, SUBTITLE, TITLE, chapterDur} from '../timeline';
import {E, hexA, lerp, prog} from '../lib/anim';
import {useLayout} from '../lib/layout';
import {useCams, type Cams} from './common';
import {Gearbox} from './gearbox/Gearbox';

// 序: in the dark a strip light passes behind the assembled gearbox and draws its outline; the title holds; a thin
// line of light opens along the bottom and becomes the HUD's progress axis at the first frame of chapter 01.

const P = CHAPTERS[0].palette;
const END = chapterDur(0);
// 16:9 keeps the box in the right half (the title takes the left); 9:16 keeps it in the lower half
const T_L: V3 = [-0.12, 0.08, 0.06];
const T_V: V3 = [0.02, 0.17, 0];
const CAMS: Cams = {
  h: [
    {pos: orbit(T_L, 1.65, 1.15, 0.24), target: T_L, focal: 85},
    {pos: orbit(T_L, 1.42, 1.08, 0.2), target: T_L, focal: 85},
  ],
  v: [
    {pos: orbit(T_V, 1.75, 1.15, 0.28), target: T_V, focal: 85},
    {pos: orbit(T_V, 1.52, 1.08, 0.24), target: T_V, focal: 85},
  ],
};

const Shot: React.FC<{cam: CamSpec}> = ({cam}) => {
  const frame = useCurrentFrame();
  // the sweep: a strip behind the box travels left to right; the key comes up only after it has passed
  const sweep = lerp(-1.4, 1.4, prog(frame, 10, 150, E.inOutSine));
  const key = 18 * prog(frame, 120, 80, E.inOutSine) * (1 - prog(frame, 285, 40, E.inCubic));
  return (
    <>
      <Cam {...cam} />
      <Gearbox spin={frame * 0.012} />
      <StudioFloor mirror={0.4} />
      <GroundShadow size={1.2} far={0.4} blur={0.02} opacity={0.85} />
      <AreaLight pos={[sweep, 0.45, -0.55]} to={[0.02, 0.08, 0]} w={0.12} h={0.9} intensity={60} color="#f3f6ff" />
      {key > 0.01 && <AreaLight pos={[-0.5, 0.9, 0.8]} to={[0.02, 0.08, 0]} w={0.7} h={0.3} intensity={key} />}
    </>
  );
};

export const S00Opening: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical, ts} = useLayout();
  const [a, b] = useCams(CAMS);
  const cam = lerpCam(a, b, prog(frame, 0, END, E.inOutSine));
  const {x0, x1, y} = rulerGeometry(W, H, vertical);
  const open = prog(frame, 282, 44, E.inOutCubic);
  const glow = 1 - prog(frame, 300, 28, E.inCubic); // bright while it opens, the HUD's quiet line at the cut
  const blackIn = 1 - prog(frame, 0, 12, E.linear);
  const title = {left: vertical ? 70 : 150, top: vertical ? 360 : H * 0.36};
  return (
    <AbsoluteFill>
      <Stage envIntensity={0.25 + 0.3 * prog(frame, 120, 80, E.inOutSine)} post={{vignette: 0.45, bloom: 0.4}}>
        <Shot cam={cam} />
      </Stage>
      <div style={{position: 'absolute', ...title}}>
        <div style={{position: 'relative', display: 'inline-block'}}>
          <StaggerText text={TITLE} at={96} step={6} font="OFL-SerifHeavy" size={(vertical ? 150 : 140) * ts} color={P.ink} mode="ink" out={270} letterSpacing={18 * ts} />
          <div style={{position: 'absolute', left: '100%', bottom: 14 * ts, marginLeft: 18 * ts, opacity: 1 - prog(frame, 270, 12, E.inCubic)}}>
            <BrandSeal at={130} size={64 * ts} color={P.accent} paper={P.bg} />
          </div>
        </div>
        <Line at={124} out={266} color={hexA(P.ink, 0.8)} size={40 * ts} style={{letterSpacing: 10 * ts, marginTop: 18 * ts}}>
          {SUBTITLE}
        </Line>
      </div>
      {open > 0 && (
        <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
          <line
            x1={lerp((x0 + x1) / 2, x0, open)}
            x2={lerp((x0 + x1) / 2, x1, open)}
            y1={y}
            y2={y}
            stroke={hexA(P.hud, 0.32 + 0.6 * glow)}
            strokeWidth={1.5 + 1.5 * glow}
            style={{filter: glow > 0.05 ? `drop-shadow(0 0 ${6 * glow}px ${hexA(P.ink, 0.8)})` : undefined}}
          />
        </svg>
      )}
      <ShotNote at={20} out={280} />
      <AbsoluteFill style={{background: '#000', opacity: blackIn}} />
    </AbsoluteFill>
  );
};
