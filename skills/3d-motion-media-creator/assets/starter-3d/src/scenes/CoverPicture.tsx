import React from 'react';
import {useVideoConfig} from 'remotion';
import {Stage} from '../three/Stage';
import {orbit, type CamSpec, type V3} from '../three/camera';
import {ExplodeSet} from './S01Explode';
import {explodeAt} from './gearbox/Gearbox';

// The covers' picture, rendered from the film's own set (tools/cover_3d.py): the exploded gearbox of chapter 01, no
// text, no notes. The base Cover.tsx sets title, seal and logo over it, so the subject keeps out of the title area:
// the right 60 % in the landscape covers, the lower 60 % in the 3:4 one. Change the set and cameras for a new film.

const SUBJECT: V3 = [0.02, 0.3, 0];
// camera targets moved off the subject so it lands in its part of the frame (measured on the renders, 2026-10-13)
const CAMS: Record<'16x9' | '4x3' | '3x4', CamSpec> = {
  '16x9': {pos: orbit([-0.19, 0.3, 0.2], 2.0, 0.8, 0.3), target: [-0.19, 0.3, 0.2], focal: 50},
  '4x3': {pos: orbit([-0.14, 0.3, 0.15], 1.5, 0.8, 0.3), target: [-0.14, 0.3, 0.15], focal: 50},
  '3x4': {pos: orbit([SUBJECT[0], 0.42, SUBJECT[2]], 1.35, 0.8, 0.3), target: [SUBJECT[0], 0.42, SUBJECT[2]], focal: 50},
};

export const CoverPicture: React.FC = () => {
  const {width, height} = useVideoConfig();
  const ratio = height > width ? '3x4' : width / height > 1.5 ? '16x9' : '4x3';
  return (
    <Stage envIntensity={0.55} grain={0} post={{vignette: 0.3}}>
      <ExplodeSet cam={CAMS[ratio]} explode={explodeAt(1000, 0)} />
    </Stage>
  );
};
