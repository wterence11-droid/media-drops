import raw from '../captions.json';

export type CaptionStyle = {
	font: string;
	color: string;
	outline: string;
	/** Outline thickness in px at 1080 wide. */
	outlineWidth: number;
	/** Multiplies the base caption size. */
	scale: number;
	/** Harder pop-in shake on the words, plus a camera kick and a splash. */
	shake?: boolean;
};

export type CaptionConfig = {
	/** Seconds into the audio file. */
	start: number;
	end: number;
	text: string;
	/** Key into "styles". The style named "outro" is the closing line on black. */
	style: string;
};

export type EffectConfig =
	| {type: 'screen-shake'; time: number; intensity: number; duration: number}
	| {type: 'red-flash'; time: number; intensity: number; duration: number}
	| {type: 'epoxy-splash'; time: number; intensity: number};

export type VisualizerConfig = {
	/** File name inside the public/ folder. */
	audioFile: string;
	fps: number;
	resolution: {width: number; height: number};
	captions: CaptionConfig[];
	effects: EffectConfig[];
	styles: Record<string, CaptionStyle>;
};

export const config = raw as VisualizerConfig;

/** Everything is laid out on this canvas, then scaled to config.resolution. */
export const WIDTH = 1080;
export const HEIGHT = 1920;

// --- Settings that captions.json has no field for -----------------------

/**
 * Seconds of black screen + opening drag before the audio starts.
 * At 0, every time in captions.json is also the time in the video. Raising it
 * delays the audio, captions and effects together, so they stay in sync.
 */
export const LEAD_IN_SEC = 0;

/** Longer captions are split into screens of at most this many words. */
export const MAX_WORDS_PER_SCREEN = 3;

/**
 * In a caption whose style has a colour, only these words take the colour and
 * the rest stay white. A coloured caption containing none of them is coloured
 * whole. Empty this list to always colour the whole caption.
 */
export const HIGHLIGHT_WORDS = ['MILLIONS', '20', 'TWENTY', '30', 'BEAT', 'PUNCHED'];

/** Caption size in px for a style with scale 1. */
export const BASE_FONT_SIZE = 184;

/** The style name that marks the closing line. */
export const OUTRO_STYLE = 'outro';

/** Ending: full-screen drag, hold on white, fade to black as the outro line starts. */
export const FINAL_DRAG_SEC = 0.9;
export const HOLD_COVERED_SEC = 0.2;
export const FADE_TO_BLACK_SEC = 0.45;
