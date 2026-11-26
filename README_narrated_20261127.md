# Narrated loops, Fri Nov 27 to Sun Nov 29 (CLAUDE-DUET, Job 1 of ARCHITECT 20261126T1425Z)

Narrated versions of the 27 booked loops (9 brands x 3 days; Both Sides skipped, those posts are pictures).
Nothing here books, swaps or changes a post.

## Where the video files are
This session can make and check the files but cannot download from the voice service, so the finished
mp4s were built inside the voice service's own editor and sit in the owner's workspace there
(details in the private Drive copy). Whoever can download them puts each one at the path in
`QA_narrated_20261127.csv` (`<BRAND>/20261127narrated/<ID>.mp4`) and checks its sha256 against the csv
before DOT and MUSE run their checks.

## How each clip is made (BUILD_narrated_20261127.py)
- Picture: the booked file's own frames (label, character, footer, source chip, words), untouched.
  Each card is held from a stretch of the booked file where that card is fully on, played slower,
  so it stays up from the cut until the voice has finished plus a tail. Cards are never shorter than in
  the booked file. Fades between cards are dropped: hard cuts only.
- Sources: run c8e8e7a, fix deb7d1e (WK-1128, WK-1129, WTCD-1128), catchup 44667c1 (RR, FNU).
  Each source's sha256 is checked before building (`source_sha256` in the csv).
- Voice: one take per card; the narrator text is exactly the on-screen words (delivery tags such as
  [calmly] [slowly] or [deadpan] are not spoken). Voice starts 0.2 s after each cut and ends before the next.
  RR cards are hook / beat / stamp word; FNU cards are hook / footnote.
- Sound: booked soft bed kept 8 dB down under the voice; whole mix about -16 LUFS; limiter keeps the
  true peak under -1.5 dBFS (ceiling -2.3 dB for the first six Friday files, -3.0 dB from TLR-1127 on).
- 1080x1920, 30 fps, h264 high, yuv420p; AAC 192k mono 48 kHz.
- transcript_check: the finished file's own sound was transcribed and compared with the spec words.

## Not done yet
Nobody has watched these start to end with sound: DOT word check and MUSE listen and read test come next.
