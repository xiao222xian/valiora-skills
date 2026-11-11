import React from 'react';
import {Composition, Folder} from 'remotion';
import {Film} from './Main';
import {CHAPTERS, FPS, TOTAL_FRAMES, chapterDur} from './timeline';
import {SCENES} from './scenes';
import {Cover} from './Cover';
import {ensureFonts, ensureTextures} from './lib/fonts';

ensureFonts();
ensureTextures();

const Main: React.FC<{withAudio?: boolean}> = ({withAudio = true}) => <Film scenes={SCENES} withAudio={withAudio} />;

const SceneOnly: React.FC<{id: string}> = ({id}) => {
  const S = SCENES[id];
  return <S />;
};

export const Root: React.FC = () => (
  <>
    <Composition id="Main-16x9" component={Main} durationInFrames={TOTAL_FRAMES} fps={FPS} width={1920} height={1080} defaultProps={{withAudio: true}} />
    <Composition id="Main-9x16" component={Main} durationInFrames={TOTAL_FRAMES} fps={FPS} width={1080} height={1920} defaultProps={{withAudio: true}} />
    <Folder name="Chapters-16x9">
      {CHAPTERS.map((c, i) => (
        <Composition
          key={c.id}
          id={`ch${String(c.no).padStart(2, '0')}-${c.id}`}
          component={SceneOnly}
          durationInFrames={chapterDur(i) + (CHAPTERS[i + 1]?.transitionFrames ?? 0)}
          fps={FPS}
          width={1920}
          height={1080}
          defaultProps={{id: c.id}}
        />
      ))}
    </Folder>
    <Folder name="Chapters-9x16">
      {CHAPTERS.map((c, i) => (
        <Composition
          key={c.id}
          id={`v${String(c.no).padStart(2, '0')}-${c.id}`}
          component={SceneOnly}
          durationInFrames={chapterDur(i) + (CHAPTERS[i + 1]?.transitionFrames ?? 0)}
          fps={FPS}
          width={1080}
          height={1920}
          defaultProps={{id: c.id}}
        />
      ))}
    </Folder>
    {/* every film delivers all three, named by ratio: tools/stills.sh covers (look), tools/deliver.sh covers <version> */}
    <Folder name="Covers">
      <Composition id="Cover-16x9" component={Cover} durationInFrames={1} fps={FPS} width={1920} height={1080} />
      <Composition id="Cover-4x3" component={Cover} durationInFrames={1} fps={FPS} width={1440} height={1080} />
      <Composition id="Cover-3x4" component={Cover} durationInFrames={1} fps={FPS} width={1080} height={1440} />
    </Folder>
  </>
);
