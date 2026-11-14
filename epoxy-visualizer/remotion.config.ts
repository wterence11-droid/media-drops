import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
Config.setOverwriteOutput(true);
// H.264 + AAC in the colour space TikTok, Reels and Facebook expect.
Config.setCodec('h264');
Config.setColorSpace('bt709');
// The film grain is expensive to encode. 22 keeps a 20s clip near 40MB with no
// visible loss; lower it for a bigger, cleaner file.
Config.setCrf(22);
// The epoxy is a WebGL shader, so headless Chrome needs a GL backend.
// "angle" uses the GPU. On a machine without one, render with:
//   npm run render -- --gl=swangle
Config.setChromiumOpenGlRenderer('angle');
