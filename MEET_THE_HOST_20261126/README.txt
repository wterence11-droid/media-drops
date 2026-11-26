MEET THE HOST - JOB 4 (Claude Duet, Thu Nov 26 2026). BUILD ONLY. Nothing booked, nothing swapped.

Scripts: comms/open/production-week/20261123T0002Z (ARCHITECT); DOT words PASS 20261123T0004Z.

STATUS: PICTURE LOCKED, VOICE NOT YET IN THE FILE.
Both voice takes were made in ElevenLabs and read the passed words exactly (checked with an
ElevenLabs Scribe transcript of each take). The build computer cannot download files from
ElevenLabs (its network blocks that host), so the voice could not be put into the mp4 here.
One step finishes it on any machine that can download the two takes:

  python3 MUX_meet_the_host_20261126.py . rhonda.mp3 dottie.mp3 <out>

That writes SEB/20261127narrated/SEB-HOST-01.mp4, DK/20261127narrated/DK-HOST-01.mp4 and
QA_REPORT_meet_the_host_20261126.csv (sha256, seconds, card seconds, loudness, peak,
words-equal-spec), and refuses to finish if any check fails. Tested here with stand-in audio:
-16.2 / -16.4 LUFS, both under -1.5 dBFS peak, 1080x1920, 30 fps, h264, 9.000 s.

Which takes (owner's ElevenLabs history, Nov 26, about 9:38-9:40 AM ET):
  SEB-HOST-01  "I'm Agent Rhonda Lyle. ..."  7.15 s, multilingual v2
  DK-HOST-01   "I'm Dottie Keys. ..."        8.59 s, turbo v2.5  (NOT the 10.73 s take: too long for 9 s)
  Voice names: Drive copy only.

FILES
  SEB-HOST-01_picture.mp4   Agent Rhonda Lyle, Side-Eye Bureau, 9.000 s, no sound
  DK-HOST-01_picture.mp4    Dottie Keys, 9.000 s, no sound
  BUILD_meet_the_host_20261126.py   how the pictures were made (sources and timings inside)
  MUX_meet_the_host_20261126.py     adds the voice and runs every check
  build_report.json         card text and timings; captions joined == spoken words: true, true

WHAT IS ON SCREEN
  Frame one: the title exactly as the script (AGENT RHONDA LYLE. SIDE-EYE BUREAU. /
  DOTTIE KEYS. OFFICE MANAGER. FICTIONAL.) over her face, plus the first caption.
  Captions: exactly the spoken words, hard cuts, timed to the take. Each card stays until the
  next line starts; the last card stays to the end.
  Rhonda: her own brand footage, mouth still, the desk radio carries her voice (as in the
  brand's earlier clips); last beat she looks back down at the file.
  Dottie: her brand portrait held with a slow push-in (mouth closed; the old portraits are
  lip-synced to other lines, so they were not reused while she speaks); on "go back to your
  inbox" it cuts to her phone screen. No lip sync was made (that would spend video credits).
  Brand disclosure lines from the original pictures stay on screen.

Voice credits used: 369 ElevenLabs characters (121 Rhonda, 124 + 124 Dottie). Transcripts cost 0.
