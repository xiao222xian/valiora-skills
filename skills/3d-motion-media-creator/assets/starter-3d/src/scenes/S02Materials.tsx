import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Cam, Stage} from '../three/Stage';
import {FLOOR_Y, GroundShadow} from '../three/GroundShadow';
import {Bevel, useMat, type MatKind} from '../three/kit';
import {AreaLight} from '../three/lights';
import {ShotNote} from '../three/ShotNote';
import {hdriFile} from '../three/textures';
import {lerpCam, orbit, project, type CamSpec, type V3} from '../three/camera';
import {E, lerp, prog} from '../lib/anim';
import {MONO} from '../lib/fonts';
import {TYPE_FLOOR, useLayout} from '../lib/layout';
import {Caption, useCams, type Cams} from './common';

// 02 材料: ten surfaces of the kit on a concrete plinth, each as a bevelled tile with a ball on it (the tile shows the
// micro-surface, the ball the reflections), lit by a studio HDRI while a soft strip light sweeps across them.

const SAMPLES: {kind: MatKind; name: string; color?: string; repeat?: number}[] = [
  {kind: 'castAlu', name: '铸铝', repeat: 2.5},
  {kind: 'brushedAlu', name: '拉丝铝'},
  {kind: 'circularAlu', name: '旋纹铝'},
  {kind: 'steel', name: '不锈钢'},
  {kind: 'chrome', name: '镀铬'},
  {kind: 'copper', name: '铜'},
  {kind: 'anodized', name: '阳极氧化铝'},
  {kind: 'rubber', name: '橡胶'},
  {kind: 'machinePaint', name: '机器漆'},
  {kind: 'leather', name: '皮革', color: '#8a5a3c'},
];
const TILE = 0.12;
const BALL = 0.032;
const PLINTH_Y = 0.06;

/** Grid cell and position of sample i: five across and two deep in 16:9, two across and five deep in 9:16. */
const cell = (i: number, vertical: boolean) => {
  const cols = vertical ? 2 : 5;
  const col = i % cols;
  const row = Math.floor(i / cols);
  const rows = SAMPLES.length / cols;
  const at: V3 = [(col - (cols - 1) / 2) * (vertical ? 0.2 : 0.19), PLINTH_Y, (row - (rows - 1) / 2) * 0.21];
  return {col, row, at};
};
const place = (i: number, vertical: boolean) => cell(i, vertical).at;

/** Where sample i's label hangs, kept off the other samples: 16:9 above the back row's balls and under the front
 * row's tiles; 9:16 outside the two columns. Returns the 3D anchor and the label's CSS offset from it. */
const labelAt = (i: number, vertical: boolean): {p: V3; shift: string} => {
  const {col, row, at} = cell(i, vertical);
  const [x, y, z] = at;
  if (vertical) return col === 0 ? {p: [x - TILE / 2, y, z], shift: 'translate(calc(-100% - 10px), -50%)'} : {p: [x + TILE / 2, y, z], shift: 'translate(10px, -50%)'};
  return row === 0 ? {p: [x, y + 0.014 + 2 * BALL, z], shift: 'translate(-50%, calc(-100% - 8px))'} : {p: [x, y, z + TILE / 2], shift: 'translate(-50%, 10px)'};
};

const C0: V3 = [0, 0.06, 0];
const CV: V3 = [0, 0.06, 0.3]; // aimed at the front rows, so the grid sits high in the frame
const CAMS: Cams = {
  h: [
    {pos: orbit(C0, 1.5, 1.38, 0.56), target: C0, focal: 50},
    {pos: orbit(C0, 1.3, 1.6, 0.5), target: [0, 0.06, 0.02], focal: 50},
  ],
  // the five rows stay inside the 9:16 stage band (y 330-1540), clear of the caption and the HUD
  v: [
    {pos: orbit(CV, 2.4, 1.45, 0.82), target: CV, focal: 50},
    {pos: orbit(CV, 2.15, 1.6, 0.78), target: CV, focal: 50},
  ],
};

const Sample: React.FC<{kind: MatKind; color?: string; repeat?: number; at: V3}> = ({kind, color, repeat = 0.45, at}) => {
  const tile = useMat(kind, {repeat, color});
  const ball = useMat(kind, {repeat: [repeat * 4, repeat * 2], color});
  return (
    <group position={at}>
      <Bevel size={[TILE, 0.014, TILE]} position={[0, 0.007, 0]} material={tile} r={0.003} />
      <mesh position={[0, 0.014 + BALL, 0]} material={ball} castShadow receiveShadow>
        <sphereGeometry args={[BALL, 64, 32]} />
      </mesh>
    </group>
  );
};

const Shot: React.FC<{cam: CamSpec; vertical: boolean}> = ({cam, vertical}) => {
  const frame = useCurrentFrame();
  const plinth = useMat('concrete', {repeat: 1.2, color: '#6b6e71'});
  // the strip light travels along the row of samples, slow in and out
  const sweep = lerp(-0.9, 0.9, prog(frame, 30, 280, E.inOutSine));
  return (
    <>
      <Cam {...cam} />
      {/* the plinth top lies FLOOR_Y under the samples' contact plane, room for the shadow between */}
      <Bevel size={vertical ? [0.6, PLINTH_Y + FLOOR_Y, 1.25] : [1.15, PLINTH_Y + FLOOR_Y, 0.6]} position={[0, (PLINTH_Y + FLOOR_Y) / 2, 0]} material={plinth} r={0.006} />
      {SAMPLES.map((s, i) => (
        <Sample key={s.kind} kind={s.kind} color={s.color} repeat={s.repeat} at={place(i, vertical)} />
      ))}
      <GroundShadow y={PLINTH_Y} size={vertical ? [0.58, 1.23] : [1.13, 0.58]} far={0.12} blur={0.012} />
      <AreaLight pos={[sweep, 0.7, 0.55]} to={[sweep * 0.6, 0.06, 0]} w={0.35} h={0.12} intensity={30} />
      <AreaLight pos={[-0.9, 0.5, -0.6]} to={[0, 0.06, 0]} w={0.6} h={0.2} intensity={5} color="#dfe8ff" />
    </>
  );
};

export const S02Materials: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, H, vertical, ts} = useLayout();
  const [a, b] = useCams(CAMS);
  const cam = lerpCam(a, b, prog(frame, 0, 360, E.inOutSine));
  return (
    <AbsoluteFill>
      <Stage hdri={hdriFile('studio_small_09', '1k')} envIntensity={0.4} envRotation={0.6} exposure={1.05} post={{vignette: 0.35}}>
        <Shot cam={cam} vertical={vertical} />
      </Stage>
      {SAMPLES.map((s, i) => {
        const {p, shift} = labelAt(i, vertical);
        const [px, py] = project(cam, W, H, p);
        const o = prog(frame, 40 + i * 8, 12, E.outCubic);
        return (
          <div
            key={s.kind}
            style={{position: 'absolute', left: px, top: py, transform: shift, fontFamily: MONO, fontSize: TYPE_FLOOR.callout * ts, letterSpacing: 1, color: '#F2EFE8', opacity: o * 0.9, whiteSpace: 'nowrap', textShadow: '0 1px 8px rgba(0,0,0,0.7)'}}
          >
            {s.name}
          </div>
        );
      })}
      <Caption lines={['同一组光下的十种表面']} at={150} out={330} />
      <ShotNote />
    </AbsoluteFill>
  );
};
