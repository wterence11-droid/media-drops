#!/usr/bin/env python3
"""MEET THE HOST - two 9-second clips (JOB 4, Thu Nov 26 2026). Build only.

Scripts: comms/open/production-week/20261123T0002Z (ARCHITECT), DOT words PASS 20261123T0004Z.
  Side-Eye Bureau: Agent Rhonda Lyle.   Dottie Keys.

Picture
  RHONDA: her own brand footage (branch claude/seb-remake-20261114, SEB-REMAKE-weekend-audit.mp4).
          8.04-10.38 s: facing camera, mouth still, desk radio pulsing (the brand shows her voice
          coming from the radio, so no lip sync is needed). Played forward/back to fill the talk.
          27.58-28.33 s: she looks back down at the file (last beat, leads into frame one).
  DOTTIE: her own brand portrait card (branch claude/dk-anim-20261108, 261114-DK-005_ANIM.mp4, 24 fps,
          0:55.0, mouth closed) held with a slow push-in (the source portraits are lip-synced to
          other lines, so they are not reused while she speaks). Last beat: her phone screen
          from the same file (0:07.5) on "go back to your inbox".
  The old burned captions in those frames are lifted off (masked fill) and the passed words are set.
Words on screen
  Frame one title exactly as the script. Captions are exactly the spoken words, hard cuts,
  timed to the ElevenLabs take's own word timings (Scribe transcript of the take).
Output: 1080x1920, 30 fps, h264, 9.000 s, no sound. MUX_meet_the_host_20261126.sh adds the voice.

Usage: build.py <seb_remake.mp4> <dk_005.mp4> <out_dir>
"""
import sys, os, subprocess, tempfile, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, N = 1080, 1920, 30, 270
BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
XBOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
CAP_Y = 1420                     # centre line of the old caption band (both brands)
BAND = (1355, 1485, 70, 1010)    # y0, y1, x0, x1 searched for old caption pixels

RHONDA = {
    "id": "SEB-HOST-01", "brand": "SEB", "off": 0.40,
    "title": ["AGENT RHONDA LYLE.", "SIDE-EYE BUREAU."],
    "spoken": "I'm Agent Rhonda Lyle. I'm fictional. I file what you thought nobody saw. Stay or scroll. It goes in the file either way.",
    # (text, start s, end s) - start = first word start + offset; each held until the next starts
    "caps": [("I'm Agent Rhonda Lyle.", 0.00, 1.75), ("I'm fictional.", 1.75, 2.83),
             ("I file what you thought nobody saw.", 2.83, 4.65), ("Stay or scroll.", 4.65, 5.81),
             ("It goes in the file either way.", 5.81, 9.00)],
    "title_until": 1.75, "end_beat": 8.10,
}
DOTTIE = {
    "id": "DK-HOST-01", "brand": "DK", "off": 0.15,
    "title": ["DOTTIE KEYS.", "OFFICE MANAGER. FICTIONAL."],
    "spoken": "I'm Dottie Keys. Fictional AI office manager. I show agents how to make AI do the paperwork. Stay, or go back to your inbox.",
    "caps": [("I'm Dottie Keys.", 0.00, 1.73), ("Fictional AI office manager.", 1.73, 3.85),
             ("I show agents how to make AI do the paperwork.", 3.85, 6.68),
             ("Stay, or go back to your inbox.", 6.68, 9.00)],
    "title_until": 1.73, "end_beat": 8.00,
}

# ---------------------------------------------------------------- helpers
def boxblur(a, r):
    """separable box blur, edges clamped; a: float32 HxW or HxWxC"""
    for ax in (0, 1):
        pad = [(0, 0)] * a.ndim; pad[ax] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad, mode="edge"), axis=ax, dtype=np.float64)
        sl_hi = [slice(None)] * a.ndim; sl_lo = [slice(None)] * a.ndim
        sl_hi[ax] = slice(2 * r + 1, None); sl_lo[ax] = slice(0, -(2 * r + 1))
        a = ((c[tuple(sl_hi)] - c[tuple(sl_lo)]) / (2 * r + 1)).astype(np.float32)
    return a

