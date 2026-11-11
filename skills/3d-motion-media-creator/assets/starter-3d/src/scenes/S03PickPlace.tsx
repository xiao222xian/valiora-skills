import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Cam, Stage} from '../three/Stage';
import {GroundShadow} from '../three/GroundShadow';
import {Bevel, ConcreteFloor, useMat} from '../three/kit';
import {AreaLight} from '../three/lights';
import {RobotArm, ikArm, openFor} from '../three/RobotArm';
import {ShotNote} from '../three/ShotNote';
import {addV, lerpV, project, shake, type CamSpec, type V3} from '../three/camera';
import {Callout} from '../components/Type';
import {E, clamp01, prog} from '../lib/anim';
import {useLayout} from '../lib/layout';
import {CHAPTERS} from '../timeline';
import {Caption, DissolveIn, useCams, useLabelBand, type Cams} from './common';
import {WHEEL, gearGeometry, outerR, ring, shaftGeometry} from './gearbox/geometry';

// 03 取放: a six-axis robot takes the large gear off a pedestal and slides it down onto a locating spindle. The tool
// point is solved by inverse kinematics on every frame: straight up and down at the stations, an arc around the base
// in between (it reads as a joint move). One canvas, two camera set-ups with a hard cut, a 6-frame shake on the seat.

const BASE: V3 = [0, 0, 0];
const TOOL = 0.275; // flange to gear centre: the fingertips end 3 mm above the gear's underside
const TOP = 0.8; // pedestal height
const HALF = WHEEL.width / 2;
const A: V3 = [1.25, TOP + 0.02 + HALF, 0.55]; // gear centre on the pick pedestal
const B: V3 = [0.35, TOP + 0.02 + 0.006 + HALF, 1.25]; // gear centre seated on the spindle collar
const UP = 0.25;
const READY: V3 = [0.95, 1.35, 0.95];
const GRIP = openFor(outerR(WHEEL.teeth));
const WIDE = 0.75;
const SEAT = 250; // local frame the gear lands on the collar (CUES.seatHit)
const YAW_A = ikArm(A, BASE, TOOL).j1;
const YAW_B = ikArm(B, BASE, TOOL).j1;
const CUT = 200; // wide shot -> close-up

/** Tool-space move around the robot: angle, reach and height interpolate separately, so the tool sweeps an arc. */
const arc = (a: V3, b: V3, t: number): V3 => {
  const fa = Math.atan2(a[2], a[0]);
  const fb = Math.atan2(b[2], b[0]);
  const ra = Math.hypot(a[0], a[2]);
  const rb = Math.hypot(b[0], b[2]);
  const f = fa + (fb - fa) * t;
  const r = ra + (rb - ra) * t;
  return [r * Math.cos(f), a[1] + (b[1] - a[1]) * t, r * Math.sin(f)];
};

const up = (p: V3): V3 => [p[0], p[1] + UP, p[2]];

/** Tool point, gripper opening and gear centre at a local frame. */
const motion = (f: number) => {
  const seg = (from: number, dur: number) => E.inOutCubic(clamp01((f - from) / dur));
  let tool: V3;
  if (f < 90) tool = arc(READY, up(A), seg(30, 60));
  else if (f < 135) tool = lerpV(up(A), A, seg(90, 30));
  else if (f < 165) tool = lerpV(A, up(A), seg(135, 30));
  else if (f < 225) tool = arc(up(A), up(B), seg(165, 60));
  else if (f < 262) tool = lerpV(up(B), B, E.outCubic(clamp01((f - 225) / (SEAT - 225))));
  else if (f < 300) tool = lerpV(B, up(B), seg(262, 38));
  else tool = arc(up(B), READY, seg(300, 55));
  const open = f < 120 ? WIDE : f < 135 ? WIDE + (GRIP - WIDE) * seg(120, 12) : f < SEAT ? GRIP : GRIP + (WIDE - GRIP) * seg(SEAT + 2, 12);
  const gear = f < 135 ? A : f < SEAT ? tool : B;
  return {tool, open, gear};
};

const CAMS: Cams = {
  // wide: high enough that the pedestals do not hide the robot between them
  h: [
    {pos: [3.1, 2.9, 3.3], target: [0.45, 0.85, 0.55], focal: 28},
    // close-up from across the fingers (they open towards and away from the robot base), not along them
    {pos: addV(B, [0.95, 0.32, -0.27]), target: addV(B, [0, 0.09, 0]), focal: 70},
  ],
  v: [
    {pos: [3.3, 3.4, 3.6], target: [0.45, 0.95, 0.55], focal: 28},
    {pos: addV(B, [0.82, 0.36, -0.23]), target: addV(B, [0, 0.12, 0]), focal: 60},
  ],
};

