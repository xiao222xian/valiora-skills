import React from 'react';
import { Composition } from 'remotion';
import timeline from '../public/data/timeline.json';
import subs from '../public/data/subs.json';
import cover from '../public/data/cover.json';
import { Film } from './Film';
import { Cover } from './Cover';
import { CoverWide } from './CoverWide';
import type { CoverSpec, Sub, Timeline } from './types';

const tl = timeline as unknown as Timeline;
const ss = subs as unknown as Sub[];
const cs = cover as unknown as CoverSpec;

// Vertical film only. A 16:9 cut is derived per lov-media-creator platform-variants, not from this composition.
// Covers: every cover.json variant gets the 3:4 Channels card plus 4:3 and 16:9 cards from the same spec.
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="InterviewVertical" component={Film} durationInFrames={tl.frames} fps={tl.fps} width={1080} height={1920}
      defaultProps={{ tl, subs: ss }} />
    {Object.keys(cs.variants).map((v) => (
      <React.Fragment key={v}>
        <Composition id={`InterviewCover34-${v}`} component={Cover} durationInFrames={1} fps={30} width={1080} height={1440}
          defaultProps={{ spec: cs, variant: v }} />
        <Composition id={`InterviewCover43-${v}`} component={CoverWide} durationInFrames={1} fps={30} width={1440} height={1080}
          defaultProps={{ spec: cs, variant: v, ratio: '43' as const }} />
        <Composition id={`InterviewCover169-${v}`} component={CoverWide} durationInFrames={1} fps={30} width={1920} height={1080}
          defaultProps={{ spec: cs, variant: v, ratio: '169' as const }} />
      </React.Fragment>
    ))}
  </>
);
