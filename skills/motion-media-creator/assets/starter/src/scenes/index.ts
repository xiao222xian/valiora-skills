import React from 'react';
import {S00Opening} from './S00Opening';
import {S01Neolithic} from './S01Neolithic';
import {S02Shang} from './S02Shang';
import {S03Warring} from './S03Warring';
import {S04Qin} from './S04Qin';
import {S05Han} from './S05Han';
import {S06Split} from './S06Split';
import {S07Tang} from './S07Tang';
import {S08Song} from './S08Song';
import {S09Yuan} from './S09Yuan';
import {S10Ming} from './S10Ming';
import {S11Qing} from './S11Qing';
import {S12Modern} from './S12Modern';
import {S13Today} from './S13Today';
import {S14Outro} from './S14Outro';

export const SCENES: Record<string, React.FC> = {
  opening: S00Opening,
  neolithic: S01Neolithic,
  shang: S02Shang,
  warring: S03Warring,
  qin: S04Qin,
  han: S05Han,
  split: S06Split,
  tang: S07Tang,
  song: S08Song,
  yuan: S09Yuan,
  ming: S10Ming,
  qing: S11Qing,
  modern: S12Modern,
  today: S13Today,
  outro: S14Outro,
};
