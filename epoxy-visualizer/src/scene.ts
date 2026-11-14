import type {Envelope} from './audio';
import {
	HEIGHT,
	HIGHLIGHT_COLORS,
	WIDTH,
	type CaptionFx,
	type VisualizerConfig,
} from './config';

/** Extra canvas around the frame so camera shake never exposes an edge. */
export const BLEED = 64;

export type Word = {
	text: string;
	startFrame: number;
	color: string | null;
};

export type Caption = {
	startFrame: number;
	endFrame: number;
	fx: CaptionFx | null;
	words: Word[];
};

export type Stroke = {
	kind: 'drag' | 'splash';
	startFrame: number;
	/** How long the stroke takes, measured on the audio-driven liquid clock. */
	duration: number;
	x: number;
	y: number;
	dirX: number;
	dirY: number;
	/** Drag: length in px. Splash: radius in px. */
	size: number;
	halfWidth: number;
	seed: number;
};

export type Scene = {
	durationInFrames: number;
	leadInFrames: number;
	hasAudio: boolean;
	/** Loudness 0..1 per video frame. */
	amp: Float32Array;
	/** Liquid clock per video frame: runs faster while the voice is loud. */
	clock: Float32Array;
	captions: Caption[];
	strokes: Stroke[];
	impacts: {frame: number; fx: CaptionFx}[];
	outro: {
		text: string;
		coverStart: number;
		fadeStart: number;
		fadeEnd: number;
	};
};

