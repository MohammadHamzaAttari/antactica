#!/usr/bin/env python3
"""ANTARCTICA FROZE FIRST — procedural cinematic animations (PIL + numpy),
rendered frame-by-frame at 1080x1920 and piped to ffmpeg."""
import subprocess
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

BASE = Path(__file__).parent
SCA = BASE / "scenes_ant"
SCA.mkdir(exist_ok=True)
IMGA = BASE / "images_ant"
FONTS = BASE / "fonts"

W, H, FPS = 1080, 1920, 30
import shutil as _sh

def _resolve_ffmpeg():
    exe = _sh.which("ffmpeg")
    if exe:
        return exe
    for cand in ("/tmp/package/ffmpeg",):
        if Path(cand).exists():
            return cand
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise RuntimeError("ffmpeg not found — install ffmpeg (with libfreetype/drawtext)")

FF = _resolve_ffmpeg()

F_TITLE = str(FONTS / "ArchivoBlack-Regular.ttf")
F_DISP = str(FONTS / "Anton-Regular.ttf")
F_UI = str(FONTS / "Oswald-SemiBold.ttf")
F_MED = str(FONTS / "Oswald-Medium.ttf")
F_BODY = str(FONTS / "Inter-Bold.ttf")
F_REG = str(FONTS / "Inter-Regular.ttf")

NAVY = (5, 10, 24)
CYAN = (103, 232, 249)
ICE = (154, 216, 255)
WHITE = (245, 248, 255)
AMBER = (255, 181, 107)
RED = (255, 107, 83)
DIM = (168, 190, 220)

_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3

def ease_in(t):
    t = min(max(t, 0.0), 1.0)
    return t ** 3

def center_text(d, txt, f, y, fill, tracking=0, alpha=255):
    """Letter-spaced centered text. Returns width."""
    total_w = 0
    sizes = []
    for ch in txt:
        bb = d.textbbox((0, 0), ch, font=f)
        sizes.append((ch, bb[2] - bb[0], bb))
        total_w += bb[2] - bb[0] + tracking
    x = (W - total_w + tracking) / 2
    for ch, w, bb in sizes:
        d.text((x - bb[0], y - bb[1]), ch, font=f, fill=fill + (alpha,))
        x += w + tracking
    return total_w

def glow_sprite(radius, color, power=1.6):
    """Pre-rendered additive glow sprite."""
    r = int(radius)
    s = r * 2 + 1
    yy, xx = np.mgrid[0:s, 0:s]
    g = np.exp(-((xx - r) ** 2 + (yy - r) ** 2) / (2 * (radius / power) ** 2))
    col = np.array(color, dtype=np.float32)
    arr = g[..., None] * col
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

def starfield(n=340, seed=7, haze=0.16):
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W, 3), dtype=np.float32)
    img += np.array([6, 9, 18], dtype=np.float32) * haze
    xs = rng.integers(0, W, n)
    ys = rng.integers(0, H, n)
    bs = rng.random(n) ** 2.6 * 220
    col = np.stack([bs, bs, np.minimum(255, bs * 1.18)], axis=-1)
    for i in range(n):
        img[ys[i], xs[i]] = col[i]
    arr = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
                     .filter(ImageFilter.GaussianBlur(0.55)), dtype=np.float32)
    # twinklers
    tw = rng.integers(0, n, 70)
    return arr, (xs, ys, bs, tw)

