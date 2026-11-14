import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
Config.setOverwriteOutput(true);
// The epoxy is a WebGL shader, so headless Chrome needs a GL backend.
// "angle" uses the GPU. On a machine without one, render with:
//   npm run render -- --gl=swangle
Config.setChromiumOpenGlRenderer('angle');
