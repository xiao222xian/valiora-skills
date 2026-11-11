import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Cam, Stage} from '../three/Stage';
import {GroundShadow} from '../three/GroundShadow';
import {StudioFloor} from '../three/kit';
import {AreaLight} from '../three/lights';
import {ShotNote} from '../three/ShotNote';
import {lerpCam, orbit, project, type CamSpec, type V3} from '../three/camera';
import {Callout} from '../components/Type';
import {E, prog} from '../lib/anim';
import {useLayout} from '../lib/layout';
import {Caption, useCams, useLabelBand, type Cams} from './common';
import {Gearbox, anchors, explodeAt, type Explode} from './gearbox/Gearbox';

// 01 拆解: the assembled gearbox comes apart part by part (bolts, cover, both shaft assemblies, bearings and seals)
// while the camera pulls back and orbits under 1 degree a second; callouts are pinned to the parts with project().

const EXPLODE_AT = 90; // local frame: the first bolt lifts on CUES.explodeHit, once the camera has pulled back
const LOW: V3 = [0.02, 0.08, 0];
const HIGH: V3 = [0.02, 0.3, 0];
const CAMS: Cams = {
  h: [
    {pos: orbit(LOW, 0.78, 0.95, 0.36), target: LOW, focal: 50},
    {pos: orbit(HIGH, 1.36, 0.78, 0.28), target: HIGH, focal: 35},
  ],
  v: [
    {pos: orbit(LOW, 0.95, 0.95, 0.36), target: LOW, focal: 50},
    {pos: orbit(HIGH, 1.5, 0.78, 0.3), target: HIGH, focal: 45},
  ],
};

/** The exploded-view set: the gearbox at `explode`, its floor and lights. CoverPicture.tsx shows it too. */
export const ExplodeSet: React.FC<{cam: CamSpec; explode: Explode}> = ({cam, explode}) => (
  <>
    <Cam {...cam} />
    <Gearbox explode={explode} />
    <StudioFloor mirror={0.35} />
    <GroundShadow size={1.4} far={0.6} blur={0.02} opacity={0.85} />
    {/* key: a warm softbox high front-left; fill: a cool strip low right; rim: a cool spot from behind */}
    <AreaLight pos={[-0.7, 1.1, 0.9]} to={[0.02, 0.15, 0]} w={0.9} h={0.35} intensity={22} />
    <AreaLight pos={[1.0, 0.35, 0.4]} to={[0.02, 0.2, 0]} w={0.25} h={0.9} intensity={6} color="#dfe8ff" />
    <spotLight position={[0.6, 0.9, -1.3]} angle={0.5} penumbra={1} intensity={9} color="#d6e4ff" />
  </>
);

export const S01Explode: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical, ts} = useLayout();
  const [a, b] = useCams(CAMS);
  // pulled back before the bolts rise out of the close framing
  const cam = lerpCam(a, b, prog(frame, 0, 125, E.inOutSine));
  const at = anchors(explodeAt(frame, EXPLODE_AT));
  const k = (vertical ? 0.8 : 1) * ts;
  const band = useLabelBand();
  const pin = (p: V3, dx: number, dy: number) => {
    const from = project(cam, W, H, p);
    return {from, to: [from[0] + dx * k, band.y(from[1] + dy * k)] as [number, number]};
  };
  const labels: {p: V3; dx: number; dy: number; label: string; at: number; align: 'left' | 'right'}[] = [
    {p: at.cover, dx: 150, dy: -40, label: '箱盖', at: 255, align: 'left'},
    {p: at.wheel, dx: 190, dy: -70, label: '大齿轮 · 34 齿', at: 263, align: 'left'},
    {p: at.pinionShaft, dx: -150, dy: 60, label: '输入轴', at: 271, align: 'right'},
    {p: at.bearing, dx: 150, dy: 120, label: '轴承', at: 279, align: 'left'},
    {p: at.housing, dx: -140, dy: 40, label: '箱体', at: 287, align: 'right'},
  ];
  return (
    <AbsoluteFill>
      <Stage envIntensity={0.55} post={{vignette: 0.35, dof: {target: at.wheel, focalLength: 0.02, bokehScale: 1.6}}}>
        <ExplodeSet cam={cam} explode={explodeAt(frame, EXPLODE_AT)} />
      </Stage>
      {labels.map((l) => {
        const {from, to} = pin(l.p, l.dx, l.dy);
        return <Callout key={l.label} from={from} to={to} label={l.label} at={l.at} color="#F2EFE8" align={l.align} shadow />;
      })}
      <Caption lines={['单级齿轮减速器', '先卸螺栓与箱盖，再取出两根轴']} at={40} out={240} />
      <ShotNote />
    </AbsoluteFill>
  );
};
