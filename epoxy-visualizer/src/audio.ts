import {OUTRO_STYLE, type VisualizerConfig} from './config';

/**
 * Loudness of the voiceover, one value per video frame.
 * `amp[0]` is the first frame of the audio file (not of the video).
 */
export type Envelope = {
	source: 'audio' | 'synthetic';
	durationSec: number;
	amp: Float32Array;
};

const cache = new Map<string, Promise<Envelope | null>>();

/**
 * Decodes the audio file with the Web Audio API and measures its RMS loudness
 * per video frame. Resolves to `null` if the file does not exist, so the
 * project still runs before the voiceover has been dropped in.
 */
export const loadAudioEnvelope = (
	url: string,
	fps: number,
): Promise<Envelope | null> => {
	const key = `${url}@${fps}`;
	const cached = cache.get(key);
	if (cached) {
		return cached;
	}

	const promise = decode(url, fps);
	cache.set(key, promise);
	return promise;
};

const decode = async (url: string, fps: number): Promise<Envelope | null> => {
	let res: Response;
	try {
		res = await fetch(url);
	} catch {
		return null;
	}

	const type = res.headers.get('content-type') ?? '';
	if (!res.ok || type.includes('text/html')) {
		return null;
	}

	const bytes = await res.arrayBuffer();
	const Ctx: typeof OfflineAudioContext =
		window.OfflineAudioContext ??
		(window as unknown as {webkitOfflineAudioContext: typeof OfflineAudioContext})
			.webkitOfflineAudioContext;
	const ctx = new Ctx(1, 1, 44100);

	let buffer: AudioBuffer;
	try {
		buffer = await ctx.decodeAudioData(bytes);
	} catch (err) {
		throw new Error(
			`Found ${url} but the browser could not decode it. Use an mp3 or wav file. (${String(err)})`,
		);
	}

	const samplesPerFrame = buffer.sampleRate / fps;
	const frames = Math.max(1, Math.ceil(buffer.length / samplesPerFrame));
	const channels: Float32Array[] = [];
	for (let c = 0; c < buffer.numberOfChannels; c++) {
		channels.push(buffer.getChannelData(c));
	}

	const rms = new Float32Array(frames);
	for (let f = 0; f < frames; f++) {
		const from = Math.floor(f * samplesPerFrame);
		const to = Math.min(buffer.length, Math.floor((f + 1) * samplesPerFrame));
		let sum = 0;
		for (const data of channels) {
			for (let i = from; i < to; i++) {
				sum += data[i] * data[i];
			}
		}

		const count = Math.max(1, (to - from) * channels.length);
		rms[f] = Math.sqrt(sum / count);
	}

	// Normalise against the loud end of the recording, so a quiet take and a
	// hot take drive the visuals equally hard.
	const sorted = Array.from(rms).sort((a, b) => a - b);
	const loud = sorted[Math.floor(sorted.length * 0.95)] || 1e-4;

	// Envelope follower: instant attack, short release.
	const amp = new Float32Array(frames);
	let env = 0;
	for (let f = 0; f < frames; f++) {
		const level = Math.min(1, rms[f] / loud);
		env = Math.max(level, env * 0.72);
		amp[f] = env;
	}

	return {source: 'audio', durationSec: buffer.duration, amp};
};

/**
 * Stand-in loudness built from the caption timings: a pulse on every word,
 * harder on highlighted and impact captions. Used until an audio file exists.
 */
export const syntheticEnvelope = (
	config: VisualizerConfig,
	fps: number,
): Envelope => {
	const spoken = config.captions.filter((c) => c.style !== OUTRO_STYLE);
	const durationSec = spoken.reduce((m, c) => Math.max(m, c.end), 0);
	const frames = Math.max(1, Math.ceil(durationSec * fps));
	const amp = new Float32Array(frames);

	for (const caption of spoken) {
		const words = caption.text.split(/\s+/).filter(Boolean);
		const span = caption.end - caption.start;
		const style = config.styles[caption.style];
		const peak = style?.shake ? 1 : (style?.scale ?? 1) > 1 ? 0.85 : 0.62;
		words.forEach((_, i) => {
			const onset = caption.start + (span * 0.9 * i) / words.length;
			const first = Math.floor(onset * fps);
			for (let f = first; f < Math.min(frames, first + fps); f++) {
				const t = f / fps - onset;
				amp[f] = Math.max(amp[f], peak * Math.exp(-t / 0.16));
			}
		});
	}

	return {source: 'synthetic', durationSec, amp};
};
