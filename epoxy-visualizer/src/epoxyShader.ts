/** Most strokes the shader composites in one frame. */
export const MAX_STROKES = 64;

export const VERTEX_SHADER = `#version 300 es
in vec2 aPos;
void main() {
	gl_Position = vec4(aPos, 0.0, 1.0);
}
`;

/**
 * Every stroke is a layer of liquid poured over the ones before it.
 * Per pixel we find how deep inside each layer we are, build up a height
 * field from that (so every layer has a thick, lit rim), then shade the top
 * surface as warped marble under a hard light.
 *
 * uA: x, y, dirX, dirY       uB: size, halfWidth, progress, seed
 * uC: kind (0 drag, 1 splash), age on the liquid clock
 */
export const FRAGMENT_SHADER = `#version 300 es
precision highp float;

out vec4 outColor;

uniform vec2 uRes;
uniform float uBleed;
uniform float uTime;
uniform float uAmp;
uniform int uCount;
uniform vec4 uA[${MAX_STROKES}];
uniform vec4 uB[${MAX_STROKES}];
uniform vec4 uC[${MAX_STROKES}];

float hash(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(
		mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
		mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
		u.y
	);
}

float fbm(vec2 p, int octaves) {
	float amp = 0.5;
	float sum = 0.0;
	float total = 0.0;
	mat2 rot = mat2(1.6, 1.2, -1.2, 1.6);
	for (int i = 0; i < octaves; i++) {
		sum += amp * vnoise(p);
		total += amp;
		p = rot * p;
		amp *= 0.5;
	}
	return sum / total;
}

const float BEVEL = 22.0;
const float FAR = -100.0;

void main() {
	vec2 p = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y) - uBleed;

	float height = 0.0;
	float depth = FAR;
	float shadow = 0.0;
	float bead = 0.0;
	float tone = 0.5;
	float edge = 1000.0;
	vec2 coord = p;

	for (int i = 0; i < ${MAX_STROKES}; i++) {
		if (i >= uCount) break;
		vec4 A = uA[i];
		vec4 B = uB[i];
		float kind = uC[i].x;
		float age = uC[i].y;
		float prog = B.z;
		float seed = B.w;
		float settle = 1.0 - exp(-age * 0.35);

		float d = FAR;
		float ridge = 0.0;
		vec2 local = p;

		if (kind < 0.5) {
			// Squeegee drag: a band swept along its direction.
			vec2 dir = A.zw;
			vec2 q = p - A.xy;
			float u = dot(q, dir);
			float v = dot(q, vec2(-dir.y, dir.x));
			float halfW = B.y * (1.0 + 0.07 * settle) + 10.0 * settle;
			float front = prog * B.x;

			if (abs(v) < halfW * 1.2 + 40.0 && u > -110.0 && u < front + 90.0) {
				float started = smoothstep(0.0, 0.06, prog);
				float side = halfW * (1.0 + 0.16 * (vnoise(vec2(u * 0.0035, seed * 13.1 + age * 0.03)) - 0.5))
					+ 26.0 * (vnoise(vec2(u * 0.02 + seed, seed * 3.7)) - 0.5);
				float lead = front
					+ started * (70.0 * (vnoise(vec2(v * 0.009, seed * 5.3 + age * 0.05)) - 0.5)
					+ 22.0 * (vnoise(vec2(v * 0.05, seed * 9.1)) - 0.5))
					- v * v / (halfW * 7.0);
				float tail = -70.0 * vnoise(vec2(v * 0.012, seed * 2.9)) + v * v / (halfW * 3.0);

				float dSide = side - abs(v);
				float dLead = lead - u;
				float dTail = u - tail;
				d = min(dSide, min(dLead, dTail));

				// Liquid piles up in front of the blade while it is moving.
				ridge = (1.0 - smoothstep(0.93, 1.0, prog))
					* exp(-pow(dLead / 22.0, 2.0)) * step(0.0, dSide);
				// Stretch the marble along the drag so it reads as pulled paint.
				local = vec2(u * 0.42, v) + seed * vec2(311.7, 127.1);
			}
		} else {
			// Splash: a blob that bursts outward into fingers and droplets.
			vec2 q = p - A.xy;
			float r = length(q);
			float R = B.x;

			if (r < R * 2.2) {
				float grow = 1.0 - pow(1.0 - prog, 3.0);
				vec2 around = q / max(r, 0.001);
				float lobes = vnoise(around * 1.8 + seed * 7.3);
				float fingers = pow(vnoise(around * 5.0 + seed * 3.1), 2.0);
				float radius = R * grow * (0.55 + 0.4 * lobes + 0.75 * fingers * grow) + 8.0 * settle;
				d = radius - r;

				for (int j = 0; j < 7; j++) {
					float fj = float(j);
					float ang = 6.2832 * hash(vec2(seed, fj * 1.7));
					float dist = R * (1.0 + 0.9 * hash(vec2(seed + 3.0, fj))) * mix(0.55, 1.0, grow);
					float size = R * (0.035 + 0.075 * hash(vec2(seed + 9.0, fj)));
					float landed = smoothstep(0.15 + 0.04 * fj, 0.5 + 0.05 * fj, prog);
					vec2 centre = A.xy + vec2(cos(ang), sin(ang)) * dist;
					d = max(d, size * landed - length(p - centre));
				}

				ridge = (1.0 - smoothstep(0.7, 1.0, prog)) * exp(-pow(d / 26.0, 2.0)) * step(0.0, d);
				local = q * 0.8 + seed * vec2(311.7, 127.1);
			}
		}

		if (d > -26.0) {
			float inside = smoothstep(0.0, 1.5, d);
			float layer = smoothstep(0.0, BEVEL, d);
			// A soft dark halo where this layer's edge sits on older liquid.
			shadow = max(shadow, smoothstep(-26.0, 0.0, d)) * (1.0 - inside);
			height = height * (1.0 - 0.65 * layer) + layer + ridge * 1.4;
			bead = bead * (1.0 - inside) + ridge;
			coord = mix(coord, local, inside);
			tone = mix(tone, hash(vec2(seed, 4.2)), inside);
			depth = max(depth, d);
			edge = min(edge, abs(d));
		}
	}

	// Slope of the layered height field, taken before any early exit.
	vec2 slope = vec2(dFdx(height), -dFdy(height));
	float alpha = smoothstep(0.0, 1.5, depth);
	if (alpha <= 0.0) {
		outColor = vec4(0.0, 0.0, 0.0, 1.0);
		return;
	}

	// Marble: noise warped by noise warped by noise, drifting on the liquid clock.
	vec2 c = coord * 0.0012;
	float t = uTime * 0.035;
	vec2 w1 = vec2(
		fbm(c * 1.6 + vec2(0.0, t), 4),
		fbm(c * 1.6 + vec2(5.2, 1.3 - t), 4)
	);
	vec2 w2 = vec2(
		fbm(c * 1.2 + 3.2 * w1 + vec2(1.7, 9.2), 4),
		fbm(c * 1.2 + 3.2 * w1 + vec2(8.3, 2.8) + t * 0.5, 4)
	);
	// Few octaves on the last pass keeps the surface smooth and liquid, not gritty.
	float f = fbm(c * 1.4 + 3.0 * w2, 3);

	// White body, silver pools, thin graphite veins and wider gunmetal ribbons.
	float darkVein = 1.0 - smoothstep(0.004, 0.02, abs(f - 0.47));
	float ribbon = 1.0 - smoothstep(0.012, 0.05, abs(f - 0.6));
	float pearlVein = 1.0 - smoothstep(0.0, 0.05, abs(w1.x - 0.5));
	float pool = smoothstep(0.5, 0.85, w2.y);

	vec3 col = mix(vec3(0.88, 0.89, 0.91), vec3(1.0, 1.0, 0.995), smoothstep(0.3, 0.62, f));
	col = mix(col, vec3(0.6, 0.61, 0.65), pool * 0.5);
	col = mix(col, vec3(0.2, 0.21, 0.24), ribbon * 0.8);
	col = mix(col, vec3(0.03, 0.03, 0.04), darkVein * 0.92);
	col = mix(col, vec3(1.0), pearlVein * 0.55 * (1.0 - darkVein) * (1.0 - ribbon));
	col *= 0.95 + 0.08 * tone;

	// Hard light from the top left: lit rims, dark trailing edges, tight speculars.
	// The marble only adds relief away from layer edges, where its pattern jumps.
	float body = smoothstep(3.0, 9.0, edge);
	vec2 g = slope * 40.0 + vec2(dFdx(f), -dFdy(f)) * 16.0 * body;
	vec3 n = normalize(vec3(-g, 1.0));
	vec3 light = normalize(vec3(-0.45, -0.6, 0.66));
	vec3 halfway = normalize(light + vec3(0.0, 0.0, 1.0));
	float diffuse = dot(n, light) - light.z;
	float spec = pow(max(dot(n, halfway), 0.0), 70.0);
	float sheen = pow(0.5 + 0.5 * sin(f * 11.0 + w1.x * 6.0 + uTime * 0.4), 8.0);

	col = col * (0.96 + 0.75 * diffuse) + spec * 1.1 + sheen * 0.06 + bead * 0.2;
	col *= 1.0 - 0.62 * shadow * shadow;
	col *= 1.0 + 0.05 * uAmp;

	outColor = vec4(clamp(col, 0.0, 1.0) * alpha, 1.0);
}
`;
