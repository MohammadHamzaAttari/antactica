#!/usr/bin/env python3
"""Procedural cinematic animations (numpy + PIL) rendered frame-by-frame.

 anim_hook      — black -> point of light -> pull-back starburst -> kinetic title
 anim_supernova — unstable first star -> flash + shockwave + ejecta -> gas cloud
 anim_timeline  — vertical cosmic timeline with sequential node reveals
 anim_earth     — warp travel -> Earth appears -> pulls back to a dot

Rendered at 540x960, upscaled to 1080x1920 by ffmpeg during encode.
"""
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

BASE = Path(__file__).parent
PROC = BASE / "proc"
PROC.mkdir(parents=True, exist_ok=True)
IMG = BASE / "images"

W, H = 540, 960
FPS = 30
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

CX, CY = W // 2, int(H * 0.42)  # cosmic action center (above FB UI zone)


# ---------- helpers ----------

def fbm(shape, octaves=6, base_freq=3.0, persistence=0.55, seed=1):
    r = np.random.default_rng(seed)
    h, w = shape
    out = np.zeros((h, w), dtype=np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        freq = base_freq * (2 ** o)
        gw, gh = max(2, int(freq)), max(2, int(freq * h / w))
        g = r.random((gh, gw)).astype(np.float32)
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * (np.asarray(img, dtype=np.float32) / 255.0)
        total += amp
        amp *= persistence
    return out / total


def _blur_layer(layer, blur):
    if blur > 0:
        return np.asarray(
            Image.fromarray(np.clip(layer * 8, 0, 255).astype(np.uint8))
            .filter(ImageFilter.GaussianBlur(blur)), dtype=np.float32) / 8.0
    return layer


def glow_points(canvas, xs, ys, brights, color, blur=1.8):
    """Additive point splat with gaussian glow.
    color: (3,) single color OR (N,3) per-point colors (RGB 0-255)."""
    xi = np.clip(np.asarray(xs, dtype=int), 0, W - 1)
    yi = np.clip(np.asarray(ys, dtype=int), 0, H - 1)
    b = np.asarray(brights, dtype=np.float32)
    colarr = np.asarray(color, dtype=np.float32)
    if colarr.ndim == 1:
        layer = np.zeros((H, W), dtype=np.float32)
        np.add.at(layer, (yi, xi), b)
        layer = _blur_layer(layer, blur)
        canvas += layer[..., None] * colarr / 255.0
    else:
        cl = np.zeros((H, W, 3), dtype=np.float32)
        for c in range(3):
            ch = np.zeros((H, W), dtype=np.float32)
            np.add.at(ch, (yi, xi), b * colarr[:, c] / 255.0)
            cl[..., c] = _blur_layer(ch, blur)
        canvas += cl
    return canvas


def encode(frames_iter, out_name, total_frames):
    out = PROC / out_name
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=1080:1920:flags=lanczos,unsharp=5:5:0.35",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i, fr in enumerate(frames_iter):
        p.stdin.write(fr)
        if i % 60 == 0:
            print(f"    {out_name}: {i}/{total_frames}")
    p.stdin.close()
    p.wait()
    print(f"  OK {out} ({out.stat().st_size/1024:.0f}KB)")


def text_img(txt, size, fill, stroke=2, stroke_fill=(0, 0, 0), max_width=None):
    """Render text to RGBA bitmap; auto-shrinks font until it fits max_width."""
    if max_width is None:
        max_width = W - 48          # 24px margin per side on the 540px canvas
    fs = size
    while fs > 14:
        font = ImageFont.truetype(FONT_B, fs)
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox = d.textbbox((0, 0), txt, font=font, stroke_width=stroke)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_width:
            break
        fs -= 2
    font = ImageFont.truetype(FONT_B, fs)
    img = Image.new("RGBA", (tw + 24, th + 24), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((12 - bbox[0], 12 - bbox[1]), txt, font=font,
                             fill=fill, stroke_width=stroke, stroke_fill=stroke_fill + (255,))
    return img


def paste_scaled(frame_pil, txt_img, center, scale, alpha):
    if scale != 1.0:
        nw, nh = max(1, int(txt_img.width * scale)), max(1, int(txt_img.height * scale))
        txt_img = txt_img.resize((nw, nh), Image.BICUBIC)
    if alpha < 1.0:
        a = txt_img.getchannel("A").point(lambda v: int(v * alpha))
        txt_img = txt_img.copy()
        txt_img.putalpha(a)
    frame_pil.alpha_composite(txt_img, (int(center[0] - txt_img.width / 2),
                                        int(center[1] - txt_img.height / 2)))


def ease_out_cubic(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


# ---------- 1. HOOK ----------
def anim_hook(T=9.43):
    N = int(T * FPS)
    rng = np.random.default_rng(101)
    n_p = 800
    ang = rng.random(n_p) * 2 * np.pi
    spd = 30 + rng.random(n_p) ** 1.6 * 150          # px/s
    birth = 2.3 + rng.random(n_p) * 0.8
    col = np.zeros((n_p, 3))
    col[:, 0] = 0.75 + rng.random(n_p) * 0.25
    col[:, 1] = 0.82 + rng.random(n_p) * 0.18
    col[:, 2] = 1.0
    t1 = text_img("100 MILLION YEARS", 62, (255, 255, 255, 255), stroke=3)
    t2 = text_img("AFTER THE BIG BANG", 40, (255, 150, 70, 255), stroke=3)
    # faint primordial backdrop visible from frame 0
    neb = fbm((H, W), octaves=6, base_freq=2.4, seed=61)
    neb = (np.clip(neb * 0.95 - 0.22, 0, 1) ** 1.25)
    neb_col = np.stack([neb * 85, neb * 130, neb * 215], axis=-1)

    def frames():
        for i in range(N):
            t = i / FPS
            cv = np.zeros((H, W, 3), dtype=np.float32)
            # primordial haze: fades in over first 0.7s, then slow luminous breathing
            nb = min(1.0, t / 0.25) * (0.8 + 0.2 * np.sin(t * 0.9))
            cv += neb_col * nb
            # deep glow present from the start, grows through the pull-back
            g = t / 9.4
            yy, xx = np.mgrid[0:H, 0:W]
            d2 = (xx - CX) ** 2 + (yy - CY) ** 2
            cv += (np.exp(-d2 / (2 * (150 + 60 * g) ** 2)) * (26 + 18 * g))[..., None] * \
                  np.array([0.35, 0.5, 1.0], dtype=np.float32)

            # the point of light
            if t > 0.45:
                flick = 0.8 + 0.2 * np.sin(t * 21)
                cv = glow_points(cv, [CX], [CY], [95 * flick],
                                 [235, 240, 255], blur=2.0)
                cv = glow_points(cv, [CX], [CY], [30 * flick],
                                 [200, 220, 255], blur=9.0)

            # pull-back starburst
            alive = t >= birth
            if alive.any():
                dt = (t - birth)[alive]
                r = (spd[alive] * dt) * (1.0 + 0.35 * dt)
                x = CX + np.cos(ang[alive]) * r * 1.0
                y = CY + np.sin(ang[alive]) * r * (H / W) * 0.9
                a = np.clip(1.0 - r / 460.0, 0, 1) ** 1.4 * np.clip(dt * 3, 0, 1)
                if t >= 6.3:
                    a *= 0.45
                # streaks: 3 points along radial dir
                for k, wgt in ((0.0, 1.0), (0.5, 0.6), (1.0, 0.3)):
                    xs = x - np.cos(ang[alive]) * r * 0.02 * k * spd[alive] / 60
                    ys = y - np.sin(ang[alive]) * r * 0.018 * k * spd[alive] / 60
                    cv = glow_points(cv, xs, ys, a * 70 * wgt, col[alive] * 255, blur=1.6)

            im = Image.fromarray(np.clip(cv, 0, 255).astype(np.uint8)).convert("RGBA")

            # kinetic title
            if t >= 6.3:
                s = 2.6 - 1.6 * ease_out_cubic((t - 6.3) / 0.32)
                al = ease_out_cubic((t - 6.3) / 0.18)
                drift = 1.0 + 0.04 * ease_out_cubic((t - 6.62) / 2.8)
                paste_scaled(im, t1, (CX, int(H * 0.40)), s * drift, al)
            if t >= 7.55:
                al = ease_out_cubic((t - 7.55) / 0.45)
                paste_scaled(im, t2, (CX, int(H * 0.40) + 88), 1.0, al)

            yield np.asarray(im.convert("RGB"), dtype=np.uint8).tobytes()

    encode(frames(), "anim_hook.mp4", N)


# ---------- 2. SUPERNOVA ----------
def anim_supernova(T=11.02):
    N = int(T * FPS)
    rng = np.random.default_rng(202)
    n_p = 1000
    ang = rng.random(n_p) * 2 * np.pi
    spd = 28 + rng.random(n_p) ** 1.5 * 135
    birth = 1.25 + rng.random(n_p) * 2.0
    pal = np.array([[255, 150, 60], [255, 90, 50], [130, 205, 255], [255, 240, 220]])
    wts = np.array([0.38, 0.27, 0.20, 0.15])
    col = pal[rng.choice(4, n_p, p=wts / wts.sum())]
    neb = fbm((H, W), octaves=7, base_freq=2.5, seed=31)
    neb = (np.clip(neb * 0.8 - 0.32, 0, 1) ** 1.5)
    neb_col = np.stack([neb * 255, neb * 120, neb * 70], axis=-1) * 0.9
    yy, xx = np.mgrid[0:H, 0:W]
    d2c = (xx - CX) ** 2 + (yy - CY) ** 2

    def frames():
        for i in range(N):
            t = i / FPS
            cv = np.zeros((H, W, 3), dtype=np.float32)

            if t < 1.25:
                # unstable giant star
                p = t / 1.25
                puls = 0.85 + 0.15 * np.sin(t * 3 * 2 * np.pi) + 0.08 * np.sin(t * 11)
                rad = 16 + 14 * p
                cv += (np.exp(-d2c / (2 * (rad * 3.2) ** 2)) * 70 * puls)[..., None] * \
                      np.array([0.7, 0.8, 1.0], dtype=np.float32)
                cv += (np.exp(-d2c / (2 * rad ** 2)) * 255)[..., None] * \
                      np.array([0.92, 0.95, 1.0], dtype=np.float32)
            else:
                te = t - 1.25
                # flash
                flash = max(0.0, 1.0 - te / 0.5) ** 2
                cv += flash * 230
                # remnant
                cv += (np.exp(-d2c / (2 * 7 ** 2)) * 200)[..., None] * \
                      np.array([0.75, 0.85, 1.0], dtype=np.float32)
                # shockwave rings
                R1 = 30 + 105 * te - 7 * te ** 2
                if 0 < R1 < 700:
                    ring = np.exp(-((np.sqrt(d2c) - R1) ** 2) / (2 * 5.5 ** 2))
                    cv += (ring * 130 * max(0.0, 1 - te / 6.5))[..., None] * \
                          np.array([0.8, 0.9, 1.0], dtype=np.float32)
                R2 = 15 + 55 * te - 3 * te ** 2
                if 0 < R2 < 500:
                    ring2 = np.exp(-((np.sqrt(d2c) - R2) ** 2) / (2 * 3.5 ** 2))
                    cv += (ring2 * 70 * max(0.0, 1 - te / 5.0))[..., None] * \
                          np.array([1.0, 0.6, 0.35], dtype=np.float32)

                # ejecta
                alive = t >= birth
                if alive.any():
                    dt = (t - birth)[alive]
                    r = spd[alive] * dt * (1 + 0.18 * dt)
                    x = CX + np.cos(ang[alive]) * r
                    y = CY + np.sin(ang[alive]) * r * (H / W) * 0.95
                    a = (np.clip(1.0 - r / 520.0, 0, 1) ** 1.3) * np.clip(dt * 4, 0, 1)
                    if t > 6.5:
                        a *= max(0.32, 1.0 - (t - 6.5) / 4.6)
                    for k, wgt in ((0.0, 1.0), (0.6, 0.55), (1.2, 0.25)):
                        xs = x - np.cos(ang[alive]) * k * spd[alive] * 0.016
                        ys = y - np.sin(ang[alive]) * k * spd[alive] * 0.016
                        cv = glow_points(cv, xs, ys, a * 62 * wgt, col[alive], blur=1.5)

                # enriched gas cloud crossfade
                if t > 6.5:
                    na = min(1.0, (t - 6.5) / 4.0) * 0.5
                    cv = cv * (1 - na) + neb_col * na

            im = Image.fromarray(np.clip(cv, 0, 255).astype(np.uint8))
            yield im.tobytes()

    encode(frames(), "anim_supernova.mp4", N)


# ---------- 3. TIMELINE ----------
NODES = ["BIG BANG", "FIRST STARS", "SUPERNOVAE", "BUILDING BLOCKS", "ROCKY WORLDS?"]


def anim_timeline(T=8.66):
    N = int(T * FPS)
    rng = np.random.default_rng(303)
    n_st = 130
    st_x, st_y = rng.integers(0, W, n_st), rng.integers(0, H, n_st)
    st_b = (rng.random(n_st) ** 2 * 120 + 15).astype(np.float32)
    top_y, bot_y = 130, 830
    sides = ["rm", "lm", "rm", "lm", "rm"]        # alternate label sides
    rail_x = CX
    node_y = np.linspace(top_y + 25, bot_y - 25, 5)
    travel_T = 7.1
    t_font, l_font = ImageFont.truetype(FONT_B, 26), ImageFont.truetype(FONT_B, 24)
    dd = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

    # measured label placement: left labels END at rail-24, right labels START at rail+24
    # shrink font per-label until it fits with 20px safety margin on both edges
    label_imgs = []
    for label, just in zip(NODES, sides):
        fs = 30
        while fs >= 18:
            f = ImageFont.truetype(FONT_B, fs)
            tw = dd.textlength(label, font=f)
            avail = (rail_x - 24 - 20) if just == "rm" else (W - rail_x - 24 - 20)
            if tw <= avail:
                break
            fs -= 2
        label_imgs.append((label, just, fs))

    def frames():
        for i in range(N):
            t = i / FPS
            cv = np.zeros((H, W, 3), dtype=np.float32)
            cv += 6
            cv = glow_points(cv, st_x, st_y, st_b, [220, 228, 255], blur=0.8)

            prog = ease_out_cubic(t / travel_T) if t < travel_T else 1.0
            dot_y = top_y + (bot_y - top_y) * prog

            # rail
            rail = np.zeros((H, W), dtype=np.float32)
            rail[int(top_y):int(max(top_y, dot_y)) + 1, CX - 1:CX + 2] = 1.0
            cv += (rail * 55)[..., None] * np.array([1.0, 0.62, 0.25], dtype=np.float32)
            rail_full = np.zeros((H, W), dtype=np.float32)
            rail_full[int(max(top_y, dot_y)):bot_y + 1, CX:CX + 1] = 1.0
            cv += (rail_full * 26)[..., None] * np.array([0.6, 0.65, 0.8], dtype=np.float32)

            im = Image.fromarray(np.clip(cv, 0, 255).astype(np.uint8)).convert("RGBA")
            dr = ImageDraw.Draw(im)

            for j, ((label, just, fs), ny) in enumerate(zip(label_imgs, node_y)):
                active = dot_y >= ny - 2
                font = ImageFont.truetype(FONT_B, fs)
                tw = dd.textlength(label, font=font)
                if just == "rm":
                    tx, ty = rail_x - 24 - tw, ny - fs // 2 - 2
                    conn_x2 = rail_x - 24 - tw - 8
                else:
                    tx, ty = rail_x + 24, ny - fs // 2 - 2
                    conn_x2 = rail_x + 24 + tw + 8
                # connector
                if active:
                    dr.line([rail_x, ny, conn_x2, ny],
                            fill=(255, 130, 50, 200), width=2)
                dr.ellipse([rail_x - 6, ny - 6, rail_x + 6, ny + 6],
                           fill=(255, 150, 60, 255) if active else (70, 80, 110, 255))
                if active:
                    dr.ellipse([rail_x - 11, ny - 11, rail_x + 11, ny + 11],
                               outline=(255, 170, 80, 160), width=2)
                alpha = 255 if active else 60
                dr.text((tx, ty), label, font=font,
                        fill=(255, 255, 255, alpha) if active else (150, 158, 185, alpha),
                        stroke_width=2, stroke_fill=(0, 0, 0, 200))

            # travelling dot + trail glow
            glow = np.zeros((H, W), dtype=np.float32)
            gy = int(np.clip(dot_y, 0, H - 1))
            glow[gy - 2:gy + 3, CX - 2:CX + 3] = 1.0
            glow = np.asarray(Image.fromarray((glow * 255).astype(np.uint8))
                              .filter(ImageFilter.GaussianBlur(7)), dtype=np.float32) / 255
            cv2 = np.asarray(im.convert("RGB"), dtype=np.float32)
            cv2 += (glow * 160)[..., None] * np.array([1.0, 0.7, 0.35], dtype=np.float32)
            im = Image.fromarray(np.clip(cv2, 0, 255).astype(np.uint8)).convert("RGBA")

            # headline appears mid-scene (auto-fit width)
            if t > 5.6:
                a = int(255 * ease_out_cubic((t - 5.6) / 0.6))
                dr2 = ImageDraw.Draw(im)
                fs_h = 26
                while fs_h > 16 and dd.textlength("A 13.8-BILLION-YEAR STORY",
                                                  font=ImageFont.truetype(FONT_B, fs_h)) > W - 60:
                    fs_h -= 2
                dr2.text((CX, 60), "A 13.8-BILLION-YEAR STORY",
                         font=ImageFont.truetype(FONT_B, fs_h),
                         fill=(255, 255, 255, a), anchor="mm",
                         stroke_width=2, stroke_fill=(0, 0, 0, a))
            if t > 7.3:
                a2 = int(255 * ease_out_cubic((t - 7.3) / 0.5))
                dr3 = ImageDraw.Draw(im)
                fs_d = 22
                while fs_d > 12 and dd.textlength("SIMULATION-INSPIRED VISUALIZATION",
                                                  font=ImageFont.truetype(FONT_B, fs_d)) > W - 40:
                    fs_d -= 1
                dr3.text((CX, 908), "SIMULATION-INSPIRED VISUALIZATION",
                         font=ImageFont.truetype(FONT_B, fs_d),
                         fill=(170, 180, 210, a2), anchor="mm")

            yield np.asarray(im.convert("RGB"), dtype=np.uint8).tobytes()

    encode(frames(), "anim_timeline.mp4", N)


# ---------- 4. EARTH PULL-BACK ----------
def anim_earth(T=9.91):
    N = int(T * FPS)
    rng = np.random.default_rng(404)
    n_s = 300
    ang = rng.random(n_s) * 2 * np.pi
    r0 = 20 + rng.random(n_s) * 240
    spd = 40 + rng.random(n_s) * 200
    tw = rng.random(n_s)

    # earth sprite
    es = 380
    earth_full = Image.open(IMG / "earth_apollo17.jpg").convert("RGB")
    w0, h0 = earth_full.size
    side = min(w0, h0)
    earth_full = earth_full.crop(((w0 - side) // 2, (h0 - side) // 2,
                                  (w0 + side) // 2, (h0 + side) // 2)).resize((es, es), Image.LANCZOS)
    # spherical shading
    yy, xx = np.mgrid[0:es, 0:es]
    dx, dy = (xx - es / 2) / (es / 2), (yy - es / 2) / (es / 2)
    rr = np.sqrt(dx ** 2 + dy ** 2)
    mask = (rr <= 1.0).astype(np.float32)
    shade = np.clip(1.15 - 0.55 * (dx * 0.9 + dy * 0.35), 0.25, 1.15)
    earr = np.asarray(earth_full, dtype=np.float32) * shade[..., None] * mask[..., None]
    earth_arr = np.clip(earr, 0, 255).astype(np.uint8)
    earth_img = Image.fromarray(earth_arr).convert("RGBA")

    FYY, FXX = np.mgrid[0:H, 0:W]
    rr_frame = np.sqrt((FXX - CX) ** 2 + (FYY - CY) ** 2)

    def frames():
        for i in range(N):
            t = i / FPS
            cv = np.zeros((H, W, 3), dtype=np.float32)
            cv += 5

            # warp streaks
            if t < 3.6:
                v = 1.0 + t / 2.2
            elif t < 6.4:
                v = max(0.25, 1.9 - (t - 3.6) * 0.5)
            else:
                v = max(-0.25, 0.35 - (t - 6.4) * 0.12)
            r = (r0 + spd * t * v) % 560
            a = np.clip(1.0 - r / 560.0, 0, 1) * 0.5 * np.clip(v + 0.35, 0.15, 2)
            x = CX + np.cos(ang) * r * 1.05
            y = CY + np.sin(ang) * r * (H / W) * 0.95
            x2 = CX + np.cos(ang) * np.maximum(r - 18 * v - 2, 0) * 1.05
            y2 = CY + np.sin(ang) * np.maximum(r - 18 * v - 2, 0) * (H / W) * 0.95
            # batched streaks: 4 interpolated points per star
            fracs = np.linspace(0, 1, 4)[None, :, None]
            xs_all = (x[:, None, None] * (1 - fracs) + x2[:, None, None] * fracs).ravel()
            ys_all = (y[:, None, None] * (1 - fracs) + y2[:, None, None] * fracs).ravel()
            bs_all = np.repeat(a, 4) * 36
            cv = glow_points(cv, xs_all, ys_all, bs_all, [200, 215, 255], blur=0.7)

            # twinkle stars
            tw_b = (np.sin(t * 3 + tw[:90] * 40) * 0.5 + 0.5) ** 2 * 60
            cv = glow_points(cv, rng2_xs, rng2_ys, tw_b, [255, 255, 255], blur=0.6)

            # earth scale
            if t < 3.4:
                s = 0.03 + 0.05 * (t / 3.4)
            elif t < 6.4:
                s = 0.08 + 0.44 * ease_out_cubic((t - 3.4) / 3.0)
            else:
                s = max(0.012, 0.52 * (1.0 - ease_out_cubic((t - 6.4) / 3.1)))
            esz = max(4, int(es * s))
            if t >= 2.6:
                ei = earth_img.resize((esz, esz), Image.BICUBIC)
                # fade-in of sprite early
                if t < 3.2:
                    ea = ei.getchannel("A").point(lambda v: int(v * (t - 2.6) / 0.6))
                    ei = ei.copy(); ei.putalpha(ea)
                px, py = int(CX - esz / 2), int(CY - esz / 2)
                # atmosphere glow behind
                gl = np.zeros((H, W), dtype=np.float32)
                gl += np.exp(-((rr_frame - esz * 0.55) ** 2) / (2 * (esz * 0.10) ** 2))
                cv += (gl * 46 * min(1.0, s * 2.4))[..., None] * \
                      np.array([0.4, 0.6, 1.0], dtype=np.float32)
                im = Image.fromarray(np.clip(cv, 0, 255).astype(np.uint8)).convert("RGBA")
                im.alpha_composite(ei, (px, py))
            else:
                im = Image.fromarray(np.clip(cv, 0, 255).astype(np.uint8)).convert("RGBA")

            if t > 9.3:
                fa = 1.0 - (t - 9.3) / 0.6
                im = Image.eval(im, lambda v: int(v * max(0.0, fa)))

            yield np.asarray(im.convert("RGB"), dtype=np.uint8).tobytes()

    # static twinkle star positions
    global rng2_xs, rng2_ys
    r2 = np.random.default_rng(405)
    rng2_xs, rng2_ys = r2.integers(0, W, 90), r2.integers(0, H, 90)

    encode(frames(), "anim_earth.mp4", N)


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["hook", "supernova", "timeline", "earth"]
    if "hook" in which:
        print("  [anim_hook]"); anim_hook()
    if "supernova" in which:
        print("  [anim_supernova]"); anim_supernova()
    if "timeline" in which:
        print("  [anim_timeline]"); anim_timeline()
    if "earth" in which:
        print("  [anim_earth]"); anim_earth()
    print("All anims done.")
