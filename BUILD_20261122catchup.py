#!/usr/bin/env python3
"""Sunday Nov 22 catch-up loops: The Receipts Room + Footnote Unknown.
10.0 s, 1080x1920, 30 fps, seamless loop (every motion is periodic over 10 s;
second-beat elements fade in at 3.2 s and out by 10.0 s so the last frame equals the first).
Usage: build.py <outdir> [id ...]
"""
import math, subprocess, sys, os, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, DUR = 1080, 1920, 30, 10.0
N = int(FPS * DUR)
ANTON = "/tmp/anton.ttf"; INTER = "/tmp/inter.ttf"; ARCH = "/tmp/archivo.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONOB = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
if not os.path.exists(MONOB): MONOB = MONO

def F(p, s): return ImageFont.truetype(p, s)

def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def fit(d, text, path, maxw, maxh, start, minsize=54, lh=1.08):
    s = start
    while s >= minsize:
        f = F(path, s); ls = wrap(d, text, f, maxw)
        h = int(len(ls) * s * lh)
        if h <= maxh and all(d.textlength(l, font=f) <= maxw for l in ls): return f, ls, s
        s -= 4
    f = F(path, minsize); return f, wrap(d, text, f, maxw), minsize

def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def window(t, a, b, c, d): return ease((t - a) / (b - a)) * (1 - ease((t - c) / (d - c)))

