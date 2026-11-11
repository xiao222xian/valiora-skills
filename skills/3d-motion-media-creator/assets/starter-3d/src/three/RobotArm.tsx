import React, {useMemo} from 'react';
import * as THREE from 'three';
import {Bevel, useMat} from './kit';
import type {V3} from './camera';

// A generic six-axis industrial robot, built here (no brand, nothing to credit). Base on the floor at its origin,
// reach about 2.3 m. Joint angles in radians:
//   j1 base yaw (about +Y)       j2 shoulder: upper arm's lean forward from vertical
//   j3 elbow: forearm's drop below the upper arm's normal (0 = forearm at right angles, forward)
//   j4 forearm roll   j5 wrist pitch (0 = tool along the forearm)   j6 flange roll
// ikArm() solves j1..j3 and j5 so the tool points straight down at a target.

export const ARM = {h0: 0.78, a1: 0.2, L2: 1.1, L3: 1.0, flange: 0.16};

export type Joints = {j1: number; j2: number; j3: number; j4?: number; j5?: number; j6?: number};
export type Tool = 'gripper' | 'spotWeld' | 'suction' | 'none';

/** Joint angles that put the tool point at `target` (world), pointing straight down, for an arm standing at `base`.
 * `toolLen` is the distance from the flange to that point: about 0.22 between the gripper's fingers, 0.3 at their
 * tips. For a straight tool path, interpolate the target and solve every frame; lerpJoints between two solutions
 * swings the tool along a curve. */
export const ikArm = (target: V3, base: V3 = [0, 0, 0], toolLen = 0.3): Joints => {
  const dx = target[0] - base[0];
  const dz = target[2] - base[2];
  const j1 = Math.atan2(-dz, dx);
  const r = Math.hypot(dx, dz) - ARM.a1;
  const z = target[1] + toolLen + ARM.flange - base[1] - ARM.h0;
  const {L2, L3} = ARM;
  const d = Math.min(L2 + L3 - 1e-3, Math.hypot(r, z));
  const t1 = Math.atan2(z, r) + Math.acos((L2 * L2 + d * d - L3 * L3) / (2 * L2 * d));
  const inner = Math.acos((L2 * L2 + L3 * L3 - d * d) / (2 * L2 * L3));
  const t2 = t1 - (Math.PI - inner);
  const j2 = Math.PI / 2 - t1;
  const j3 = -t2 - j2;
  const j5 = -Math.PI / 2 + (j2 + j3);
  return {j1, j2, j3, j4: 0, j5, j6: 0};
};

export const lerpJoints = (a: Joints, b: Joints, t: number): Joints => ({
  j1: a.j1 + (b.j1 - a.j1) * t,
  j2: a.j2 + (b.j2 - a.j2) * t,
  j3: a.j3 + (b.j3 - a.j3) * t,
  j4: (a.j4 ?? 0) + ((b.j4 ?? 0) - (a.j4 ?? 0)) * t,
  j5: (a.j5 ?? 0) + ((b.j5 ?? 0) - (a.j5 ?? 0)) * t,
  j6: (a.j6 ?? 0) + ((b.j6 ?? 0) - (a.j6 ?? 0)) * t,
});

/** Gripper finger centre offset from the tool axis for `open` 0..1; the fingers are 0.05 thick, so their inner faces
 * stand gripGap(open) - 0.025 off the axis. */
export const gripGap = (open: number) => 0.05 + open * 0.12;
/** The `toolOpen` that closes the fingers on a part `halfWidth` off the axis (half its width across the fingers). */
export const openFor = (halfWidth: number) => (halfWidth + 0.025 - 0.05) / 0.12;

const ToolHead: React.FC<{tool: Tool; open: number; dark: THREE.Material; steel: THREE.Material; copper: THREE.Material; rubber: THREE.Material}> = ({tool, open, dark, steel, copper, rubber}) => {
  if (tool === 'none') return null;
  if (tool === 'gripper') {
    const gap = gripGap(open);
    return (
      <group>
        <Bevel size={[0.08, 0.2, 0.2]} position={[0.04, 0, 0]} material={dark} />
        {[-1, 1].map((s) => (
          <Bevel key={s} size={[0.22, 0.05, 0.12]} position={[0.18, s * gap, 0]} material={steel} r={0.006} />
        ))}
      </group>
    );
  }
  if (tool === 'suction') {
    return (
      <group>
        <Bevel size={[0.06, 0.5, 0.5]} position={[0.05, 0, 0]} material={dark} r={0.008} />
        {[-1, 1].flatMap((a) =>
          [-1, 1].map((b) => (
            <group key={`${a}${b}`} position={[0.13, a * 0.18, b * 0.18]}>
              <mesh rotation={[0, 0, Math.PI / 2]} material={steel} castShadow>
                <cylinderGeometry args={[0.012, 0.012, 0.1, 16]} />
              </mesh>
              <mesh position={[0.06, 0, 0]} rotation={[0, 0, Math.PI / 2]} material={rubber} castShadow>
                <cylinderGeometry args={[0.035, 0.022, 0.03, 24]} />
              </mesh>
            </group>
          )),
        )}
      </group>
    );
  }
  // spot-weld gun: a C-shaped yoke with two copper electrode caps; `open` separates the caps
  const g = 0.02 + open * 0.08;
  return (
    <group>
      <Bevel size={[0.16, 0.18, 0.16]} position={[0.08, 0, 0]} material={dark} r={0.01} />
      <Bevel size={[0.42, 0.06, 0.07]} position={[0.32, 0.17, 0]} material={steel} r={0.008} />
      <Bevel size={[0.06, 0.4, 0.07]} position={[0.5, 0, 0]} material={steel} r={0.008} />
      <Bevel size={[0.3, 0.06, 0.07]} position={[0.38, -0.17, 0]} material={steel} r={0.008} />
      <mesh position={[0.5 - 0.04, 0.14 - g, 0]} material={copper} castShadow>
        <cylinderGeometry args={[0.012, 0.016, 0.06, 20]} />
      </mesh>
      <mesh position={[0.5 - 0.04, -0.14 + g, 0]} material={copper} castShadow>
        <cylinderGeometry args={[0.016, 0.012, 0.06, 20]} />
      </mesh>
    </group>
  );
};

