import {staticFile} from 'remotion';

let loading: Promise<void> | null = null;

/** Anton ships in public/fonts, so the "Anton" in config.json styles never depends on a font CDN. */
export const loadFonts = (): Promise<void> => {
	if (!loading) {
		const face = new FontFace(
			'Anton',
			`url(${staticFile('fonts/Anton-Regular.woff2')}) format('woff2')`,
		);
		loading = face.load().then((loaded) => {
			document.fonts.add(loaded);
		});
	}

	return loading;
};
