import React from 'react';
import {S00Opening} from './S00Opening';
import {S01Explode} from './S01Explode';
import {S02Materials} from './S02Materials';
import {S03PickPlace} from './S03PickPlace';
import {S04Batch} from './S04Batch';
import {S05Outro} from './S05Outro';

// tools/preview.sh reads the `  <id>: <Component>,` lines below and imports ../scenes/<Component>: keep one chapter a
// line and the file named after its component.
export const SCENES: Record<string, React.FC> = {
  opening: S00Opening,
  explode: S01Explode,
  materials: S02Materials,
  pickplace: S03PickPlace,
  batch: S04Batch,
  outro: S05Outro,
};