/** The robot. `paint` is the body colour (machine enamel); joints and base are graphite. */
export const RobotArm: React.FC<{joints: Joints; position?: V3; rotationY?: number; tool?: Tool; toolOpen?: number; paint?: string; scale?: number}> = ({
  joints,
  position = [0, 0, 0],
  rotationY = 0,
  tool = 'gripper',
  toolOpen = 0,
  paint = '#d6d2c9',
  scale = 1,
}) => {
  const body = useMat('machinePaint', {color: paint});
  const dark = useMat('graphitePaint');
  const steel = useMat('steel', {repeat: 0.5});
  const chrome = useMat('chrome');
  const copper = useMat('copper', {repeat: 0.3});
  const rubber = useMat('rubber', {repeat: 0.5});
  const {j1, j2, j3, j4 = 0, j5 = 0, j6 = 0} = joints;
  const {h0, a1, L2, L3, flange} = ARM;
  const cable = useMemo(() => {
    const c = new THREE.CatmullRomCurve3([new THREE.Vector3(-0.12, 0.25, 0.17), new THREE.Vector3(-0.2, 0.6, 0.2), new THREE.Vector3(-0.12, 0.95, 0.19)]);
    return new THREE.TubeGeometry(c, 24, 0.025, 12, false);
  }, []);
  return (
    <group position={position} rotation={[0, rotationY, 0]} scale={scale}>
      {/* fixed base */}
      <mesh position={[0, 0.06, 0]} material={dark} castShadow receiveShadow>
        <cylinderGeometry args={[0.36, 0.4, 0.12, 48]} />
      </mesh>
      <group rotation={[0, j1, 0]}>
        <mesh position={[0, 0.26, 0]} material={dark} castShadow>
          <cylinderGeometry args={[0.3, 0.33, 0.28, 48]} />
        </mesh>
        <Bevel size={[0.62, 0.42, 0.5]} position={[0.06, 0.58, 0]} material={body} r={0.05} />
        {/* shoulder; the drum runs 1 cm past the housing (0.52 vs 0.5): equal lengths put both end faces on z = ±0.25
            and they z-fought (2026-10-12) */}
        <group position={[a1, h0, 0]} rotation={[0, 0, -j2]}>
          <mesh rotation={[Math.PI / 2, 0, 0]} material={dark} castShadow>
            <cylinderGeometry args={[0.2, 0.2, 0.52, 40]} />
          </mesh>
          <Bevel size={[0.3, L2, 0.32]} position={[0, L2 / 2, 0.02]} material={body} r={0.06} />
          <mesh geometry={cable} material={rubber} castShadow />
          {/* elbow */}
          <group position={[0, L2, 0]} rotation={[0, 0, -j3]}>
            <mesh rotation={[Math.PI / 2, 0, 0]} material={dark} castShadow>
              <cylinderGeometry args={[0.16, 0.16, 0.42, 40]} />
            </mesh>
            <Bevel size={[0.42, 0.3, 0.3]} position={[-0.08, 0.02, 0]} material={body} r={0.05} />
            <group rotation={[j4, 0, 0]}>
              <Bevel size={[L3 - 0.12, 0.2, 0.22]} position={[(L3 - 0.12) / 2 + 0.06, 0, 0]} material={body} r={0.05} />
              {/* wrist */}
              <group position={[L3, 0, 0]} rotation={[0, 0, j5]}>
                <mesh rotation={[Math.PI / 2, 0, 0]} material={dark} castShadow>
                  <cylinderGeometry args={[0.1, 0.1, 0.24, 32]} />
                </mesh>
                <group rotation={[j6, 0, 0]}>
                  <mesh position={[flange / 2, 0, 0]} rotation={[0, 0, Math.PI / 2]} material={chrome} castShadow>
                    <cylinderGeometry args={[0.07, 0.08, flange, 32]} />
                  </mesh>
                  <group position={[flange, 0, 0]}>
                    <ToolHead tool={tool} open={toolOpen} dark={dark} steel={steel} copper={copper} rubber={rubber} />
                  </group>
                </group>
              </group>
            </group>
          </group>
        </group>
      </group>
    </group>
  );
};
