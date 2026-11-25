#!/usr/bin/env python3
"""WTCD Thanksgiving clip (WTCD-1126) - TIMING-ONLY replacement. ARCHITECT, Wed Nov 25 2026.
Owner decision A (Sun Nov 22): every approved word stays exactly as it is; the long card 3 is split
into two cards shown one after the other (3a at least 7.0 s, 3b at least 5.5 s); hard cuts between
text cards; font size unchanged.

How: the picture is the booked clip's own picture (brand label, shield, rings, footer, source chip).
The old words are lifted off the ORIGINAL first export (same method as BUILD_20261122fix.py), which
gives 300 word-free frames (one 10 s loop). The loop is played twice, slowed to 12 s per turn, so the
clip is 24.0 s and still loops cleanly. The approved words are then set with hard cuts on the new
timing. Sound: the original soft bed, extended by joining it to itself (no new sound made).

Usage: build.py <orig.mp4> <spec.json> <out.mp4>
"""
import sys, os, json, subprocess, shutil, tempfile, wave
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, N = 1080, 1920, 30, 300
NOUT = 720                                   # 24.0 s
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CY, MAXW = 1113, 910
FULL = {0: 45, 1: 110, 2: 200, 3: 260}
ZB, CT, CB = 1445, 1450, 1545
# new timing, in output frames (first frame, last frame) - hard cuts, no fades
TL = [("title", 0, 68), ("card2", 69, 263), ("card3a", 264, 476), ("card3b", 477, 644), ("card4", 645, 719)]
CHIP_FROM = 69

def F(p, s): return ImageFont.truetype(p, s)

def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def layout(d, text, hook, top_limit, bottom_limit, force_size=None):
    size = force_size or (94 if hook else 72)
    while True:
        f = F(BOLD if hook else SANS, size)
        ls = wrap(d, text, f, MAXW)
        pitch = int(round(size * (1.15 if hook else 1.11)))
        h = pitch * len(ls)
        top = CY - h // 2
        ok_lines = (not hook) or len(ls) <= 3 or size <= 78
        if force_size or (top >= top_limit and top + h <= bottom_limit and ok_lines) or size <= 50: break
        size -= 2
    return f, ls, pitch, top, size

