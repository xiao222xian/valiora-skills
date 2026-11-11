import React, {useMemo} from 'react';
import {useFrame, useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {HorizontalBlurShader} from 'three/examples/jsm/shaders/HorizontalBlurShader.js';
import {VerticalBlurShader} from 'three/examples/jsm/shaders/VerticalBlurShader.js';

// A soft contact shadow on the ground, in place of drei <ContactShadows>: the composer keeps the renderer's autoClear
// off, so ContactShadows' uncleared targets pile every frame's shadow into a trail across a sequential render. The
// first 3D film turned autoClear on around it each frame (ClearBeforeComposer, 2026-10-12), which works (src/dev/
// ShadowAB.tsx, 2026-10-13) but flips renderer state for everything else in the frame; this one clears each of its
// own targets itself, leaves autoClear alone, and takes its blur in metres.
//
// It renders the scene from just below `y`, looking up, into a depth map: so the undersides of the objects must be
// above that camera. Objects stand on y = 0 (their contact plane); the receiving surface lies 3 mm lower (the kit's
// floors default to FLOOR_Y); a part whose underside sat level with the camera would be culled and cast nothing.

/** Floors sit this far under the contact plane y = 0: room for the shadow camera and its plane between them. */
export const FLOOR_Y = -0.003;
const CAM_BELOW = 0.001;

export type GroundShadowProps = {
  /** Contact plane: where the objects' undersides rest (default 0). */
  y?: number;
  /** Centre of the shadowed area in x and z. */
  center?: [number, number];
  /** Width (x) and depth (z) of the shadowed area in metres. */
  size: number | [number, number];
  /** Height above the contact plane that still casts shadow; darker the closer an object is. */
  far?: number;
  /** Softness: how far the shadow spreads past an object's footprint, in metres. A resting object's shadow is only
   * this halo (its footprint is under it), so it is what grounds it. */
  blur?: number;
  opacity?: number;
  resolution?: number;
  color?: string;
};

const quad = (material: THREE.ShaderMaterial) => {
  const s = new THREE.Scene();
  s.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material));
  return s;
};

export const GroundShadow: React.FC<GroundShadowProps> = ({y = 0, center = [0, 0], size, far = 1, blur = 0.03, opacity = 0.8, resolution = 1024, color = '#000000'}) => {
  const {gl, scene} = useThree();
  const [w, d] = Array.isArray(size) ? size : [size, size];
  const g = useMemo(() => {
    const target = new THREE.WebGLRenderTarget(resolution, resolution);
    const temp = new THREE.WebGLRenderTarget(resolution, resolution);
    target.texture.generateMipmaps = temp.texture.generateMipmaps = false;
    // looking straight up from just under the contact plane: image right is world +X, image up world +Z (the plane
    // that shows it is flipped in y to lie the same way)
    const camera = new THREE.OrthographicCamera(-w / 2, w / 2, d / 2, -d / 2, 0, far + CAM_BELOW);
    camera.rotation.set(Math.PI / 2, 0, 0);
    const depth = new THREE.MeshDepthMaterial();
    depth.side = THREE.DoubleSide;
    const tint = new THREE.Color(color);
    let patched = false;
    depth.onBeforeCompile = (shader) => {
      shader.uniforms.ucolor = {value: tint};
      const out = 'vec4( vec3( 1.0 - fragCoordZ ), opacity );';
      patched = shader.fragmentShader.includes(out);
      shader.fragmentShader = shader.fragmentShader
        .replace('void main() {', 'uniform vec3 ucolor;\nvoid main() {')
        // alpha falls off with height above the ground; the colour is the shadow tint
        .replace(out, 'vec4( ucolor, 1.0 - fragCoordZ );');
      if (!patched) console.warn('GroundShadow: three changed the depth shader; the shadow will be a flat silhouette');
    };
    const hBlur = new THREE.ShaderMaterial({...HorizontalBlurShader, uniforms: THREE.UniformsUtils.clone(HorizontalBlurShader.uniforms), depthTest: false, depthWrite: false});
    const vBlur = new THREE.ShaderMaterial({...VerticalBlurShader, uniforms: THREE.UniformsUtils.clone(VerticalBlurShader.uniforms), depthTest: false, depthWrite: false});
    const quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    quadCam.position.z = 0.5;
    quadCam.updateMatrixWorld();
    // pulled towards the camera in depth: 2 mm above a floor is below depth precision at 15 m
    const plane = new THREE.MeshBasicMaterial({map: target.texture, transparent: true, opacity, depthWrite: false, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2});
    return {target, temp, camera, depth, hScene: quad(hBlur), vScene: quad(vBlur), hBlur, vBlur, quadCam, plane};
  }, [resolution, w, d, far, color, opacity]);
  const mesh = React.useRef<THREE.Mesh>(null);

  useFrame(() => {
    const {target, temp, camera, depth, hScene, vScene, hBlur, vBlur, quadCam} = g;
    camera.position.set(center[0], y - CAM_BELOW, center[1]);
    camera.updateMatrixWorld();
    const clearColor = gl.getClearColor(new THREE.Color());
    const clearAlpha = gl.getClearAlpha();
    const autoClear = gl.autoClear;
    const bg = scene.background;
    const override = scene.overrideMaterial;
    gl.autoClear = false;
    gl.setClearColor(0x000000, 0);
    if (mesh.current) mesh.current.visible = false;
    scene.background = null;
    scene.overrideMaterial = depth;
    gl.setRenderTarget(target);
    gl.clear(true, true, false);
    gl.render(scene, camera);
    scene.overrideMaterial = override;
    scene.background = bg;
    if (mesh.current) mesh.current.visible = true;
    for (const k of [1, 0.4]) {
      hBlur.uniforms.tDiffuse.value = target.texture;
      // the 9-tap kernel spans 8 steps; a step in target UV units
      hBlur.uniforms.h.value = (blur * k) / w / 4;
      gl.setRenderTarget(temp);
      gl.clear(true, true, false);
      gl.render(hScene, quadCam);
      vBlur.uniforms.tDiffuse.value = temp.texture;
      vBlur.uniforms.v.value = (blur * k) / d / 4;
      gl.setRenderTarget(target);
      gl.clear(true, true, false);
      gl.render(vScene, quadCam);
    }
    gl.setRenderTarget(null);
    gl.setClearColor(clearColor, clearAlpha);
    gl.autoClear = autoClear;
  });

  return (
    <mesh ref={mesh} position={[center[0], y - CAM_BELOW, center[1]]} rotation={[-Math.PI / 2, 0, 0]} scale={[1, -1, 1]} material={g.plane} renderOrder={1}>
      <planeGeometry args={[w, d]} />
    </mesh>
  );
};