const mulberry32 = (seed: number) => {
	let a = seed >>> 0;
	return () => {
		a = (a + 0x6d2b79f5) >>> 0;
		let t = a;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
};

const bare = (word: string) => word.replace(/[^A-Za-z0-9]/g, '').toUpperCase();

/** Liquid-clock speed: a slow creep in silence, a surge when the voice is loud. */
const CLOCK_BASE = 0.55;
const CLOCK_GAIN = 1.7;

export const buildScene = (
	config: VisualizerConfig,
	envelope: Envelope,
	fps: number,
): Scene => {
	const leadInFrames = Math.round(config.leadInSec * fps);
	const toFrame = (audioSec: number) => leadInFrames + Math.round(audioSec * fps);

	const highlights = new Map(
		Object.entries(config.highlights).map(([word, color]) => [
			bare(word),
			HIGHLIGHT_COLORS[color] ?? color,
		]),
	);

	const captions: Caption[] = config.captions.map((c) => {
		const texts = c.text.split(/\s+/).filter(Boolean);
		const chars = texts.reduce((n, w) => n + w.length, 0);
		const span = c.end - c.start;
		let before = 0;
		const words = texts.map((text, i): Word => {
			// Words land one after another across the first 80% of the caption,
			// longer words taking proportionally longer to say.
			const auto = c.start + (span * 0.8 * before) / Math.max(1, chars);
			before += text.length;
			return {
				text,
				startFrame: toFrame(c.wordStarts?.[i] ?? auto),
				color: highlights.get(bare(text)) ?? null,
			};
		});
		return {
			startFrame: toFrame(c.start),
			endFrame: toFrame(c.end),
			fx: c.fx ?? null,
			words,
		};
	});

	const lastCaptionEnd = captions.reduce((m, c) => Math.max(m, c.endFrame), leadInFrames);
	const sec = (s: number) => Math.round(s * fps);

	// The final full-screen drag starts just before the last word leaves.
	const coverStart = Math.max(leadInFrames, lastCaptionEnd - sec(0.3));
	const coverEnd = coverStart + sec(config.outro.coverSec);
	const fadeStart = coverEnd + sec(config.outro.holdCoveredSec);
	const fadeEnd = fadeStart + sec(config.outro.fadeSec);
	const audioEnd = envelope.source === 'audio' ? toFrame(envelope.durationSec) : 0;
	const durationInFrames = Math.max(
		fadeEnd + sec(config.outro.holdTextSec),
		audioEnd + sec(0.2),
	);

	const amp = new Float32Array(durationInFrames);
	const clock = new Float32Array(durationInFrames + 1);
	for (let f = 0; f < durationInFrames; f++) {
		const a = f - leadInFrames;
		amp[f] = a >= 0 && a < envelope.amp.length ? envelope.amp[a] : 0;
		clock[f + 1] = clock[f] + (CLOCK_BASE + CLOCK_GAIN * amp[f]) / fps;
	}

	const clockAt = (frame: number) =>
		clock[Math.max(0, Math.min(durationInFrames, frame))];

	const rng = mulberry32(20_30);
	const rand = (lo: number, hi: number) => lo + (hi - lo) * rng();
	const strokes: Stroke[] = [];

	// 1. Opening drag: top to bottom through the middle, timed so the liquid
	//    has just passed the caption area when the first word lands.
	const introStart = Math.min(sec(0.25), Math.floor(leadInFrames / 3));
	const firstWord = captions[0]?.startFrame ?? leadInFrames;
	strokes.push({
		kind: 'drag',
		startFrame: introStart,
		duration: Math.max(0.2, (clockAt(firstWord) - clockAt(introStart)) / 0.45),
		x: WIDTH / 2,
		y: -BLEED - 60,
		dirX: 0,
		dirY: 1,
		size: HEIGHT + 2 * BLEED + 160,
		halfWidth: 300,
		seed: rng() * 100,
	});

	// 2. One stroke or splash per caption change.
	const cells: [number, number][] = [];
	for (let row = 0; row < 4; row++) {
		for (let col = 0; col < 2; col++) {
			cells.push([WIDTH * (0.25 + 0.5 * col), HEIGHT * (0.125 + 0.25 * row)]);
		}
	}

	for (let i = cells.length - 1; i > 0; i--) {
		const j = Math.floor(rng() * (i + 1));
		[cells[i], cells[j]] = [cells[j], cells[i]];
	}

	captions.slice(1).forEach((caption, i) => {
		const seed = rng() * 100;
		if (caption.fx === 'hit') {
			strokes.push({
				kind: 'splash',
				startFrame: caption.startFrame,
				duration: 0.6,
				x: WIDTH / 2 + rand(-70, 70),
				y: HEIGHT / 2 + rand(-90, 90),
				dirX: 1,
				dirY: 0,
				size: 470,
				halfWidth: 0,
				seed,
			});
			return;
		}

		if (caption.fx === 'shake') {
			strokes.push({
				kind: 'splash',
				startFrame: caption.startFrame,
				duration: 0.65,
				x: WIDTH / 2 + rand(-300, 300),
				y: HEIGHT / 2 + rand(-520, 520),
				dirX: 1,
				dirY: 0,
				size: rand(250, 330),
				halfWidth: 0,
				seed,
			});
			return;
		}

		const [cx, cy] = cells[i % cells.length];
		const pick = rng();
		let angle: number;
		if (pick < 0.55) {
			angle = (rng() < 0.5 ? 0 : Math.PI) + rand(-0.12, 0.12);
		} else if (pick < 0.8) {
			angle = (rng() < 0.5 ? 0 : Math.PI) + rand(0.3, 0.6) * (rng() < 0.5 ? -1 : 1);
		} else {
			angle = (rng() < 0.5 ? 0.5 : -0.5) * Math.PI + rand(-0.1, 0.1);
		}

		const length = rand(650, 1150);
		const dirX = Math.cos(angle);
		const dirY = Math.sin(angle);
		const centreX = cx + rand(-130, 130);
		const centreY = cy + rand(-130, 130);
		const back = rand(0.4, 0.6);
		strokes.push({
			kind: 'drag',
			startFrame: caption.startFrame,
			duration: rand(0.9, 1.4) * (length / 900),
			x: centreX - dirX * length * back,
			y: centreY - dirY * length * back,
			dirX,
			dirY,
			size: length,
			halfWidth: rand(80, 165),
			seed,
		});
	});

	// 3. Final drag: full width, top to bottom, until nothing black is left.
	strokes.push({
		kind: 'drag',
		startFrame: coverStart,
		duration: Math.max(0.2, clockAt(coverEnd) - clockAt(coverStart)),
		x: WIDTH / 2,
		y: -BLEED - 220,
		dirX: 0,
		dirY: 1,
		size: HEIGHT + 2 * BLEED + 520,
		halfWidth: WIDTH / 2 + BLEED + 160,
		seed: rng() * 100,
	});

	strokes.sort((a, b) => a.startFrame - b.startFrame);

	const impacts = captions.flatMap((c) =>
		c.fx ? [{frame: c.startFrame, fx: c.fx}] : [],
	);

	return {
		durationInFrames,
		leadInFrames,
		hasAudio: envelope.source === 'audio',
		amp,
		clock,
		captions,
		strokes,
		impacts,
		outro: {text: config.outro.text, coverStart, fadeStart, fadeEnd},
	};
};

/** 0..1 progress of a stroke on the liquid clock at a given frame. */
export const strokeProgress = (scene: Scene, stroke: Stroke, frame: number) => {
	if (frame <= stroke.startFrame) {
		return 0;
	}

	const f = Math.min(scene.durationInFrames, frame);
	const elapsed = scene.clock[f] - scene.clock[stroke.startFrame];
	return Math.min(1, elapsed / stroke.duration);
};

/** Deterministic 0..1 noise for shake, so every render is identical. */
export const noise1 = (n: number) => {
	const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
	return s - Math.floor(s);
};