# ---------------- The Receipts Room: printed receipt on a dark counter ----------------
def rr_layers(it):
    bg = Image.new("RGB", (W, H), (20, 21, 26))
    d = ImageDraw.Draw(bg)
    for y in range(0, H, 6):  # soft vignette bands
        k = abs(y - H / 2) / (H / 2)
        d.rectangle([0, y, W, y + 6], fill=(int(26 - 9 * k), int(27 - 9 * k), int(34 - 10 * k)))
    d.text((W // 2, 1790), "AI-made visuals.", font=F(INTER, 34), fill=(150, 152, 160), anchor="mm")
    PW, PH = 860, 1470
    paper = Image.new("RGBA", (PW, PH + 40), (0, 0, 0, 0))
    p = ImageDraw.Draw(paper)
    p.rectangle([0, 0, PW, PH], fill=(247, 244, 236, 255))
    for x in range(0, PW, 40):  # torn zig-zag bottom
        p.polygon([(x, PH), (x + 20, PH + 34), (x + 40, PH)], fill=(247, 244, 236, 255))
    ink = (28, 28, 32)
    p.text((PW // 2, 92), "THE RECEIPTS ROOM", font=F(MONOB, 54), fill=ink, anchor="mm")
    p.text((PW // 2, 160), "- - - - - - - - - - - - - - - -", font=F(MONO, 34), fill=(120, 118, 112), anchor="mm")
    p.text((60, 200), "DATE  %s" % it["stamp_date"], font=F(MONO, 34), fill=(90, 88, 84))
    p.text((PW - 60, 200), "NO. %s" % it["no"], font=F(MONO, 34), fill=(90, 88, 84), anchor="ra")
    f, ls, s = fit(p, it["hook"].upper(), ANTON, PW - 120, 520, 132)
    y = 300
    for l in ls:
        p.text((60, y), l, font=f, fill=ink); y += int(s * 1.1)
    p.text((PW // 2, PH - 150), "- - - - - - - - - - - - - - - -", font=F(MONO, 34), fill=(120, 118, 112), anchor="mm")
    p.text((60, PH - 110), "ITEMS  1", font=F(MONO, 34), fill=(90, 88, 84))
    p.text((PW - 60, PH - 110), "KEPT ON FILE", font=F(MONO, 34), fill=(90, 88, 84), anchor="ra")
    hook_bottom = y
    beat = Image.new("RGBA", (PW, PH + 40), (0, 0, 0, 0))
    b = ImageDraw.Draw(beat)
    f2, ls2, s2 = fit(b, it["beat"], MONOB, PW - 120, 300, 58, minsize=40, lh=1.25)
    y2 = hook_bottom + 60
    b.line([(60, y2 - 24), (PW - 60, y2 - 24)], fill=(120, 118, 112, 255), width=3)
    for l in ls2:
        b.text((60, y2), l, font=f2, fill=ink); y2 += int(s2 * 1.25)
    st = Image.new("RGBA", (620, 220), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    red = (196, 38, 38, 235)
    sd.rounded_rectangle([8, 8, 612, 212], radius=22, outline=red, width=12)
    sf, _, _ = fit(sd, it["stamp"], ANTON, 560, 150, 120, minsize=60)
    sd.text((310, 110), it["stamp"], font=sf, fill=red, anchor="mm")
    st = st.rotate(-9, expand=True, resample=Image.BICUBIC)
    return bg, paper, beat, st, (PW, PH), y2

def rr_frame(t, L):
    bg, paper, beat, st, (PW, PH), y2 = L
    fr = bg.copy()
    dy = int(round(8 * math.sin(2 * math.pi * t / DUR)))
    px, py = (W - PW) // 2, 200 + dy
    sh = Image.new("RGBA", (PW + 80, PH + 120), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([40, 50, PW + 40, PH + 60], fill=(0, 0, 0, 120))
    fr.paste(sh.filter(ImageFilter.GaussianBlur(18)), (px - 40, py - 20), sh.filter(ImageFilter.GaussianBlur(18)))
    fr.paste(paper, (px, py), paper)
    a = window(t, 3.2, 3.8, 9.3, 9.9)
    if a > 0.004:
        bb = beat.copy(); bb.putalpha(bb.getchannel("A").point(lambda v: int(v * a)))
        fr.paste(bb, (px, py + int(18 * (1 - a))), bb)
    s = window(t, 4.6, 4.85, 9.3, 9.9)
    if s > 0.004:
        avail = (PH - 190) - (y2 + 20)
        base = min(1.0, avail / float(st.height))
        k = base * (1.0 + 0.35 * (1 - ease((t - 4.6) / 0.25)))
        ss = st.resize((int(st.width * k), int(st.height * k)), Image.BICUBIC)
        ss.putalpha(ss.getchannel("A").point(lambda v: int(v * s)))
        cy = (y2 + 20 + PH - 190) // 2
        fr.paste(ss, (px + PW // 2 + 70 - ss.width // 2, py + cy - ss.height // 2), ss)
    return fr

# ---------------- Footnote Unknown: the page, the asterisk, the footnote ----------------
def fnu_layers(it):
    bg = Image.new("RGB", (W, H), (244, 239, 226))
    d = ImageDraw.Draw(bg)
    for y in range(330, 1500, 86): d.line([(90, y), (W - 90, y)], fill=(226, 219, 202), width=2)
    d.line([(150, 0), (150, H)], fill=(232, 196, 190), width=3)
    d.rectangle([0, 96, W, 216], fill=(18, 18, 20))
    d.text((W // 2, 156), "FOOTNOTE UNKNOWN", font=F(ANTON, 70), fill=(255, 214, 10), anchor="mm")
    d.text((W // 2, 1820), "AI-made visuals.", font=F(INTER, 34), fill=(120, 114, 100), anchor="mm")
    f, ls, s = fit(d, it["hook"].upper(), ANTON, W - 300, 760, 140)
    rows, y = [], 360
    for l in ls:
        rows.append((l, y, int(d.textlength(l, font=f)))); y += int(s * 1.14)
    hook = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hook)
    for l, yy, _ in rows: hd.text((190, yy), l, font=f, fill=(18, 18, 20))
    lastw = rows[-1][2]
    ast_xy = (min(190 + lastw + 24, W - 170), rows[-1][1] + int(s * 0.16))
    foot = Image.new("RGBA", (W, 520), (0, 0, 0, 0))
    fd = ImageDraw.Draw(foot)
    fd.line([(190, 20), (560, 20)], fill=(18, 18, 20, 255), width=5)
    f2, ls2, s2 = fit(fd, it["beat"], ARCH, W - 380, 380, 70, minsize=46, lh=1.22)
    fd.text((190, 56), "*", font=F(ANTON, 90), fill=(204, 36, 36))
    yy = 70
    for l in ls2:
        fd.text((250, yy), l, font=f2, fill=(30, 30, 34)); yy += int(s2 * 1.22)
    return bg, hook, rows, s, ast_xy, foot, y

def fnu_frame(t, L):
    bg, hook, rows, s, ast_xy, foot, yend = L
    fr = bg.copy(); d = ImageDraw.Draw(fr)
    hl = window(t, 0.25, 0.9, 9.4, 9.9)
    if hl > 0.004:  # highlighter swipe behind the last line of the hook
        l, yy, w = rows[-1]
        d.rectangle([180, yy + int(s * 0.22), 180 + int((w + 20) * hl), yy + int(s * 1.08)], fill=(255, 224, 60))
    fr.paste(hook, (0, 0), hook)
    k = 1.0 + 0.14 * (0.5 - 0.5 * math.cos(2 * math.pi * 3 * t / DUR))
    af = F(ANTON, int(s * 0.95 * k))
    ImageDraw.Draw(fr).text(ast_xy, "*", font=af, fill=(204, 36, 36), anchor="lt")
    a = window(t, 3.2, 3.9, 9.3, 9.9)
    if a > 0.004:
        ff = foot.copy(); ff.putalpha(ff.getchannel("A").point(lambda v: int(v * a)))
        fr.paste(ff, (0, max(yend + 110, 1180) + int(40 * (1 - a))), ff)
    return fr

BRANDS = {"RR": (rr_layers, rr_frame, 98.0), "FNU": (fnu_layers, fnu_frame, 130.8)}

def render(it, outdir):
    mk, frame, hz = BRANDS[it["brand"]]
    L = mk(it)
    out = os.path.join(outdir, it["brand"], it["id"] + ".mp4"); os.makedirs(os.path.dirname(out), exist_ok=True)
    bed = ("sine=f=%.1f:d=10,volume=0.045[a1];sine=f=%.1f:d=10,volume=0.03[a2];"
           "[a1][a2]amix=inputs=2:normalize=0,tremolo=f=0.2:d=0.5,afade=t=in:d=0.4,afade=t=out:st=9.6:d=0.4[a]" % (hz, hz * 1.5))
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
           "-filter_complex", bed, "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-t", "10", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(N):
        fr = frame(i / FPS, L)
        if i in (0, 150, 285, N - 1): fr.save(os.path.join(outdir, it["brand"], "%s_f%03d.jpg" % (it["id"], i)), quality=80)
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    return out

if __name__ == "__main__":
    outdir = sys.argv[1]; want = set(sys.argv[2:])
    items = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "spec.json")))["items"]
    for it in items:
        if want and it["id"] not in want: continue
        print(render(it, outdir), flush=True)
