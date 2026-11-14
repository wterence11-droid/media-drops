import React, {useEffect, useMemo, useState} from 'react';
import {
	AbsoluteFill,
	Audio,
	Sequence,
	cancelRender,
	continueRender,
	delayRender,
	interpolate,
	staticFile,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';
import {loadAudioEnvelope, syntheticEnvelope, type Envelope} from './audio';
import {Captions, outlineShadow} from './Captions';
import {BASE_FONT_SIZE, config, HEIGHT, WIDTH} from './config';
import {EpoxyCanvas} from './EpoxyCanvas';
import {loadFonts} from './fonts';
import {Grain} from './Grain';
import {buildScene, noise1, type Scene} from './scene';

/** Loudness curve from the audio file, or the caption-based stand-in if there is no file yet. */
export const loadEnvelope = async (fps: number): Promise<Envelope> => {
	const fromAudio = await loadAudioEnvelope(staticFile(config.audioFile), fps);
	return fromAudio ?? syntheticEnvelope(config, fps);
};

/** Holds the render until the font and the loudness curve are in. */
const useScene = (): Scene | null => {
	const {fps} = useVideoConfig();
	const [envelope, setEnvelope] = useState<Envelope | null>(null);
	const [handle] = useState(() => delayRender('Loading font and audio'));

	useEffect(() => {
		Promise.all([loadEnvelope(fps), loadFonts()])
			.then(([loaded]) => {
				setEnvelope(loaded);
				continueRender(handle);
			})
			.catch((err) => cancelRender(err));
	}, [fps, handle]);

	return useMemo(() => (envelope ? buildScene(config, envelope, fps) : null), [envelope, fps]);
};

/** Camera shake: a little with the voice, a lot on screen-shake effects. */
const useShake = (scene: Scene, frame: number) => {
	const amp = scene.amp[Math.min(scene.amp.length - 1, frame)] ?? 0;
	let strength = 5 * amp * amp;
	let punch = 0;

	for (const shake of scene.shakes) {
		const age = frame - shake.frame;
		if (age < 0 || age >= shake.frames) {
			continue;
		}

		const left = 1 - age / shake.frames;
		strength += shake.strength * left * left;
		punch += (shake.strength / 1000) * left * left;
	}

	// Red flash: solid red for its duration, then the liquid stays stained a beat longer.
	let flash = 0;
	let stain = 0;
	for (const f of scene.flashes) {
		const age = frame - f.frame;
		if (age < 0) {
			continue;
		}

		flash = Math.max(flash, f.intensity * Math.max(0, 1 - age / f.frames) ** 0.6);
		stain = Math.max(stain, f.intensity * Math.max(0, 1 - age / (f.frames * 3)));
	}

	return {
		x: (noise1(frame * 2.1) - 0.5) * 2 * strength,
		y: (noise1(frame * 2.1 + 50) - 0.5) * 2 * strength,
		rotate: (noise1(frame * 2.1 + 90) - 0.5) * strength * 0.045,
		scale: 1 + punch,
		flash,
		stain,
	};
};

export const Visualizer: React.FC = () => {
	const scene = useScene();
	if (!scene) {
		return <AbsoluteFill style={{backgroundColor: '#000'}} />;
	}

	return <Stage scene={scene} />;
};

const Stage: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {width, height} = useVideoConfig();
	const shake = useShake(scene, frame);
	const {fadeStart, fadeEnd, startFrame: outroStart, text, style} = scene.outro;
	const camera = `translate(${shake.x.toFixed(2)}px, ${shake.y.toFixed(2)}px) rotate(${shake.rotate.toFixed(3)}deg) scale(${shake.scale.toFixed(4)})`;

	const blackout = interpolate(frame, [fadeStart, fadeEnd], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const outroIn = interpolate(frame, [outroStart, outroStart + 10], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	// The opening is pure black: grain only comes up with the liquid.
	const grain = interpolate(frame, [0, Math.max(1, scene.leadInFrames)], [0, 0.34], {
		extrapolateRight: 'clamp',
	});
	// Laid out at 1080x1920, then scaled to whatever resolution the config asks for.
	const fit = Math.min(width / WIDTH, height / HEIGHT);

	return (
		<AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
			{scene.hasAudio ? (
				<Sequence from={scene.leadInFrames} layout="none">
					<Audio src={staticFile(config.audioFile)} />
				</Sequence>
			) : null}

			<div
				style={{
					position: 'absolute',
					left: (width - WIDTH * fit) / 2,
					top: (height - HEIGHT * fit) / 2,
					width: WIDTH,
					height: HEIGHT,
					overflow: 'hidden',
					transform: `scale(${fit})`,
					transformOrigin: '0 0',
				}}
			>
				<AbsoluteFill style={{transform: camera}}>
					<EpoxyCanvas scene={scene} />
				</AbsoluteFill>
				<AbsoluteFill
					style={{backgroundColor: '#ff0a0a', opacity: shake.stain, mixBlendMode: 'multiply'}}
				/>
				<AbsoluteFill style={{backgroundColor: '#ff0000', opacity: shake.flash}} />
				<AbsoluteFill style={{transform: camera}}>
					<Captions scene={scene} />
				</AbsoluteFill>

				<AbsoluteFill style={{backgroundColor: '#000', opacity: blackout}} />

				<AbsoluteFill
					style={{
						alignItems: 'center',
						justifyContent: 'center',
						opacity: outroIn,
						transform: `scale(${(1.06 - 0.06 * outroIn + 0.00035 * Math.max(0, frame - outroStart)).toFixed(4)})`,
					}}
				>
					<div
						style={{
							maxWidth: 940,
							textAlign: 'center',
							fontFamily: style.font,
							fontSize: BASE_FONT_SIZE * style.scale,
							lineHeight: 1.1,
							letterSpacing: '0.02em',
							textTransform: 'uppercase',
							color: style.color,
							textShadow: outlineShadow(style.outlineWidth, style.outline, false),
						}}
					>
						{text}
					</div>
				</AbsoluteFill>

				<AbsoluteFill
					style={{
						background:
							'radial-gradient(ellipse 75% 62% at 50% 50%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.62) 100%)',
						pointerEvents: 'none',
					}}
				/>
				<Grain strength={grain} />
			</div>
		</AbsoluteFill>
	);
};
