import React, {useLayoutEffect, useRef} from 'react';
import {useCurrentFrame} from 'remotion';
import {HEIGHT, WIDTH} from './config';
import {FRAGMENT_SHADER, MAX_STROKES, VERTEX_SHADER} from './epoxyShader';
import {BLEED, strokeProgress, type Scene} from './scene';

type GlState = {
	gl: WebGL2RenderingContext;
	uniforms: Record<string, WebGLUniformLocation | null>;
};

const compile = (gl: WebGL2RenderingContext, type: number, source: string) => {
	const shader = gl.createShader(type)!;
	gl.shaderSource(shader, source);
	gl.compileShader(shader);
	if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
		throw new Error(`Epoxy shader failed to compile: ${gl.getShaderInfoLog(shader)}`);
	}

	return shader;
};

const init = (canvas: HTMLCanvasElement): GlState => {
	const gl = canvas.getContext('webgl2', {
		alpha: false,
		antialias: false,
		preserveDrawingBuffer: true,
	});
	if (!gl) {
		throw new Error(
			'WebGL2 is not available. When rendering, pass --gl=angle (GPU) or --gl=swangle (no GPU).',
		);
	}

	const program = gl.createProgram()!;
	gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER));
	gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER));
	gl.linkProgram(program);
	if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
		throw new Error(`Epoxy shader failed to link: ${gl.getProgramInfoLog(program)}`);
	}

	gl.useProgram(program);

	// One triangle that covers the whole canvas.
	gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
	gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
	const aPos = gl.getAttribLocation(program, 'aPos');
	gl.enableVertexAttribArray(aPos);
	gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

	const uniforms: GlState['uniforms'] = {};
	for (const name of ['uRes', 'uBleed', 'uTime', 'uAmp', 'uCount', 'uA', 'uB', 'uC']) {
		uniforms[name] = gl.getUniformLocation(program, name);
	}

	return {gl, uniforms};
};

const a = new Float32Array(MAX_STROKES * 4);
const b = new Float32Array(MAX_STROKES * 4);
const c = new Float32Array(MAX_STROKES * 4);

/** The liquid layer. A pure function of the frame, so any frame can render in any order. */
export const EpoxyCanvas: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const canvasRef = useRef<HTMLCanvasElement>(null);
	const stateRef = useRef<GlState | null>(null);

	useLayoutEffect(() => {
		const canvas = canvasRef.current;
		if (!canvas) {
			return;
		}

		if (!stateRef.current || stateRef.current.gl.isContextLost()) {
			stateRef.current = init(canvas);
		}

		const {gl, uniforms} = stateRef.current;
		const f = Math.max(0, Math.min(scene.durationInFrames - 1, frame));

		// Only strokes that have started, newest last. If there are ever more
		// than the shader holds, the oldest (long since buried) are dropped.
		const live = scene.strokes.filter((s) => s.startFrame < f).slice(-MAX_STROKES);
		live.forEach((s, i) => {
			const x = strokeProgress(scene, s, f);
			a.set([s.x, s.y, s.dirX, s.dirY], i * 4);
			b.set(
				[s.size, s.halfWidth, s.kind === 'drag' ? 1 - Math.pow(1 - x, 1.7) : x, s.seed],
				i * 4,
			);
			c.set([s.kind === 'drag' ? 0 : 1, scene.clock[f] - scene.clock[s.startFrame], 0, 0], i * 4);
		});

		gl.viewport(0, 0, canvas.width, canvas.height);
		gl.uniform2f(uniforms.uRes, canvas.width, canvas.height);
		gl.uniform1f(uniforms.uBleed, BLEED);
		gl.uniform1f(uniforms.uTime, scene.clock[f]);
		gl.uniform1f(uniforms.uAmp, scene.amp[f]);
		gl.uniform1i(uniforms.uCount, live.length);
		gl.uniform4fv(uniforms.uA, a);
		gl.uniform4fv(uniforms.uB, b);
		gl.uniform4fv(uniforms.uC, c);
		gl.drawArrays(gl.TRIANGLES, 0, 3);
		gl.flush();
	}, [frame, scene]);

	return (
		<canvas
			ref={canvasRef}
			width={WIDTH + BLEED * 2}
			height={HEIGHT + BLEED * 2}
			style={{
				position: 'absolute',
				left: -BLEED,
				top: -BLEED,
				width: WIDTH + BLEED * 2,
				height: HEIGHT + BLEED * 2,
			}}
		/>
	);
};
