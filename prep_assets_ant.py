#!/usr/bin/env python3
"""ANTARCTICA FROZE FIRST — prep: organize real assets, fonts, GIF->MP4 clips,
VO manifest with estimated word timings, brand lockups."""
import subprocess, json, shutil
from pathlib import Path

BASE = Path(__file__).parent
SEARCH = BASE / "image-search"
IMGA = BASE / "images_ant"
SCA = BASE / "scenes_ant"
FONTS = BASE / "fonts"
BRAND = BASE / "brand"
IMGA.mkdir(exist_ok=True)
SCA.mkdir(exist_ok=True)
FONTS.mkdir(exist_ok=True)
BRAND.mkdir(exist_ok=True)

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
FP = FF.replace("ffmpeg-linux", "ffprobe-linux") if False else FF

def ff(args, **kw):
    return subprocess.run([FF, "-y", "-loglevel", "error", *args], capture_output=True, text=True, **kw)

import re as _re
def ffprobe(p):
    r = subprocess.run([FF, "-i", str(p), "-f", "null", "-"],
                       capture_output=True, text=True)
    m = _re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        raise RuntimeError(f"no duration for {p}: {r.stderr[-300:]}")
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)

# ---------------- fonts ----------------
FONT_SRC = Path("/tmp/fonts2")
import tarfile
for tgz, want in [("anton.tgz", ["Anton-Regular.ttf"]),
                  ("oswald.tgz", ["Oswald-Bold.ttf", "Oswald-SemiBold.ttf", "Oswald-Medium.ttf"]),
                  ("archivo-black.tgz", ["ArchivoBlack-Regular.ttf"]),
                  ("inter.tgz", ["Inter-Bold.ttf", "Inter-Medium.ttf", "Inter-Regular.ttf"])]:
    with tarfile.open(FONT_SRC / tgz) as tf:
        for m in tf.getmembers():
            base = m.name.split("/")[-1]
            if base in want:
                dest = FONTS / base
                with tf.extractfile(m) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
                print("font", dest)
FONT_TITLE = str(FONTS / "ArchivoBlack-Regular.ttf")       # display titles
FONT_DISP = str(FONTS / "Anton-Regular.ttf")               # big condensd
FONT_UI = str(FONTS / "Oswald-SemiBold.ttf")               # HUD/captions
FONT_BODY = str(FONTS / "Inter-Bold.ttf")                  # body bold
FONT_NUM = str(FONTS / "Inter-Bold.ttf")

# ---------------- stills ----------------
STILLS = {
    "lima":        (SEARCH / "antarctica-lima-satellite-mosaic-nasa-bl-1.png", "png"),
    "eocene":      (SEARCH / "eocene-antarctica-reconstruction-map-34--2.webp", "png"),
    "drake_map":   (SEARCH / "drake-passage-satellite-view-south-ameri-1.png", "png"),
    "drake_ocean": (SEARCH / "drake-passage-satellite-view-south-ameri-4.jpg", "jpg"),
    "acc1":        (SEARCH / "antarctic-circumpolar-current-flow-visua-1.jpg", "jpg"),
    "acc2":        (SEARCH / "antarctic-circumpolar-current-flow-visua-2.jpg", "jpg"),
    "arctic1":     (SEARCH / "arctic-sea-ice-nasa-satellite-minimum-ex-3.jpg", "jpg"),
    "arctic2":     (SEARCH / "arctic-sea-ice-nasa-satellite-minimum-ex-4.jpg", "jpg"),
    "arctic3":     (SEARCH / "arctic-sea-ice-nasa-satellite-minimum-ex-1.webp", "jpg"),
    "glacier1":    (SEARCH / "antarctica-glacier-aerial-view-ice-sheet-1.jpg", "jpg"),
    "glacier2":    (SEARCH / "antarctica-glacier-aerial-view-ice-sheet-2.jpg", "jpg"),
    "iceberg1":    (SEARCH / "antarctica-iceberg-ocean-close-up-1.jpg", "jpg"),
    "icebridge":   (SEARCH / "nasa-operation-icebridge-antarctica-glac-3.jpg", "jpg"),
    "co2_graph":   (SEARCH / "global-temperature-co2-last-66-million-y-2.jpg", "jpg"),
}
from PIL import Image
for name, (src, ext) in STILLS.items():
    if not src.exists():
        print("MISS", name); continue
    dest = IMGA / f"{name}.{ext}"
    if ext == "png":
        Image.open(src).convert("RGB").save(dest, "PNG")
    else:
        Image.open(src).convert("RGB").save(dest, "JPEG", quality=93)
    print("still", name, Image.open(dest).size)