const Cell: React.FC<{cam: CamSpec}> = ({cam}) => {
  const frame = useCurrentFrame();
  const {tool, open, gear} = motion(frame);
  const joints = ikArm(tool, BASE, TOOL);
  const ped = useMat('machinePaint', {color: '#6c7075'});
  // dark machined plates: bright brushed aluminium under the overhead strip blew out to white
  const plate = useMat('darkSteel', {repeat: 0.6});
  const chrome = useMat('chrome', {roughness: 1.6});
  const wheelMat = useMat('darkSteel', {repeat: 8});
  const g = useMemo(() => {
    const spindle = shaftGeometry(WHEEL.bore - 0.0004, 0, 0.09);
    // lathe along Z -> stand it up along Y
    spindle.rotateX(-Math.PI / 2);
    const collar = ring(0.026, WHEEL.bore - 0.0004, 0.006);
    collar.rotateX(-Math.PI / 2);
    return {wheel: gearGeometry(WHEEL.teeth, WHEEL.width, WHEEL.bore), spindle, collar};
  }, []);
  // the gear keeps its place between the fingers: while carried it turns with the robot's yaw
  const yaw = frame < 135 ? 0 : (frame < SEAT ? joints.j1 : YAW_B) - YAW_A;
  return (
    <>
      <Cam {...cam} />
      <RobotArm joints={joints} position={BASE} tool="gripper" toolOpen={open} />
      {[A, B].map((p, i) => (
        <group key={i} position={[p[0], 0, p[2]]}>
          <Bevel size={[0.32, TOP, 0.32]} position={[0, TOP / 2, 0]} material={ped} r={0.01} />
          <Bevel size={[0.36, 0.02, 0.36]} position={[0, TOP + 0.01, 0]} material={plate} r={0.004} />
        </group>
      ))}
      <group position={[B[0], TOP + 0.02, B[2]]}>
        <mesh geometry={g.collar} material={chrome} position={[0, 0.003, 0]} castShadow receiveShadow />
        <mesh geometry={g.spindle} material={chrome} castShadow receiveShadow />
      </group>
      <mesh geometry={g.wheel} material={wheelMat} position={gear} rotation={[-Math.PI / 2, 0, yaw]} castShadow receiveShadow />
      <ConcreteFloor tile={3} color="#7d8083" />
      <GroundShadow center={[0.6, 0.6]} size={6} far={2.2} blur={0.06} opacity={0.75} />
      {/* an overhead light row over the cell, a cool rim from behind the robot, a low warm bounce */}
      <AreaLight pos={[0.7, 3.4, 0.7]} to={[0.7, 0, 0.7]} w={2.6} h={0.5} intensity={14} color="#f4f1ea" />
      <AreaLight pos={[-1.8, 1.6, -1.4]} to={[0.4, 0.9, 0.4]} w={1.4} h={0.4} intensity={7} color="#d7e3ff" />
      <AreaLight pos={[2.6, 0.5, 2.2]} to={[0.6, 0.6, 0.6]} w={1.2} h={0.6} intensity={1.5} color="#ffd9b0" />
    </>
  );
};

export const S03PickPlace: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical} = useLayout();
  const [wide, close] = useCams(CAMS);
  const base = frame < CUT ? wide : close;
  const drift: V3 = frame < CUT ? [-0.3 * prog(frame, 0, CUT, E.linear), -0.2 * prog(frame, 0, CUT, E.linear), 0] : [0, -0.02 * prog(frame, CUT, 160, E.inOutSine), 0];
  const s = shake(frame, [SEAT], frame < CUT ? 0.01 : 0.0035);
  const cam: CamSpec = {...base, pos: addV(addV(base.pos, drift), s), target: addV(base.target, s)};
  const spindleTop = project(cam, W, H, [B[0], TOP + 0.02 + 0.09, B[2]]);
  const band = useLabelBand();
  return (
    <DissolveIn frames={CHAPTERS.find((c) => c.id === 'pickplace')!.transitionFrames}>
      {/* the robot stands about 6 m from the wide camera: fog starts behind it */}
      <Stage envIntensity={0.5} exposure={1.1} post={{vignette: 0.4, bloom: 0.25}} fog={[9, 45]}>
        <Cell cam={cam} />
      </Stage>
      {frame >= CUT && (
        <Callout
          from={spindleTop}
          to={[spindleTop[0] + (vertical ? -150 : -260), band.y(spindleTop[1] - (vertical ? 160 : 120))]}
          label="定位心轴"
          at={CUT + 6}
          out={SEAT - 12}
          color="#F2EFE8"
          align="right"
          shadow
        />
      )}
      <Caption lines={['机械臂取下大齿轮', '装上定位心轴']} at={40} out={CUT - 6} />
      <ShotNote />
    </DissolveIn>
  );
};
