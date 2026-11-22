#!/usr/bin/env python3
"""Caption-fix rebuild for six of the 20261122run loops (ARCHITECT-TASK helper, Sun Nov 22 2026).
Keeps the booked video's own picture (brand label, character, rings, footer, timing) and its own sound.
Only the words change: the old on-screen words are lifted off every frame and the corrected words
are set in the same type, colour, place and fade timing.
Usage: rebuild.py <old.mp4> <out.mp4> <spec.json> <id> [--parity]
"""
import sys, os, json, subprocess, shutil, tempfile, time
T0 = time.time()
def tick(m): print(f'[{time.time()-T0:6.1f}s] {m}', file=sys.stderr, flush=True), time
T0 = time.time()
def tick(m): print(f'[{time.time()-T0:6.1f}s] {m}', file=sys.stderr, flush=True)
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, N = 1080, 1920, 30, 300
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CY = 1113            # vertical centre of every text block in the original build
MAXW = 910
FULL = {0: 45, 1: 110, 2: 200, 3: 260}          # a frame where each beat is fully on
WIN = {0: (0, 72), 1: (62, 162), 2: (150, 248), 3: (236, 299)}   # frames where a beat may be visible

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

def layout(d, text, hook, top_limit, bottom_limit):
    size = 94 if hook else 72
    while True:
        f = F(BOLD if hook else SANS, size)
        ls = wrap(d, text, f, MAXW)
        pitch = int(round(size * (1.15 if hook else 1.11)))
        h = pitch * len(ls)
        top = CY - h // 2
        ok_lines = (not hook) or len(ls) <= 3 or size <= 78
        if (top >= top_limit and top + h <= bottom_limit and ok_lines) or size <= 50: break
        size -= 2
    return f, ls, pitch, top, size

