#!/usr/bin/env python3
"""Narrated versions of the booked loops (CLAUDE-DUET, Thu Nov 26 2026). Job 1 of ARCHITECT 20261126T1425Z.

Picture: the booked file's own frames, untouched (label, character, footer, source chip, words).
Each card (one on-screen text state) is held from a stretch of the booked file where that card is fully
on, played slower so the card stays up from the cut until the voice has finished plus a tail. Cards are
never shorter than in the booked file. Fades between cards are dropped: hard cuts only.
Sound: one narration take per card (the narrator reads that card's on-screen words), voice starts LEAD s
after each cut and ends before the next cut; the booked soft bed stays quietly under the voice.
Whole mix brought to -16 LUFS with a limiter so the true peak stays under -1.5 dBFS.

Usage: build_narrated.py <jobs.json> <store_dir> <out_dir>
  jobs.json: [{id, brand, words[], prompts[], plateau[[f0,f1],...], min[s,...], src_sha256}]
  store_dir: SRC_<id>.mp4 and <id>_c<k>.mp3
"""
import sys, os, json, subprocess, hashlib, re
import numpy as np
import soundfile as sf
import pyloudnorm as pyln

W, H, FPS, SR = 1080, 1920, 30, 48000
CALM = {"WTCD", "WK", "CU", "RR"}
LEAD = 0.20
BED_GAIN_DB = -8.0
TARGET = -16.0
CEIL = 10 ** (-3.0 / 20)


