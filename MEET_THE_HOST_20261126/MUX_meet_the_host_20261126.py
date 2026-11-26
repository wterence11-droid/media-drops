#!/usr/bin/env python3
"""MEET THE HOST - add the voice to the picture-locked clips and run the sound and spec checks.

Needs: python3 and ffmpeg/ffprobe on PATH. Run it where the two voice takes can be downloaded
(the build computer could not reach ElevenLabs' file host).

Voice takes (in the owner's ElevenLabs history, Thu Nov 26 2026, generated 14:38-14:40 UTC):
  SEB-HOST-01  "I'm Agent Rhonda Lyle. ..."  model multilingual v2, 7.15 s   -> rhonda.mp3
  DK-HOST-01   "I'm Dottie Keys. ..."        model turbo v2.5,     8.59 s   -> dottie.mp3
  (An earlier 10.73 s Dottie take is too long for 9 s and is NOT used.)
  Voice names are in the Drive copy, not on the board.

Usage:  python3 MUX_meet_the_host_20261126.py <dir with *_picture.mp4> <rhonda.mp3> <dottie.mp3> <out dir>
Writes: <out>/SEB/20261127narrated/SEB-HOST-01.mp4, <out>/DK/20261127narrated/DK-HOST-01.mp4,
        <out>/QA_REPORT_meet_the_host_20261126.csv
Targets: about -16 LUFS integrated, true peak under -1.5 dBFS, 1080x1920, 30 fps, h264, 9.000 s.
"""
import sys, os, json, subprocess, hashlib, re, csv

CLIPS = {
    "SEB-HOST-01": {"brand": "SEB", "offset": 0.40, "voice_len": 7.15,
        "cards": [("I'm Agent Rhonda Lyle.", 0.00, 1.75), ("I'm fictional.", 1.75, 2.83),
                  ("I file what you thought nobody saw.", 2.83, 4.65), ("Stay or scroll.", 4.65, 5.81),
                  ("It goes in the file either way.", 5.81, 9.00)],
        "spec": "I'm Agent Rhonda Lyle. I'm fictional. I file what you thought nobody saw. Stay or scroll. It goes in the file either way."},
    "DK-HOST-01": {"brand": "DK", "offset": 0.15, "voice_len": 8.59,
        "cards": [("I'm Dottie Keys.", 0.00, 1.73), ("Fictional AI office manager.", 1.73, 3.85),
                  ("I show agents how to make AI do the paperwork.", 3.85, 6.68),
                  ("Stay, or go back to your inbox.", 6.68, 9.00)],
        "spec": "I'm Dottie Keys. Fictional AI office manager. I show agents how to make AI do the paperwork. Stay, or go back to your inbox."},
}
DUR = 9.0

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True)

def measure(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1))
    p = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1))
    return i, p

def mux(pic, voice, cfg, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ms = int(round(cfg["offset"] * 1000))
    base = f"aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms},apad,atrim=0:{DUR}"
    # pass 1: measure
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", voice, "-af",
                        base + ",loudnorm=I=-16:TP=-2:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
    if "inf" in str(js["input_i"]):
        sys.exit(f"{voice}: no audible sound found - wrong or empty file?")
    ln = (f"loudnorm=I=-16:TP=-2:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    af = base + "," + ln + ",aresample=48000,alimiter=limit=0.79:attack=2:release=40:level=false,atrim=0:" + str(DUR)
    run(["ffmpeg", "-v", "error", "-y", "-i", pic, "-i", voice, "-filter_complex", f"[1:a]{af}[a]",
         "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-t", str(DUR), "-movflags", "+faststart", out])

def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate",
             "-show_entries", "format=duration", "-of", "json", path])
    return json.loads(r.stdout)

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def main():
    picdir, rh, dk, outdir = sys.argv[1:5]
    voices = {"SEB-HOST-01": rh, "DK-HOST-01": dk}
    rows = []
    for cid, cfg in CLIPS.items():
        out = os.path.join(outdir, cfg["brand"], "20261127narrated", f"{cid}.mp4")
        mux(os.path.join(picdir, f"{cid}_picture.mp4"), voices[cid], cfg, out)
        i, p = measure(out)
        pr = probe(out); v = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
        secs = float(pr["format"]["duration"])
        words_eq = " ".join(c[0] for c in cfg["cards"]) == cfg["spec"]
        spec_ok = (v["codec_name"] == "h264" and v["width"] == 1080 and v["height"] == 1920
                   and v["r_frame_rate"] == "30/1" and abs(secs - DUR) < 0.05)
        sound_ok = -17.0 <= i <= -15.0 and p < -1.5
        rows.append({"id": cid, "file": os.path.relpath(out, outdir), "sha256": sha(out), "seconds": f"{secs:.3f}",
                     "card_seconds": ";".join(f"{c[2] - c[1]:.2f}" for c in cfg["cards"]),
                     "voice_start_s": cfg["offset"], "voice_end_s": round(cfg["offset"] + cfg["voice_len"], 2),
                     "loudness_lufs": i, "peak_dbfs": p, "words_equal_spec": "yes" if words_eq else "no",
                     "spec_1080x1920_30fps_h264": "yes" if spec_ok else "no",
                     "sound_target_met": "yes" if sound_ok else "no"})
        print(rows[-1])
    qa = os.path.join(outdir, "QA_REPORT_meet_the_host_20261126.csv")
    with open(qa, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("QA:", qa)
    if any(r["sound_target_met"] != "yes" or r["spec_1080x1920_30fps_h264"] != "yes" or r["words_equal_spec"] != "yes" for r in rows):
        sys.exit("A check failed - do not hand these off.")

if __name__ == "__main__":
    main()
