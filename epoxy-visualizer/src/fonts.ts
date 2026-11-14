import {staticFile} from 'remotion';

export const FONT_FAMILY = 'Anton, Impact, "Arial Narrow Bold", sans-serif';

let loading: Promise<void> | null = null;

/** Anton ships in public/fonts, so renders never depend on a font CDN. */
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
