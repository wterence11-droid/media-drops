import React from 'react';
import {Composition} from 'remotion';
import {config, FPS, HEIGHT, WIDTH} from './config';
import {buildScene} from './scene';
import {loadEnvelope, Visualizer} from './Visualizer';

export const Root: React.FC = () => {
	return (
		<Composition
			id="Visualizer"
			component={Visualizer}
			width={WIDTH}
			height={HEIGHT}
			fps={FPS}
			durationInFrames={FPS * 30}
			// Length follows the captions and the audio file, whichever runs longer.
			calculateMetadata={async () => {
				const envelope = await loadEnvelope(FPS);
				return {durationInFrames: buildScene(config, envelope, FPS).durationInFrames};
			}}
		/>
	);
};
