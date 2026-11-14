import React, {useLayoutEffect, useRef} from 'react';
import {useCurrentFrame} from 'remotion';
import {HEIGHT, WIDTH} from './config';

const GRAIN_W = WIDTH / 2;
const GRAIN_H = HEIGHT / 2;

/** Film grain, reseeded from the frame number so renders are repeatable. */
export const Grain: React.FC<{strength: number}> = ({strength}) => {
	const frame = useCurrentFrame();
	const ref = useRef<HTMLCanvasElement>(null);

	useLayoutEffect(() => {
		const ctx = ref.current?.getContext('2d');
		if (!ctx) {
			return;
		}

		const image = ctx.createImageData(GRAIN_W, GRAIN_H);
		const pixels = new Uint32Array(image.data.buffer);
		let state = (frame + 1) * 0x9e3779b1;
		for (let i = 0; i < pixels.length; i++) {
			state ^= state << 13;
			state ^= state >>> 17;
			state ^= state << 5;
			const v = state & 0xff;
			// Little-endian ABGR: grey value, alpha set by how far it is from mid-grey.
			const alpha = Math.abs(v - 128) * 0.5;
			pixels[i] = (alpha << 24) | (v << 16) | (v << 8) | v;
		}

		ctx.putImageData(image, 0, 0);
	}, [frame]);

	return (
		<canvas
			ref={ref}
			width={GRAIN_W}
			height={GRAIN_H}
			style={{
				position: 'absolute',
				inset: 0,
				width: WIDTH,
				height: HEIGHT,
				opacity: strength,
				pointerEvents: 'none',
			}}
		/>
	);
};
