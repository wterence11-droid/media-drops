# Builds the CTS-001 card images (1080x1920) in the Caught in Retrograde look.
# Words are the Architect's locked CTS-001 words (comms 20261127T0102Z). Nothing added.
import sys, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
OUT = sys.argv[1]
W, H = 1080, 1920
GOLD = (226, 184, 92); CREAM = (240, 232, 214); DIM = (150, 140, 170)
B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
LABEL = "CAUGHT IN RETROGRADE"
FOOT = "Real cases from the public record. For entertainment. AI voice. AI-made visuals."

def base():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        c = tuple(int(a + (b - a) * t) for a, b in zip((36, 27, 56), (22, 15, 34)))
        d.line([(0, y), (W, y)], fill=c)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    for r, a in ((420, 18), (320, 22), (220, 26)):
        g.ellipse([W//2 - r + 60, 640 - r, W//2 + r + 60, 640 + r], fill=(120, 80, 70, a))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    im = Image.alpha_composite(im.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(B, 40)
    w = d.textlength(LABEL, font=f)
    d.text(((W - w) / 2, 140), LABEL, font=f, fill=GOLD)
    d.line([(W/2 - 110, 200), (W/2 + 110, 200)], fill=GOLD, width=3)
    f2 = ImageFont.truetype(R, 30)
    for i, ln in enumerate(("Real cases from the public record. For entertainment.", "AI voice. AI-made visuals.")):
        w = d.textlength(ln, font=f2)
        d.text(((W - w) / 2, 1620 + i * 44), ln, font=f2, fill=CREAM)
    return im

def sparkles(d, cx, cy):
    for dx, dy, s in ((-190, -150, 22), (170, -110, 16), (-150, 140, 14), (140, 150, 18)):
        x, y = cx + dx, cy + dy
        d.polygon([(x, y - s), (x + s*0.4, y), (x, y + s), (x - s*0.4, y)], fill=GOLD)

def moon(im, cx=540, cy=560):
    d = ImageDraw.Draw(im)
    for r, col in ((200, (60, 45, 90)), (180, (52, 40, 80))):
        d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=col, width=3)
    d.ellipse([cx-150, cy-150, cx+150, cy+150], outline=GOLD, width=5)
    d.ellipse([cx-138, cy-138, cx+138, cy+138], fill=(26, 18, 40))
    m = Image.new("L", (W, H), 0); md = ImageDraw.Draw(m)
    md.ellipse([cx-138, cy-138, cx+138, cy+138], fill=255)
    md.ellipse([cx-70, cy-150, cx+170, cy+120], fill=0)
    im.paste(Image.new("RGB", (W, H), CREAM), (0, 0), m)
    sparkles(d, cx, cy)

def sign(im, glyph, cx=540, cy=560):
    d = ImageDraw.Draw(im)
    for r, col in ((200, (60, 45, 90)), (180, (52, 40, 80))):
        d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=col, width=3)
    d.ellipse([cx-150, cy-150, cx+150, cy+150], outline=GOLD, width=5)
    d.ellipse([cx-138, cy-138, cx+138, cy+138], fill=(26, 18, 40))
    f = ImageFont.truetype(R, 190)
    bb = d.textbbox((0, 0), glyph, font=f)
    d.text((cx - (bb[0]+bb[2])/2, cy - (bb[1]+bb[3])/2), glyph, font=f, fill=GOLD)
    sparkles(d, cx, cy)

def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for wd in text.split():
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = wd
    lines.append(cur); return lines

def body(im, text, size, color, top=900, bold=True, gap=1.25):
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(B if bold else R, size)
    lines = wrap(d, text, f, 900)
    y = top
    for ln in lines:
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y), ln, font=f, fill=color)
        y += int(size * gap)

def save(im, name): im.save(f"{OUT}/{name}.png")

im = base(); moon(im); body(im, "Which sign has a story ready, until the receipts show up?", 74, GOLD, top=920); save(im, "c1_hook")
names = ["GEMINI.", "LEO.", "AQUARIUS.", "SCORPIO.", "ARIES.", "VIRGO."]
for k in range(1, 7):
    im = base(); moon(im)
    d = ImageDraw.Draw(im); f = ImageFont.truetype(B, 72)
    y = 860
    for i, n in enumerate(names):
        if i < k:
            w = d.textlength(n, font=f)
            d.text(((W - w) / 2, y), n, font=f, fill=GOLD if i == k - 1 else CREAM)
        y += 100
    save(im, f"c2_roll{k}")
im = base(); moon(im); body(im, "That part is a joke. This part is public record.", 76, CREAM, top=950); save(im, "c2b_bridge")
im = base(); sign(im, "♊"); body(im, "GEMINI", 140, GOLD, top=980); save(im, "c3_gemini")
im = base(); sign(im, "♌"); body(im, "LEO", 140, GOLD, top=980); save(im, "c4_leo")
im = base(); moon(im); body(im, "Charge it to the sign. Drop your sign's charges in the comments.", 70, GOLD, top=920); save(im, "c5_end")
print("ok")