def encode(frames_iter, name, total):
    out = SCA / name
    cmd = [FF, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i, fr in enumerate(frames_iter):
        p.stdin.write(np.asarray(fr, dtype=np.uint8).tobytes())
        if i % 40 == 0:
            print(f"    {name}: {i}/{total}")
    p.stdin.close()
    p.wait()
    print(f"  OK {name} ({out.stat().st_size / 1024:.0f}KB)")

# ============================================================ 1. COLD OPEN
def anim_cold_open(T=3.6):
    N = int(T * FPS)
    rng = np.random.default_rng(11)
    stars, tw = starfield(420, seed=11)
    # frost crystals
    n_c = 110
    cx = rng.integers(0, W, n_c)
    cy = rng.integers(0, H, n_c)
    rot = rng.random(n_c) * 360
    size = 6 + rng.random(n_c) ** 2 * 46
    birth = rng.random(n_c) * (T - 0.9) + 0.05
    hue = rng.choice([0, 1], n_c, p=[0.55, 0.45])  # 0 ice-white, 1 cyan

    t1 = font(F_TITLE, 168)
    t2 = font(F_TITLE, 118)
    t3 = font(F_UI, 44)

    def frames():
        for i in range(N):
            t = i / FPS
            cv = stars.copy()
            # twinkle
            xs, ys, bs, tidx = tw
            ph = np.sin(t * 2.4 + tidx * 1.7)
            boost = np.clip(ph, 0, 1) * 60
            for kk, j in enumerate(tidx):
                cv[ys[j], xs[j]] = min(255, bs[j] + boost[kk])
            img = Image.fromarray(np.clip(cv, 0, 255).astype(np.uint8)).convert("RGBA")
            # frost layer
            frost = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            fd = ImageDraw.Draw(frost)
            for k in range(n_c):
                if t < birth[k]:
                    continue
                age = t - birth[k]
                s = min(size[k], size[k] * (0.25 + age * 1.6))
                ga = int(min(235, 90 + age * 160))
                col = (210, 235, 255, ga) if hue[k] == 0 else \
                      (140, 225, 250, ga)
                x, y, r = cx[k], cy[k], rot[k]
                for arm in range(6):
                    a = math.radians(r + arm * 60)
                    ex = x + math.cos(a) * s
                    ey = y + math.sin(a) * s
                    fd.line([x, y, ex, ey], fill=col, width=2)
                    for frac in (0.45, 0.75):
                        bx = x + math.cos(a) * s * frac
                        by = y + math.sin(a) * s * frac
                        for da in (-38, 38):
                            a2 = math.radians(r + arm * 60 + da)
                            fd.line([bx, by, bx + math.cos(a2) * s * 0.30 * frac,
                                     by + math.sin(a2) * s * 0.30 * frac], fill=col, width=1)
            frost = frost.filter(ImageFilter.GaussianBlur(0.6))
            img = Image.alpha_composite(img, frost)
            # central aurora glow
            if t > 0.2:
                g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                gg = glow_sprite(460 * (0.7 + 0.3 * t / T), (40, 120, 220), 2.6)
                a = int(46 * min(1, t / 1.2) + 20)
                gg.putalpha(gg.getchannel("A").point(lambda v: min(v, a) if v else 0))
                g.paste(gg, (W // 2 - gg.width // 2, int(H * 0.30) - gg.height // 2), gg)
                img = Image.alpha_composite(img, g)
            d = ImageDraw.Draw(img)
            # title
            if t >= 0.45:
                k = ease_out((t - 0.45) / 0.5)
                scale = 2.4 - 1.4 * k
                al = int(255 * k)
                img2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d2 = ImageDraw.Draw(img2)
                center_text(d2, "ANTARCTICA", t1, int(H * 0.305), WHITE, tracking=6, alpha=al)
                center_text(d2, "FROZE FIRST", t2, int(H * 0.405), CYAN, tracking=10, alpha=al)
                img2 = img2.resize((int(W / scale), int(H / scale)), Image.BICUBIC)
                img2 = img2.resize((W, H), Image.BICUBIC)
                img = Image.alpha_composite(img, img2)
            if t >= 1.35:
                al = int(255 * ease_out((t - 1.35) / 0.55))
                center_text(d, "25 MILLION YEARS BEFORE THE ARCTIC", t3,
                            int(H * 0.475), DIM, tracking=8, alpha=al)
            if t >= 2.0:
                al = int(255 * ease_out((t - 2.0) / 0.6))
                center_text(d, "AND SCIENCE FINALLY KNOWS WHY", t3,
                            int(H * 0.52), AMBER, tracking=6, alpha=al)
            yield img.convert("RGB")

    encode(frames(), "anim_cold.mp4", N)

# ============================================================ 2. PALEO (warm Earth)
def anim_paleo(T=4.6):
    N = int(T * FPS)
    stars, tw = starfield(300, seed=23)
    # globe sprite: ocean + green antarctica
    R = 560
    cx, cy = W // 2, int(H * 0.40)
    gimg = Image.new("RGBA", (R * 2 + 40, R * 2 + 40), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gimg)
    m = R + 20
    gd.ellipse([m - R, m - R, m + R, m + R], fill=(24, 70, 130, 255))
    # ocean gradient bands
    for rr in range(R - 8, 0, -24):
        gd.ellipse([m - rr, m - rr, m + rr, m + rr], fill=(26 + (R - rr) // 10, 78 + (R - rr) // 8, 140 + (R - rr) // 9, 255))
    # green antarctica blob (union of ellipses, bottom)
    import random as _r
    _r.seed(5)
    blob = Image.new("L", gimg.size, 0)
    bd = ImageDraw.Draw(blob)
    for _ in range(26):
        bx = m + _r.uniform(-R * 0.42, R * 0.42)
        by = m + _r.uniform(R * 0.42, R * 0.62)
        br = _r.uniform(R * 0.10, R * 0.30)
        bd.ellipse([bx - br, by - br, bx + br, by + br], fill=255)
    green = Image.new("RGBA", gimg.size, (70, 170, 95, 255))
    gimg.paste(green, (0, 0), blob)
    # shading rim
    gd.ellipse([m - R, m - R, m + R, m + R], outline=(10, 25, 50, 255), width=6)
    globe = gimg

    f1 = font(F_UI, 52)
    f2 = font(F_BODY, 40)
    f3 = font(F_MED, 36)

    def frames():
        for i in range(N):
            t = i / FPS
            cv = stars.copy()
            img = Image.fromarray(np.clip(cv, 0, 255).astype(np.uint8)).convert("RGBA")
            # warm sun glow
            sg = glow_sprite(560, (255, 170, 90), 2.8)
            a = int(70 + 24 * np.sin(t * 1.3))
            sg.putalpha(sg.getchannel("A").point(lambda v: min(v, a) if v else 0))
            img.paste(sg, (W - sg.width + 160, 60 - sg.height // 2 + 160), sg)
            # globe with slow breathing scale
            sc = 1.0 + 0.015 * np.sin(t * 0.9)
            gs = globe.resize((int(globe.width * sc), int(globe.height * sc)), Image.BICUBIC)
            img.paste(gs, (cx - gs.width // 2, cy - gs.height // 2), gs)
            d = ImageDraw.Draw(img)
            # chips
            if t >= 0.5:
                al = ease_out((t - 0.5) / 0.45)
                center_text(d, "34 MILLION YEARS AGO", f1, int(H * 0.075), WHITE, 6, int(255 * al))
            if t >= 1.1:
                al = ease_out((t - 1.1) / 0.45)
                d.rounded_rectangle([W // 2 - 330, int(H * 0.245), W // 2 + 330, int(H * 0.245) + 92],
                                    radius=20, fill=(255, 107, 53, int(235 * al)), outline=None)
                center_text(d, "EARTH: +5°C WARMER", f2, int(H * 0.262), WHITE, 4, int(255 * al))
            if t >= 1.7:
                al = ease_out((t - 1.7) / 0.45)
                center_text(d, "ANTARCTICA WAS GREEN", f1, int(H * 0.775), (120, 220, 140), 6, int(255 * al))
            if t >= 2.35:
                al = ease_out((t - 2.35) / 0.45)
                center_text(d, "FORESTS · RIVERS · WARM SEAS", f3, int(H * 0.825), DIM, 4, int(255 * al))
            if t >= 3.0:
                al = ease_out((t - 3.0) / 0.45)
                center_text(d, "SO WHAT HAPPENED?", f1, int(H * 0.875), CYAN, 6, int(255 * al))
            yield img.convert("RGB")

    encode(frames(), "anim_paleo.mp4", N)

# ============================================================ 3. GATEWAY (polar map)
def anim_gateway(T=6.2):
    N = int(T * FPS)
    stars, tw = starfield(260, seed=31, haze=0.10)
    import math
    # base polar map
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(base)
    cx, cy = W // 2, int(H * 0.44)
    # ocean disc
    Ro = 760
    bd.ellipse([cx - Ro, cy - Ro, cx + Ro, cy + Ro], fill=(10, 24, 52, 255))
    for rr in range(140, Ro, 140):
        bd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(30, 55, 100, 160), width=2)
    # antarctica (white center)
    Ra = 330
    bd.ellipse([cx - Ra, cy - Ra, cx + Ra, cy + Ra], fill=(226, 238, 250, 255))
    bd.ellipse([cx - Ra, cy - Ra, cx + Ra, cy + Ra], outline=(120, 165, 210, 255), width=5)
    base = base.filter(ImageFilter.GaussianBlur(0.4))

    f1 = font(F_DISP, 56)
    f2 = font(F_UI, 40)
    f3 = font(F_MED, 34)
    fbig = font(F_DISP, 66)

    def frames():
        for i in range(N):
            t = i / FPS
            img = base.copy()
            d = ImageDraw.Draw(img)
            # drift phases
            k = ease_in(min(1, t / 4.2))
            # South America: upper-left of antarctica, drifting away
            sax0, say0 = cx - 320, cy - 520
            sax = sax0 - 620 * k * 0.9
            say = say0 - 300 * k * 0.9
            # Australia: upper-right
            aux0, auy0 = cx + 360, cy - 430
            aux = aux0 + 560 * k
            auy = auy0 - 240 * k
            d.ellipse([sax - 130, say - 100, sax + 150, say + 110], fill=(150, 122, 92, 255))
            d.ellipse([aux - 120, auy - 85, aux + 140, auy + 95], fill=(150, 122, 92, 255))
            d.text((sax - 60, say - 42), "SA", font=font(F_MED, 30), fill=(255, 240, 220, 255))
            d.text((aux - 62, auy - 40), "AUS", font=font(F_MED, 30), fill=(255, 240, 220, 255))
            # labels of gaps (centered in the gap regions)
            if t >= 1.6:
                al = int(255 * ease_out((t - 1.6) / 0.5))
                d.text((cx - 690, cy - 400), "DRAKE", font=fbig, fill=(103, 232, 249, al))
                d.text((cx - 700, cy - 310), "PASSAGE", font=fbig, fill=(103, 232, 249, al))
                d.line([cx - 470, cy - 360, cx - 340, cy - 460], fill=(103, 232, 249, al), width=4)
            if t >= 2.6:
                al = int(255 * ease_out((t - 2.6) / 0.5))
                d.text((cx + 180, cy - 440), "TASMANIAN", font=fbig, fill=(103, 232, 249, al))
                d.text((cx + 240, cy - 350), "GATEWAY", font=fbig, fill=(103, 232, 249, al))
            # ACC dashed ring forms
            if t >= 3.4:
                al = ease_out((t - 3.4) / 0.7)
                phase = (t - 3.4) * 26
                for ang in np.arange(0, 360, 7):
                    a0 = math.radians(ang + phase)
                    a1 = math.radians(ang + phase + 3.5)
                    x0, y0 = cx + math.cos(a0) * (Ra + 90), cy + math.sin(a0) * (Ra + 90)
                    x1, y1 = cx + math.cos(a1) * (Ra + 90), cy + math.sin(a1) * (Ra + 90)
                    d.line([x0, y0, x1, y1], fill=(103, 232, 249, int(200 * al)), width=7)
            if t >= 4.4:
                al = int(255 * ease_out((t - 4.4) / 0.5))
                center_text(d, "A CURRENT IS BORN", f1, int(H * 0.86), WHITE, 8, al)
            if t >= 5.1:
                al = int(255 * ease_out((t - 5.1) / 0.45))
                center_text(d, "THE STRONGEST ON EARTH", f2, int(H * 0.905), CYAN, 6, al)
            yield img.convert("RGB")

    encode(frames(), "anim_gateway.mp4", N)

# ============================================================ 4. CURRENT (flowlines)
def anim_current(T=5.6):
    N = int(T * FPS)
    stars, tw = starfield(300, seed=41, haze=0.12)
    import math
    cx, cy = W // 2, int(H * 0.42)
    Ra = 280
    f1 = font(F_DISP, 58)
    f2 = font(F_UI, 38)

    def frames():
        for i in range(N):
            t = i / FPS
            cv = stars.copy()
            img = Image.fromarray(np.clip(cv, 0, 255).astype(np.uint8)).convert("RGBA")
            d = ImageDraw.Draw(img)
            d.ellipse([cx - Ra, cy - Ra, cx + Ra, cy + Ra], fill=(226, 238, 250, 255))
            d.ellipse([cx - Ra, cy - Ra, cx + Ra, cy + Ra], outline=(120, 165, 210, 255), width=5)
            # rotating flow dashes on 3 rings
            rings = [Ra + 60, Ra + 130, Ra + 210]
            widths = [8, 9, 11]
            speeds = [34, 24, 17]
            for ri, (rr, wd, sp) in enumerate(zip(rings, widths, speeds)):
                phase = t * sp
                n_dash = 18
                for jj in range(n_dash):
                    a0 = math.radians(jj * (360 / n_dash) + phase)
                    a1 = math.radians(jj * (360 / n_dash) + phase + 9)
                    x0, y0 = cx + math.cos(a0) * rr, cy + math.sin(a0) * rr
                    x1, y1 = cx + math.cos(a1) * rr, cy + math.sin(a1) * rr
                    d.line([x0, y0, x1, y1], fill=(103, 232, 249, 225), width=wd)
            # warm current from top, deflected
            if t >= 1.2:
                k = min(1, (t - 1.2) / 0.9)
                y_top = -80 + k * (cy - Ra - 150)
                d.line([cx, -80, cx, y_top], fill=(255, 107, 83, 235), width=12)
                if k >= 0.98:
                    spread = ease_out(min(1, (t - 2.1) / 0.8))
                    for sgn in (-1, 1):
                        for f in (0.25, 0.5, 0.75):
                            x1 = cx + sgn * 90 * (1 + f) * spread
                            y1 = y_top + 60 * f * spread
                            d.line([cx + sgn * 6, y_top + 6, x1, y1],
                                   fill=(255, 107, 83, int(200 * spread)), width=8)
            if t >= 0.4:
                al = int(255 * ease_out((t - 0.4) / 0.5))
                center_text(d, "ANTARCTIC CIRCUMPOLAR", f1, int(H * 0.775), WHITE, 8, al)
            if t >= 1.0:
                al = int(255 * ease_out((t - 1.0) / 0.5))
                center_text(d, "CURRENT", f1, int(H * 0.83), CYAN, 8, al)
            if t >= 2.5:
                al = int(255 * ease_out((t - 2.5) / 0.5))
                center_text(d, "WARM WATER — BLOCKED", f2, int(H * 0.895), RED, 6, al)
            if t >= 3.6:
                al = int(255 * ease_out((t - 3.6) / 0.5))
                center_text(d, "ANTARCTICA — SEALED OFF", f2, int(H * 0.945), DIM, 6, al)
            yield img.convert("RGB")

    encode(frames(), "anim_current.mp4", N)

# ============================================================ 5. FREEZE (LIMA + CO2)
def anim_freeze(T=6.8):
    N = int(T * FPS)
    src = Image.open(IMGA / "lima.png").convert("RGB")
    # center-crop to 9:16
    tw, th = src.size
    cw = int(th * 9 / 16)
    x0 = (tw - cw) // 2
    crop = src.crop((x0, 0, x0 + cw, th)).resize((W, H), Image.LANCZOS)
    arr = np.asarray(crop, dtype=np.float32)
    # natural grade
    nat = np.clip(arr * np.array([1.02, 1.04, 1.10]) * 1.12, 0, 255)
    # warm "34 MYA" grade (green-ish warm)
    warm = np.clip(arr * np.array([1.18, 1.06, 0.78]) + np.array([22, 14, -6]), 0, 255)
    f1 = font(F_DISP, 64)
    f2 = font(F_UI, 40)
    fbig = font(F_TITLE, 150)
    fbig2 = font(F_TITLE, 110)

    def frames():
        for i in range(N):
            t = i / FPS
            mix = ease_in(min(1, t / 2.0))
            base = warm * (1 - mix) + nat * mix
            img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
            d = ImageDraw.Draw(img)
            # darken top/bottom for text zones
            shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shade)
            sd.rectangle([0, 0, W, 250], fill=(0, 5, 15, 150))
            sd.rectangle([0, H - 560, W, H], fill=(0, 5, 15, 170))
            img = Image.alpha_composite(img, shade)
            # frost pulse rings
            cx0, cy0 = W // 2, int(H * 0.46)
            for ri, delay in enumerate((1.6, 2.4, 3.2)):
                if t > delay:
                    k = (t - delay) / 2.6
                    if k < 1:
                        rr = 80 + k * 1150
                        alpha = int(150 * (1 - k))
                        d.ellipse([cx0 - rr, cy0 - rr, cx0 + rr, cy0 + rr],
                                  outline=(220, 245, 255, alpha), width=5)
            # CO2 counter
            if t >= 1.0:
                k = min(1, (t - 1.0) / 5.0)
                co2 = int(900 - k * 500)
                al = int(255 * ease_out((t - 1.0) / 0.4))
                d.text((70, 120), "CO2 LEVEL", font=f2, fill=(168, 190, 220, al))
                d.text((60, 170), f"{co2} ppm", font=fbig, fill=(255, 255, 255, al))
                if co2 <= 750 and t >= 2.6:
                    yc = 390
                    d.line([70, yc, 980, yc], fill=(255, 107, 83, 220), width=4)
                    d.text((70, yc + 14), "POINT OF NO RETURN — ~750 ppm", font=f2,
                           fill=(255, 107, 83, 255))
            # temp chip
            if t >= 2.2:
                al = int(255 * ease_out((t - 2.2) / 0.4))
                d.rounded_rectangle([60, H - 520, 640, H - 400], radius=18,
                                    fill=(10, 30, 55, 200), outline=(70, 130, 190, 160), width=3)
                d.text((90, H - 495), "+5°C WARMER THAN TODAY", font=f2, fill=(255, 181, 107, al))
                d.text((90, H - 440), "↓  THE WORLD COOLS", font=f2, fill=(168, 190, 220, al))
            if t >= 3.6:
                al = int(255 * ease_out((t - 3.6) / 0.45))
                center_text(d, "THE FREEZE BEGINS", f1, H - 330, WHITE, 8, al)
            if t >= 4.6:
                al = int(255 * ease_out((t - 4.6) / 0.45))
                center_text(d, "ICE UP TO 4 KM DEEP", f1, H - 260, CYAN, 8, al)
            yield img.convert("RGB")

    encode(frames(), "anim_freeze.mp4", N)

# ============================================================ 6. ARCTIC (split)
def anim_arctic(T=5.8):
    N = int(T * FPS)
    stars, tw = starfield(300, seed=51, haze=0.12)
    import math
    f1 = font(F_DISP, 52)
    f2 = font(F_UI, 36)
    f3 = font(F_MED, 32)
    cxL, cxR = W // 2 - 300, W // 2 + 300
    cyc = int(H * 0.40)
    RR = 260

    def frames():
        for i in range(N):
            t = i / FPS
            cv = stars.copy()
            img = Image.fromarray(np.clip(cv, 0, 255).astype(np.uint8)).convert("RGBA")
            d = ImageDraw.Draw(img)
            # left: Antarctica (land circle, white)
            d.ellipse([cxL - RR, cyc - RR, cxL + RR, cyc + RR], fill=(226, 238, 250, 255))
            d.ellipse([cxL - RR, cyc - RR, cxL + RR, cyc + RR], outline=(120, 165, 210, 255), width=5)
            # ocean ring around it
            d.ellipse([cxL - RR - 40, cyc - RR - 40, cxL + RR + 40, cyc + RR + 40],
                      outline=(70, 140, 210, 200), width=3)
            # right: Arctic (ocean circle, dark) with land ring
            d.ellipse([cxR - RR, cyc - RR, cxR + RR, cyc + RR], fill=(18, 44, 92, 255))
            d.ellipse([cxR - RR - 40, cyc - RR - 40, cxR + RR + 40, cyc + RR + 40],
                      fill=(120, 108, 84, 120), outline=(150, 130, 100, 220), width=4)
            # warm arrows into arctic (reaching it)
            if t >= 1.6:
                k = min(1, (t - 1.6) / 0.8)
                yy = cyc + RR + 60 + k * 90
                d.line([cxR, cyc + RR + 90, cxR, yy], fill=(255, 107, 83, 230), width=9)
                if k >= 0.99:
                    spread = ease_out(min(1, (t - 2.4) / 0.7))
                    for sgn in (-1, 1):
                        for f in (0.3, 0.7):
                            d.line([cxR + sgn * 4, yy + 4, cxR + sgn * 70 * (1 + f) * spread, yy + 46 * f * spread],
                                   fill=(255, 107, 83, int(190 * spread)), width=7)
            # labels
            if t >= 0.3:
                al = int(255 * ease_out((t - 0.3) / 0.45))
                d.text((cxL - 240, cyc - RR - 170), "LAND INSIDE", font=f2, fill=(154, 216, 255, al))
                d.text((cxR - 200, cyc - RR - 170), "OCEAN INSIDE", font=f2, fill=(255, 181, 107, al))
            if t >= 1.0:
                al = int(255 * ease_out((t - 1.0) / 0.45))
                d.text((cxL - 150, cyc + RR + 64), "ANTARCTICA", font=f1, fill=(154, 216, 255, al))
                d.text((cxR - 130, cyc + RR + 64), "ARCTIC", font=f1, fill=(255, 181, 107, al))
            # timeline
            if t >= 2.2:
                al = int(255 * ease_out((t - 2.2) / 0.45))
                yT = int(H * 0.83)
                x0, x1 = 180, W - 180
                d.line([x0, yT, x1, yT], fill=(70, 110, 160, al), width=6)
                moving = ease_in(min(1, (t - 2.2) / 2.2))
                mx = x0 + (x1 - x0) * moving
                d.ellipse([mx - 14, yT - 14, mx + 14, yT + 14], fill=(255, 255, 255, al))
                xA, xAr = x0 + (x1 - x0) * 0.22, x0 + (x1 - x0) * 0.94
                d.ellipse([xA - 8, yT - 8, xA + 8, yT + 8], fill=(103, 232, 249, al))
                d.ellipse([xAr - 8, yT - 8, xAr + 8, yT + 8], fill=(255, 181, 107, al))
                d.text((xA - 90, yT + 26), "34 MYA", font=f3, fill=(103, 232, 249, al))
                d.text((xAr - 110, yT + 26), "2.6 MYA", font=f3, fill=(255, 181, 107, al))
            if t >= 3.2:
                al = int(255 * ease_out((t - 3.2) / 0.5))
                center_text(d, "25 MILLION YEARS LATER", f1, int(H * 0.90), WHITE, 8, al)
            yield img.convert("RGB")

    encode(frames(), "anim_arctic.mp4", N)

if __name__ == "__main__":
    anim_cold_open()
    anim_paleo()
    anim_gateway()
    anim_current()
    anim_freeze()
    anim_arctic()
    print("all anims done")
