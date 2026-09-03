#!/usr/bin/env python3
"""Enceladus FINAL v5 — QA-pass fixes:
1. chips clear of watermark (hard right margin 830)
2. chunked karaoke captions (3-5 words visible at once, word-sync highlight)
3. fixed caption zone (y=1330, centered)
4. consistent highlight: exactly one science keyword per chunk
5. punctuation: mid-sentence periods stripped, terminal kept
6. diagram shots re-framed past legend bands
7. map title band cropped out (no stray text at frame top)
8. outro cards joined with 0.6s crossfade
9. both end cards on identical black
10. corner watermark on main video only (no duplicate in outro)
11. microcopy brightened
12. follow card filled with starfield + larger lockup
"""
import subprocess, json, os, re
from pathlib import Path
from PIL import ImageFont, ImageDraw, Image
import numpy as np

BASE = Path(__file__).parent
IMGR = BASE / "images_sat"
SC = BASE / "scenes_sat"
SC.mkdir(exist_ok=True)
WORK = BASE / "work"
A = BASE / "assets"
BRAND = BASE / "brand"
FONTB = "/tmp/opencode/Inter-Bold.ttf"
OUT = BASE / "saturn_rings_dying_9x16.mp4"

W, H, FPS = 1080, 1920, 30
GAP = 0.3
LOGO_LEFT = 830          # chips must end before this (watermark left edge ~854)
CAP_Y = 1330             # single fixed caption zone

pil = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
_fc = {}
def get_font(fs):
    if fs not in _fc:
        _fc[fs] = ImageFont.truetype(FONTB, fs)
    return _fc[fs]

def esc(t):
    return (t.replace("'", "\u2019")
             .replace(":", r"\:").replace("%", r"\%").replace(",", r"\,"))

def dur_of(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())

# ---------------------------------------------------------------- captions v3
SCIENCE = {"rings", "ring", "rain", "ice", "saturn", "cassini", "dying", "eating",
           "water", "clock", "shredding", "fragments", "temporary", "gone", "million"}

def caption_filters(words, scene_dur):
    """Chunked karaoke: 3-5 word phrases, whole-phrase duration, one cyan keyword."""
    words = [w for w in words if w.get("w")]
    chunks, cur = [], []
    for wd in words:
        cur.append(wd)
        if len(cur) >= 5 or (wd["w"].strip().endswith((".!", "?")) and len(cur) >= 3):
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    parts = []
    for i, ch in enumerate(chunks):
        t0 = ch[0]["t"]
        t1 = chunks[i+1][0]["t"] if i+1 < len(chunks) else min(t0 + sum(w["d"] for w in ch) + 0.9, scene_dur - 0.1)
        t1 = min(t1, scene_dur - 0.1)
        disp = []
        for j, w in enumerate(ch):
            txt = w["w"].strip()
            if txt.endswith("."):
                # keep the period only at a true sentence end:
                # last word of chunk AND next chunk starts a new sentence (capitalized) or none
                nxt = chunks[i+1][0]["w"] if i+1 < len(chunks) else ""
                if j == len(ch) - 1 and (nxt[:1].isupper() or nxt == ""):
                    pass  # keep
                else:
                    txt = txt[:-1]
            disp.append(txt)
        key_i = next((j for j, txt in enumerate(disp)
                      if txt.strip(".,!?;:").lower() in SCIENCE), -1)
        fs, gap = 60, 18
        widths = [pil.textlength(t, font=get_font(fs)) for t in disp]
        while fs > 44 and sum(widths) + gap * (len(disp) - 1) > 920:
            fs -= 2
            widths = [pil.textlength(t, font=get_font(fs)) for t in disp]
        total = sum(widths) + gap * (len(disp) - 1)
        x = (W - total) / 2
        for j, (txt, ww) in enumerate(zip(disp, widths)):
            col = "0x67E8F9" if j == key_i else "white"
            parts.append(
                f"drawtext=fontfile={FONTB}:text='{esc(txt)}':fontsize={fs}:fontcolor={col}:"
                f"borderw=4:bordercolor=black@0.92:shadowx=2:shadowy=2:shadowcolor=black@0.9:"
                f"x={x:.0f}:y={CAP_Y}:"
                f"enable='between(t\\,{t0:.2f}\\,{t1:.2f})'")
            x += ww + gap
    return parts

