import type {Envelope} from './audio';
import {
	FADE_TO_BLACK_SEC,
	FINAL_DRAG_SEC,
	HEIGHT,
	HIGHLIGHT_WORDS,
	HOLD_COVERED_SEC,
	LEAD_IN_SEC,
	MAX_WORDS_PER_SCREEN,
	OUTRO_STYLE,
	WIDTH,
	type CaptionStyle,
	type VisualizerConfig,
} from './config';

/** Extra canvas around the frame so camera shake never exposes an edge. */
export const BLEED = 64;

export type Word = {
	text: string;
	startFrame: number;
	color: string;
};

/** What is on screen at once: at most MAX_WORDS_PER_SCREEN words of one caption. */
export type Screen = {
	startFrame: number;
	endFrame: number;
	style: CaptionStyle;
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

export type Shake = {frame: number; frames: number; strength: number};
export type Flash = {frame: number; frames: number; intensity: number};

export type Scene = {
	durationInFrames: number;
	leadInFrames: number;
	hasAudio: boolean;
	/** Loudness 0..1 per video frame. */
	amp: Float32Array;
	/** Liquid clock per video frame: runs faster while the voice is loud. */
	clock: Float32Array;
	screens: Screen[];
	strokes: Stroke[];
	shakes: Shake[];
	flashes: Flash[];
	/** The closing line. `text` is empty when the config has no outro caption. */
	outro: {
		text: string;
		style: CaptionStyle;
		startFrame: number;
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
const highlightWords = new Set(HIGHLIGHT_WORDS.map(bare));

const FALLBACK_STYLE: CaptionStyle = {
	font: 'Anton, Impact, sans-serif',
	color: '#FFFFFF',
	outline: '#000000',
	outlineWidth: 8,
	scale: 1,
};

/** Splits words into the fewest screens of at most `max` words, as evenly as possible. */
const chunk = (words: string[], max: number): string[][] => {
	const count = Math.ceil(words.length / max);
	const out: string[][] = [];
	let at = 0;
	for (let i = 0; i < count; i++) {
		const take = Math.ceil((words.length - at) / (count - i));
		out.push(words.slice(at, at + take));
		at += take;
	}

	return out;
};

/** Liquid-clock speed: a slow creep in silence, a surge when the voice is loud. */
const CLOCK_BASE = 0.55;
const CLOCK_GAIN = 1.7;

/** Camera travel in px for a screen-shake of intensity 1. */
const SHAKE_PX = 48;
/** Splash radius in px for an epoxy-splash of intensity 1. */
const SPLASH_PX = 470;

export const buildScene = (
	config: VisualizerConfig,
	envelope: Envelope,
	fps: number,
): Scene => {
	const leadInFrames = Math.round(LEAD_IN_SEC * fps);
	const toFrame = (audioSec: number) => leadInFrames + Math.round(audioSec * fps);
	const sec = (s: number) => Math.round(s * fps);
	const styleOf = (name: string) => config.styles[name] ?? FALLBACK_STYLE;

	const spoken = config.captions.filter((c) => c.style !== OUTRO_STYLE);
	const outroCaption = config.captions.find((c) => c.style === OUTRO_STYLE) ?? null;

	// Captions -> screens of 1-3 words, each word with its own entrance time.
	// Time inside a caption is shared out by letter count: long words take longer to say.
	const screens: Screen[] = [];
	for (const caption of spoken) {
		const style = styleOf(caption.style);
		const texts = caption.text.split(/\s+/).filter(Boolean);
		const hasKeyword = texts.some((t) => highlightWords.has(bare(t)));
		const total = Math.max(1, texts.reduce((n, t) => n + t.length, 0));
		const span = caption.end - caption.start;
		const base = styleOf('normal').color;

		let before = 0;
		for (const group of chunk(texts, MAX_WORDS_PER_SCREEN)) {
			const letters = group.reduce((n, t) => n + t.length, 0);
			const start = caption.start + (span * before) / total;
			const end = caption.start + (span * (before + letters)) / total;
			let inside = 0;
			const words = group.map((text): Word => {
				// Words land across the first 80% of their screen.
				const at = start + ((end - start) * 0.8 * inside) / Math.max(1, letters);
				inside += text.length;
				const coloured = !hasKeyword || highlightWords.has(bare(text));
				return {text, startFrame: toFrame(at), color: coloured ? style.color : base};
			});
			screens.push({startFrame: toFrame(start), endFrame: toFrame(end), style, words});
			before += letters;
		}
	}

	const firstWord = screens[0]?.startFrame ?? leadInFrames;
	const lastSpoken = screens.reduce((m, s) => Math.max(m, s.endFrame), leadInFrames);

	// Ending. With an outro caption, the fade lands as its line starts; without
	// one, the screen is covered and faded right after the last caption.
	const outroStart = outroCaption ? toFrame(outroCaption.start) : lastSpoken + sec(1.2);
	const fadeEnd = outroStart + sec(0.1);
	const fadeStart = fadeEnd - sec(FADE_TO_BLACK_SEC);
	const coverEnd = fadeStart - sec(HOLD_COVERED_SEC);
	const coverStart = Math.max(firstWord, coverEnd - sec(FINAL_DRAG_SEC));
	const audioEnd = envelope.source === 'audio' ? toFrame(envelope.durationSec) : 0;
	const durationInFrames = Math.max(
		outroCaption ? toFrame(outroCaption.end) : fadeEnd + sec(0.3),
		audioEnd,
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

	const splash = (startFrame: number, radius: number, spread: number): Stroke => ({
		kind: 'splash',
		startFrame,
		duration: 0.6,
		x: WIDTH / 2 + rand(-300, 300) * spread,
		y: HEIGHT / 2 + rand(-520, 520) * spread,
		dirX: 1,
		dirY: 0,
		size: radius,
		halfWidth: 0,
		seed: rng() * 100,
	});

	// 1. Opening drag: top to bottom through the middle, timed so the liquid
	//    has just passed the caption area when the first word lands. With no
	//    lead-in there is no time for that, so it simply starts on frame 0.
	const introStart = Math.min(sec(0.2), Math.floor(leadInFrames / 3));
	const introReach = Math.max(firstWord, introStart + sec(0.5));
	strokes.push({
		kind: 'drag',
		startFrame: introStart,
		duration: Math.max(0.2, (clockAt(introReach) - clockAt(introStart)) / 0.45),
		x: WIDTH / 2,
		y: -BLEED - 60,
		dirX: 0,
		dirY: 1,
		size: HEIGHT + 2 * BLEED + 160,
		halfWidth: 300,
		seed: rng() * 100,
	});

	// 2. One stroke per screen change; a splash instead when the style shakes.
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

	screens.slice(1).forEach((screen, i) => {
		if (screen.style.shake) {
			strokes.push(splash(screen.startFrame, rand(250, 330), 1));
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
			startFrame: screen.startFrame,
			duration: rand(0.9, 1.4) * (length / 900),
			x: centreX - dirX * length * back,
			y: centreY - dirY * length * back,
			dirX,
			dirY,
			size: length,
			halfWidth: rand(80, 165),
			seed: rng() * 100,
		});
	});

	// 3. Effects from the config.
	const shakes: Shake[] = [];
	const flashes: Flash[] = [];
	for (const effect of config.effects ?? []) {
		const frame = toFrame(effect.time);
		if (effect.type === 'screen-shake') {
			shakes.push({
				frame,
				frames: Math.max(1, sec(effect.duration)),
				strength: SHAKE_PX * effect.intensity,
			});
		} else if (effect.type === 'red-flash') {
			flashes.push({
				frame,
				frames: Math.max(1, sec(effect.duration)),
				intensity: effect.intensity,
			});
		} else if (effect.type === 'epoxy-splash') {
			strokes.push(splash(frame, SPLASH_PX * effect.intensity, 0.3));
		}
	}

	// Styles with "shake" also give the camera a short kick as they land.
	const seen = new Set<number>();
	for (const screen of screens) {
		if (screen.style.shake && !seen.has(screen.startFrame)) {
			seen.add(screen.startFrame);
			shakes.push({frame: screen.startFrame, frames: sec(0.3), strength: 15});
		}
	}

	// 4. Final drag: full width, top to bottom, until nothing black is left.
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

	return {
		durationInFrames,
		leadInFrames,
		hasAudio: envelope.source === 'audio',
		amp,
		clock,
		screens,
		strokes,
		shakes,
		flashes,
		outro: {
			text: outroCaption?.text ?? '',
			style: outroCaption ? styleOf(outroCaption.style) : FALLBACK_STYLE,
			startFrame: outroStart,
			fadeStart,
			fadeEnd,
		},
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
