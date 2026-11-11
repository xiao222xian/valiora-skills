import React, {useMemo} from 'react';
import {staticFile} from 'remotion';
import {useGLTF} from '@react-three/drei';
import * as THREE from 'three';
import {clone as cloneDeep} from 'three/examples/jsm/utils/SkeletonUtils.js';
import type {V3} from './camera';

// Any glTF / GLB under public/, cleaned for the film: brand marks removed, materials swapped, centred on the origin
// and standing on y = 0. List a model's node, mesh, material and image names with tools/gltf_nodes.py before choosing
// what to remove, and add the model to src/credits.ts when you take it (a CC BY model also gets `changed`, e.g.
// '移除标志', when this file removes or replaces anything).

/** A node or material name, a pattern, or a test on the object itself. */
export type Match = string | RegExp | ((o: THREE.Object3D) => boolean);

const hit = (o: THREE.Object3D, m: Match) => {
  if (typeof m === 'function') return m(o);
  const mats = (o as THREE.Mesh).isMesh ? ([] as THREE.Material[]).concat((o as THREE.Mesh).material) : [];
  const names = [o.name, ...mats.map((x) => x?.name ?? '')];
  return names.some((n) => (typeof m === 'string' ? n === m : m.test(n)));
};

export type ModelProps = {
  /** File under public/, e.g. 'assets/models/press.glb'. */
  src: string;
  /** Removed from the scene (not just hidden, so they cast no shadow and do not count towards fit and ground): brand
   * marks, licence plates, sample-asset logos. Matched against node names and material names. */
  remove?: Match[];
  /** Material name -> replacement, e.g. a tyre sidewall whose texture carries a logo -> plain rubber. */
  replace?: Record<string, THREE.Material>;
  /** Keep only the scene's top-level nodes whose names pass (one part out of an assembly). */
  only?: (name: string) => boolean;
  /** Draco-compressed geometry: decoders come from public/draco/ (copy them from
   * node_modules/three/examples/jsm/libs/draco/gltf/). A render cannot reach drei's default CDN; without this a
   * compressed model stops with "No DRACOLoader instance provided" instead of hanging. */
  draco?: boolean;
  /** Scale the cleaned model so its bounding box measures `size` metres along `axis` ('max' = longest side). Leave it
   * out when the file is already in metres. */
  fit?: {size: number; axis?: 'x' | 'y' | 'z' | 'max'};
  /** Centre on the origin and stand on y = 0 (default true). */
  ground?: boolean;
  /** Pose of an animated model: the clip (by name, default the first) at `t` seconds. Pass frame / fps; mixer.update()
   * with a clock delta would differ from tab to tab. */
  clip?: {name?: string; t: number};
  position?: V3;
  rotationY?: number;
  scale?: number;
  castShadow?: boolean;
  receiveShadow?: boolean;
};

const useClean = ({src, remove, replace, only, draco, fit, ground = true, castShadow = true, receiveShadow = true}: ModelProps) => {
  const gltf = useGLTF(staticFile(src), draco ? staticFile('draco/') : false);
  return useMemo(() => {
    // SkeletonUtils.clone keeps skinned meshes bound to their own bones; Object3D.clone() does not
    const s = cloneDeep(gltf.scene);
    const drop: THREE.Object3D[] = [];
    s.traverse((o) => {
      if (remove?.some((m) => hit(o, m))) drop.push(o);
      if (only && o.parent === s && !only(o.name)) drop.push(o);
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = castShadow;
      mesh.receiveShadow = receiveShadow;
      if (replace) {
        const swap = (x: THREE.Material) => replace[x?.name ?? ''] ?? x;
        mesh.material = Array.isArray(mesh.material) ? mesh.material.map(swap) : swap(mesh.material);
      }
    });
    for (const o of drop) o.removeFromParent();
    s.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(s);
    const size = box.getSize(new THREE.Vector3());
    const k = fit ? fit.size / (fit.axis && fit.axis !== 'max' ? size[fit.axis] : Math.max(size.x, size.y, size.z)) : 1;
    const c = box.getCenter(new THREE.Vector3());
    const offset: V3 = ground ? [-c.x * k, -box.min.y * k, -c.z * k] : [0, 0, 0];
    return {scene: s, k, offset, size: size.multiplyScalar(k), animations: gltf.animations};
    // the options are compared by identity: keep `remove`, `replace` and `only` outside the component or memoised
  }, [gltf, remove, replace, only, fit?.size, fit?.axis, ground, castShadow, receiveShadow]);
};

/** A cleaned glTF. Every instance is its own clone, so two <Model>s of one file can differ. */
export const Model: React.FC<ModelProps> = (props) => {
  const {scene, k, offset, animations} = useClean(props);
  const {clip, position = [0, 0, 0], rotationY = 0, scale = 1} = props;
  const mixer = useMemo(() => {
    if (!animations.length) return null;
    const m = new THREE.AnimationMixer(scene);
    const c = (clip?.name && THREE.AnimationClip.findByName(animations, clip.name)) || animations[0];
    m.clipAction(c).play();
    return m;
  }, [scene, animations, clip?.name]);
  if (mixer && clip) mixer.setTime(clip.t);
  return (
    <group position={position} rotation={[0, rotationY, 0]} scale={scale}>
      <group position={offset} scale={k}>
        <primitive object={scene} />
      </group>
    </group>
  );
};

/** Size in metres (x, y, z) of the cleaned and fitted model, e.g. to place parts around it. */
export const useModelSize = (props: ModelProps): THREE.Vector3 => useClean(props).size;
