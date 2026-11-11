import {useEffect, useRef} from 'react';
import {continueRender, delayRender, useCurrentFrame} from 'remotion';
import {useThree} from '@react-three/fiber';

/** Place after <EffectComposer>. In a fresh render tab the composer builds its passes after Remotion's single
 * per-frame advance, so the tab's first frame or two come out black (every chunk of a chunked render, every
 * `remotion still`). This holds the tab's first screenshot for two animation frames and renders again, and renders
 * every later frame once more after this frame's effect passes are mounted. The hold is taken in an effect, not
 * during render, because a suspending sibling (textures, models, HDRIs) discards renders that never commit. */
export const PostWarmup: React.FC = () => {
  const {advance} = useThree();
  const frame = useCurrentFrame();
  const warmed = useRef(false);
  useEffect(() => {
    if (warmed.current) return;
    warmed.current = true;
    const handle = delayRender('Warming up the post-processing passes');
    let b = 0;
    const a = requestAnimationFrame(() => {
      advance(performance.now());
      b = requestAnimationFrame(() => {
        advance(performance.now());
        continueRender(handle);
      });
    });
    return () => {
      cancelAnimationFrame(a);
      cancelAnimationFrame(b);
      continueRender(handle);
    };
  }, [advance]);
  useEffect(() => {
    advance(performance.now());
  }, [frame, advance]);
  return null;
};
