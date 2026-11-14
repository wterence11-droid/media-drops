import React, {useMemo} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {BASE_FONT_SIZE, type CaptionStyle} from './config';
import {noise1, type Scene, type Screen, type Word} from './scene';

/** Widest a single word may be before the screen's text is shrunk to fit. */
const MAX_WORD_WIDTH = 900;
const MAX_LINE_WIDTH = 980;

const shadowCache = new Map<string, string>();

// A ring of hard shadows gives a thick outline with round corners
// (-webkit-text-stroke spikes on Anton's sharp joins), plus a hard drop below.
export const outlineShadow = (radius: number, color: string, drop = true) => {
	const key = `${radius}|${color}|${drop}`;
	const cached = shadowCache.get(key);
	if (cached) {
		return cached;
	}

	const parts: string[] = [];
	const steps = 32;
	for (let i = 0; i < steps; i++) {
		const angle = (i / steps) * Math.PI * 2;
		parts.push(
			`${(Math.cos(angle) * radius).toFixed(2)}px ${(Math.sin(angle) * radius).toFixed(2)}px 0 ${color}`,
		);
	}

	if (drop) {
		parts.push(`0 ${radius + 8}px 0 ${color}`);
	}

	const shadow = parts.join(', ');
	shadowCache.set(key, shadow);
	return shadow;
};

let measurer: CanvasRenderingContext2D | null = null;

/** Font size for a screen: the style's scale, shrunk if its widest word would not fit. */
const fitFontSize = (words: Word[], style: CaptionStyle) => {
	const wanted = BASE_FONT_SIZE * style.scale;
	measurer ??= document.createElement('canvas').getContext('2d');
	if (!measurer) {
		return wanted;
	}

	measurer.font = `${wanted}px ${style.font}`;
	const widest = Math.max(...words.map((w) => measurer!.measureText(w.text).width));
	return widest > MAX_WORD_WIDTH ? (wanted * MAX_WORD_WIDTH) / widest : wanted;
};

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

const poseAt = (age: number, fps: number, seed: number, hard: boolean): Pose => {
	const scale = 0.3 + 0.7 * pop(age / fps);
	// Shake that dies out over the first few frames; styles with "shake" hit harder and longer.
	const kick = Math.exp(-Math.max(0, age) / (hard ? 4.5 : 2.6));
	const travel = hard ? 64 : 34;
	const step = Math.floor(Math.max(0, age));
	return {
		scale,
		x: (noise1(seed + step * 3.1) - 0.5) * travel * kick,
		y: (noise1(seed + step * 5.7 + 9) - 0.5) * travel * kick,
		rotate: (noise1(seed + step * 7.3 + 4) - 0.5) * (hard ? 15 : 9) * kick,
	};
};

const transformOf = (pose: Pose) =>
	`translate(${pose.x.toFixed(2)}px, ${pose.y.toFixed(2)}px) rotate(${pose.rotate.toFixed(2)}deg) scale(${pose.scale.toFixed(4)})`;

const WordView: React.FC<{word: Word; style: CaptionStyle; age: number; seed: number}> = ({
	word,
	style,
	age,
	seed,
}) => {
	const {fps} = useVideoConfig();
	const hard = Boolean(style.shake);
	const shown = age >= 0;
	const pose = poseAt(age, fps, seed, hard);

	// Motion blur: while the word is still moving fast, draw it again at
	// earlier sub-frame times and soften it in proportion to its speed.
	const speed = Math.abs(pose.scale - poseAt(age - 0.5, fps, seed, hard).scale);
	const blur = Math.min(9, speed * 26);
	const ghosts = shown && age < 5 ? [0.3, 0.6, 0.9] : [];

	const text: React.CSSProperties = {
		display: 'block',
		color: word.color,
		textShadow: outlineShadow(style.outlineWidth, style.outline),
		whiteSpace: 'nowrap',
	};

	return (
		<span
			style={{
				position: 'relative',
				display: 'inline-block',
				margin: '0 0.13em',
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
						transform: transformOf(poseAt(age - back, fps, seed, hard)),
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

const ScreenView: React.FC<{screen: Screen; index: number; frame: number}> = ({
	screen,
	index,
	frame,
}) => {
	const {style, words} = screen;
	const fontSize = useMemo(() => fitFontSize(words, style), [words, style]);

	// Quick blurred lift on the way out, so the next screen cuts in clean.
	const left = screen.endFrame - frame;
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
					maxWidth: MAX_LINE_WIDTH,
					fontFamily: style.font,
					fontSize,
					lineHeight: 1.08,
					textTransform: 'uppercase',
					letterSpacing: '0.01em',
					opacity: 1 - exit,
					filter: exit > 0 ? `blur(${(exit * 10).toFixed(1)}px)` : undefined,
					transform: `translateY(${(-exit * 46).toFixed(1)}px) scale(${(1 + exit * 0.08).toFixed(3)})`,
				}}
			>
				{words.map((word, i) => (
					<WordView
						key={i}
						word={word}
						style={style}
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
	const index = scene.screens.findIndex((s) => frame >= s.startFrame && frame < s.endFrame);
	if (index === -1) {
		return null;
	}

	return <ScreenView key={index} screen={scene.screens[index]} index={index} frame={frame} />;
};
