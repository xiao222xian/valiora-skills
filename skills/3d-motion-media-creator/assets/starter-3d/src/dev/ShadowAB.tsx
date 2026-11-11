import React from 'react';
import {useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {ContactShadows} from '@react-three/drei';
import {useFrame} from '@react-three/fiber';
import {Bloom, EffectComposer, SMAA, Vignette} from '@react-three/postprocessing';
import * as THREE from 'three';
import {Cam} from '../three/Stage';
import {FLOOR_Y, GroundShadow} from '../three/GroundShadow';
import {AreaLight} from '../three/lights';
import {PostWarmup} from '../three/PostWarmup';
import {MONO} from '../lib/fonts';
import {useLayout} from '../lib/layout';

// Regression for the ground contact shadow under the post chain, not part of the film: a box slides over a light floor
// in four panels. Run it in a chapter's slot as a sequential render; a fresh-tab still hides the trail:
//   MODULE=../dev/ShadowAB tools/preview.sh explode sheet 16x9 30 60 330
// Expected (2026-10-13; three 0.186.1, drei 10.7.9, postprocessing 6.39.5; local frame 300 of frames 270-300 at full
// size, floor 160-165/255 away from the box): 1 GroundShadow darkens the floor at the box's foot to about 131 and
// leaves no trail; 2 drei ContactShadows under the composer leaves a trail of earlier shadows (118-156 behind the box);
// 3 the same with ClearBeforeComposer, the first 3D film's fix: shadow (about 127), no trail; 4 no composer, the
// reference (about 97, wider). Moved 2 mm above the contact plane, as the first film placed it, ContactShadows draws
// nothing under a box standing on the floor, with or without the composer. Run it again after upgrading three, drei
// or postprocessing.

type Mode = 'ground' | 'contact' | 'clear' | 'nopost';
const PANELS: [Mode, string][] = [
  ['ground', '1 GroundShadow (kit)'],
  ['contact', '2 drei ContactShadows'],
  ['clear', '3 ContactShadows + ClearBeforeComposer'],
  ['nopost', '4 ContactShadows, no post chain'],
];

/** The first 3D film's fix (2026-10-12): autoClear on before the frame's own passes, off before the composer. */
const ClearBeforeComposer: React.FC = () => {
  useFrame(({gl}) => {
    gl.autoClear = true;
  }, -1);
  useFrame(({gl}) => {
    gl.autoClear = false;
  }, 0.5);
  return null;
};

const Bench: React.FC<{mode: Mode}> = ({mode}) => {
  const frame = useCurrentFrame();
  const x = -1.4 + (2.8 * Math.min(frame, 330)) / 330;
  return (
    <>
      <Cam pos={[0, 2.2, 3.4]} target={[0, 0, 0]} focal={35} />
      <mesh position={[x, 0.2, 0]} castShadow>
        <boxGeometry args={[0.4, 0.4, 0.4]} />
        <meshStandardMaterial color="#8a8d90" roughness={0.6} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, FLOOR_Y, 0]}>
        <planeGeometry args={[12, 12]} />
        <meshStandardMaterial color="#d9d9d6" roughness={0.9} />
      </mesh>
      {mode === 'ground' ? (
        <GroundShadow size={6} far={1} blur={0.08} opacity={0.9} />
      ) : (
        // its camera sits where GroundShadow's does, 1 mm under the contact plane, so both see the same box
        <ContactShadows position={[0, -0.001, 0]} scale={6} far={1} blur={1.5} opacity={0.9} resolution={512} />
      )}
      {mode === 'clear' && <ClearBeforeComposer />}
      <ambientLight intensity={0.5} />
      <AreaLight pos={[0, 3, 1.5]} to={[0, 0, 0]} w={3} h={1} intensity={6} />
    </>
  );
};

export const ShadowAB: React.FC = () => {
  const {W, H} = useLayout();
  const w = W / 2;
  const h = H / 2;
  return (
    <div style={{position: 'absolute', inset: 0, background: '#1c1d1f'}}>
      {PANELS.map(([mode, label], i) => (
        <div key={mode} style={{position: 'absolute', left: (i % 2) * w, top: Math.floor(i / 2) * h, width: w, height: h, overflow: 'hidden'}}>
          <ThreeCanvas width={w} height={h} gl={{antialias: false, preserveDrawingBuffer: true, toneMapping: THREE.AgXToneMapping}} camera={{fov: 30, near: 0.01, far: 100, position: [0, 1, 5]}}>
            <color attach="background" args={['#1c1d1f']} />
            <Bench mode={mode} />
            {mode !== 'nopost' && (
              <>
                {/* Stage's chain without depth of field */}
                <EffectComposer multisampling={0} enableNormalPass={false}>
                  <SMAA />
                  <Bloom intensity={0.35} luminanceThreshold={0.9} luminanceSmoothing={0.2} mipmapBlur />
                  <Vignette eskil={false} offset={0.25} darkness={0.3} />
                </EffectComposer>
                <PostWarmup />
              </>
            )}
          </ThreeCanvas>
          <div style={{position: 'absolute', right: 24, top: 20, fontFamily: MONO, fontSize: 22, color: '#F2EFE8'}}>{label}</div>
        </div>
      ))}
    </div>
  );
};
