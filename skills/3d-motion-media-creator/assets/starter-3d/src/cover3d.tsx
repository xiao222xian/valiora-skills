// Entry for the covers' picture (tools/cover_3d.py): one still per cover ratio, at the sizes the base Cover.tsx uses.
import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {CoverPicture} from './scenes/CoverPicture';

registerRoot(() => (
  <>
    <Composition id="CoverPic-16x9" component={CoverPicture} durationInFrames={1} fps={30} width={1920} height={1080} />
    <Composition id="CoverPic-4x3" component={CoverPicture} durationInFrames={1} fps={30} width={1440} height={1080} />
    <Composition id="CoverPic-3x4" component={CoverPicture} durationInFrames={1} fps={30} width={1080} height={1440} />
  </>
));
