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
import {Captions} from './Captions';
import {config} from './config';
import {EpoxyCanvas} from './EpoxyCanvas';
import {FONT_FAMILY, loadFonts} from './fonts';
import {Grain} from './Grain';
import {buildScene, noise1, type Scene} from './scene';

/** Loudness curve from the audio file, or the caption-based stand-in if there is no file yet. */
export const loadEnvelope = async (fps: number): Promise<Envelope> => {
	const fromAudio = await loadAudioEnvelope(staticFile(config.audio), fps);
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

/** Camera shake: a little with the voice, a lot on impact words. */
const useShake = (scene: Scene, frame: number) => {
	const amp = scene.amp[Math.min(scene.amp.length - 1, frame)] ?? 0;
	let strength = 5 * amp * amp;
	let punch = 0;
	let flash = 0;

	for (const impact of scene.impacts) {
		const age = frame - impact.frame;
		if (age < 0 || age > 45) {
			continue;
		}

		if (impact.fx === 'hit') {
			strength += 52 * Math.exp(-age / 7);
			punch += 0.05 * Math.exp(-age / 5);
			flash = Math.max(flash, Math.exp(-age / 2.4));
		} else {
			strength += 17 * Math.exp(-age / 4.5);
			punch += 0.015 * Math.exp(-age / 4);
		}
	}

	return {
		x: (noise1(frame * 2.1) - 0.5) * 2 * strength,
		y: (noise1(frame * 2.1 + 50) - 0.5) * 2 * strength,
		rotate: (noise1(frame * 2.1 + 90) - 0.5) * strength * 0.045,
		scale: 1 + punch,
		flash,
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
	const shake = useShake(scene, frame);
	const {fadeStart, fadeEnd, text} = scene.outro;
	const camera = `translate(${shake.x.toFixed(2)}px, ${shake.y.toFixed(2)}px) rotate(${shake.rotate.toFixed(3)}deg) scale(${shake.scale.toFixed(4)})`;

	const blackout = interpolate(frame, [fadeStart, fadeEnd], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const outroIn = interpolate(frame, [fadeEnd - 6, fadeEnd + 12], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	// The opening is pure black: grain only comes up with the liquid.
	const grain = interpolate(frame, [0, Math.max(1, scene.leadInFrames)], [0, 0.34], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
			{scene.hasAudio ? (
				<Sequence from={scene.leadInFrames} layout="none">
					<Audio src={staticFile(config.audio)} />
				</Sequence>
			) : null}

			<AbsoluteFill style={{transform: camera}}>
				<EpoxyCanvas scene={scene} />
			</AbsoluteFill>
			{/* Red flash: a hard hit of solid red, then the liquid stays stained for a beat. */}
			<AbsoluteFill
				style={{
					backgroundColor: '#ff0a0a',
					opacity: Math.min(1, shake.flash * 3) * 0.55,
					mixBlendMode: 'multiply',
				}}
			/>
			<AbsoluteFill style={{backgroundColor: '#ff0000', opacity: shake.flash * 0.8}} />
			<AbsoluteFill style={{transform: camera}}>
				<Captions scene={scene} />
			</AbsoluteFill>

			<AbsoluteFill style={{backgroundColor: '#000', opacity: blackout}} />

			<AbsoluteFill
				style={{
					alignItems: 'center',
					justifyContent: 'center',
					opacity: outroIn,
					transform: `scale(${(1.06 - 0.06 * outroIn + 0.00035 * Math.max(0, frame - fadeEnd)).toFixed(4)})`,
				}}
			>
				<div
					style={{
						maxWidth: 900,
						textAlign: 'center',
						fontFamily: FONT_FAMILY,
						fontSize: 150,
						lineHeight: 1.1,
						letterSpacing: '0.02em',
						textTransform: 'uppercase',
						color: '#fff',
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
		</AbsoluteFill>
	);
};
