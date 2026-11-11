import * as THREE from 'three';
import {rng} from '../lib/anim';

// Camera maths shared by <Cam> (Stage.tsx) and the DOM layer: a 2D callout pinned to a 3D point has to use exactly
// the projection the canvas uses, or the leader drifts off the part as the camera moves.

export type V3 = [number, number, number];

/** A physical camera: position, look-at point, focal length in mm on a 36 mm long side, roll in radians. */
export type CamSpec = {pos: V3; target: V3; focal: number; roll?: number};

/** Vertical field of view (radians) of a `focal` mm lens on a 36 mm long side. The long side is the width in 16:9 and
 * the height in 9:16, so a 50 mm shot frames the subject the same way along the long axis of both films. */
export const vfovOf = (focal: number, W: number, H: number) => {
  const aspect = W / H;
  const longHalf = Math.atan(18 / focal);
  return aspect >= 1 ? 2 * Math.atan(Math.tan(longHalf) / aspect) : 2 * longHalf;
};

/** Screen position (px) of world point p seen through cam on a W x H frame. Same basis as three's lookAt, including
 * its nudge when the view is parallel to `up` (a straight top-down shot). */
export const project = (cam: CamSpec, W: number, H: number, p: V3): [number, number] => {
  const pos = new THREE.Vector3(...cam.pos);
  const back = pos.clone().sub(new THREE.Vector3(...cam.target)).normalize();
  const roll = cam.roll ?? 0;
  const up = new THREE.Vector3(Math.sin(roll), Math.cos(roll), 0);
  const r = new THREE.Vector3().crossVectors(up, back);
  if (r.lengthSq() === 0) {
    if (Math.abs(up.z) === 1) back.x += 0.0001;
    else back.z += 0.0001;
    back.normalize();
    r.crossVectors(up, back);
  }
  r.normalize();
  const u = new THREE.Vector3().crossVectors(back, r);
  const d = new THREE.Vector3(...p).sub(pos);
  const z = -d.dot(back);
  const tv = Math.tan(vfovOf(cam.focal, W, H) / 2);
  const th = tv * (W / H);
  const nx = d.dot(r) / (z * th);
  const ny = d.dot(u) / (z * tv);
  return [((nx + 1) / 2) * W, ((1 - ny) / 2) * H];
};

/** Interpolate two camera specs; the eased t is up to the caller. */
export const lerpCam = (a: CamSpec, b: CamSpec, t: number): CamSpec => ({
  pos: lerpV(a.pos, b.pos, t),
  target: lerpV(a.target, b.target, t),
  focal: a.focal + (b.focal - a.focal) * t,
  roll: (a.roll ?? 0) + ((b.roll ?? 0) - (a.roll ?? 0)) * t,
});

/** A point on a circle around `target`: azimuth from +X towards +Z, elevation above the horizon, both in radians.
 * Keep an orbit at or under 10 degrees a second (0.0058 rad a frame at 30 fps). */
export const orbit = (target: V3, radius: number, azimuth: number, elevation: number): V3 => [
  target[0] + radius * Math.cos(elevation) * Math.cos(azimuth),
  target[1] + radius * Math.sin(elevation),
  target[2] + radius * Math.cos(elevation) * Math.sin(azimuth),
];

/** Deterministic camera shake after impacts: a decaying jolt of `decay` frames per hit (absolute or local frames,
 * whichever `frame` is). Returns an offset in metres to add to both cam.pos and cam.target. Seeded per hit and frame,
 * so every render tab and every re-render shakes the same way (drei CameraShake reads the clock). */
export const shake = (frame: number, hits: number[], amp = 0.012, decay = 6): V3 => {
  let x = 0;
  let y = 0;
  let z = 0;
  for (const h of hits) {
    const t = frame - h;
    if (t < 0 || t > decay) continue;
    const r = rng(Math.round(h) * 31 + Math.round(t) * 7 + 1);
    const k = amp * Math.pow(1 - t / decay, 2);
    x += (r() * 2 - 1) * k;
    y += (r() * 2 - 1) * k * 1.4;
    z += (r() * 2 - 1) * k * 0.5;
  }
  return [x, y, z];
};

export const addV = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const lerpV = (a: V3, b: V3, t: number): V3 => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
