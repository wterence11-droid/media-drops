# CTS-001 build (CLAUDE-DUET), as run in the voice service's sandbox on Fri Nov 27 2026.
# Inputs in /workspace/in: card PNGs from CIR/20261128cts/cards (commit 6d8a0b2) and six voice takes a1..a6.mp3
# (one per card, voice = Caught in Retrograde narrator, model eleven_v4; voice name in the private Drive copy).
import json, subprocess, hashlib, os
import numpy as np, soundfile as sf, librosa
IN, OUT, TMP = "/workspace/in", os.environ.get("OUT", "/workspace/out"), os.environ.get("TMP", "/workspace/tmp")
os.makedirs(TMP, exist_ok=True); os.makedirs(OUT, exist_ok=True)
SR, FPS, TAIL = 48000, 30, 0.35
CARDS = [("1_hook", "a1.mp3", ["c1_hook.png"]),
         ("2_roll", "a2.mp3", [f"c2_roll{k}.png" for k in range(1, 7)]),
         ("2b_bridge", "a3.mp3", ["c2b_bridge.png"]),
         ("3_gemini", "a4.mp3", ["c3_gemini.png"]),
         ("4_leo", "a5.mp3", ["c4_leo.png"]),
         ("5_end", "a6.mp3", ["c5_end.png"])]
audio, concat, qa = [], [], {"cards": []}
for cid, take, imgs in CARDS:
    y, _ = librosa.load(f"{IN}/{take}", sr=SR, mono=True)
    nfr = int(np.ceil((len(y) / SR + TAIL) * FPS))           # card stays up until the voice ends + 0.35 s
    seg = np.zeros(int(round(nfr / FPS * SR)), dtype=np.float32); seg[:len(y)] = y
    audio.append(seg)
    if len(imgs) == 1:
        concat.append((imgs[0], nfr)); rev = None
    else:                                                     # roll: each name appears as the voice says it
        merged = []
        for s, e in librosa.effects.split(y, top_db=35, frame_length=1024, hop_length=256):
            if merged and (s - merged[-1][1]) / SR < 0.12: merged[-1][1] = e
            else: merged.append([s, e])
        if len(merged) == len(imgs):
            starts = [0] + [int(round(m[0] / SR * FPS)) for m in merged[1:]]; rev = "voice onsets"
        else:
            starts = [int(round(i * nfr / len(imgs))) for i in range(len(imgs))]; rev = "equal steps"
        b = starts + [nfr]
        for i, im in enumerate(imgs): concat.append((im, b[i + 1] - b[i]))
    qa["cards"].append({"card": cid, "take_seconds": round(len(y) / SR, 3), "card_seconds": round(nfr / FPS, 3), "frames": nfr, "roll_reveal": rev})
mix = np.concatenate(audio)
sf.write(f"{TMP}/mix_raw.wav", mix.astype(np.float32), SR, subtype="PCM_24")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{TMP}/mix_raw.wav", "-af", "loudnorm=I=-15:TP=-2.0:LRA=11", "-ar", str(SR), "-c:a", "pcm_s24le", f"{TMP}/mix_n.wav"], check=True)
mx, _ = sf.read(f"{TMP}/mix_n.wav", dtype="float32")
mx = mx[:len(mix)] if len(mx) >= len(mix) else np.pad(mx, (0, len(mix) - len(mx)))
sf.write(f"{TMP}/mix.wav", mx, SR, subtype="PCM_24")
with open(f"{TMP}/list.txt", "w") as f:
    for im, n in concat: f.write(f"file '{IN}/{im}'\nduration {n / FPS:.6f}\n")
    f.write(f"file '{IN}/{concat[-1][0]}'\n")
total = sum(n for _, n in concat); dst = f"{OUT}/CTS-001.mp4"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{TMP}/list.txt",
    "-vf", "fps=30,scale=1080:1920,format=yuv420p", "-frames:v", str(total), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-an", f"{TMP}/pic.mp4"], check=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{TMP}/pic.mp4", "-i", f"{TMP}/mix.wav", "-map", "0:v:0", "-map", "1:a:0",
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", dst], check=True)
qa.update({"file": "CTS-001.mp4", "sha256": hashlib.sha256(open(dst, "rb").read()).hexdigest(), "frames": total})
print(json.dumps(qa, indent=1))
