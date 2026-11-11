import React from 'react';
import {AbsoluteFill, staticFile} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {Environment} from '@react-three/drei';
import {useThree} from '@react-three/fiber';
import {Bloom, DepthOfField, EffectComposer, SMAA, Vignette} from '@react-three/postprocessing';
import * as THREE from 'three';
import {Paper} from '../components/Paper';
import {useLayout} from '../lib/layout';
import {vfovOf, type V3} from './camera';
import {StudioEnv} from './lights';
import {PostWarmup} from './PostWarmup';

export type {V3} from './camera';

/** Default fog, near and far in metres from the camera: product-scale sets (everything within ~5 m) are untouched,
 * and the floor fades into `bg` long before its far edge or the horizon: a floor that ends, or meets a near-black
 * background in a straight line, read as a hard horizon in the starter's 9:16 shots and 3:4 cover (2026-10-13). */
export const FOG: [number, number] = [6, 40];

export type PostSpec = {
  bloom?: number; // intensity; the threshold stays high so only highlights and emissive parts glow
  bloomThreshold?: number;
  /** Depth of field focused on a world point. Animate `target` and `bokehScale` (live); `focalLength` is a
   * construction parameter of the effect, so changing it rebuilds the pass every frame. */
  dof?: {target: V3; focalLength?: number; bokehScale?: number} | null;
  vignette?: number;
};

/** Physical camera: focal length in mm on a 36 mm long side (camera.ts vfovOf). Set from the scene's frame-derived
 * CamSpec on every render; nothing animates it from inside the canvas. */
export const Cam: React.FC<{pos: V3; target: V3; focal: number; roll?: number}> = ({pos, target, focal, roll = 0}) => {
  const {camera, size} = useThree();
  const cam = camera as THREE.PerspectiveCamera;
  cam.fov = THREE.MathUtils.radToDeg(vfovOf(focal, size.width, size.height));
  cam.near = 0.01;
  cam.far = 400;
  cam.position.set(...pos);
  cam.up.set(Math.sin(roll), Math.cos(roll), 0);
  cam.lookAt(...target);
  cam.updateProjectionMatrix();
  return null;
};

/** One 3D shot: canvas, AgX tone mapping, image-based reflections (an HDRI from public/assets/hdri, or the built-in
 * studio of light panels), the post chain, and the film grain on top in the DOM. Every motion inside must come from
 * useCurrentFrame(); nothing here reads real time. Mount at most one Stage per chapter at a time: a chapter transition
 * already overlaps two, and each canvas is a WebGL context. The post chain keeps the renderer's autoClear off: anything
 * that renders into its own target must clear it itself (GroundShadow and MeshReflectorMaterial do; drei
 * <ContactShadows> does not, see GroundShadow.tsx). */
export const Stage: React.FC<{
  children: React.ReactNode;
  bg?: string;
  exposure?: number;
  hdri?: string; // file under public/assets/hdri (textures.ts HDRIS, fetched by tools/fetch_textures.py)
  envIntensity?: number;
  envRotation?: number; // radians around Y
  envBackground?: boolean;
  post?: PostSpec;
  shadows?: boolean;
  grain?: number; // DOM grain over the picture (public/tex/grain*.png), shared with the 2D chapters
  /** Fog in `bg`, [near, far] metres from the camera (default FOG; none when the HDRI is the background). Start it
   * behind the farthest subject of the shot; keep floors well past `far` (the kit's are 400 m). */
  fog?: [number, number] | null;
}> = ({children, bg = '#0a0b0d', exposure = 1, hdri, envIntensity = 0.5, envRotation = 0, envBackground = false, post = {}, shadows = true, grain = 0.05, fog}) => {
  const {W, H} = useLayout();
  const {bloom = 0.35, bloomThreshold = 0.9, dof = null, vignette = 0.3} = post;
  const fogRange = fog === undefined ? (envBackground ? null : FOG) : fog;
  return (
    <Paper bg={bg} dark fibre={0} grain={grain} vignette={0}>
      <AbsoluteFill>
        <ThreeCanvas
          width={W}
          height={H}
          // three r186 dropped PCFSoftShadowMap; variance maps give the soft edge (see ShadowSpot for the floor caveat)
          shadows={shadows ? 'variance' : false}
          // the composer antialiases (SMAA); a multisampled canvas under the composer breaks its output
          gl={{antialias: false, preserveDrawingBuffer: true, toneMapping: THREE.AgXToneMapping, toneMappingExposure: exposure}}
          camera={{fov: 30, near: 0.01, far: 400, position: [0, 1, 5]}}
        >
          <color attach="background" args={[bg]} />
          {fogRange && <fog attach="fog" args={[bg, fogRange[0], fogRange[1]]} />}
          {hdri ? (
            <Environment
              files={staticFile(`assets/hdri/${hdri}`)}
              environmentIntensity={envIntensity}
              environmentRotation={[0, envRotation, 0]}
              background={envBackground}
              backgroundIntensity={envIntensity}
              backgroundRotation={[0, envRotation, 0]}
            />
          ) : (
            <StudioEnv intensity={envIntensity} rotation={envRotation} />
          )}
          {children}
          <EffectComposer multisampling={0} enableNormalPass={false}>
            <SMAA />
            {dof ? <DepthOfField target={new THREE.Vector3(...dof.target)} focalLength={dof.focalLength ?? 0.02} bokehScale={dof.bokehScale ?? 2.5} /> : <></>}
            <Bloom intensity={bloom} luminanceThreshold={bloomThreshold} luminanceSmoothing={0.2} mipmapBlur />
            <Vignette eskil={false} offset={0.25} darkness={vignette} />
          </EffectComposer>
          <PostWarmup />
        </ThreeCanvas>
      </AbsoluteFill>
    </Paper>
  );
};
