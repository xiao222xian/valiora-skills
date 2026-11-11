import React, {useMemo} from 'react';
import * as THREE from 'three';
import {useMat} from '../../three/kit';
import type {V3} from '../../three/camera';
import {E, clamp01} from '../../lib/anim';
import {BEARING, BOLTS, BOSS, HOUSING, PINION, SHAFT, SPLIT, WHEEL, bossHalf, boltGeometries, coverBlock, gearGeometry, housingWalls, ring, shaftGeometry} from './geometry';

/** How far each part has travelled out of the assembly, 0..1 (eased by the caller or by explodeAt). */
export type Explode = {bolts: number; cover: number; wheel: number; pinion: number; bearings: number; seals: number};
export const ASSEMBLED: Explode = {bolts: 0, cover: 0, wheel: 0, pinion: 0, bearings: 0, seals: 0};

/** Disassembly order with heavy slow-in, slow-out moves (no overshoot): bolts, cover, the two shaft assemblies,
 * then bearings and seals slide off along the shafts. Local frames from `at`. */
export const explodeAt = (frame: number, at: number): Explode => {
  const p = (from: number, dur: number) => E.inOutCubic(clamp01((frame - at - from) / dur));
  return {bolts: p(0, 40), cover: p(25, 50), wheel: p(55, 50), pinion: p(70, 50), bearings: p(100, 45), seals: p(115, 45)};
};

// travel of each part (metres)
const LIFT = {bolts: 0.42, cover: 0.3, wheel: 0.2, pinion: 0.13};
const SLIDE = {pinion: 0.06, wheel: 0.07, seal: 0.04};

/** Where a part's anchor sits in the exploded state, for callouts (project() it through the shot's camera). */
export const anchors = (x: Explode) => ({
  cover: [HOUSING.x1 - 0.02, HOUSING.top + LIFT.cover * x.cover, HOUSING.z] as V3,
  bolt: [BOLTS[5][0], HOUSING.top + 0.006 + LIFT.bolts * x.bolts, BOLTS[5][1]] as V3,
  wheel: [WHEEL.x + 0.05, SPLIT + LIFT.wheel * x.wheel + 0.045, WHEEL.width / 2] as V3,
  pinionShaft: [PINION.x, SPLIT + LIFT.pinion * x.pinion, SHAFT.pinion.z1 - 0.01] as V3,
  bearing: [WHEEL.x, SPLIT + LIFT.wheel * x.wheel + BEARING.wheel, -(BEARING.z + SLIDE.wheel * x.bearings)] as V3,
  housing: [HOUSING.x0 + 0.01, SPLIT * 0.6, HOUSING.z] as V3,
});

const seal = (r: number) => new THREE.TorusGeometry(r + 0.0032, 0.0028, 16, 48);

/** The gearbox on y = 0, shafts along Z, input shaft out of the front (+Z). Materials come from the kit; geometry is
 * built once per mount. `spin` turns the gear train (radians of the pinion). */