def text_layer(text, hook, top_limit, bottom_limit, force_size=None, balance=False):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    f, ls, pitch, top, size = layout(d, text, hook, top_limit, bottom_limit, force_size)
    if balance:                       # same words, same size, same number of lines - only even out the line lengths
        mw = MAXW
        while mw > 400 and len(wrap(d, text, f, mw - 10)) == len(ls): mw -= 10
        ls = wrap(d, text, f, mw)
    asc, desc = f.getmetrics()
    y = top + (pitch - (asc + desc)) // 2 + 3
    for l in ls:
        d.text((W // 2, y), l, font=f, fill=255, anchor="ma"); y += pitch
    return np.asarray(im, np.float32) / 255.0, ls, size, (top, top + pitch * len(ls))

def main():
    orig, specp, out = sys.argv[1:4]
    spec = json.load(open(specp)); it = spec["items"]["WTCD-1126"]; br = spec["brands"][it["brand"]]
    tmp = tempfile.mkdtemp(prefix="tg_")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", orig, f"{tmp}/o_%03d.png"], check=True)
    class Frames:                         # read frames from disk one at a time (keeps memory small)
        def __getitem__(self, i): return np.array(Image.open(f"{tmp}/o_{i + 1:03d}.png").convert("RGB"))
    fr = Frames()
    lum = lambda a: a.astype(np.float32).sum(2) / 3.0
    def bright_bottom(a):
        z = lum(a)[:, 380:700] > 96
        y = 300
        while y < 900 and not z[y].any(): y += 1
        gap, last = 0, y
        while y < 1000 and gap < 10:
            if z[y].any(): last, gap = y, 0
            else: gap += 1
            y += 1
        return last
    face_bottom = max(bright_bottom(fr[i]) for i in FULL.values())
    ZT = face_bottom + 12
    # ---- old words: union of the four beats' masks (same as the Nov 22 fix build)
    union = np.zeros((H, W), np.uint8)
    for b, fi in FULL.items():
        m = np.zeros((H, W), bool)
        m[ZT:ZB] = lum(fr[fi])[ZT:ZB] > (96 if b == 0 else 110)
        union |= m.astype(np.uint8)
    union = cv2.dilate(union, np.ones((11, 11), np.uint8))
    feather0 = np.clip(cv2.GaussianBlur(union.astype(np.float32), (0, 0), 1.5) * 2.0, 0, 1)
    y0, y1 = ZT - 24, ZB + 24
    um = union[y0:y1] * 255
    # ---- the source chip, taken from a frame where it is fully on
    a110 = fr[FULL[1]].astype(np.float32)
    edge110 = a110[CT:CB, 4:40].mean(1)[:, None, :]
    cdiff = np.abs(a110[CT:CB] - edge110).sum(2)
    chip_a = np.clip(cv2.GaussianBlur((cdiff > 9).astype(np.float32), (0, 0), 0.8) * 1.6, 0, 1)[..., None]
    chip_rgb = a110[CT:CB].copy()
    # ---- 300 word-free frames
    os.makedirs(f"{tmp}/p", exist_ok=True)
    for i in range(N):
        src = fr[i]
        a = src.astype(np.float32)
        crop = a[y0:y1].copy()
        wgt = (1.0 - um.astype(np.float32) / 255.0)[..., None]
        fill = crop.copy(); todo = (um > 0)
        for sg in (5, 11, 24):
            if not todo.any(): break
            den = cv2.GaussianBlur(wgt, (0, 0), sg); den = den if den.ndim == 2 else den[..., 0]
            num = cv2.GaussianBlur(crop * wgt, (0, 0), sg)
            ok = todo & (den > 0.18)
            fill[ok] = num[ok] / den[ok][:, None]
            todo &= ~ok
        if todo.any():
            hh, ww = crop.shape[:2]
            ws = cv2.resize(wgt[..., 0], (ww // 4, hh // 4), interpolation=cv2.INTER_AREA)
            cs = cv2.resize(crop * wgt, (ww // 4, hh // 4), interpolation=cv2.INTER_AREA)
            for sg in (10, 22, 45, 90):
                if not todo.any(): break
                den = cv2.GaussianBlur(ws, (0, 0), sg); num = cv2.GaussianBlur(cs, (0, 0), sg)
                est = cv2.resize(num / np.maximum(den, 1e-4)[..., None], (ww, hh), interpolation=cv2.INTER_LINEAR)
                denu = cv2.resize(den, (ww, hh), interpolation=cv2.INTER_LINEAR)
                ok = todo & (denu > (0.12 if sg < 90 else 0.0))
                fill[ok] = est[ok]
                todo &= ~ok
        fe = feather0[y0:y1, :, None]
        a[y0:y1] = a[y0:y1] * (1 - fe) + fill * fe
        a[CT:CB] = src[CT:CB, 4:40].astype(np.float32).mean(1)[:, None, :]        # chip band back to plain ground
        np.save(f"{tmp}/p/{i:03d}.npy", a.clip(0, 255).astype(np.uint8))
    _cache = {}
    def plate(i):
        if i not in _cache:
            if len(_cache) > 3: _cache.pop(next(iter(_cache)))
            _cache[i] = np.load(f"{tmp}/p/{i:03d}.npy").astype(np.float32)
        return _cache[i]
    # ---- the approved words
    beats = it["beats"]
    b3 = beats[2]
    cut = b3.index("Collection of that amount")
    b3a, b3b = b3[:cut].strip(), b3[cut:].strip()
    assert (b3a + " " + b3b) == b3, "split changed the words"
    top_limit = face_bottom + 14
    probe = Image.new("L", (W, H), 0)
    _, _, _, _, size3 = layout(ImageDraw.Draw(probe), b3, False, top_limit, CT - 12)   # the booked card 3's size
    cards = {
        "title": text_layer(beats[0], True, top_limit, CT - 12),
        "card2": text_layer(beats[1], False, top_limit, CT - 12),
        "card3a": text_layer(b3a, False, top_limit, CT - 12, force_size=size3, balance=True),
        "card3b": text_layer(b3b, False, top_limit, CT - 12, force_size=size3, balance=True),
        "card4": text_layer(beats[3], False, top_limit, CT - 12),
    }
    col_hook = np.array(br["palette"]["accent"], np.float32); col_text = np.array(br["palette"]["text"], np.float32)
    os.makedirs(f"{tmp}/n", exist_ok=True)
    for j in range(NOUT):
        s = j * (2 * N) / NOUT
        i0 = int(np.floor(s)) % N; f = s - np.floor(s)
        a = plate(i0) * (1 - f) + plate((i0 + 1) % N) * f if f > 1e-6 else plate(i0).copy()
        if j >= CHIP_FROM:
            a[CT:CB] = a[CT:CB] * (1 - chip_a) + chip_rgb * chip_a
        for name, f0, f1 in TL:
            if f0 <= j <= f1:
                m = cards[name][0][..., None]
                a = a * (1 - m) + (col_hook if name == "title" else col_text) * m
        Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(f"{tmp}/n/n_{j + 1:04d}.png")
    # ---- sound: the original bed joined to itself (best-match join, 1 s linear cross-fade), 24.0 s
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", orig, "-vn", "-ac", "1", "-ar", "48000", f"{tmp}/a.wav"], check=True)
    w = wave.open(f"{tmp}/a.wav"); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64)
    XF = sr                                                     # 1 s
    def join(a, b):
        tail = a[-XF:]
        best, bl = -1e18, 0
        for lag in range(0, sr // 20):                          # slide up to 50 ms to line the waves up
            c = float(np.dot(tail, b[lag:lag + XF]))
            if c > best: best, bl = c, lag
        b = b[bl:]
        r = np.linspace(0, 1, XF)
        return np.concatenate([a[:-XF], tail * (1 - r) + b[:XF] * r, b[XF:]]), bl
    y, l1 = join(x[:int(9.0 * sr)], x[int(1.0 * sr):int(9.2 * sr)])
    need = int(24.0 * sr)
    tail_len = need - (len(y) - XF)
    seg = x[len(x) - tail_len - sr // 20:]
    y, l2 = join(y, seg)
    y = y[:need] if len(y) >= need else np.concatenate([y, np.zeros(need - len(y))])
    # make sure the end is the bed's own fade-out
    endfade = np.ones(need); k = int(0.35 * sr); endfade[-k:] = np.minimum(1.0, np.linspace(1, 0, k) * 3)
    y = y * endfade
    wo = wave.open(f"{tmp}/b.wav", "w"); wo.setnchannels(1); wo.setsampwidth(2); wo.setframerate(sr)
    wo.writeframes(y.clip(-32768, 32767).astype(np.int16).tobytes()); wo.close()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", f"{tmp}/n/n_%04d.png", "-i", f"{tmp}/b.wav",
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-profile:v", "high", "-r", "30", "-c:a", "aac", "-b:a", "128k", "-t", "24", "-movflags", "+faststart", out], check=True)
    rep = dict(id="WTCD-1126-TIMING", frames=NOUT, seconds=NOUT / FPS, face_bottom=face_bottom, card3_font_px=size3,
               cards={n: dict(words=" ".join(cards[n][1]), lines=cards[n][1], font_px=cards[n][2], rows=cards[n][3],
                              first_frame=f0, last_frame=f1, on_seconds=round((f1 - f0 + 1) / FPS, 2),
                              word_count=len(" ".join(cards[n][1]).split())) for n, f0, f1 in TL},
               chip_from_frame=CHIP_FROM, audio_join_lags=[l1, l2])
    json.dump(rep, open(out.replace(".mp4", ".build.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))
    shutil.rmtree(tmp)

if __name__ == "__main__":
    main()
