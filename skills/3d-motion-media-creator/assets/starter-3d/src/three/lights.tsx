import React, {memo, useMemo} from 'react';
import {Environment, Lightformer} from '@react-three/drei';
import * as THREE from 'three';
import {RectAreaLightUniformsLib} from 'three/examples/jsm/lights/RectAreaLightUniformsLib.js';
import type {V3} from './camera';

// Lights with a visible source: a soft strip (area light), a lamp that casts shadows (spot), and a studio environment
// for reflections built from light panels, so a shot needs no HDRI file.

// Area lights light nothing until the LTC tables are loaded; R3F does not load them. Idempotent.
RectAreaLightUniformsLib.init();

const aim = (pos: V3, to: V3) => {
  const d = new THREE.Vector3(to[0] - pos[0], to[1] - pos[1], to[2] - pos[2]).normalize();
  // an area light emits along its local -Z; Matrix4.lookAt(eye, target) points +Z from target to eye, so
  // lookAt(origin, d) turns -Z onto d (pointing it at `to` by hand is easy to get backwards)
  const up = Math.abs(d.y) > 0.99 ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(0, 1, 0);
  const m = new THREE.Matrix4().lookAt(new THREE.Vector3(0, 0, 0), d, up);
  return new THREE.Quaternion().setFromRotationMatrix(m);
};

/** A rectangular soft light (a strip light, a softbox, a window) at `pos`, facing `to`. Width and height in metres.
 * Area lights cast no shadows: ground the objects with <GroundShadow>, or add a <ShadowSpot>. */
export const AreaLight: React.FC<{pos: V3; to: V3; w: number; h: number; intensity: number; color?: string}> = ({pos, to, w, h, intensity, color = '#fff4e6'}) => {
  const q = useMemo(() => aim(pos, to), [pos.join(','), to.join(',')]);
  return <rectAreaLight position={pos} quaternion={q} width={w} height={h} intensity={intensity} color={color} />;
};

/** A shadow-casting spot standing in for a lamp: aimed at `to`, soft edge, a 2048 map with a small bias. Under
 * variance shadows (Stage's default) a plane that receives this banding: let floors take <GroundShadow> instead. */
export const ShadowSpot: React.FC<{pos: V3; to: V3; intensity: number; angle?: number; color?: string; size?: number}> = ({pos, to, intensity, angle = 0.6, color = '#fff4e6', size = 2048}) => {
  const target = useMemo(() => {
    const o = new THREE.Object3D();
    o.position.set(...to);
    o.updateMatrixWorld();
    return o;
  }, [to.join(',')]);
  return (
    <>
      <primitive object={target} />
      <spotLight
        position={pos}
        target={target}
        intensity={intensity}
        angle={angle}
        penumbra={1}
        decay={2}
        color={color}
        castShadow
        shadow-mapSize-width={size}
        shadow-mapSize-height={size}
        shadow-bias={-0.0004}
        shadow-radius={6}
        shadow-blurSamples={12}
      />
    </>
  );
};

/** Reflection environment of a product studio: a long overhead softbox, two tall side strips, a low back rim. Baked
 * once per render tab (Environment frames=1), which is safe only because nothing in it moves. Memoised: Environment
 * re-bakes whenever its children change, and a scene re-renders its children every frame. */
export const StudioEnv: React.FC<{intensity?: number; rotation?: number; warm?: string; cool?: string}> = memo(({intensity = 0.6, rotation = 0, warm = '#fff1e0', cool = '#e6eeff'}) => (
  <Environment resolution={256} environmentIntensity={intensity} environmentRotation={[0, rotation, 0]}>
    <Lightformer form="rect" intensity={3} color={warm} position={[0, 6, 0]} rotation={[Math.PI / 2, 0, 0]} scale={[10, 2, 1]} />
    <Lightformer form="rect" intensity={1.2} color={warm} position={[-6, 2, 1]} rotation={[0, Math.PI / 2, 0]} scale={[2, 6, 1]} />
    <Lightformer form="rect" intensity={0.8} color={cool} position={[6, 2, -1]} rotation={[0, -Math.PI / 2, 0]} scale={[2, 6, 1]} />
    <Lightformer form="rect" intensity={1.5} color={cool} position={[0, 1.2, -7]} scale={[12, 0.6, 1]} />
  </Environment>
));