def gblur(a, r):
    for _ in range(3): a = boxblur(a, max(1, r // 2))
    return a

def dilate(m, r):
    return boxblur(m.astype(np.float32), r) > 1e-3

def caption_mask(rgb):
    """old burned caption: white letters (with dark outline) inside the band"""
    y0, y1, x0, x1 = BAND
    m = np.zeros(rgb.shape[:2], bool)
    sub = rgb[y0:y1, x0:x1].astype(np.int16)
    white = (sub.min(2) > 225) & (np.abs(sub[..., 0] - sub[..., 2]) < 18)
    m[y0:y1, x0:x1] = white
    zone = dilate(m, 16)                                  # letters + thick outline + drop shadow
    dark = rgb.astype(np.int16).max(2) < 70
    return dilate(m | (zone & dark), 4)

def fill(rgb, mask):
    """masked fill by normalised convolution (coarse to fine fallback)"""
    a = rgb.astype(np.float32)
    if not mask.any(): return rgb
    ys, xs = np.where(mask)
    y0, y1 = max(0, ys.min() - 90), min(H, ys.max() + 90)
    crop = a[y0:y1].copy(); m = mask[y0:y1]
    wgt = (~m).astype(np.float32)
    out = crop.copy(); todo = m.copy()
    for r in (6, 14, 30, 60):
        if not todo.any(): break
        den = gblur(wgt, r); num = gblur(crop * wgt[..., None], r)
        ok = todo & (den > 0.15)
        out[ok] = num[ok] / den[ok][:, None]
        todo &= ~ok
    soft = np.clip(gblur(m.astype(np.float32), 2) * 1.5, 0, 1)[..., None]
    a[y0:y1] = crop * (1 - soft) + out * soft
    return a.clip(0, 255).astype(np.uint8)

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

def draw_caption(im, text):
    d = ImageDraw.Draw(im)
    size = 66
    while True:
        f = ImageFont.truetype(XBOLD, size)
        ls = wrap(d, text, f, 900)
        if len(ls) <= 2 or size <= 50: break
        size -= 2
    if len(ls) == 2:                  # same words, same size: even out the two line lengths
        mw = 900
        while mw > 300 and len(wrap(d, text, f, mw - 10)) == 2: mw -= 10
        ls = wrap(d, text, f, mw)
    pitch = int(size * 1.18)
    y = CAP_Y - pitch * len(ls) // 2
    for l in ls:
        d.text((W // 2, y), l, font=f, fill=(255, 255, 255), anchor="ma",
               stroke_width=7, stroke_fill=(12, 12, 16))
        y += pitch
    return ls, size

def draw_title(im, lines, kind):
    d = ImageDraw.Draw(im)
    if kind == "SEB":
        f1, f2 = ImageFont.truetype(BLACK, 70), ImageFont.truetype(XBOLD, 46)
        bg, c1, c2, cy = (243, 223, 122), (22, 33, 62), (176, 40, 40), 1610
    else:
        f1, f2 = ImageFont.truetype(BLACK, 70), ImageFont.truetype(XBOLD, 44)
        bg, c1, c2, cy = (245, 197, 66), (24, 20, 52), (24, 20, 52), 1282
    w = max(d.textlength(lines[0], font=f1), d.textlength(lines[1], font=f2)) + 90
    h = 190 if kind == "SEB" else 160
    box = (W // 2 - w / 2, cy - h / 2, W // 2 + w / 2, cy + h / 2)
    d.rounded_rectangle((box[0] + 6, box[1] + 8, box[2] + 6, box[3] + 8), 26, fill=(0, 0, 0))
    d.rounded_rectangle(box, 26, fill=bg, outline=c1, width=5)
    o1, o2 = (-72, 18) if kind == "SEB" else (-62, 14)
    d.text((W // 2, cy + o1), lines[0], font=f1, fill=c1, anchor="ma")
    d.text((W // 2, cy + o2), lines[1], font=f2, fill=c2, anchor="ma")

def frames_of(path, tmp, tag):
    os.makedirs(f"{tmp}/{tag}", exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, f"{tmp}/{tag}/%04d.png"], check=True)
    return lambda i: np.array(Image.open(f"{tmp}/{tag}/{i:04d}.png").convert("RGB"))

def pingpong(k, n):
    p = k % (2 * n - 2)
    return p if p < n else 2 * n - 2 - p

def encode(frame_dir, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{frame_dir}/%04d.png",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                    "-profile:v", "high", "-movflags", "+faststart", "-r", str(FPS), out], check=True)

def render(spec, plate_fn, out, tmp):
    od = f"{tmp}/out_{spec['id']}"; os.makedirs(od, exist_ok=True)
    log = []
    for k in range(N):
        t = k / FPS
        im = Image.fromarray(plate_fn(k, t))
        cap = [c for c in spec["caps"] if c[1] <= t < c[2]]
        if cap: ls, sz = draw_caption(im, cap[0][0])
        if t < spec["title_until"]: draw_title(im, spec["title"], spec["brand"])
        im.save(f"{od}/{k + 1:04d}.png")
        log.append(cap[0][0] if cap else "")
    encode(od, out)
    return log

# ---------------------------------------------------------------- main
def main():
    seb, dk, outdir = sys.argv[1:4]
    os.makedirs(outdir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="mth_")
    S = frames_of(seb, tmp, "seb")           # 24 fps source
    D = frames_of(dk, tmp, "dk")             # 30 fps source

    # --- Rhonda plates (cleaned once per source frame)
    A0, A1 = 194, 249                        # 8.04-10.38 s  (1-based file numbers)
    C0, C1 = 663, 680                        # 27.58-28.33 s
    clean = {}
    def sclean(i):
        if i not in clean:
            f = S(i); clean[i] = fill(f, caption_mask(f))
        return clean[i]
    nA = A1 - A0 + 1
    def r_plate(k, t):
        if t < RHONDA["end_beat"]:
            return sclean(A0 + pingpong(int(k * 24 / 30), nA))
        j = int((t - RHONDA["end_beat"]) * 24)
        return sclean(min(C0 + j, C1))
    rlog = render(RHONDA, r_plate, f"{outdir}/{RHONDA['id']}_picture.mp4", tmp)

    # --- Dottie plates
    face = D(1321); face = fill(face, caption_mask(face))     # 0:55.0
    screen = D(181); screen = fill(screen, caption_mask(screen))  # 0:07.5
    cx, cy = 540, 560
    fim = Image.fromarray(face)
    def d_plate(k, t):
        if t >= DOTTIE["end_beat"]: return screen
        z = 1.0 + 0.035 * (t / DOTTIE["end_beat"])
        w, h = W / z, H / z
        x0 = cx - (cx) / z; y0 = cy - (cy) / z
        return np.array(fim.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h)))
    dlog = render(DOTTIE, d_plate, f"{outdir}/{DOTTIE['id']}_picture.mp4", tmp)

    # words check: captions joined == spoken words (exact)
    report = {}
    for spec in (RHONDA, DOTTIE):
        joined = " ".join(c[0] for c in spec["caps"])
        report[spec["id"]] = {"captions_equal_spoken": joined == spec["spoken"],
                              "title": " ".join(spec["title"]), "offset_s": spec["off"],
                              "cards": [[c[0], c[1], c[2]] for c in spec["caps"]]}
    json.dump(report, open(f"{outdir}/build_report.json", "w"), indent=1)
    print(json.dumps(report, indent=1))

if __name__ == "__main__":
    main()
