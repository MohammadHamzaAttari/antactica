#!/usr/bin/env python3
"""ANTARCTICA FROZE FIRST — master build (v2: johnvansickle ffmpeg, dip transitions).
Real NASA imagery + real animated clips + procedural animations,
word-synced karaoke captions, HUD chips, source credits, watermark,
cinematic music bed + SFX, sidechain ducking, loudnorm master.
Output: antarctica_froze_first_9x16.mp4 (1080x1920@30)."""
import subprocess, json, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

BASE = Path(__file__).parent
IMGA = BASE / "images_ant"
SCA = BASE / "scenes_ant"
WORK = BASE / "work"
BRAND = BASE / "brand"
FONTS = BASE / "fonts"
WORK.mkdir(exist_ok=True)

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
W, H, FPS = 1080, 1920, 30
FADE = 0.22
OUT = BASE / "antarctica_froze_first_9x16.mp4"

F_CAP = str(FONTS / "Inter-Bold.ttf")
F_CHIP = str(FONTS / "Oswald-SemiBold.ttf")
F_TITLE = str(FONTS / "ArchivoBlack-Regular.ttf")
F_UI = str(FONTS / "Oswald-Medium.ttf")

CYAN = "0x67E8F9"

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"CMD FAIL: {' '.join(str(c) for c in cmd[:9])}...\n{r.stderr[-600:]}")
    return r