# ---------------- real animated clips ----------------
CLIPS = {
    "clip_arctic":    SEARCH / "arctic-sea-ice-growth-animation-gif-nasa-1.gif",   # Wikimedia Arctic sea-ice loss (real)
    "clip_icesheet":  SEARCH / "antarctica-ice-sheet-flow-animation-gif--1.gif",  # NASA ice-sheet GIF (real)
    "clip_seaice":    Path("/tmp/fonts2/Sea-ice-leads-main/SeaIce_01112002_15032003.gif"),  # real sea-ice leads anim
}
for name, src in CLIPS.items():
    out = SCA / f"{name}.mp4"
    if src.exists():
        # upscale + center-crop to 9:16 with slow drift
        vf = ("scale=1080:1920:force_original_aspect_ratio=increase,"
              "crop=1080:1920,"
              "zoompan=z='1.12+0.04*sin(2*PI*on/240)':x='iw/2-(iw/zoom/2)':"
              "y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
              "unsharp=5:5:0.4,eq=saturation=1.15:contrast=1.06")
        ff(["-i", str(src), "-vf", vf, "-t", "14", "-r", "30",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(out)])
        print("clip", name, ffprobe(out), "s")
    else:
        print("MISS clip", name)

# ---------------- VO manifest ----------------
VO = BASE / "audio" / "vo_ant"
SCENES = [
    ("s1", "Antarctica froze twenty-five million years before the Arctic. And science finally knows why. Thirty-four million years ago, Earth was five degrees warmer than today. Then, the bottom of the world turned to ice."),
    ("s2", "This was no frozen desert. Fossils prove Antarctica was covered in forests. Rivers ran where ice now stands four kilometers thick. And the ocean around it was warm. So what happened?"),
    ("s3", "Two ancient gateways tore open. South America ripped away from Antarctica, carving out the Drake Passage. Australia drifted north, unlocking the Tasmanian Gateway. For the first time, an ocean current could race around the entire continent."),
    ("s4", "That current became the strongest on Earth. The Antarctic Circumpolar Current. A wall of cold water, circling endlessly. It blocked every warm current from the north. Antarctica was sealed inside its own refrigerator."),
    ("s5", "Then, carbon dioxide dropped past the point of no return. Ice spread across the continent in a geological instant. In a few hundred thousand years, Antarctica vanished under ice up to four kilometers deep. And it never melted back."),
    ("s6", "But the Arctic waited twenty-five million more years. Because it is an ocean, surrounded by land. And warm currents kept reaching it. Antarctica froze first, because it was land surrounded by ocean. Cut off. And alone."),
    ("s7", "Today, that one current still steers the climate of the whole planet. One current, born thirty-four million years ago. So here is my question: what do you think is hiding under all that ice? Tell me in the comments."),
    ("s8", "Follow Universe Impact."),
]
import re
manifest = []
for name, text in SCENES:
    mp3 = VO / f"{name}.mp3"
    dur = ffprobe(mp3)
    # --- estimate word timings: sentences proportional to chars, words to len ---
    sents = [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]
    wl = [len(s) for s in sents]
    total_chars = sum(wl)
    words, t = [], 0.0
    for si, s in enumerate(sents):
        sdur = dur * wl[si] / total_chars
        ws = s.split()
        cl = [len(w) for w in ws]
        csum = sum(cl)
        st = t
        for w, c in zip(ws, cl):
            wd = sdur * c / csum
            words.append({"w": w, "t": round(st, 3), "d": round(wd, 3)})
            st += wd
        t += sdur
    manifest.append({"name": name, "file": str(mp3), "duration": round(dur, 3),
                     "text": text, "words": words})