export const Gearbox: React.FC<{explode?: Explode; spin?: number; position?: V3; rotationY?: number}> = ({explode = ASSEMBLED, spin = 0, position, rotationY = 0}) => {
  // the cast grain at its real size: one tile of the concrete-derived micro-surface every 6 cm
  const cast = useMat('castAlu', {repeat: 16});
  const shaftMat = useMat('steel', {repeat: [1, 0.25]});
  const pinionMat = useMat('steel', {repeat: 10});
  const wheelMat = useMat('darkSteel', {repeat: 8});
  const raceMat = useMat('chrome', {roughness: 2, repeat: 4});
  const sealMat = useMat('rubber', {repeat: 4});
  const boltMat = useMat('darkSteel', {repeat: 2});
  const g = useMemo(() => {
    const {head, shank} = boltGeometries();
    return {
      walls: housingWalls(),
      cover: coverBlock(),
      pinion: gearGeometry(PINION.teeth, PINION.width, PINION.bore),
      wheel: gearGeometry(WHEEL.teeth, WHEEL.width, WHEEL.bore),
      pinionShaft: shaftGeometry(SHAFT.pinion.r, SHAFT.pinion.z0, SHAFT.pinion.z1),
      wheelShaft: shaftGeometry(SHAFT.wheel.r, SHAFT.wheel.z0, SHAFT.wheel.z1),
      bossLo: {pinion: bossHalf(BOSS.pinion, BEARING.pinion + BOSS.clearance, false), wheel: bossHalf(BOSS.wheel, BEARING.wheel + BOSS.clearance, false)},
      bossHi: {pinion: bossHalf(BOSS.pinion, BEARING.pinion + BOSS.clearance, true), wheel: bossHalf(BOSS.wheel, BEARING.wheel + BOSS.clearance, true)},
      race: {pinion: ring(BEARING.pinion, SHAFT.pinion.r, BEARING.width), wheel: ring(BEARING.wheel, SHAFT.wheel.r, BEARING.width)},
      // the rubber shield of a sealed bearing, 0.6 mm proud of the race face
      shield: {pinion: ring(BEARING.pinion - 0.0035, SHAFT.pinion.r + 0.0035, BEARING.width + 0.0012, 0.0003), wheel: ring(BEARING.wheel - 0.0035, SHAFT.wheel.r + 0.0035, BEARING.width + 0.0012, 0.0003)},
      seal: {pinion: seal(SHAFT.pinion.r), wheel: seal(SHAFT.wheel.r)},
      boltHead: head,
      boltShank: shank,
    };
  }, []);
  const x = explode;
  const yCover = LIFT.cover * x.cover;
  const yBolts = LIFT.bolts * x.bolts;
  const wheelSpin = -spin * (PINION.teeth / WHEEL.teeth) + Math.PI / WHEEL.teeth; // half a pitch: a gap faces the pinion
  // one shaft assembly: shaft, gear, a bearing at each wall, the lip seal where the shaft leaves the housing
  const train = (k: 'pinion' | 'wheel') => {
    const P = k === 'pinion' ? PINION : WHEEL;
    const lift = LIFT[k] * x[k];
    const slide = SLIDE[k] * x.bearings;
    const out = k === 'pinion' ? 1 : -1; // the shaft leaves through the front (pinion) or the back (wheel)
    const sealZ = out * (HOUSING.z + BOSS.depth + 0.004 + SLIDE.seal * x.seals + SLIDE[k] * x.bearings);
    return (
      <group key={k} position={[P.x, SPLIT + lift, 0]}>
        <mesh geometry={k === 'pinion' ? g.pinionShaft : g.wheelShaft} material={shaftMat} castShadow receiveShadow />
        <mesh geometry={g[k]} material={k === 'pinion' ? pinionMat : wheelMat} rotation={[0, 0, k === 'pinion' ? spin : wheelSpin]} castShadow receiveShadow />
        {[-1, 1].map((s) => (
          <group key={s} position={[0, 0, s * (BEARING.z + slide)]}>
            <mesh geometry={g.race[k]} material={raceMat} castShadow receiveShadow />
            <mesh geometry={g.shield[k]} material={sealMat} />
          </group>
        ))}
        <mesh geometry={g.seal[k]} material={sealMat} position={[0, 0, sealZ]} castShadow />
      </group>
    );
  };
  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* lower housing: walls, floor, the lower halves of the four bearing bosses */}
      <mesh geometry={g.walls} material={cast} castShadow receiveShadow />
      <mesh material={cast} position={[(HOUSING.x0 + HOUSING.x1) / 2, (HOUSING.floor + 0.0005) / 2, 0]} receiveShadow>
        <boxGeometry args={[HOUSING.x1 - HOUSING.x0 - HOUSING.wall, HOUSING.floor - 0.0005, 2 * HOUSING.z - HOUSING.wall]} />
      </mesh>
      {(['pinion', 'wheel'] as const).flatMap((k) =>
        [1, -1].map((s) => <mesh key={`lo${k}${s}`} geometry={g.bossLo[k]} material={cast} position={[k === 'pinion' ? PINION.x : WHEEL.x, SPLIT, s * HOUSING.z]} rotation={[0, s > 0 ? 0 : Math.PI, 0]} castShadow receiveShadow />),
      )}
      {train('wheel')}
      {train('pinion')}
      {/* cover with the upper boss halves */}
      <group position={[0, yCover, 0]}>
        <mesh geometry={g.cover} material={cast} castShadow receiveShadow />
        {(['pinion', 'wheel'] as const).flatMap((k) =>
          [1, -1].map((s) => <mesh key={`hi${k}${s}`} geometry={g.bossHi[k]} material={cast} position={[k === 'pinion' ? PINION.x : WHEEL.x, SPLIT, s * HOUSING.z]} rotation={[0, s > 0 ? 0 : Math.PI, 0]} castShadow receiveShadow />),
        )}
      </group>
      {BOLTS.map(([bx, bz], i) => (
        <group key={i} position={[bx, HOUSING.top + yBolts, bz]}>
          <mesh geometry={g.boltHead} material={boltMat} castShadow />
          {/* the shank only shows once the bolt is out of its hole */}
          {x.bolts > 0 && <mesh geometry={g.boltShank} material={boltMat} castShadow />}
        </group>
      ))}
    </group>
  );
};
