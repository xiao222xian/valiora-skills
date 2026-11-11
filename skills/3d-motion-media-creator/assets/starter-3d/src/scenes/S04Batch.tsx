import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {mergeGeometries} from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import {Cam, Stage} from '../three/Stage';
import {GroundShadow} from '../three/GroundShadow';
import {ConcreteFloor, useMat} from '../three/kit';
import {AreaLight} from '../three/lights';
import {ShotNote} from '../three/ShotNote';
import {lerpCam, type CamSpec, type V3} from '../three/camera';
import {BigNumber, thousands} from '../components/Type';
import {E, clamp01, prog} from '../lib/anim';
import {useLayout} from '../lib/layout';
import {Caption, useCams, type Cams} from './common';
import {HOUSING, PINION, SHAFT, SPLIT, WHEEL, shaftGeometry, unitBlock} from './gearbox/geometry';

// 04 批量: 1,200 finished units set down row by row on the shop floor while the camera pulls back from the first one
// to the whole batch. Two instanced meshes (housings, shaft ends) whose matrices are computed from the frame: the
// instance count is the number of units started, so units not yet placed cost nothing.

const COLS = 40;
const ROWS = 30;
const N = COLS * ROWS;
const DX = 0.42;
const DZ = 0.36;
const FIRST = 0; // local frame the first unit starts down
const LAST = 250; // local frame the last unit starts down
const DROP = 10; // frames from 0.25 m above the floor to the floor
const DROP_H = 0.25;

/** Unit i: rows from the front (+Z) backwards, left to right inside a row. */
const unitAt = (i: number): V3 => {
  const c = i % COLS;
  const r = Math.floor(i / COLS);
  return [(c - (COLS - 1) / 2) * DX, 0, ((ROWS - 1) / 2 - r) * DZ];
};
const startOf = (i: number) => FIRST + (i / (N - 1)) * (LAST - FIRST);
const placedAt = (frame: number) => {
  const n = Math.floor(((frame - DROP - FIRST) / (LAST - FIRST)) * (N - 1)) + 1;
  return Math.max(0, Math.min(N, n));
};

const U0 = unitAt(0);
const CAMS: Cams = {
  h: [
    {pos: [U0[0] + 1.0, 0.5, U0[2] + 1.35], target: [U0[0] + 0.1, 0.06, U0[2]], focal: 70},
    {pos: [6.5, 7.5, 13.5], target: [0, 0, -0.5], focal: 24},
  ],
  v: [
    {pos: [U0[0] + 0.9, 0.6, U0[2] + 1.45], target: [U0[0] + 0.1, 0.08, U0[2]], focal: 60},
    {pos: [5.5, 11.5, 15.5], target: [0, 0, -1.5], focal: 24},
  ],
};

const Units: React.FC = () => {
  const frame = useCurrentFrame();
  const body = useMat('castAlu', {repeat: 16});
  const steel = useMat('steel', {repeat: [1, 0.25]});
  const geo = useMemo(() => {
    // shaft ends that stick out of a closed unit: input out of the front, output out of the back
    const pin = shaftGeometry(SHAFT.pinion.r, HOUSING.z, SHAFT.pinion.z1);
    pin.translate(PINION.x, SPLIT, 0);
    const wheel = shaftGeometry(SHAFT.wheel.r, SHAFT.wheel.z0, -HOUSING.z);
    wheel.translate(WHEEL.x, SPLIT, 0);
    // both shaft ends in one draw call
    return {block: unitBlock(), ends: mergeGeometries([pin, wheel])};
  }, []);
  const bodies = useRef<THREE.InstancedMesh>(null);
  const ends = useRef<THREE.InstancedMesh>(null);
  const started = Math.max(0, Math.min(N, Math.floor(((frame - FIRST) / (LAST - FIRST)) * (N - 1)) + 1));
  // matrices are a function of the frame alone; set before Remotion's advance() draws this frame
  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    for (const mesh of [bodies.current, ends.current]) {
      if (!mesh) continue;
      for (let i = 0; i < started; i++) {
        const [x, , z] = unitAt(i);
        const t = E.inOutCubic(clamp01((frame - startOf(i)) / DROP));
        m.makeTranslation(x, DROP_H * (1 - t), z);
        mesh.setMatrixAt(i, m);
      }
      mesh.count = started;
      mesh.instanceMatrix.needsUpdate = true;
    }
  }, [frame, started]);
  return (
    <>
      <instancedMesh ref={bodies} args={[geo.block, body, N]} frustumCulled={false} castShadow receiveShadow />
      <instancedMesh ref={ends} args={[geo.ends, steel, N]} frustumCulled={false} castShadow />
    </>
  );
};

const Hall: React.FC<{cam: CamSpec}> = ({cam}) => (
  <>
    <Cam {...cam} />
    <Units />
    <ConcreteFloor tile={3} color="#77797c" />
    <GroundShadow size={[COLS * DX + 2, ROWS * DZ + 2]} far={0.3} blur={0.04} resolution={2048} />
    {/* four overhead light rows of a shop hall, slightly warm; a cool skylight bounce from the back */}
    {[-6, -2, 2, 6].map((x) => (
      <AreaLight key={x} pos={[x, 6, 0]} to={[x, 0, 0]} w={0.6} h={14} intensity={6} color="#f6f0e4" />
    ))}
    <AreaLight pos={[0, 4, -12]} to={[0, 0, 0]} w={18} h={2} intensity={1.2} color="#d6e2ff" />
  </>
);

export const S04Batch: React.FC = () => {
  const frame = useCurrentFrame();
  const {W, vertical} = useLayout();
  const [a, b] = useCams(CAMS);
  const cam = lerpCam(a, b, prog(frame, 30, 300, E.inOutCubic));
  const n = placedAt(frame);
  return (
    <AbsoluteFill>
      {/* the far rows stand about 26 m from the end camera: fog starts behind them */}
      <Stage envIntensity={0.8} exposure={1.1} post={{vignette: 0.38}} fog={[28, 100]}>
        <Hall cam={cam} />
      </Stage>
      {/* a counting figure needs equal-width digits: the sans has them, the serif (Noto Serif SC) does not */}
      <BigNumber text={thousands(n)} x={vertical ? 70 : W - 96} y={vertical ? 1040 : 640} size={140} at={70} color="#F2EFE8" align={vertical ? 'left' : 'right'} unit="台 · 已就位" font="OFL-SansMedium" />
      <Caption lines={['同一型号，一千二百台']} at={260} out={355} />
      <ShotNote />
    </AbsoluteFill>
  );
};
