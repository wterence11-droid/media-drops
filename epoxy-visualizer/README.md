# Epoxy visualizer

A 9:16 caption visualizer for a voiceover: white metallic epoxy is squeegeed
across a black screen, driven by how loud the voice is, with word-by-word
captions on top. Built with [Remotion](https://www.remotion.dev) (React), a
WebGL canvas for the liquid, and the Web Audio API for the loudness analysis.

## Run it

```bash
npm install
npm run dev      # opens Remotion Studio: live preview with a scrubbable timeline
npm run render   # writes out/visualizer.mp4 with the audio included
```

Needs Node 18 or newer. The first render downloads a headless Chrome.

## Add your audio

Drop the voiceover into `public/` under the name set by `"audioFile"` in
`captions.json` (mp3 or wav). As shipped that is `public/audio.mp3`.

Until that file exists the project still runs: it is silent and the motion
follows a stand-in loudness curve built from the caption timings. Once the
file is there, the liquid and the camera shake follow the real voice, and the
video stretches to fit the audio if it runs longer than the captions.

## captions.json

All timing lives here. Times are seconds into the audio file.

| Key | What it does |
| --- | --- |
| `audioFile` | File name inside `public/`. |
| `fps`, `resolution` | Output frame rate and size. The scene is designed at 1080x1920 and scaled to fit. |
| `captions` | `start`, `end`, `text` and the name of a style. |
| `styles` | Named looks: `font`, `color`, `outline`, `outlineWidth` (px), `scale`, and optionally `shake`. |
| `effects` | Timed hits, listed below. |

How captions are drawn:

- **At most three words on screen.** A longer caption is split into even
  screens inside its own time window, so "OH BUT YOU ONLY GOT" plays as
  "OH BUT YOU" then "ONLY GOT". Each word pops in on its own.
- **Highlight colour goes on the key word.** In a caption whose style has a
  colour, only MILLIONS, 20, TWENTY, 30, BEAT and PUNCHED take it; the other
  words stay white. A coloured caption with none of those words is coloured
  whole.
- **`scale`** multiplies the base size (184px). A word too wide for the frame
  shrinks the screen it is on until it fits.
- **`shake: true`** makes the words land with a harder shake, gives the camera
  a short kick, and swaps that screen's squeegee stroke for a splash.
- **The style named `outro`** is the closing line: the liquid finishes
  covering the screen just before it, then fades to black as the line appears.

Effects:

| `type` | Fields | What it does |
| --- | --- | --- |
| `screen-shake` | `time`, `intensity`, `duration` | Camera shake that decays over `duration`. Intensity 1 is about 48px of travel. |
| `red-flash` | `time`, `intensity`, `duration` | Solid red at `intensity` opacity fading over `duration`; the liquid stays tinted a little longer. |
| `epoxy-splash` | `time`, `intensity` | A splash near the centre. Intensity 1 is a 470px radius. |

## Settings that are not in captions.json

These sit at the bottom of `src/config.ts`:

| Constant | Default | What it does |
| --- | --- | --- |
| `LEAD_IN_SEC` | `0` | At 0, every time in `captions.json` is also the time in the video. Raise it (0.8 works well) for a beat of black and the opening drag before the voice; audio, captions and effects all shift together. |
| `MAX_WORDS_PER_SCREEN` | `3` | Raise it to stop captions being split. |
| `HIGHLIGHT_WORDS` | the six above | Empty the list to colour whole captions instead. |
| `BASE_FONT_SIZE` | `184` | Caption size at scale 1. |
| `FINAL_DRAG_SEC`, `HOLD_COVERED_SEC`, `FADE_TO_BLACK_SEC` | `0.9`, `0.2`, `0.45` | Pace of the ending. |

## How the audio drives it

`src/audio.ts` decodes the file with the Web Audio API and measures its
loudness for every video frame. That one curve drives:

- **Spread speed.** Strokes advance on a "liquid clock" that creeps in silence
  and runs about four times faster at full volume.
- **Camera shake.** A small shake that grows with loudness, on top of the
  timed effects.
- **Surface.** The marble drifts on the same clock and brightens slightly with
  the voice.

Every frame is computed from the frame number alone, so the export matches the
preview exactly.

## Where things live

| File | What it is |
| --- | --- |
| `captions.json` | Audio file, captions, styles, effects. |
| `src/config.ts` | The config's shape, plus the settings it has no field for. |
| `src/scene.ts` | Turns the config into screens, strokes, splashes and shakes. Stroke sizes and the liquid clock speed are here. |
| `src/epoxyShader.ts` | The liquid: stroke shapes, marble, lighting. |
| `src/Captions.tsx` | Word pop-in, outline and motion blur. |
| `src/Visualizer.tsx` | Layer order, camera shake, red flash, fade and outro. |

## Notes

- **Rendering without a GPU** (a server or CI box): `npm run render -- --gl=swangle`.
- **Font.** Anton is bundled in `public/fonts` under the SIL Open Font License,
  so renders do not depend on a font CDN.
- **Remotion licence.** Free for individuals and companies of up to three
  people; larger companies need a licence. See remotion.dev/license.
