import {Config} from '@remotion/cli/config';

// WebGL needs a GPU backend. Without an explicit renderer headless Chrome silently falls back to SwiftShader (about
// 5.7 s a frame on the first 3D film's benchmark, 2026-10-12); ANGLE goes through Metal on macOS. This file covers
// `remotion render`, `remotion still` and the Studio. tools/stills.mjs (preview stills, `deliver.sh covers`) calls
// the renderer directly and reads GL from the environment instead: export GL=angle.
Config.setChromiumOpenGlRenderer('angle');
// every render tab shares one GPU process: more than 4 tabs gained nothing; tools/deliver.sh passes its own
// concurrency (default 6), so give it 4 there: tools/deliver.sh 16x9 v0.1 4
Config.setConcurrency(4);
// a tab's first frame compiles shaders and decodes textures, HDRIs and models
Config.setDelayRenderTimeoutInMilliseconds(120000);