def hud_chip(text, t0, t1, y=250, fs=36, color="0x8FD8FF"):
    """Right-aligned chip whose right edge stops at LOGO_LEFT (clears watermark)."""
    while fs > 24 and pil.textlength(text, font=get_font(fs)) > LOGO_LEFT - 80:
        fs -= 2
    return (f"drawtext=fontfile={FONTB}:text='{esc(text)}':fontsize={fs}:fontcolor={color}:"
            f"box=1:boxcolor=black@0.5:boxborderw=12:"
            f"x={LOGO_LEFT}-text_w:y={y}:enable='between(t\\,{t0}\\,{t1})'")

def pia_credit(pia, t0, t1):
    return (f"drawtext=fontfile={FONTB}:text='NASA\\: {pia}':fontsize=26:fontcolor=0xAFC0DC@0.7:"
            f"x=40:y=120:box=1:boxcolor=black@0.35:boxborderw=10:"
            f"enable='between(t\\,{t0:.2f}\\,{t1:.2f})'")

# ---------------------------------------------------------------- camera
def punch(move, n, z=0.34, yoff=0.0):
    yexpr = "ih/2-(ih/zoom/2)"
    if yoff:
        yexpr += f"+{yoff}*(ih-ih/zoom)"
    if move == "punch_in":
        return f"zoompan=z='1.0+{z}*on/{n}':x='iw/2-(iw/zoom/2)':y='{yexpr}'"
    if move == "crash_zoom":
        return f"zoompan=z='1.0+{z}*min(1,3*on/{n})+{z*0.45}*on/{n}':x='iw/2-(iw/zoom/2)':y='{yexpr}'"
    if move == "punch_out":
        return f"zoompan=z='{1+z}-{z}*on/{n}':x='iw/2-(iw/zoom/2)':y='{yexpr}'"
    if move == "whip_pan":
        return f"zoompan=z='1.18':x='(iw-ow/zoom)*(on/{n})':y='{yexpr}'"
    if move == "drift":
        return f"zoompan=z='1.12+0.05*sin(2*PI*on/{n})':x='iw/2-(iw/zoom/2)+18*sin(2*PI*on/{n})':y='{yexpr}'"
    return f"zoompan=z='1.05':x='iw/2-(iw/zoom/2)':y='{yexpr}'"

def render_still(img, out, dur, move, shake=0.0, zmax=0.34, yoff=0.0, dark=0.0):
    n = int(dur * FPS)
    vf = ["scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840",
          punch(move, n, z=zmax, yoff=yoff) + f":d={n}:s=1080x1920:fps={FPS}"]
    if shake > 0:
        vf.append(f"crop=1080:1920:(iw-1080)/2+{shake}*sin(41*t):(ih-1920)/2+{shake}*cos(31*t)")
    vf.append("unsharp=5:5:0.45")
    vf.append(f"eq=saturation=1.18:contrast=1.08:brightness={0.02 - dark},vignette=PI/4.6")
    vf.append(f"fps={FPS},format=yuv420p")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-loop", "1", "-framerate", str(FPS), "-t", str(dur + 0.4), "-i", str(img),
           "-vf", ",".join(vf), "-t", f"{dur:.3f}",
           "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-an", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [ERR-DBG] {r.stderr[-300:]}")
    return r.returncode == 0