(BASE / "audio" / "vo_ant" / "manifest.json").write_text(json.dumps(manifest, indent=1))
print("VO manifest:", {m["name"]: m["duration"] for m in manifest})
print("TOTAL VO:", round(sum(m["duration"] for m in manifest), 2))

# ---------------- brand lockups ----------------
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

def orbit_icon(size, glow=(64, 200, 255)):
    """Tilted ring + glowing dot planet. Supersampled."""
    ss = 4
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S // 2, S // 2
    # glow halo
    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    for r, a in [(S * 0.42, 90), (S * 0.30, 140), (S * 0.20, 190)]:
        hd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=glow + (a,))
    halo = halo.filter(ImageFilter.GaussianBlur(S * 0.06))
    img = Image.alpha_composite(img, halo)
    # ring (tilted ellipse) - draw as rotated ellipse: use arc with thick width
    rx, ry = S * 0.30, S * 0.115
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=(235, 245, 255, 255),
               width=max(2, S // 55))
    ring = ring.rotate(-24, center=(cx, cy), resample=Image.BICUBIC)
    img = Image.alpha_composite(img, ring)
    # planet dot on ring
    px = cx + S * 0.30 * 0.92
    py = cy
    dot = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dot)
    r = S * 0.075
    dd.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255, 255))
    dd.ellipse([px - r * 0.55, py - r * 0.55, px + r * 0.55, py + r * 0.55], fill=glow + (255,))
    dot = dot.filter(ImageFilter.GaussianBlur(1.2 * ss))
    img = Image.alpha_composite(img, dot)
    return img.resize((size, size), Image.LANCZOS)

def make_watermark():
    W = 240
    icon = orbit_icon(int(W * 0.62))
    fname = ImageFont.truetype(FONT_DISP, int(W * 0.185))
    fname2 = ImageFont.truetype(FONT_DISP, int(W * 0.145))
    img = Image.new("RGBA", (W, int(W * 1.02)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # soft dark plate for legibility
    plate = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    pd.rounded_rectangle([4, 4, W - 4, img.height - 4], radius=26, fill=(0, 0, 0, 120))
    plate = plate.filter(ImageFilter.GaussianBlur(2))
    img = Image.alpha_composite(img, plate)
    img.paste(icon, (int(W * 0.19), int(W * 0.045)), icon)
    for i, (txt, f) in enumerate([("UNIVERSE", fname), ("IMPACT", fname2)]):
        bb = d.textbbox((0, 0), txt, font=f)
        tw = bb[2] - bb[0]
        y = int(W * (0.52 if i == 0 else 0.70))
        d.text(((W - tw) / 2 - bb[0], y - bb[1]), txt, font=f, fill=(255, 255, 255, 235))
    img.save(BRAND / "watermark_ant.png")
    print("brand watermark", img.size)

def make_banner():
    W = 1200
    H = int(W * 0.30)
    ss = 3
    img = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    icon = orbit_icon(int(H * ss * 0.78))
    img.paste(icon, (int(W * ss * 0.03), int(H * ss * 0.11)), icon)
    fbig = ImageFont.truetype(FONT_TITLE, int(H * ss * 0.30))
    fsub = ImageFont.truetype(FONT_UI, int(H * ss * 0.115))
    tx = int(W * ss * 0.185)
    d.text((tx, int(H * ss * 0.16)), "UNIVERSE IMPACT", font=fbig, fill=(245, 248, 255, 255))
    d.text((tx, int(H * ss * 0.62)), "SCIENCE THAT FEELS LIKE SCIENCE FICTION",
           font=fsub, fill=(140, 215, 255, 255))
    img = img.resize((W, H), Image.LANCZOS)
    img.save(BRAND / "banner_ant.png")
    print("brand banner", img.size)

make_watermark()
make_banner()
print("prep done")
