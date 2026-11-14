import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT_FAMILY} from './fonts';
import {noise1, type Caption, type Scene, type Word} from './scene';

const FONT_SIZE = 184;
const OUTLINE = 13;

// A ring of hard shadows gives a thick outline with round corners.
// (-webkit-text-stroke spikes at this weight on Anton's sharp joins.)
const outline = (radius: number) => {
	const parts: string[] = [];
	const steps = 32;
	for (let i = 0; i < steps; i++) {
		const angle = (i / steps) * Math.PI * 2;
		parts.push(
			`${(Math.cos(angle) * radius).toFixed(2)}px ${(Math.sin(angle) * radius).toFixed(2)}px 0 #000`,
		);
	}

	parts.push(`0 ${radius + 9}px 0 #000`);
	return parts.join(', ');
};

const OUTLINE_SHADOW = outline(OUTLINE);

/** Under-damped spring: 0 -> 1 with ~23% overshoot, peaking near 3 frames in. */
const pop = (seconds: number) => {
	if (seconds <= 0) {
		return 0;
	}

	const omega = 38;
	const zeta = 0.42;
	const damped = omega * Math.sqrt(1 - zeta * zeta);
	return (
		1 -
		Math.exp(-zeta * omega * seconds) *
			(Math.cos(damped * seconds) + ((zeta * omega) / damped) * Math.sin(damped * seconds))
	);
};

type Pose = {scale: number; x: number; y: number; rotate: number};

const poseAt = (age: number, fps: number, seed: number): Pose => {
	const scale = 0.3 + 0.7 * pop(age / fps);
	// Shake that dies out over the first few frames.
	const kick = Math.exp(-Math.max(0, age) / 2.6);
	const step = Math.floor(Math.max(0, age));
	return {
		scale,
		x: (noise1(seed + step * 3.1) - 0.5) * 34 * kick,
		y: (noise1(seed + step * 5.7 + 9) - 0.5) * 34 * kick,
		rotate: (noise1(seed + step * 7.3 + 4) - 0.5) * 9 * kick,
	};
};

const transformOf = (pose: Pose) =>
	`translate(${pose.x.toFixed(2)}px, ${pose.y.toFixed(2)}px) rotate(${pose.rotate.toFixed(2)}deg) scale(${pose.scale.toFixed(4)})`;

const WordView: React.FC<{word: Word; age: number; seed: number}> = ({word, age, seed}) => {
	const {fps} = useVideoConfig();
	const shown = age >= 0;
	const pose = poseAt(age, fps, seed);

	// Motion blur: while the word is still moving fast, draw it again at
	// earlier sub-frame times and soften it in proportion to its speed.
	const speed = Math.abs(pose.scale - poseAt(age - 0.5, fps, seed).scale);
	const blur = Math.min(9, speed * 26);
	const ghosts = shown && age < 5 ? [0.3, 0.6, 0.9] : [];

	const text: React.CSSProperties = {
		display: 'block',
		color: word.color ?? '#fff',
		textShadow: OUTLINE_SHADOW,
		whiteSpace: 'nowrap',
	};

	return (
		<span
			style={{
				position: 'relative',
				display: 'inline-block',
				margin: '0 0.13em',
				// Highlighted words run larger, and the line makes room for them.
				fontSize: word.color ? '1.12em' : undefined,
				visibility: shown ? 'visible' : 'hidden',
			}}
		>
			{ghosts.map((back, i) => (
				<span
					key={back}
					style={{
						...text,
						position: 'absolute',
						inset: 0,
						opacity: 0.3 - i * 0.09,
						filter: `blur(${(blur * 0.8 + 2).toFixed(1)}px)`,
						transform: transformOf(poseAt(age - back, fps, seed)),
					}}
				>
					{word.text}
				</span>
			))}
			<span
				style={{
					...text,
					position: 'relative',
					filter: blur > 0.3 ? `blur(${blur.toFixed(1)}px)` : undefined,
					transform: transformOf(pose),
				}}
			>
				{word.text}
			</span>
		</span>
	);
};

const CaptionView: React.FC<{caption: Caption; index: number; frame: number}> = ({
	caption,
	index,
	frame,
}) => {
	// Quick blurred lift on the way out, so the next caption cuts in clean.
	const left = caption.endFrame - frame;
	const exit = left <= 2 ? (3 - left) / 3 : 0;

	return (
		<div
			style={{
				position: 'absolute',
				inset: 0,
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
			}}
		>
			<div
				style={{
					display: 'flex',
					flexWrap: 'wrap',
					justifyContent: 'center',
					alignContent: 'center',
					maxWidth: 960,
					fontFamily: FONT_FAMILY,
					fontSize: FONT_SIZE,
					lineHeight: 1.08,
					textTransform: 'uppercase',
					letterSpacing: '0.01em',
					opacity: 1 - exit,
					filter: exit > 0 ? `blur(${(exit * 10).toFixed(1)}px)` : undefined,
					transform: `translateY(${(-exit * 46).toFixed(1)}px) scale(${(1 + exit * 0.08).toFixed(3)})`,
				}}
			>
				{caption.words.map((word, i) => (
					<WordView
						key={i}
						word={word}
						age={frame - word.startFrame}
						seed={index * 17 + i * 5}
					/>
				))}
			</div>
		</div>
	);
};

export const Captions: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const index = scene.captions.findIndex((c) => frame >= c.startFrame && frame < c.endFrame);
	if (index === -1) {
		return null;
	}

	return <CaptionView caption={scene.captions[index]} index={index} frame={frame} />;
};
