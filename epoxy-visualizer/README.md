# Epoxy visualizer

A 1080x1920 (9:16) caption visualizer for a voiceover: white metallic epoxy is
squeegeed across a black screen, driven by how loud the voice is, with
word-by-word captions on top. Built with [Remotion](https://www.remotion.dev)
(React), a WebGL canvas for the liquid, and the Web Audio API for the loudness
analysis. Exports MP4 at 30fps.

## Run it

```bash
npm install
npm run dev      # opens Remotion Studio: live preview with a scrubbable timeline
npm run render   # writes out/visualizer.mp4 (1080x1920, 30fps, audio included)
```

Needs Node 18 or newer. The first render downloads a headless Chrome.

## Add your audio

Drop the voiceover into `public/` and point `"audio"` in `captions.json` at
the file name (mp3 or wav):

```json
"audio": "voiceover.mp3"
```

Until that file exists the project still runs: it is silent and the motion
follows a stand-in loudness curve built from the caption timings. Once the
file is there, the liquid and the camera shake follow the real voice, and the
video length stretches to fit the audio if it runs longer than the captions.

## Time the captions

Everything is in `captions.json`. Times are seconds into the audio file.

```json
{"text": "BEAT THE SHIT", "start": 17.0, "end": 17.85, "fx": "hit"}
```

| Field | What it does |
| --- | --- |
| `text` | The 1 to 3 words shown together. Each word pops in on its own. |
| `start`, `end` | When the caption appears and leaves. |
| `fx` | Optional. `"shake"`: camera shake and a splash. `"hit"`: hard shake, red flash and a big splash. |
| `wordStarts` | Optional. Exact start time of each word, e.g. `[17.0, 17.3, 17.55]`. Without it the words are spread across the caption. |

The shipped timings are estimates at a natural speaking pace. They need to be
matched to the real recording: scrub the timeline in Studio, read the time
where each phrase starts, and type it in. Studio reloads on save.

Other settings in the same file:

| Setting | What it does |
| --- | --- |
| `leadInSec` | Black screen plus the opening squeegee drag before the audio starts. |
| `highlights` | Word to colour. `"red"`, `"yellow"` or any CSS colour. Punctuation and case are ignored. |
| `outro.text` | The closing line on black. |
| `outro.coverSec` | How long the final full-screen drag takes. |
| `outro.holdCoveredSec`, `outro.fadeSec`, `outro.holdTextSec` | Hold on the full white screen, fade to black, hold on the closing line. |

## How the audio drives it

`src/audio.ts` decodes the file with the Web Audio API and measures its
loudness for every video frame. That one curve drives:

- **Spread speed.** Strokes advance on a "liquid clock" that creeps in silence
  and runs about four times faster at full volume.
- **Camera shake.** A small shake that grows with loudness, plus a kick on
  every `fx` caption.
- **Surface.** The marble drifts on the same clock and brightens slightly with
  the voice.

Every frame is computed from the frame number alone, so the export matches the
preview exactly.

## Where things live

| File | What it is |
| --- | --- |
| `captions.json` | Audio file name, caption timings, highlight colours, outro. |
| `src/scene.ts` | Turns the config into strokes, splashes and impacts. Stroke sizes and the liquid clock speed are here. |
| `src/epoxyShader.ts` | The liquid: stroke shapes, marble, lighting. |
| `src/Captions.tsx` | Caption font size, outline, pop-in and motion blur. |
| `src/Visualizer.tsx` | Layer order, camera shake, red flash, fade and outro. |

## Notes

- **Rendering without a GPU** (a server or CI box): `npm run render -- --gl=swangle`.
- **Font.** Anton is bundled in `public/fonts` under the SIL Open Font License,
  so renders do not depend on a font CDN.
- **Remotion licence.** Free for individuals and companies of up to three
  people; larger companies need a licence. See remotion.dev/license.