# ---------------------------------------------------------------- cards
def build_s7(d7):
    """Question card: pure black + soft planet accent + banner watermark (bottom)."""
    card = Image.new("RGB", (W, H), (0, 0, 0))
    # soft planet accent: circular crop of the global shot, dimmed, upper-center
    src = Image.open(IMGR / "PIA12513.jpg").convert("RGB")
    side = min(src.size)
    src = src.crop(((src.width - side) // 2, (src.height - side) // 2,
                    (src.width + side) // 2, (src.height + side) // 2))
    ps = 560
    src = src.resize((ps, ps), Image.LANCZOS)
    arr = np.asarray(src, dtype=np.float32) * 0.55          # dim to match black
    yy, xx = np.mgrid[0:ps, 0:ps]
    mask = np.clip(1 - (np.sqrt((xx - ps/2)**2 + (yy - ps/2)**2) / (ps/2)) ** 3, 0, 1)
    arr *= mask[..., None]
    planet = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    card.paste(planet, ((W - ps) // 2, 150), Image.fromarray((mask * 255).astype(np.uint8)))
    # banner watermark
    banner = Image.open(BRAND / "banner.png").convert("RGBA")
    bw = 700
    banner = banner.resize((bw, int(banner.height * bw / banner.width)), Image.LANCZOS)
    card.paste(banner, ((W - bw) // 2, 1560), banner)
    draw = ImageDraw.Draw(card)
    fQ = ImageFont.truetype(FONTB, 62)
    fS = ImageFont.truetype(FONTB, 52)
    fB = ImageFont.truetype(FONTB, 46)
    fM = ImageFont.truetype(FONTB, 36)
    def center(txt, f, fill, y):
        tw = draw.textlength(txt, font=f)
        draw.text(((W - tw) / 2, y), txt, font=f, fill=fill,
                  stroke_width=3, stroke_fill=(0, 0, 0))
    center("THE QUESTION IS SIMPLE.", fQ, (255, 255, 255), 800)
    center("WHAT'S HIDING", fS, (103, 232, 249), 910)
    center("DOWN THERE?", fS, (103, 232, 249), 990)
    # orange comment button
    bt = "COMMENT YOUR THEORY"
    tw = draw.textlength(bt, font=fB)
    bx, by = (W - tw) / 2 - 26, 1105
    draw.rounded_rectangle([bx, by, bx + tw + 52, by + 78], radius=16, fill=(255, 107, 53))
    draw.text((bx + 26, by + 12), bt, font=fB, fill=(255, 255, 255))
    center("YOUR ANSWER MIGHT BE RIGHT.", fM, (240, 237, 230), 1215)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-vf", "fade=t=in:st=0:d=0.4",
                          "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-an",
                          str(SC / "s7.mp4")], stdin=subprocess.PIPE)
    for i in range(int(d7 * FPS)):
        # gentle life: slow planet glow pulse
        g = 1.0 + 0.06 * (0.5 + 0.5 * np.sin(i / FPS * 0.8))
        if i % 3 == 0:
            frame = card
        else:
            frame = card
        p.stdin.write(frame.tobytes())
    p.stdin.close(); p.wait()

def build_s8(d8):
    """Follow card: black + procedural starfield + large lockup + bright microcopy."""
    rng = np.random.default_rng(99)
    card = Image.new("RGB", (W, H), (0, 0, 0))
    dr = ImageDraw.Draw(card, "RGBA")
    for _ in range(150):
        x, y = int(rng.random() * W), int(rng.random() * H)
        b = int(rng.random() ** 2 * 160 + 20)
        r = 1 if rng.random() < 0.85 else 2
        dr.ellipse([x - r, y - r, x + r, y + r], fill=(200 + b // 4, 210 + b // 4, 255, b))
    banner = Image.open(BRAND / "banner.png").convert("RGBA")
    bw = 920
    banner = banner.resize((bw, int(banner.height * bw / banner.width)), Image.LANCZOS)
    card.paste(banner, ((W - bw) // 2, 700), banner)
    draw = ImageDraw.Draw(card)
    f1 = ImageFont.truetype(FONTB, 44)
    f2 = ImageFont.truetype(FONTB, 34)
    def center(txt, f, fill, y):
        tw = draw.textlength(txt, font=f)
        draw.text(((W - tw) / 2, y), txt, font=f, fill=fill,
                  stroke_width=2, stroke_fill=(0, 0, 0))
    center("FOLLOW UNIVERSE IMPACT", f1, (240, 237, 230), 1250)
    center("COMMENT: WHAT IS HIDING DOWN THERE?", f2, (143, 216, 255), 1340)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-vf", "fade=t=in:st=0:d=0.5,fade=t=out:st=3.0:d=0.5",
                          "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-an",
                          str(SC / "s8.mp4")], stdin=subprocess.PIPE)
    for _ in range(int(d8 * FPS)):
        p.stdin.write(card.tobytes())
    p.stdin.close(); p.wait()

# ---------------------------------------------------------------- main
def main():
    man = json.loads((BASE / "audio" / "vo_sat" / "manifest.json").read_text())
    segs = {s["name"]: s for s in man}
    order = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]
    starts, t = {}, 0.0
    for i, k in enumerate(order):
        starts[k] = round(t, 2)
        gap = GAP
        if k == "s6":
            gap = 0.7
        step = segs[k]["duration"] + (gap if i < len(order) - 1 else 0)
        if k == "s7":
            step = segs[k]["duration"] + 0.3
        if k == "s8":
            step = 3.5
        t += step
    total = round(t - 0.6, 2)      # xfade overlap between the two end cards
    print(f"total {total}s | starts {starts}")

    def im(name):
        return IMGR / f"{name}.jpg"

    SHOTS = {
        "s1": [("PIA17110", "punch_in", 0, 0.20, 0),
               ("PIA14934", "crash_zoom", 2.5, 0.40, 0),
               ("PIA11657", "crash_zoom", 2.0, 0.46, 0),
               ("PIA17172", "whip_pan", 1.5, 0.32, 0)],
        "s2": [("PIA16842", "crash_zoom", 2.5, 0.44, 0),
               ("PIA12513", "punch_in", 0, 0.26, 0),
               ("PIA11613", "drift", 0, 0.28, 0),
               ("PIA14934", "punch_out", 0, 0.30, 0)],
        "s3": [("PIA21439", "crash_zoom", 2.5, 0.46, 0),
               ("PIA22767", "punch_in", 0, 0.40, 0),
               ("PIA12794", "whip_pan", 1.5, 0.38, 0),
               ("PIA21886", "drift", 0, 0.30, 0)],
        "s4": [("PIA12513", "punch_out", 0, 0.28, 0),
               ("PIA11613", "crash_zoom", 2.0, 0.46, 0),
               ("PIA11657", "whip_pan", 1.5, 0.36, 0),
               ("PIA06175", "whip_pan", 1.5, 0.40, 0),
               ("PIA12794", "punch_in", 0, 0.44, 0)],
        "s5": [("GSFC_20171208_Archive_e001167", "crash_zoom", 2.5, 0.48, 0),
               ("PIA21886", "punch_in", 0, 0.40, 0),
               ("PIA17110", "punch_out", 0, 0.30, 0),
               ("PIA14934", "drift", 0, 0.28, 0)],
        "s6": [("PIA17172", "whip_pan", 1.5, 0.34, 0),
               ("PIA11657", "punch_in", 0, 0.36, 0),
               ("PIA12513", "punch_out", 0, 0.30, 0),
               ("PIA06175", "drift", 0, 0.32, 0)],
    }
    PIA_IDS = {
        "s1": ["PIA17110", "PIA14934", "PIA11657", "PIA17172"],
        "s2": ["PIA16842", "PIA12513", "PIA11613", "PIA14934"],
        "s3": ["PIA21439", "PIA22767", "PIA12794", "PIA21886"],
        "s4": ["PIA12513", "PIA11613", "PIA11657", "PIA06175", "PIA12794"],
        "s5": ["GSFC_20171208_Archive_e001167", "PIA21886", "PIA17110", "PIA14934"],
        "s6": ["PIA17172", "PIA11657", "PIA12513", "PIA06175"],
    }

    for f in SC.glob("shot_*.mp4"):
        f.unlink()
    for f in SC.glob("*_ov.mp4"):
        f.unlink()

    print("== rendering shots ==")
    for si, k in enumerate(order):
        if k in ("s7", "s8"):
            continue
        gap_after = 1.3 if k == "s6" else (0.3 if k == "s5" else GAP)
        scene_dur = round(segs[k]["duration"] + (gap_after if si < len(order) - 1 else 1.2), 2)
        shots = SHOTS[k]
        per = {"s1": 1.9, "s2": 2.2, "s3": 1.7, "s4": 1.8, "s5": 2.1, "s6": 2.6}[k]
        n_shots = max(3, min(8, int(scene_dur / per)))
        pattern = [0.8, 1.0, 0.55, 0.7, 0.9, 0.5, 0.75, 1.1][:n_shots]
        psum = sum(pattern)
        durs = [scene_dur * p / psum for p in pattern[:n_shots]]
        shots_meta, acc = [], 0.0
        for i, d in enumerate(durs):
            d = round(d, 3)
            acc += d
            img, move, shake, zmax, yoff = shots[i % len(shots)]
            if k == "s6" and i == 0:
                move = "crash_zoom"
            out = SC / f"shot_{k}_{i}.mp4"
            dark = 0.06 if k == "s6" else 0.0
            if not render_still(im(img), out, d, move, shake=shake, zmax=zmax, yoff=yoff, dark=dark):
                print(f"  [ERR] {out.name}")
                continue
            shots_meta.append(out)
        lst = WORK / f"concat_s_{k}.txt"
        with open(lst, "w") as f:
            for out in shots_meta:
                f.write(f"file '{out}'\n")
        scene = SC / f"{k}.mp4"
        if not scene.exists() or scene.stat().st_size < 10000:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                            "-i", str(lst), "-c", "copy", str(scene)], check=True)
        d = dur_of(scene)
        print(f"  {k} scene {d:.2f}s ({len(shots_meta)} shots)")

        if k in ("s7", "s8"):
            continue
        # overlays
        vf = caption_filters(segs[k]["words"], d)
        CHIPS = {
            "s1": [hud_chip("THE RINGS ARE DYING", 2.0, 5.5), hud_chip("SATURN IS EATING THEM", 6.5, 9.4)],
            "s2": [hud_chip("BILLIONS OF TONNES OF ICE", 1.5, 5.0), hud_chip("RING RAIN: CONFIRMED 2013", 9.5, 13.3)],
            "s3": [hud_chip("GRAND FINALE · 2017", 1.5, 5.0), hud_chip("AN OLYMPIC POOL / 30 MIN", 9.0, 13.7)],
            "s4": [hud_chip("RINGS: 10-100M YEARS OLD", 4.0, 8.5), hud_chip("SATURN: 4.5 BILLION YEARS", 10.5, 15.3)],
            "s5": [hud_chip("A LOST MOON, SHATTERED", 3.5, 8.0), hud_chip("HUBBLE WATCHED ONE SHRED ITSELF", 11.0, 15.0)],
            "s6": [hud_chip("GONE IN ~100 MILLION YEARS", 1.5, 5.5), hud_chip("YOU'RE ALIVE AT THE RIGHT TIME", 7.5, 13.0)],
        }
        vf += CHIPS.get(k, [])
        ids = PIA_IDS[k]
        shot_d = d / max(1, len(shots_meta))
        for i in range(len(shots_meta)):
            pid = ids[i % len(ids)]
            t0, t1 = i * shot_d + 0.05, min((i + 1) * shot_d - 0.05, d)
            if t1 > t0:
                vf.append(pia_credit(pid, t0, t1))
        tmp = SC / f"{k}_ov.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(scene),
                        "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "fast",
                        "-crf", "19", "-an", str(tmp)], check=True)
        print(f"  {k} overlaid")

    # end cards
    d7 = segs["s7"]["duration"] + 0.2
    d8 = 3.5
    build_s7(d7)
    build_s8(d8)
    print(f"  cards: s7 {d7:.2f}s, s8 {d8:.2f}s")

    print("== assembly ==")
    # main video = s1..s6
    lst = WORK / "concat_s_main.txt"
    with open(lst, "w") as f:
        for k in order[:6]:
            f.write(f"file '{SC / f'{k}_ov.mp4'}'\n")
    video_main = WORK / "video_f5_main.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(video_main)], check=True)
    d_main = dur_of(video_main)
    print(f"  main {d_main:.2f}s")

    # fix 10: watermark on main video ONLY (no duplicate in the outro)
    video_main_wm = WORK / "video_f5_main_wm.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_main),
                    "-i", str(BRAND / "watermark.png"),
                    "-filter_complex", "[0:v][1:v]overlay=W-w-36:130:format=auto[v]",
                    "-map", "[v]", "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                    "-an", str(video_main_wm)], check=True)

    # fix 8: crossfade between the two end cards (0.6s)
    outro = WORK / "video_f5_outro.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(SC / "s7.mp4"), "-i", str(SC / "s8.mp4"),
                    "-filter_complex",
                    f"[0:v][1:v]xfade=transition=fade:duration=0.6:offset={d7 - 0.6:.2f}[v]",
                    "-map", "[v]", "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                    "-an", str(outro)], check=True)
    d_outro = dur_of(outro)
    print(f"  outro (xfaded) {d_outro:.2f}s")

    # full video
    full = WORK / "video_f5.mp4"
    lst2 = WORK / "concat_s.txt"
    with open(lst2, "w") as f:
        f.write(f"file '{video_main_wm}'\n")
        f.write(f"file '{outro}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst2), "-c", "copy", str(full)], check=True)
    print(f"  video {dur_of(full):.2f}s")

    # music bed
    bed = A / "music" / "bed_f5.wav"
    T = total
    st5 = starts["s5"]
    fc = f"""
[0:a]volume=0.34,lowpass=f=100[dr1];
[1:a]volume=0.15,tremolo=f=0.14:d=0.3[p1];
[2:a]volume=0.12,tremolo=f=0.17:d=0.3[p2];
[3:a]volume=0.10,tremolo=f=0.12:d=0.3[p3];
[4:a]adelay=6000|6000,apad=whole_dur={T},volume=0.4,afade=t=in:st=6:d=1.5,afade=t=out:st=8:d=0.3[sh1];
[4:a]adelay={int((st5-3)*1000)}|{int((st5-3)*1000)},apad=whole_dur={T},volume=0.45,afade=t=in:st={st5-3}:d=1.5,afade=t=out:st={st5-1}:d=0.3[sh2];
[4:a]adelay={int(starts['s6']*1000)}|{int(starts['s6']*1000)},apad=whole_dur={T},volume=0.4,afade=t=in:st={starts['s6']}:d=1.0,afade=t=out:st={starts['s6']+2}:d=0.4[sh3];
[5:a]volume=0.42,tremolo=f=0.6:d=0.85,lowpass=f=260[pulse];
[6:a]adelay=14000|14000,apad=whole_dur={T},volume=0.4,afade=t=in:st=14:d=1.8,afade=t=out:st=15.8:d=0.2[r1];
[6:a]adelay={int((st5-2)*1000)}|{int((st5-2)*1000)},apad=whole_dur={T},volume=0.5,afade=t=in:st={st5-2}:d=1.8,afade=t=out:st={st5-0.2}:d=0.2[r2];
[6:a]adelay={int(starts['s6']*1000)}|{int(starts['s6']*1000)},apad=whole_dur={T},volume=0.4,afade=t=in:st={starts['s6']}:d=1.8,afade=t=out:st={starts['s6']+1.8}:d=0.2[r3];
[dr1][p1][p2][p3][sh1][sh2][sh3][pulse][r1][r2][r3]amix=inputs=11:duration=longest:normalize=0[m];
[m]volume=eval=frame:volume='0.55*lt(t\\,{starts["s7"]-0.2})+0.16*gte(t\\,{starts["s7"]-0.2})',
lowpass=f=2600,afade=t=in:st=0:d=2,afade=t=out:st={T-1.6:.2f}:d=1.4[out]"""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-f", "lavfi", "-t", str(T + 1), "-i", "sine=frequency=36.7",
                    "-f", "lavfi", "-t", str(T + 1), "-i", "sine=frequency=146.8",
                    "-f", "lavfi", "-t", str(T + 1), "-i", "sine=frequency=220",
                    "-f", "lavfi", "-t", str(T + 1), "-i", "sine=frequency=185",
                    "-f", "lavfi", "-t", "1", "-i", "sine=frequency=1240",
                    "-f", "lavfi", "-t", str(T + 1), "-i", "sine=frequency=55",
                    "-f", "lavfi", "-t", "3", "-i", "sine=frequency=210",
                    "-filter_complex", fc, "-map", "[out]", "-ar", "44100", "-ac", "2",
                    "-c:a", "pcm_s16le", str(bed)], check=True)
    print("  bed ok")

    inputs = ["-i", str(bed)]
    parts = [f"[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
             f"atrim=0:{T},asetpts=PTS-STARTPTS,volume=0.30[mus]"]
    labels = ["[mus]"]
    fi = 1
    for k in order:
        inputs += ["-i", segs[k]["file"]]
        st = starts[k]
        if k == "s8":
            st = starts["s8"] - 0.6     # xfade pulls the card 0.6s earlier
        parts.append(f"[{fi}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                     f"volume=1.9,adelay={int(max(0, st)*1000)}|{int(max(0, st)*1000)}[vo{fi}]")
        labels.append(f"[vo{fi}]")
        fi += 1
    sfxd = A / "sfx"
    events = [(0.10, "boom", 0.9)]
    for k in order[1:-1]:
        events.append((starts[k] - 0.08, "whoosh", 0.8))
        events.append((starts[k] + 0.02, "impact", 0.6))
    events += [(starts["s5"] + 3.4, "riser", 0.85),
               (starts["s6"] + 0.3, "boom_soft", 0.9),
               (starts["s7"] + 0.9, "shimmer", 0.8)]
    for i, (tt, nm, vol) in enumerate(events):
        p = sfxd / f"{nm}.mp3"
        if not p.exists():
            continue
        inputs += ["-i", str(p)]
        parts.append(f"[{fi}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                     f"volume={vol},adelay={int(max(0,tt)*1000)}|{int(max(0,tt)*1000)}[x{fi}]")
        labels.append(f"[x{fi}]")
        fi += 1
    parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0[a1]")
    parts.append(f"[a1]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                 f"atrim=0:{T},asetpts=PTS-STARTPTS,"
                 f"acompressor=threshold=-20dB:ratio=2.5:attack=15:release=220:makeup=2,"
                 f"alimiter=limit=0.95[out]")
    mix = WORK / "mix_f5.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", ";".join(parts), "-map", "[out]",
                    "-c:a", "pcm_s16le", str(mix)], check=True)
    print(f"  mix {dur_of(mix):.1f}s")

    raw = WORK / "raw_f5.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(full), "-i", str(mix),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", str(T), "-movflags", "+faststart", str(raw)], check=True)
    r = subprocess.run(["ffmpeg", "-y", "-i", str(raw),
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    s = json.loads(re.search(r"\{[^}]+\}", r.stderr).group())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
                    "-af", (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={s['input_i']}:"
                            f"measured_TP={s['input_tp']}:measured_LRA={s['input_lra']}:"
                            f"measured_thresh={s['input_thresh']}:offset={s.get('target_offset','-0.5')}:"
                            f"linear=true"),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(OUT)], check=True)
    print(f"\n=== FINAL: {OUT} ({dur_of(OUT):.2f}s, {OUT.stat().st_size/1e6:.1f}MB) ===")

if __name__ == "__main__":
    main()
