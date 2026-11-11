import React from 'react';
import {Composition} from 'remotion';
import {Film} from '../Main';
import {FPS, TOTAL_FRAMES} from '../timeline';

/** Single-chapter preview root for tools/preview.sh: the full film timeline (absolute frames) with
 * only this chapter mounted, plus subtitles and HUD, in both aspects. No sound. The generated entry
 * (src/dev/entry-<id>.tsx) imports this file and one scene module, never src/scenes/index.ts, so a
 * broken chapter elsewhere cannot break this bundle. */
export const harnessRoot = (id: string, Scene: React.FC): React.FC => {
  const scenes = {[id]: Scene};
  const One: React.FC = () => <Film scenes={scenes} withAudio={false} />;
  return () => (
    <>
      <Composition id="H-16x9" component={One} durationInFrames={TOTAL_FRAMES} fps={FPS} width={1920} height={1080} />
      <Composition id="H-9x16" component={One} durationInFrames={TOTAL_FRAMES} fps={FPS} width={1080} height={1920} />
    </>
  );
};
