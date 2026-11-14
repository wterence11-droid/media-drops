import raw from '../captions.json';

export type CaptionFx = 'shake' | 'hit';

export type CaptionConfig = {
	/** 1-3 words, shown together in the centre of the screen. */
	text: string;
	/** Seconds into the audio file. */
	start: number;
	end: number;
	/** "shake": camera shake + splash. "hit": hard shake + red flash + big splash. */
	fx?: CaptionFx;
	/** Optional exact start time of each word, in seconds into the audio file. */
	wordStarts?: number[];
};

export type VisualizerConfig = {
	/** File name inside the public/ folder. */
	audio: string;
	/** Black screen + first squeegee drag before the audio starts. */
	leadInSec: number;
	/** Word (without punctuation) -> "red" | "yellow" | any CSS colour. */
	highlights: Record<string, string>;
	outro: {
		text: string;
		coverSec: number;
		holdCoveredSec: number;
		fadeSec: number;
		holdTextSec: number;
	};
	captions: CaptionConfig[];
};

export const config = raw as VisualizerConfig;

export const WIDTH = 1080;
export const HEIGHT = 1920;
export const FPS = 30;

export const HIGHLIGHT_COLORS: Record<string, string> = {
	red: '#ff1f1f',
	yellow: '#ffe600',
};
