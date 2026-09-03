#!/usr/bin/env python3
"""Procedural cosmic stills (numpy fBm): primordial haze, starfields, brand bg."""
import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path

IMG = Path(__file__).parent / "images"
IMG.mkdir(exist_ok=True)
W, H = 1080, 1920

rng = np.random.default_rng(7)


def fbm(shape, octaves=6, base_freq=3.0, persistence=0.55, seed=None):
    """Fractal brownian motion via downsampled random noise upsampling."""
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


def nebula(fname, base_rgb, glow_rgb, n_stars=260, star_bright=0.8, dark_frac=0.55, seed=1):
    """Layered gas cloud + stars."""
    density = fbm((H, W), octaves=7, base_freq=2.5, seed=seed)
    detail = fbm((H, W), octaves=5, base_freq=9.0, seed=seed + 10)
    dens = np.clip(density * 0.75 + detail * 0.35 - dark_frac, 0, 1) ** 1.6

    base = np.zeros((H, W, 3), dtype=np.float32)
    for i in range(3):
        base[..., i] += base_rgb[i] * (0.06 + 0.14 * dens)

    glow = np.zeros((H, W, 3), dtype=np.float32)
    for i in range(3):
        glow[..., i] += glow_rgb[i] * dens

    img = np.clip(base + glow * 0.85, 0, 255)

    # stars
    stars = np.zeros((H, W), dtype=np.float32)
    xs = rng.integers(0, W, n_stars)
    ys = rng.integers(0, H, n_stars)
    for x, y in zip(xs, ys):
        b = rng.random() ** 2.2 * star_bright * 255
        r_s = rng.choice([0, 0, 0, 1])
        stars[max(0, y - r_s):y + r_s + 1, max(0, x - r_s):x + r_s + 1] = b
    stars_img = np.asarray(Image.fromarray(np.clip(stars, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), dtype=np.float32)

    img = img + stars_img[..., None] * (1.0 - dens[..., None] * 0.4)
    img = np.clip(img, 0, 255).astype(np.uint8)
    Image.fromarray(img).save(IMG / fname, quality=92)
    print(f"  {fname}")


def starfield(fname, n_stars=420, pale_dot=None, vignette_str=0.55, seed=3):
    """Sparse starfield on near-black; optional one pale standout dot."""
    r = np.random.default_rng(seed)
    img = np.full((H, W, 3), 4, dtype=np.float32)
    # faint milky haze
    haze = fbm((H, W), octaves=6, base_freq=2.0, seed=seed + 5)
    img += (haze[..., None] * np.array([14, 18, 30], dtype=np.float32))

    for _ in range(n_stars):
        x, y = r.integers(0, W), r.integers(0, H)
        b = r.random() ** 2.4 * 235
        c = np.array([b, b, min(255, b * (1.0 + r.random() * 0.25))])
        rr = r.choice([0, 0, 0, 1])
        img[max(0, y - rr):y + rr + 1, max(0, x - rr):x + rr + 1] = c
    if pale_dot:
        x, y, b = pale_dot
        yy, xx = np.mgrid[0:H, 0:W]
        d2 = (xx - x) ** 2 + (yy - y) ** 2
        glow = np.exp(-d2 / (2 * 42.0 ** 2)) * b * 0.55
        core = np.exp(-d2 / (2 * 5.5 ** 2)) * b
        img += (glow + core)[..., None] * np.array([0.92, 0.95, 1.0], dtype=np.float32)

    # vignette
    yy, xx = np.mgrid[0:H, 0:W]
    rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = 1 - vignette_str * np.clip(rr - 0.35, 0, 1) ** 1.5
    img *= vig[..., None]

    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(IMG / fname, quality=92)
    print(f"  {fname}")


if __name__ == "__main__":
    print("Generating procedural stills...")
    # dark primordial H/He clouds (scene 03/04 alt)
    nebula("proc_primordial.jpg", (10, 16, 34), (40, 70, 120), n_stars=140, dark_frac=0.62, seed=11)
    # enriched dust clouds, slightly warm (scene 05 alt)
    nebula("proc_dust.jpg", (18, 14, 12), (90, 60, 35), n_stars=200, dark_frac=0.60, seed=23)
    # sparse starfield + pale standout dot (credibility scene)
    starfield("proc_credibility.jpg", n_stars=380, pale_dot=(W // 2 + 60, int(H * 0.40), 200), seed=31)
    # clean starfield (timeline bg / CTA bg)
    starfield("proc_stars.jpg", n_stars=520, seed=44)
    # brand outro nebula (subtle)
    nebula("proc_brand.jpg", (8, 10, 22), (30, 46, 92), n_stars=300, dark_frac=0.66, seed=57)
    print("Done.")
