import React from 'react';
import {AbsoluteFill, Sequence, staticFile} from 'remotion';
import {Audio} from '@remotion/media';
import {CHAPTERS, chapterDur} from './timeline';
import {ChapterCard} from './components/ChapterCard';
import {HUD} from './components/HUD';
import {Reveal} from './components/Reveal';
import {Subtitles} from './components/Subtitles';
import {ensureFonts, ensureTextures} from './lib/fonts';

ensureFonts();
ensureTextures();

/** The film. Each chapter's Sequence is extended by the next chapter's transition length so the
 * outgoing picture keeps playing underneath the incoming mask. Layers, bottom to top: chapters,
 * chapter cards, subtitles, HUD. `scenes` is the chapter registry: Root passes every chapter, a single-chapter
 * preview (src/dev/harness.tsx) only its own, so this file must not import src/scenes. */
export const Film: React.FC<{scenes: Record<string, React.FC>; withAudio?: boolean}> = ({scenes, withAudio = true}) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {CHAPTERS.map((c, i) => {
        const Scene = scenes[c.id];
        if (!Scene) return null;
        const next = CHAPTERS[i + 1];
        const extend = next ? next.transitionFrames : 0;
        return (
          <Sequence key={c.id} from={c.start} durationInFrames={chapterDur(i) + extend} name={`${String(c.no).padStart(2, '0')} ${c.era}`}>
            <Reveal kind={c.transition} frames={c.transitionFrames} seed={c.no} edge={c.transition === 'bloom' ? c.palette.accent : c.transition === 'wipeRight' ? c.palette.ruler : '#141210'}>
              <Scene />
            </Reveal>
          </Sequence>
        );
      })}
      <ChapterCard />
      <Subtitles />
      <HUD />
      {/* one lossless master (music + voice-over, premixed by tools/voice_mix.py), mounted once;
          the encoder makes the only lossy pass */}
      {withAudio && <Audio src={staticFile('audio/bgm-master.wav')} />}
    </AbsoluteFill>
  );
};
