#!/usr/bin/env python3
"""Both Sides catch-up quote pictures, Sun Nov 22 2026 (ARCHITECT-TASK helper run).
Look = the brand's own quote-picture look (Q1/Q2/Q3 of 20261114batch1): painted red ground,
gold 'BOTH SIDES' label, two short gold rules, cream Lora Bold line, half-moon mark.
Method: take an existing brand quote picture, lift every bright element off it (inpaint),
optionally mirror the painted ground, put the brand's own label / rules / mark back from the
original pixels, and set the new DOT-passed line in the same type and place.
Usage: build_quotes.py <batch1_dir> <outdir>
"""
import sys, json, hashlib
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

LORA = "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"
W, H = 1080, 1350
CREAM = (245, 235, 217)
ITEMS = [
 dict(id="Q4", base="Q1", flip=True,  line="They're on their road. You're not late on yours."),
 dict(id="T4P", base="Q2", flip=True, line="Rest and quitting are not the same thing. Agree or disagree?"),
 dict(id="Q5", base="Q3", flip=True,  line="Rest counts too. Make the plan fit your energy."),
 dict(id="Q6", base="Q1", flip=False, line="A small test can teach you what to try next."),
]

def font(size):
    f = ImageFont.truetype(LORA, size)
    f.set_variation_by_name("Bold")
    return f

def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines

def balance(d, text, f, maxw, n):
    """n lines, as even as possible, none wider than maxw."""
    words = text.split(); best = None
    def rec(i, k, acc):
        nonlocal best
        if k == 1:
            l = " ".join(words[i:])
            if d.textlength(l, font=f) > maxw: return
            ls = acc + [l]; ws = [d.textlength(x, font=f) for x in ls]
            score = max(ws) - min(ws[:-1] + [max(ws)]) + 0.5 * max(ws)
            if best is None or score < best[0]: best = (score, ls)
            return
        for j in range(i + 1, len(words) - k + 2):
            l = " ".join(words[i:j])
            if d.textlength(l, font=f) > maxw: break
            rec(j, k - 1, acc + [l])
    rec(0, n, [])
    return best[1] if best else None

def build(it, src, out):
    orig = np.array(Image.open(f"{src}/{it['base']}.png").convert("RGB"))
    g = orig[..., 1].astype(np.int32)
    mask = (g > 34).astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))
    clean = cv2.inpaint(cv2.cvtColor(orig, cv2.COLOR_RGB2BGR), mask, 7, cv2.INPAINT_TELEA)
    clean = cv2.cvtColor(clean, cv2.COLOR_BGR2RGB)
    if it["flip"]: clean = clean[:, ::-1].copy()
    img = clean.astype(np.float32)
    # put the brand's own label, rules and mark back, from the original pixels (soft matte on green)
    for (y0, y1, x0, x1) in [(80, 120, 76, 302), (462, 480, 480, 600), (882, 900, 480, 600), (1100, 1200, 494, 586)]:
        o = orig[y0:y1, x0:x1].astype(np.float32)
        a = np.clip((o[..., 1] - 30.0) / 110.0, 0, 1)[..., None]
        a = np.where(a > 0.92, 1.0, a)
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + o * a
    im = Image.fromarray(img.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    size = 86
    while True:
        f = font(size); ls = wrap(d, it["line"], f, 800)
        if len(ls) <= 3 or size <= 58: break
        size -= 2
    ls = balance(d, it["line"], f, 800, len(ls)) or ls
    pitch = int(round(size * 1.26))
    asc, desc = f.getmetrics()
    block = pitch * (len(ls) - 1) + asc + desc
    y = 681 - block // 2
    for l in ls:
        d.text((W // 2, y), l, font=f, fill=CREAM, anchor="ma")
        y += pitch
    png = f"{out}/{it['id']}.png"; jpg = f"{out}/{it['id']}.jpg"
    im.save(png); im.save(jpg, quality=95, subsampling=0)
    return dict(id=it["id"], base=it["base"], mirrored=it["flip"], line=it["line"], lines=ls, font_px=size,
                jpg_sha256=hashlib.sha256(open(jpg, "rb").read()).hexdigest())

if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    rep = [build(it, src, out) for it in ITEMS]
    json.dump(rep, open(f"{out}/BUILD_REPORT_quotes.json", "w"), indent=1)
    for r in rep: print(r)