def text_layer(text, hook, color, top_limit, bottom_limit):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    f, ls, pitch, top, size = layout(d, text, hook, top_limit, bottom_limit)
    asc, desc = f.getmetrics()
    y = top + (pitch - (asc + desc)) // 2 + 3
    for l in ls:
        d.text((W // 2, y), l, font=f, fill=255, anchor="ma"); y += pitch
    a = np.asarray(im, np.float32) / 255.0
    return a, ls, size, (top, top + pitch * len(ls))

def main():
    old, out, specp, iid = sys.argv[1:5]
    parity = "--parity" in sys.argv
    spec = json.load(open(specp)); it = spec["items"][iid]; br = spec["brands"][it["brand"]]
    tmp = tempfile.mkdtemp(prefix="rb_")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", old, f"{tmp}/o_%03d.png"], check=True)
    fr = [np.array(Image.open(f"{tmp}/o_{i:03d}.png").convert("RGB")) for i in range(1, N + 1)]
    tick('frames loaded')
    tick('frames loaded')
    lum = lambda a: a.astype(np.float32).sum(2) / 3.0
    bgrow = lambda a: lum(a)[:, 4:40].mean(1)             # the plain gradient, read at the left edge
    ZB = 1445                                    # words zone (below the character, above the chip)
    CT, CB = 1450, 1545                                   # chip band
    # ---- where the character ends. Its bright part (face / badge) stops well above the words;
    #      its body is a flat mid-tone, found by colour, so it is never mistaken for words.
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
    face_bottom = max(bright_bottom(fr[i]) for i in (FULL[0], FULL[1], FULL[2], FULL[3]))
    ZT = face_bottom + 12
    # body template from the hook frame (no words near the body there); the body only bobs up and down
    tf = fr[FULL[0]]
    seed = tf[face_bottom + 40:face_bottom + 70, 520:560].reshape(-1, 3).astype(np.float32)
    body_rgb = np.median(seed, 0)
    has_body = br.get('character') != 'shield'      # the badge character has no body under it
    tmpl = np.zeros((H, W), np.uint8)
    if has_body:
        tmpl = (np.abs(tf.astype(np.float32) - body_rgb).sum(2) < 26).astype(np.uint8)
        tmpl[:face_bottom - 60] = 0; tmpl[940:] = 0; tmpl[:, :380] = 0; tmpl[:, 700:] = 0
        tmpl = cv2.dilate(cv2.erode(tmpl, np.ones((5, 5), np.uint8)), np.ones((5, 5), np.uint8))
    def bright_top(a):
        z = lum(a)[:, 380:700] > 96
        y = 300
        while y < 900 and not z[y].any(): y += 1
        return y
    t0 = bright_top(tf)
    dys = [bright_top(a) - t0 for a in fr]
    def shifted(m, dy):
        o = np.zeros_like(m)
        if dy >= 0: o[dy:] = m[:H - dy]
        else: o[:H + dy] = m[-dy:]
        return o
    bodies = [shifted(tmpl, dy) for dy in dys]
    body_bottom = (int(np.where(tmpl.any(1))[0].max()) + max(dys)) if has_body else face_bottom
    tick('bodies done, bob %d..%d, body bottom %d' % (min(dys), max(dys), body_bottom))
    # ---- old words: one mask per beat from a fully-on frame (words only: brighter than any body), then the union
    masks = {}
    for b, fi in FULL.items():
        a = fr[fi]; m = np.zeros((H, W), bool)
        m[ZT:ZB] = lum(a)[ZT:ZB] > (96 if b == 0 else 110)
        masks[b] = m
    union = np.zeros((H, W), np.uint8)
    for b in masks: union |= masks[b].astype(np.uint8)
    union = cv2.dilate(union, np.ones((11, 11), np.uint8))
    tick('masks done')
    tick('masks done')
    # ---- fade curve of each beat, measured on the old video (pixels only that beat uses)
    alpha = {}
    for b, fi in FULL.items():
        other = np.zeros((H, W), np.uint8)
        for o in masks:
            if o != b: other |= masks[o].astype(np.uint8)
        other = cv2.dilate(other, np.ones((7, 7), np.uint8)).astype(bool)
        hi = 0.8 * float(np.percentile(lum(fr[fi])[masks[b]], 95))
        core = masks[b] & (lum(fr[fi]) > hi) & ~other
        if core.sum() < 400: core = masks[b] & (lum(fr[fi]) > hi)
        ref = (lum(fr[fi])[core] - np.repeat(bgrow(fr[fi])[:, None], W, 1)[core]).mean()
        cur = np.zeros(N, np.float32)
        for i in (list(range(WIN[b][0], WIN[b][1] + 1)) + (list(range(276, 300)) if b == 0 else [])):
            v = (lum(fr[i])[core] - np.repeat(bgrow(fr[i])[:, None], W, 1)[core]).mean() / ref
            cur[i] = float(np.clip(v, 0, 1))
        cur[cur < 0.04] = 0; cur[cur > 0.97] = 1
        alpha[b] = cur
    # chip: fade curve and box, from the old video
    cl = lum(fr[110])[CT:CB] - bgrow(fr[110])[CT:CB, None]
    chipm = cl > 10
    cols = np.where(chipm.any(0))[0]; rows = np.where(chipm.any(1))[0]
    chip_box = (int(cols.min()), CT + int(rows.min()), int(cols.max()), CT + int(rows.max()))
    ctext = (lum(fr[110])[CT:CB] > 150)
    cref = (lum(fr[110])[CT:CB][ctext] - bgrow(fr[110])[CT:CB, None].repeat(W, 1)[ctext]).mean()
    calpha = np.array([float(np.clip((lum(a)[CT:CB][ctext] - bgrow(a)[CT:CB, None].repeat(W, 1)[ctext]).mean() / cref, 0, 1)) for a in fr], np.float32)
    calpha[calpha < 0.04] = 0; calpha[calpha > 0.97] = 1
    chip_rgb = tuple(int(v) for v in np.median(fr[110][chip_box[1] + 4:chip_box[3] - 4, chip_box[0] + 14:chip_box[0] + 22].reshape(-1, 3), 0))
    tick('fades done')
    tick('fades done')
    # ---- new words
    beats = it["beats_old"] if parity else it["beats"]
    top_limit = body_bottom + 14
    layers, info = [], []
    for b, t in enumerate(beats):
        a, ls, size, span = text_layer(t, b == 0, None, top_limit, CT - 12)
        layers.append(a); info.append(dict(beat=b + 1, lines=ls, font_px=size, rows=span))
    col_hook = np.array(br["palette"]["accent"], np.float32); col_text = np.array(br["palette"]["text"], np.float32)
    new_chip = None if parity else it.get("source_chip_new")
    if new_chip:
        cim = Image.new("RGBA", (W, CB - CT), (0, 0, 0, 0)); cd = ImageDraw.Draw(cim)
        ch = chip_box[3] - chip_box[1] + 1
        cf = F(BOLD, 38)
        tw = cd.textlength(new_chip, font=cf); bw = int(tw + 2 * 30)
        x0 = (W - bw) // 2; y0 = chip_box[1] - CT
        cd.rounded_rectangle([x0, y0, x0 + bw, y0 + ch - 1], radius=ch // 2, fill=chip_rgb + (255,))
        cd.text((W // 2, y0 + ch // 2), new_chip, font=cf, fill=tuple(br["palette"]["text"]) + (255,), anchor="mm")
        chip_new = np.asarray(cim, np.float32)
    y0, y1 = ZT - 24, ZB + 24
    um = union[y0:y1] * 255
    feather0 = np.clip(cv2.GaussianBlur(union.astype(np.float32), (0, 0), 1.5) * 2.0, 0, 1)
    os.makedirs(f"{tmp}/n", exist_ok=True)
    tick('start frames')
    for i in range(N):
        if i % 50 == 0: tick('frame %d' % i)
        a = fr[i].astype(np.float32)
        crop = fr[i][y0:y1].astype(np.float32)
        bod = bodies[i][y0:y1]
        wgt = ((1.0 - um.astype(np.float32) / 255.0) * (1 - cv2.dilate(bod, np.ones((9, 9), np.uint8))))[..., None]
        fill = crop.copy(); todo = (um > 0)
        for sg in (5, 11, 24):
            if not todo.any(): break
            den = cv2.GaussianBlur(wgt, (0, 0), sg)
            num = cv2.GaussianBlur(crop * wgt, (0, 0), sg)
            den = den if den.ndim == 2 else den[..., 0]
            ok = todo & (den > 0.18)
            fill[ok] = num[ok] / den[ok][:, None]
            todo &= ~ok
        if todo.any():      # big solid blocks of old words: fill from a quarter-size copy
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
        inner = cv2.erode(bod, np.ones((5, 5), np.uint8)).astype(bool)
        ring = cv2.dilate(bod, np.ones((5, 5), np.uint8)).astype(bool) & ~inner
        fill[inner] = body_rgb
        fill[ring] = crop[ring]
        stray = ring & (um > 0) & ((crop.sum(2) / 3.0) > (float(body_rgb.sum()) / 3.0 + 22))   # bits of old words on the body's edge
        fill[stray] = body_rgb
        fe = feather0[y0:y1, :, None]
        a[y0:y1] = a[y0:y1] * (1 - fe) + fill * fe
        if new_chip:
            edge = fr[i][CT:CB, 4:40].astype(np.float32).mean(1)[:, None, :]
            a[CT:CB] = edge
            ca = (chip_new[..., 3:4] / 255.0) * calpha[i]
            a[CT:CB] = a[CT:CB] * (1 - ca) + chip_new[..., :3] * ca
        for b, la in enumerate(layers):
            al = alpha[b][i]
            if al <= 0: continue
            m = (la * al)[..., None]
            a = a * (1 - m) + (col_hook if b == 0 else col_text) * m
        Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(f"{tmp}/n/n_{i + 1:03d}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", f"{tmp}/n/n_%03d.png", "-i", old,
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-profile:v", "high", "-r", "30", "-c:a", "copy", "-t", "10", "-movflags", "+faststart", out], check=True)
    rep = dict(id=iid, face_bottom=face_bottom, body_bottom=body_bottom, top_limit=top_limit, chip_box=chip_box, beats=info,
               chip=new_chip or "unchanged", fade_frames={b: [int(np.argmax(alpha[b] > 0)), int(N - 1 - np.argmax(alpha[b][::-1] > 0))] for b in alpha})
    json.dump(rep, open(out.replace(".mp4", ".build.json"), "w"), indent=1)
    print(json.dumps(rep))
    shutil.rmtree(tmp)

if __name__ == "__main__":
    main()