def dur_of(p):
    r = subprocess.run([FF, "-i", str(p), "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        raise RuntimeError(f"no duration for {p}")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

def esc(t):
    return (t.replace("'", "\u2019").replace(":", r"\:").replace("%", r"\%")
             .replace(",", r"\,"))

pil = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
_fc = {}
def get_font(path, fs):
    k = (path, fs)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, fs)
    return _fc[k]

def text_w(path, fs, txt):
    return pil.textlength(txt, font=get_font(path, fs))

# ============================================================ timeline
manifest = json.loads((BASE / "audio" / "vo_ant" / "manifest.json").read_text())
segs = {s["name"]: s for s in manifest}
ORDER = ["cold", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]
durs = {"cold": 3.6, "s8": 4.2}
for k in ("s1", "s2", "s3", "s4", "s5", "s6", "s7"):
    durs[k] = round(segs[k]["duration"] + 0.55, 2)
starts, t = {}, 0.0
for k in ORDER:
    starts[k] = round(t, 3)
    t += durs[k]
TOTAL = round(t, 3)
print("TIMELINE:", {k: starts[k] for k in ORDER}, "| TOTAL:", TOTAL)

# ============================================================ stills
IMG_EXT = {"lima": "png", "drake_map": "png", "eocene": "png"}

def render_still(img, out, dur, move, zmax=0.30, yoff=0.0, shake=0.0, dark=0.0):
    n = int(dur * FPS)
    yexpr = "ih/2-(ih/zoom/2)"
    if yoff:
        yexpr += f"+{yoff}*(ih-ih/zoom)"
    moves = {
        "punch_in": f"zoompan=z='1.0+{zmax}*on/{n}':x='iw/2-(iw/zoom/2)':y='{yexpr}'",
        "crash_zoom": f"zoompan=z='1.0+{zmax}*min(1,3*on/{n})+{zmax*0.45}*on/{n}':x='iw/2-(iw/zoom/2)':y='{yexpr}'",
        "punch_out": f"zoompan=z='{1+zmax}-{zmax}*on/{n}':x='iw/2-(iw/zoom/2)':y='{yexpr}'",
        "whip_pan": f"zoompan=z='1.16':x='(iw-ow/zoom)*(on/{n})':y='{yexpr}'",
        "whip_pan_r": f"zoompan=z='1.16':x='(iw-ow/zoom)*(1-on/{n})':y='{yexpr}'",
        "drift": f"zoompan=z='1.12+0.05*sin(2*PI*on/{n})':x='iw/2-(iw/zoom/2)+20*sin(2*PI*on/{n})':y='{yexpr}'",
        "rise": f"zoompan=z='1.22':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(1-on/{n})'",
    }
    vf = ["scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840",
          moves[move] + f":d={n}:s=1080x1920:fps={FPS}"]
    if shake > 0:
        vf.append(f"crop=1080:1920:(iw-1080)/2+{shake}*sin(41*t):(ih-1920)/2+{shake}*cos(31*t)")
    vf.append("unsharp=5:5:0.45")
    vf.append(f"eq=saturation=1.16:contrast=1.08:brightness={0.02 - dark},vignette=0.68")
    vf.append(f"fps={FPS},format=yuv420p")
    run([FF, "-y", "-loglevel", "error",
         "-loop", "1", "-framerate", str(FPS), "-t", str(dur + 0.4), "-i", str(img),
         "-vf", ",".join(vf), "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(out)])

# ============================================================ shot plans
PLANS = {
    "s1": [("still", "lima", "crash_zoom", 0.30, 1.0),
           ("still", "acc2", "punch_in", 0.26, 0.7),
           ("still", "glacier1", "whip_pan", 0.20, 0.8),
           ("still", "icebridge", "drift", 0.24, 0.7)],
    "s2": [("anim", "anim_paleo.mp4", None),
           ("still", "drake_ocean", "whip_pan", 0.20, 0.8),
           ("still", "eocene", "punch_in", 0.26, 0.7),
           ("still", "glacier2", "punch_in", 0.24, 0.7)],
    "s3": [("anim", "anim_gateway.mp4", None),
           ("still", "drake_map", "punch_in", 0.28, 0.8),
           ("still", "drake_ocean", "drift", 0.22, 0.9)],
    "s4": [("anim", "anim_current.mp4", None),
           ("clip", "clip_seaice.mp4", 6.5),
           ("still", "acc1", "whip_pan", 0.20, 1.0)],
    "s5": [("anim", "anim_freeze.mp4", None),
           ("clip", "clip_icesheet.mp4", 5.0),
           ("still", "glacier1", "punch_in", 0.26, 1.0),
           ("still", "co2_graph", "punch_in", 0.24, 1.0)],
    "s6": [("anim", "anim_arctic.mp4", None),
           ("clip", "clip_arctic.mp4", 5.0),
           ("still", "arctic1", "whip_pan", 0.20, 1.0),
           ("still", "arctic2", "punch_in", 0.24, 1.0)],
}
CREDITS = {
    "s1": ["NASA / USGS — LIMA", "NASA SVS", "NASA / EOS", "NASA ICEBRIDGE"],
    "s2": ["SCHEMATIC — 34 MYA", "SOUTHERN OCEAN", "CLIMATE RECONSTRUCTION", "NASA / EOS"],
    "s3": ["SCHEMATIC — GATEWAYS", "DRAKE PASSAGE MAP", "DRAKE PASSAGE"],
    "s4": ["SCHEMATIC — ACC", "SEA-ICE LEADS ANIMATION", "NASA SVS"],
    "s5": ["NASA LIMA + SIMULATION", "NASA ICE-SHEET ANIMATION", "NASA / EOS", "WESTERHOLD ET AL. 2020"],
    "s6": ["SCHEMATIC — COMPARISON", "NASA / NSIDC", "NASA SVS", "NASA SVS"],
}
CHIPS = {
    "s1": [("FROZE 25M YEARS BEFORE THE ARCTIC", "twenty-five million years before the arctic", 330),
           ("34 MYA: EARTH +5°C WARMER", "thirty-four million years ago", 430)],
    "s7": [("THE ACC STILL STEERS EARTH'S CLIMATE", "steers the climate of the whole planet", 330)],
}

# ============================================================ captions
def caption_filters(words, scene_dur, windows, end_cap=None):
    parts = []
    for w0, w1 in windows:
        if w0 < 0.3:
            w0 = max(w0, 0.26)
        if w1 > scene_dur - 0.3:
            w1 = min(w1, scene_dur - 0.26)
        ws = [w for w in words
              if w["t"] + w["d"] * 0.5 >= w0 - 0.01 and w["t"] < w1 + 0.01]
        if end_cap is not None:
            ws = [w for w in ws if w["t"] < end_cap]
        if not ws:
            continue
        groups, cur = [], []
        for w in ws:
            cur.append(w)
            if len(cur) >= 4:
                groups.append(cur); cur = []
        if cur:
            groups.append(cur)
        for g in groups:
            t0 = max(w0 + 0.02, g[0]["t"] - 0.03)
            t1 = min(w1 - 0.02, g[-1]["t"] + g[-1]["d"] + 0.22)
            if end_cap is not None:
                t1 = min(t1, end_cap)
            if t1 <= t0:
                continue
            txts = [w["w"].strip() for w in g]
            fs, gap = 56, 16
            widths = [text_w(F_CAP, fs, t) for t in txts]
            while fs > 44 and sum(widths) + gap * (len(txts) - 1) > 900:
                fs -= 2
                widths = [text_w(F_CAP, fs, t) for t in txts]
            total = sum(widths) + gap * (len(txts) - 1)
            x = (W - total) / 2
            for j, (txt, ww) in enumerate(zip(txts, widths)):
                parts.append(
                    f"drawtext=fontfile={F_CAP}:text='{esc(txt)}':fontsize={fs}:fontcolor=white:"
                    f"borderw=4:bordercolor=black@0.9:shadowx=2:shadowy=2:shadowcolor=black@0.85:"
                    f"x={int(x)}:y=1330:enable='between(t\\,{t0:.2f}\\,{t1:.2f})'")
                wt0 = max(w0, g[j]["t"])
                wt1 = min(w1, g[j]["t"] + g[j]["d"])
                if end_cap is not None:
                    wt1 = min(wt1, end_cap)
                if wt1 > wt0:
                    parts.append(
                        f"drawtext=fontfile={F_CAP}:text='{esc(txt)}':fontsize={fs}:fontcolor={CYAN}:"
                        f"borderw=4:bordercolor=black@0.9:shadowx=2:shadowy=2:shadowcolor=black@0.85:"
                        f"x={int(x)}:y=1330:enable='between(t\\,{wt0:.2f}\\,{wt1:.2f})'")
                x += ww + gap
    return parts

def phrase_window(scene_key, phrase):
    ws = segs[scene_key]["words"]
    joined = " ".join(w["w"].strip().lower() for w in ws)
    i = joined.find(" ".join(phrase.split()))
    if i < 0:
        return None
    idx = len(joined[:i].split())
    pwords = phrase.split()
    t0 = ws[idx]["t"]
    t1 = ws[idx + len(pwords) - 1]["t"] + ws[idx + len(pwords) - 1]["d"]
    return (t0, t1)

def chip_filter(text, t0, t1, y):
    fs = 34
    while fs > 26 and text_w(F_CHIP, fs, text) > 830 - 120:
        fs -= 2
    x = 830 - int(text_w(F_CHIP, fs, text)) - 24
    return (f"drawtext=fontfile={F_CHIP}:text='{esc(text)}':fontsize={fs}:fontcolor={CYAN}:"
            f"box=1:boxcolor=black@0.55:boxborderw=14:"
            f"x={x}:y={y}:enable='between(t\\,{t0:.2f}\\,{t1:.2f})'")

def credit_filter(text, t0, t1):
    return (f"drawtext=fontfile={F_UI}:text='{esc(text)}':fontsize=25:fontcolor=0xAFC0DC@0.75:"
            f"x=36:y=110:box=1:boxcolor=black@0.35:boxborderw=9:"
            f"enable='between(t\\,{t0:.2f}\\,{t1:.2f})'")

# ============================================================ cards
def build_s7(dur):
    rng = np.random.default_rng(77)
    card = np.zeros((H, W, 3), dtype=np.float32)
    card += np.array([5, 8, 18], dtype=np.float32)
    for _ in range(200):
        x, y = int(rng.random() * W), int(rng.random() * H)
        b = rng.random() ** 2.2 * 200 + 15
        card[y, x] = (b, b, min(255, b * 1.15))
    img = Image.fromarray(np.clip(card, 0, 255).astype(np.uint8)).convert("RGB")
    src = Image.open(IMGA / "lima.png").convert("RGB")
    side = min(src.size)
    src = src.crop(((src.width - side) // 2, (src.height - side) // 2,
                    (src.width + side) // 2, (src.height + side) // 2)).resize((620, 620), Image.LANCZOS)
    arr = np.asarray(src, dtype=np.float32) * 0.42
    yy, xx = np.mgrid[0:620, 0:620]
    mask = np.clip(1 - (np.sqrt((xx - 310) ** 2 + (yy - 310) ** 2) / 310) ** 3, 0, 1)
    arr *= mask[..., None]
    planet = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    img.paste(planet, ((W - 620) // 2, 130), Image.fromarray((mask * 255).astype(np.uint8)))
    d = ImageDraw.Draw(img)
    def center(txt, f, fill, y, track=0):
        total = 0
        bb = []
        for ch in txt:
            b = d.textbbox((0, 0), ch, font=f)
            w = b[2] - b[0]
            bb.append((ch, w, b))
            total += w + track
        x = (W - total + track) / 2
        for ch, w, b in bb:
            d.text((x - b[0], y - b[1]), ch, font=f, fill=fill)
            x += w + track
    f1 = ImageFont.truetype(F_TITLE, 74)
    f2 = ImageFont.truetype(F_TITLE, 60)
    f3 = ImageFont.truetype(F_UI, 44)
    f4 = ImageFont.truetype(F_UI, 34)
    center("SO HERE'S MY QUESTION.", f1, (245, 248, 255), 830, 2)
    center("WHAT'S HIDING UNDER", f2, (103, 232, 249), 950, 2)
    center("ALL THAT ICE?", f2, (103, 232, 249), 1030, 2)
    bt = "COMMENT YOUR THEORY"
    tw = d.textlength(bt, font=f3)
    bx, by = (W - tw) / 2 - 30, 1145
    d.rounded_rectangle([bx, by, bx + tw + 60, by + 84], radius=18, fill=(255, 107, 53))
    d.text((bx + 30, by + 14), bt, font=f3, fill=(255, 255, 255))
    center("YOUR ANSWER MIGHT BE RIGHT.", f4, (240, 237, 230), 1285, 2)
    img.save(WORK / "s7_card.png")
    n = int(dur * FPS)
    run([FF, "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS),
         "-t", str(dur + 0.4), "-i", str(WORK / "s7_card.png"),
         "-vf", f"zoompan=z='1.06+0.025*sin(2*PI*on/{n})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps={FPS},format=yuv420p",
         "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-an", str(SCA / "s7_card.mp4")])

def build_s8(dur):
    rng = np.random.default_rng(99)
    card = np.zeros((H, W, 3), dtype=np.float32)
    card += np.array([5, 8, 18], dtype=np.float32)
    for _ in range(240):
        x, y = int(rng.random() * W), int(rng.random() * H)
        b = rng.random() ** 2.2 * 220 + 12
        card[y, x] = (b, b, min(255, b * 1.18))
    img = Image.fromarray(np.clip(card, 0, 255).astype(np.uint8)).convert("RGBA")
    banner = Image.open(BRAND / "banner_ant.png").convert("RGBA")
    bw = 1020
    banner = banner.resize((bw, int(banner.height * bw / banner.width)), Image.LANCZOS)
    img.paste(banner, ((W - bw) // 2, 780), banner)
    d = ImageDraw.Draw(img)
    def center(txt, f, fill, y, track=2):
        total = 0
        bb = []
        for ch in txt:
            b = d.textbbox((0, 0), ch, font=f)
            w = b[2] - b[0]
            bb.append((ch, w, b))
            total += w + track
        x = (W - total + track) / 2
        for ch, w, b in bb:
            d.text((x - b[0], y - b[1]), ch, font=f, fill=fill)
            x += w + track
    f2 = ImageFont.truetype(F_UI, 42)
    f3 = ImageFont.truetype(F_UI, 32)
    center("NEW MYSTERIES. EVERY WEEK.", f2, (240, 237, 230), 1120, 3)
    center("COMMENT: WHAT IS HIDING UNDER ALL THAT ICE?", f3, (143, 216, 255), 1210, 1)
    img.convert("RGB").save(WORK / "s8_card.png")
    run([FF, "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS),
         "-t", str(dur + 0.4), "-i", str(WORK / "s8_card.png"),
         "-vf", "scale=1080:1920,format=yuv420p",
         "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-an", str(SCA / "s8_card.mp4")])

# ============================================================ scenes
def build_scene(k):
    d = durs[k]
    if k == "s7":
        build_s7(d)
        out = SCA / "s7_ov.mp4"
        run([FF, "-y", "-loglevel", "error", "-i", str(SCA / "s7_card.mp4"),
             "-vf", f"fade=t=in:st=0:d={FADE},fade=t=out:st={d-FADE:.3f}:d={FADE},format=yuv420p",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-an", str(out)])
        return str(out)
    if k == "s8":
        build_s8(d)
        out = SCA / "s8_ov.mp4"
        run([FF, "-y", "-loglevel", "error", "-i", str(SCA / "s8_card.mp4"),
             "-vf", f"fade=t=in:st=0:d={FADE},fade=t=out:st={d-0.5:.3f}:d=0.5,format=yuv420p",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-an", str(out)])
        return str(out)
    if k == "cold":
        out = SCA / "cold_ov.mp4"
        run([FF, "-y", "-loglevel", "error", "-i", str(SCA / "anim_cold.mp4"),
             "-vf", f"fade=t=in:st=0:d={FADE},fade=t=out:st={d-FADE:.3f}:d={FADE},format=yuv420p",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-an", str(out)])
        return str(out)
    fixed, weighted = [], []
    for item in PLANS[k]:
        if item[0] in ("anim", "clip"):
            fname = SCA / item[1]
            dd = dur_of(fname)
            if item[0] == "clip":
                dd = min(dd, item[2])
            fixed.append((fname, dd, item[0]))
        else:
            weighted.append(item)
    rem = d - sum(f[1] for f in fixed)
    weights = [it[4] for it in weighted]
    wsum = sum(weights)
    files, wins, tacc = [], [], 0.0
    for (fname, dd, kind) in fixed:
        if kind == "clip" and dd < dur_of(fname) - 0.02:
            tmp = WORK / f"trim_{k}_{len(files)}.mp4"
            run([FF, "-y", "-loglevel", "error", "-i", str(fname), "-t", f"{dd:.3f}",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                 "-an", str(tmp)])
            fname = tmp
        files.append(fname)
        wins.append((round(tacc, 3), round(tacc + dd, 3)))
        tacc += dd
    for it in weighted:
        _, name, move, z, w = it
        dd = rem * w / wsum
        ext = IMG_EXT.get(name, "jpg")
        out = WORK / f"shot_{k}_{name}.mp4"
        if not out.exists():
            render_still(IMGA / f"{name}.{ext}", out, dd, move, zmax=z)
        files.append(out)
        wins.append((round(tacc, 3), round(tacc + dd, 3)))
        tacc += dd
    lst = WORK / f"list_{k}.txt"
    lst.write_text("".join(f"file '{f}'\n" for f in files))
    base = WORK / f"base_{k}.mp4"
    run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(base)])
    cap_windows = [w for w, f in zip(wins, files) if Path(f).name != "anim_freeze.mp4"]
    words = segs[k]["words"] if k in segs else []
    vf = []
    if k in segs:
        end_cap = None
        if k == "s7":
            qw = next((w for w in words if w["w"].strip().lower() == "so"), None)
            if qw:
                end_cap = qw["t"] - 0.05
        if k in ("s1", "s7"):
            vf = caption_filters(words, d, [(0.0, d)], end_cap=end_cap)
        else:
            vf = caption_filters(words, d, cap_windows)
    if k in CHIPS:
        for disp, phrase, y in CHIPS[k]:
            wnd = phrase_window(k, phrase)
            if wnd:
                vf.append(chip_filter(disp, wnd[0], wnd[1], y))
    creds = CREDITS.get(k, [])
    for i, (w0, w1) in enumerate(wins):
        if i < len(creds):
            vf.append(credit_filter(creds[i], w0 + 0.1, min(w1 - 0.05, d - FADE - 0.06)))
    vf += [f"fade=t=in:st=0:d={FADE}", f"fade=t=out:st={d-FADE:.3f}:d={FADE}"]
    ov = SCA / f"{k}_ov.mp4"
    run([FF, "-y", "-loglevel", "error", "-i", str(base),
         "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-an", str(ov)])
    print(f"  {k}: {dur_of(ov):.2f}s ({len(files)} shots, {len(vf)} overlays)")
    return str(ov)

# ============================================================ audio
def build_audio():
    T = TOTAL
    DUR = str(int(T) + 2)
    vo_keys = [k for k in ORDER if k != "cold"]
    vo_idx = {k: 1 + i for i, k in enumerate(vo_keys)}   # input 0 = bed
    t1, t3, t4, t5, t6, t7 = (starts[k] for k in ("s1", "s3", "s4", "s5", "s6", "s7"))
    fc = f"""
[0:a]volume=0.55,lowpass=f=140,tremolo=f=0.1:d=0.5[drone];
[1:a]volume=0.16,tremolo=f=0.1:d=0.35,lowpass=f=900[pad];
[2:a]volume=0.14,bandpass=f=320:w=2,tremolo=f=0.25:d=0.4,lowpass=f=1500[air];
[3:a]adelay={int(t4*1000)}|{int(t4*1000)},apad,atrim=0:{T},volume=0.30,tremolo=f=0.85:d=0.55,lowpass=f=220[pulse];
[4:a]adelay={int(max(0,t5-2.6)*1000)}|{int(max(0,t5-2.6)*1000)},apad,atrim=0:{T},volume=0.5,afade=t=in:st={max(0,t5-2.6)}:d=2.2,afade=t=out:st={t5-0.1}:d=0.3[riser];
[5:a]adelay={int((t1+2.0)*1000)}|{int((t1+2.0)*1000)},apad,atrim=0:{T},volume=0.22,tremolo=f=13:d=0.8,afade=t=in:st={t1+2.0}:d=0.4,afade=t=out:st={t1+3.4}:d=0.4[sh1];
[5:a]adelay={int(t7*1000)}|{int(t7*1000)},apad,atrim=0:{T},volume=0.26,tremolo=f=13:d=0.8,afade=t=in:st={t7}:d=0.5,afade=t=out:st={t7+2.0}:d=0.4[sh2];
[6:a]adelay={int(t6*1000)}|{int(t6*1000)},apad,atrim=0:{T},volume=0.5,afade=t=in:st={t6}:d=0.06,afade=t=out:st={t6+0.7}:d=0.8[subdrop];
[drone][pad][air][pulse][riser][sh1][sh2][subdrop]amix=inputs=8:duration=longest[m0];
[m0]volume=8[m];
[m]volume=eval=frame:volume='0.5+0.35*between(t\\,{t5-0.5}\\,{t6+1})',lowpass=f=2400,afade=t=in:st=0:d=1.6,afade=t=out:st={T-2.4:.2f}:d=2.2[bed]"""
    run([FF, "-y", "-loglevel", "error",
         "-f", "lavfi", "-t", DUR, "-i", "aevalsrc=0.55*sin(2*PI*41.2*t)+0.34*sin(2*PI*55*t)+0.16*sin(2*PI*82.4*t)",
         "-f", "lavfi", "-t", DUR, "-i", "aevalsrc=0.26*sin(2*PI*110*t)+0.2*sin(2*PI*130.81*t)+0.16*sin(2*PI*164.81*t)+0.1*sin(2*PI*220*t)",
         "-f", "lavfi", "-t", DUR, "-i", "anoisesrc=d=999:c=brown:r=44100:a=0.5",
         "-f", "lavfi", "-t", DUR, "-i", "sine=frequency=49",
         "-f", "lavfi", "-t", "3.2", "-i", "aevalsrc=0.5*sin(2*PI*(150+730*t/2.9)*t)",
         "-f", "lavfi", "-t", "2.2", "-i", "sine=frequency=1318.5",
         "-f", "lavfi", "-t", "1.6", "-i", "sine=frequency=36.5",
         "-filter_complex", fc, "-map", "[bed]", "-ar", "44100", "-ac", "2",
         "-c:a", "pcm_s16le", str(WORK / "bed_ant.wav")])
    vo_inputs, vo_parts, vo_labels = [], [], []
    for k in vo_keys:
        vo_inputs += ["-i", segs[k]["file"]]
    for i, k in enumerate(vo_keys):
        st = starts[k]
        vo_parts.append(f"[{vo_idx[k]}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                        f"volume=1.0,adelay={int(st*1000)}|{int(st*1000)}[vo{i}]")
        vo_labels.append(f"[vo{i}]")
    vo_parts.append(f"{''.join(vo_labels)}amix=inputs={len(vo_labels)}:duration=longest[vom];"
                    f"[vom]volume={len(vo_labels)}[vos];[vos]asplit[vo][vo2]")
    inp, sfx_parts = [], []
    n = len(vo_keys) + 1
    def add_sfx(tt, args, filt):
        nonlocal n
        inp.extend(["-f", "lavfi", "-t", "3.0", "-i", args])
        sfx_parts.append(f"[{n}:a]{filt},volume=0.8,adelay={int(max(0,tt)*1000)}|{int(max(0,tt)*1000)},apad,atrim=0:{T}[sf{n}]")
        n += 1
    for k in ORDER[1:]:
        add_sfx(starts[k] - 0.05, "anoisesrc=d=1.4:c=pink:r=44100:a=0.5",
                "highpass=f=250,lowpass=f=3800,afade=t=in:st=0:d=0.3,afade=t=out:st=0.85:d=0.5,tremolo=f=9:d=0.4")
    add_sfx(0.02, "sine=frequency=48:duration=1.8", "volume=0.9,afade=t=in:st=0:d=0.01,afade=t=out:st=0.15:d=1.6,lowpass=f=160")
    add_sfx(t5 + 0.05, "sine=frequency=48:duration=1.8", "volume=0.9,afade=t=in:st=0:d=0.01,afade=t=out:st=0.15:d=1.6,lowpass=f=160")
    add_sfx(starts["s2"] + 0.4, "anoisesrc=d=0.5:c=white:r=44100:a=0.8",
            "bandpass=f=2800:w=1.2,afade=t=in:st=0:d=0.005,afade=t=out:st=0.08:d=0.4,tremolo=f=26:d=0.9")
    add_sfx(t3 + 1.2, "sine=frequency=70:duration=1.4", "volume=0.85,afade=t=in:st=0:d=0.01,afade=t=out:st=0.12:d=1.28,lowpass=f=220")
    add_sfx(t6 + 1.0, "sine=frequency=42:duration=1.8", "volume=0.6,afade=t=in:st=0:d=0.02,afade=t=out:st=0.3:d=1.5,lowpass=f=120")
    sfx_parts.append(f"{''.join(f'[sf{i}]' for i in range(9, n))}amix=inputs={n-9}:duration=longest[sfx0];"
                     f"[sfx0]volume={n-9}[sfx]")
    graph = ";".join([
        "[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[bedin]",
        *vo_parts,
        "[bedin][vo]sidechaincompress=threshold=0.02:ratio=7:attack=18:release=300:makeup=1[bedduck]",
        *sfx_parts,
        "[bedduck][vo2][sfx]amix=inputs=3:duration=longest[a0];"
        "[a0]volume=3[a1]",
        f"[a1]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,atrim=0:{T},asetpts=PTS-STARTPTS,"
        "acompressor=threshold=-20dB:ratio=2.5:attack=15:release=220:makeup=2,"
        "alimiter=limit=0.95[out]",
    ])
    run([FF, "-y", "-loglevel", "error", "-i", str(WORK / "bed_ant.wav"), *vo_inputs, *inp,
         "-filter_complex", graph, "-map", "[out]", "-ar", "44100", "-ac", "2",
         "-c:a", "pcm_s16le", str(WORK / "mix_ant.wav")])
    # loudnorm 2-pass (parse human-readable summary)
    r = run([FF, "-y", "-i", str(WORK / "mix_ant.wav"),
             "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=summary", "-f", "null", "-"])
    def grab(name):
        m = re.search(name + r":\s+([-+\d.]+)", r.stderr)
        return m.group(1) if m else None
    i_, tp, lra, th = grab("Input Integrated"), grab("Input True Peak"), grab("Input LRA"), grab("Input Threshold")
    if i_ is None:
        print("LOUDNORM PARSE FAIL", r.stderr[-400:])
        raise SystemExit(1)
    run([FF, "-y", "-loglevel", "error", "-i", str(WORK / "mix_ant.wav"),
         "-af", (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={i_}:"
                 f"measured_TP={tp}:measured_LRA={lra}:measured_thresh={th}:linear=true"),
         "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k", str(WORK / "master_ant.m4a")])
    print("  audio master ok")

# ============================================================ main
def main():
    print("== rendering scenes ==")
    ovs = {}
    for k in ORDER:
        ovs[k] = build_scene(k)
    print("== concat (per-scene dip fades) ==")
    lst = WORK / "list_all.txt"
    lst.write_text("".join(f"file '{ovs[k]}'\n" for k in ORDER))
    run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(WORK / "video_ant.mp4")])
    print("  video:", round(dur_of(WORK / "video_ant.mp4"), 2), "s")
    wm_on = starts["s1"]
    wm_off = starts["s8"] - 0.6
    run([FF, "-y", "-loglevel", "error", "-i", str(WORK / "video_ant.mp4"),
         "-i", str(BRAND / "watermark_ant.png"),
         "-filter_complex",
         f"[0:v][1:v]overlay=W-w-36:96:enable='between(t\\,{wm_on}\\,{wm_off})'[v]",
         "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-an", str(WORK / "video_ant_wm.mp4")])
    print("== audio ==")
    build_audio()
    print("== mux ==")
    run([FF, "-y", "-loglevel", "error", "-i", str(WORK / "video_ant_wm.mp4"),
         "-i", str(WORK / "master_ant.m4a"), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "copy", "-t", f"{TOTAL:.3f}", "-movflags", "+faststart", str(OUT)])
    print(f"\n=== FINAL: {OUT} ({dur_of(OUT):.2f}s, {OUT.stat().st_size/1e6:.1f}MB) ===")
    run([FF, "-y", "-loglevel", "error", "-i", str(OUT), "-ss", "1.6", "-frames:v", "1",
         "-q:v", "2", str(BASE / "thumbnail_ant.jpg")])
    for tt, nm in [(starts["s1"] + 2, "qa_s1"), (starts["s2"] + 2, "qa_s2"),
                   (starts["s3"] + 3, "qa_s3"), (starts["s4"] + 3, "qa_s4"),
                   (starts["s5"] + 3, "qa_s5"), (starts["s6"] + 3, "qa_s6"),
                   (starts["s7"] + 3, "qa_s7"), (starts["s8"] + 2, "qa_s8")]:
        run([FF, "-y", "-loglevel", "error", "-i", str(OUT), "-ss", f"{tt:.2f}",
             "-frames:v", "1", "-q:v", "3", str(WORK / f"{nm}.jpg")])
    print("thumbnail + QA frames saved")

if __name__ == "__main__":
    main()
