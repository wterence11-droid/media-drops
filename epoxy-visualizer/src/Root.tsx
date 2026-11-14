import React from 'react';
import {Composition} from 'remotion';
import {config} from './config';
import {buildScene} from './scene';
import {loadEnvelope, Visualizer} from './Visualizer';

export const Root: React.FC = () => {
	return (
		<Composition
			id="Visualizer"
			component={Visualizer}
			width={config.resolution.width}
			height={config.resolution.height}
			fps={config.fps}
			durationInFrames={config.fps * 30}
			// Length follows the captions and the audio file, whichever runs longer.
			calculateMetadata={async () => {
				const envelope = await loadEnvelope(config.fps);
				return {durationInFrames: buildScene(config, envelope, config.fps).durationInFrames};
			}}
		/>
	);
};