def sh(cmd):
    return subprocess.run(cmd, check=True, capture_output=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_audio(p):
    raw = sh(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def trim(x, thr_db=-45.0, pad=0.03):
    thr = 10 ** (thr_db / 20)
    win = int(0.01 * SR)
    env = np.sqrt(np.convolve(x ** 2, np.ones(win) / win, mode="same"))
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(pad * SR)); b = min(len(x), idx[-1] + int(pad * SR))
    y = x[a:b].copy()
    f = int(0.008 * SR)
    y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
    return y


def loop_bed(bed, n):
    xf = int(0.5 * SR)
    out = bed.copy()
    while len(out) < n:
        r = np.linspace(0, 1, xf)
        out = np.concatenate([out[:-xf], out[-xf:] * (1 - r) + bed[:xf] * r, bed[xf:]])
    return out[:n]


def limiter(x, ceil):
    """Look-ahead peak limiter: gain never lets |x| exceed ceil; 5 ms attack, 80 ms release."""
    a = np.abs(x)
    need = np.minimum(1.0, ceil / np.maximum(a, 1e-9))
    look = int(0.005 * SR)
    # min over look-ahead window
    from numpy.lib.stride_tricks import sliding_window_view
    padded = np.concatenate([need, np.ones(look)])
    g = sliding_window_view(padded, look + 1).min(axis=1)[: len(x)]
    rel = np.exp(-1.0 / (0.08 * SR))
    out = np.empty_like(g); cur = 1.0
    for i in range(len(g)):
        cur = g[i] if g[i] < cur else min(g[i], cur * rel + (1 - rel))
        out[i] = cur
    # smooth attack
    k = np.ones(look) / look
    out = np.minimum(out, np.convolve(out, k, mode="same"))
    return x * out


def build(job, store, outdir, cache):
    jid, brand = job["id"], job["brand"]
    src = os.path.join(store, f"SRC_{jid}.mp4")
    got = sha(src)
    assert got == job["src_sha256"], f"{jid}: source hash {got} != booked {job['src_sha256']}"
    # words check: narration text (minus delivery tags) == on-screen words from the spec, card by card
    narr = [re.sub(r"^(\[[^\]]+\]\s*)+", "", p) for p in job["prompts"]]
    words_ok = narr == job["words"]
    # voice takes
    takes = [trim(load_audio(os.path.join(store, f"{jid}_c{k}.mp3"))) for k in range(len(job["words"]))]
    tail = 0.75 if brand in CALM else 0.5
    n_cards = len(takes)
    frames_per = []
    for k, t in enumerate(takes):
        need = LEAD + len(t) / SR + tail + (0.35 if k == n_cards - 1 else 0.0)
        d = max(job["min"][k], need)
        frames_per.append(int(np.ceil(d * FPS)))
    nout = sum(frames_per)
    # source frames to a memmap on disk
    raw = os.path.join(cache, f"{jid}.rgb")
    sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", raw])
    fr = np.memmap(raw, np.uint8, "r").reshape(-1, H, W, 3)
    # picture
    vpath = os.path.join(cache, f"{jid}_v.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS), vpath], stdin=subprocess.PIPE)
    cards = []
    j0 = 0
    for k, n in enumerate(frames_per):
        p0, p1 = job["plateau"][k]
        for i in range(n):
            s = p0 + (p1 - p0) * (i / max(1, n - 1))
            a = int(np.floor(s)); f = s - a; b = min(a + 1, p1)
            if f < 1e-3 or a == b:
                img = fr[a]
            else:
                img = (fr[a].astype(np.float32) * (1 - f) + fr[b].astype(np.float32) * f + 0.5).astype(np.uint8)
            enc.stdin.write(np.ascontiguousarray(img).tobytes())
        cards.append(dict(card=k + 1, first_frame=j0, last_frame=j0 + n - 1, seconds=round(n / FPS, 3),
                          source_frames=[p0, p1], voice_seconds=round(len(takes[k]) / SR, 3), words=job["words"][k]))
        j0 += n
    enc.stdin.close(); enc.wait()
    del fr; os.remove(raw)
    # sound
    total = int(round(nout / FPS * SR))
    bed = loop_bed(load_audio(src), total) * 10 ** (BED_GAIN_DB / 20)
    voice = np.zeros(total)
    for k, t in enumerate(takes):
        st = int(round((cards[k]["first_frame"] / FPS + LEAD) * SR))
        end_lim = int(round((cards[k]["last_frame"] + 1) / FPS * SR))
        assert st + len(t) <= end_lim, f"{jid} card {k+1}: voice runs past the cut"
        voice[st:st + len(t)] += t
    mix = voice + bed
    fade = int(0.02 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
    meter = pyln.Meter(SR)
    for _ in range(4):
        lu = meter.integrated_loudness(mix)
        mix = mix * 10 ** ((TARGET - lu) / 20)
        mix = limiter(mix, CEIL)
    wav = os.path.join(cache, f"{jid}.wav")
    sf.write(wav, mix.astype(np.float32), SR, subtype="FLOAT")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{jid}.mp4")
    sh(["ffmpeg", "-v", "error", "-y", "-i", vpath, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-ac", "1", "-shortest", "-movflags", "+faststart", out])
    os.remove(vpath); os.remove(wav)
    # measure the finished file
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); TP = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    pr = json.loads(sh(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", out]).stdout)
    v = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
    fmt_ok = (v["codec_name"] == "h264" and v["width"] == W and v["height"] == H and v["r_frame_rate"] == "30/1"
              and int(v["nb_frames"]) == nout)
    secs = float(pr["format"]["duration"])
    return dict(id=jid, brand=brand, sha256=sha(out), seconds=round(nout / FPS, 3), container_seconds=round(secs, 3),
                frames=nout, card_seconds="|".join(f"{c['seconds']:.2f}" for c in cards), lufs=I, true_peak_dbfs=TP,
                words_equal_spec="yes" if words_ok else "no", format_ok=fmt_ok, source_sha256=got, cards=cards)


def main():
    jobs = json.load(open(sys.argv[1])); store, outdir = sys.argv[2], sys.argv[3]
    cache = os.environ.get("TMP", "/tmp"); os.makedirs(cache, exist_ok=True)
    only = set(sys.argv[4:])
    for job in jobs:
        if only and job["id"] not in only:
            continue
        rep = build(job, store, outdir, cache)
        json.dump(rep, open(os.path.join(store, f"{job['id']}.qa.json"), "w"), indent=1)
        print(json.dumps({k: rep[k] for k in rep if k != "cards"}), flush=True)


if __name__ == "__main__":
    main()
