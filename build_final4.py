#!/usr/bin/env python3
"""Enceladus FINAL — v4 per review: hard hook, escalation pacing, ocean-setpiece dive,
word-level captions (one highlighted word), cliffhanger ending + black-screen branding."""
import subprocess, json, os, re
from pathlib import Path
from PIL import ImageFont, ImageDraw, Image

BASE = Path(__file__).parent
IMGR = BASE / "images_real"
SC = BASE / "scenes_f4"
SC.mkdir(exist_ok=True)
WORK = BASE / "work"
A = BASE / "assets"
FONTB = "/tmp/opencode/Inter-Bold.ttf"
OUT = BASE / "enceladus_final_9x16.mp4"
BRAND = BASE / "brand"

W, H, FPS = 1080, 1920, 30
GAP = 0.4

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

# ---------------------------------------------------------------- captions v2
# word-level, 3-4 words per line, ONE highlighted word per line, no heavy box
KEYWORDS = {"frozen", "ocean", "geysers", "cassini", "impossible", "spray",
            "salts", "organic", "silica", "phosphates", "life", "ring",
            "water", "absurd", "global", "vents", "hiding", "going", "back", "ten", "dark"}

def word_lines(words, scene_dur):
    """Return list of lines; each line = list of (word, t0, t1, is_key)."""
    words = [w for w in words if w.get("w")]
    chunks, cur = [], []
    for wd in words:
        cur.append(wd)
        if len(cur) >= 4 or (wd["w"].strip().endswith((".!?",)) and len(cur) >= 3):
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    lines = []
    for i, ch in enumerate(chunks):
        t0 = ch[0]["t"]
        t1 = chunks[i+1][0]["t"] if i+1 < len(chunks) else min(t0 + sum(w["d"] for w in ch) + 0.8, scene_dur - 0.1)
        t1 = min(t1, scene_dur - 0.1)
        # one keyword max per line: the first match
        key_i = next((j for j, w in enumerate(ch) if w["w"].strip(".,!?;:").lower() in KEYWORDS), -1)
        ws = [(w["w"].strip(), max(t0, w["t"]), min(t1, w["t"] + max(w["d"], 0.12)), j == key_i)
              for j, w in enumerate(ch)]
        lines.append((ws, t0, t1))
    return lines

def caption_filters(words, scene_dur):
    parts = []
    for ws, t0, t1 in word_lines(words, scene_dur):
        fs = 62
        gap = 20
        widths = [pil.textlength(w, font=get_font(fs)) for w, *_ in ws]
        while sum(widths) + gap * (len(ws) - 1) > 940 and fs > 46:
            fs -= 2
            widths = [pil.textlength(w, font=get_font(fs)) for w, *_ in ws]
        total = sum(widths) + gap * (len(ws) - 1)
        x = (1080 - total) / 2
        for (word, wt0, wt1, is_key), ww in zip(ws, widths):
            col = "0x67E8F9" if is_key else "white"
            parts.append(
                f"drawtext=fontfile={FONTB}:text='{esc(word)}':fontsize={fs}:fontcolor={col}:"
                f"borderw=4:bordercolor=black@0.92:shadowx=2:shadowy=2:shadowcolor=black@0.9:"
                f"x={x:.0f}:y=1330:"
                f"enable='between(t\\,{wt0:.2f}\\,{wt1:.2f})'")
            x += ww + gap
    return parts

def hud_chip(text, t0, t1, y=250, fs=36, color="0x8FD8FF"):
    return (f"drawtext=fontfile={FONTB}:text='{esc(text)}':fontsize={fs}:fontcolor={color}:"
            f"box=1:boxcolor=black@0.5:boxborderw=12:"
            f"x=w-text_w-40:y={y}:enable='between(t\\,{t0}\\,{t1})'")

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

# ---------------------------------------------------------------- main
def main():
    man = json.loads((BASE / "audio" / "vo_e2" / "manifest.json").read_text())
    segs = {s["name"]: s for s in man}
    order = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]
    # s6->s7 gap is longer (cliffhanger beat -> black screen)
    starts, t = {}, 0.0
    for i, k in enumerate(order):
        starts[k] = round(t, 2)
        gap = GAP
        if k == "s6":
            gap = 1.3          # silent beat after cliffhanger
        elif k == "s5":
            gap = 0.3
        step = segs[k]["duration"] + (gap if i < len(order) - 1 else 0)
        if k == "s7":
            step = max(6.5, segs[k]["duration"] + 1.6)
        if k == "s8":
            step = 4.2
        t += step
    total = round(t, 2)
    print(f"total {total}s | starts {starts}")

    def im(name):
        return IMGR / f"{name}.jpg"

    # GLOBAL -> medium -> INSIDE, escalation in the middle, deep-dive setpiece in s5
    SHOTS = {
        "s1": [("PIA17216", "punch_in", 0, 0.16, 0),      # GLOBAL whole moon
               ("PIA14642", "crash_zoom", 2.5, 0.42, 0),  # real jets fast
               ("PIA06443", "crash_zoom", 2.0, 0.46, 0),
               ("PIA17202", "punch_in", 0, 0.34, 0)],
        "s2": [("PIA14642", "punch_in", 0, 0.30, 0),
               ("PIA08354", "crash_zoom", 2.0, 0.30, 0),  # full disk
               ("PIA06205", "crash_zoom", 2.5, 0.44, 0),  # flyby close
               ("PIA17198", "whip_pan", 1.5, 0.30, 0),
               ("PIA17205", "punch_out", 0, 0.30, 0)],
        "s3": [("PIA17216", "punch_in", 0, 0.18, 0),      # global re-anchor
               ("PIA10352", "crash_zoom", 2.5, 0.46, 0),  # tiger stripes
               ("PIA11688", "whip_pan", 1.5, 0.38, 0),    # geyser basin
               ("PIA13620", "crash_zoom", 2.0, 0.52, 0),  # inside a stripe
               ("PIA11686", "punch_out", 0, 0.30, 0)],
        "s4": [("PIA08921", "punch_in", 0, 0.20, 0),      # crescent + E ring
               ("PIA12512", "whip_pan", 1.5, 0.36, 0),    # E ring
               ("PIA17172", "drift", 0, 0.28, 0),         # system scale
               ("PIA08133", "punch_out", 0, 0.32, 0),
               ("PIA12512", "crash_zoom", 2.0, 0.42, 0)],
        # THE SETPIECE: surface -> into ice -> ocean -> core -> vents
        "s5": [("PIA17216", "punch_in", 0, 0.18, 0),      # global
               ("PIA08354", "crash_zoom", 2.0, 0.34, 0),  # dive to surface
               ("PIA18071", "punch_in", 0, 0.28, 0.0),    # whole diagram
               ("PIA18071", "crash_zoom", 2.5, 0.55, 0.30),  # through the crust
               ("PIA18071", "crash_zoom", 2.0, 0.74, 0.52),  # into the ocean
               ("PIA18071", "drift", 0, 0.82, 0.72),      # rocky core / vents, slow
               ("PIA14937", "whip_pan", 1.5, 0.28, 0)],   # out to the real map
        "s6": [("PIA17216", "punch_out", 0, 0.30, 0),     # pull away, mystery grade
               ("PIA08354", "drift", 0, 0.22, 0),
               ("PIA14642", "punch_in", 0, 0.30, 0)],
    }
    PIA_IDS = {
        "s1": ["PIA17216", "PIA14642", "PIA06443", "PIA17202"],
        "s2": ["PIA14642", "PIA08354", "PIA06205", "PIA17198", "PIA17205"],
        "s3": ["PIA17216", "PIA10352", "PIA11688", "PIA13620", "PIA11686"],
        "s4": ["PIA08921", "PIA12512", "PIA17172", "PIA08133", "PIA12512"],
        "s5": ["PIA17216", "PIA08354", "PIA18071", "PIA18071", "PIA18071", "PIA18071", "PIA14937"],
        "s6": ["PIA17216", "PIA08354", "PIA14642"],
    }

    for f in SC.glob("shot_*.mp4"):
        f.unlink()
    for f in SC.glob("s*.mp4"):
        f.unlink()

    print("== rendering shots ==")
    for si, k in enumerate(order):
        if k in ("s7", "s8"):
            continue
        gap_after = 1.3 if k == "s6" else (0.3 if k == "s5" else GAP)
        scene_dur = round(segs[k]["duration"] + (gap_after if si < len(order) - 1 else 1.2), 2)
        shots = SHOTS[k]
        # escalation: middle scenes get more cuts
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
            out = SC / f"shot_{k}_{i}.mp4"
            dark = 0.06 if k == "s6" else 0.0
            if not render_still(im(img), out, d, move, shake=shake, zmax=zmax, yoff=yoff, dark=dark):
                print(f"  [ERR] {out.name}")
                continue
            shots_meta.append(out)
        lst = WORK / f"concat_f4_{k}.txt"
        with open(lst, "w") as f:
            for out in shots_meta:
                f.write(f"file '{out}'\n")
        scene = SC / f"{k}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", str(scene)], check=True)
        d = dur_of(scene)
        print(f"  {k} scene {d:.2f}s ({len(shots_meta)} shots)")

        if k in ("s7", "s8"):
            continue
        # overlays
        vf = caption_filters(segs[k]["words"], d)
        CHIPS = {
            "s1": [hud_chip("AN OCEAN · 10+ KM BELOW THE ICE", 3.2, 8.0)],
            "s2": [hud_chip("100+ GEYSERS", 2.5, 6.0), hud_chip("CASSINI FLEW THROUGH · 2005", 10.0, 15.0)],
            "s3": [hud_chip("SALTS · ORGANICS · SILICA", 2.5, 6.5), hud_chip("PHOSPHATES: 2023", 11.0, 16.5)],
            "s4": [hud_chip("PLUME: 10,000 KM", 2.0, 5.5), hud_chip("E RING = ITS OCEAN", 9.5, 15.0)],
            "s5": [hud_chip("THE HIDDEN OCEAN", 2.5, 6.0), hud_chip("NO SUNLIGHT REQUIRED", 10.5, 16.0)],
            "s6": [hud_chip("BEST PLACE TO SEARCH FOR LIFE", 2.0, 10.5)],
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
        tmp.replace(scene)
        print(f"  {k} overlaid")

    # s7: engagement question over dark starfield + page watermark banner
    print("== s7 question card ==")
    d7 = round(max(6.5, segs["s7"]["duration"] + 1.6), 2)
    q_lines = [("THE QUESTION IS SIMPLE.", 54, "white", 700),
               ("WHAT'S HIDING", 64, "0x67E8F9", 810),
               ("DOWN THERE?", 64, "0x67E8F9", 900)]
    vf7 = [f"fade=t=in:st=0:d=0.4"]
    for i, (txt, fs, col, y) in enumerate(q_lines):
        t0 = 0.5 + i * 0.45
        vf7.append(
            f"drawtext=fontfile={FONTB}:text='{esc(txt)}':fontsize={fs}:fontcolor={col}:"
            f"borderw=4:bordercolor=black@0.9:x=(w-text_w)/2:y={y}:"
            f"enable='gte(t\\,{t0})'")
    vf7.append(
        f"drawtext=fontfile={FONTB}:text='COMMENT YOUR THEORY':fontsize=44:fontcolor=white:"
        f"box=1:boxcolor=0xFF6B35@0.85:boxborderw=18:"
        f"x=(w-text_w)/2:y=1030:enable='gte(t\\,2.2)'")
    vf7.append(
        f"drawtext=fontfile={FONTB}:text='YOUR ANSWER MIGHT BE RIGHT.':fontsize=32:fontcolor=0xE8DCC8:"
        f"x=(w-text_w)/2:y=1130:enable='gte(t\\,3.0)'")
    vf7.append(f"fade=t=out:st={d7-0.4:.2f}:d=0.4")
    # starfield background from a dimmed real frame
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-loop", "1", "-framerate", str(FPS), "-t", str(d7 + 0.5),
                    "-i", str(im("PIA17216")),
                    "-vf", (f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
                            f"eq=brightness=-0.28:saturation=0.75,gblur=sigma=8,"
                            f"vignette=PI/3.8,scale=1080:1920,format=yuv420p"),
                    "-t", str(d7), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                    str(SC / "s7_bg.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(SC / "s7_bg.mp4"), "-i", str(BRAND / "banner.png"),
                    "-filter_complex",
                    (f"[1:v]scale=760:-1[wm];"
                     f"[0:v][wm]overlay=(W-w)/2:H-560,"
                     + ",".join(vf7)),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-an",
                    str(SC / "s7.mp4")], check=True)
    print(f"  s7 question card {d7:.2f}s")

    # s8: black branding card — banner composited with PIL (fade-alpha overlays are broken)
    print("== s8 branding card ==")
    d8 = 4.2
    card = Image.new("RGB", (W, H), (0, 0, 0))
    banner = Image.open(BRAND / "banner.png").convert("RGBA")
    bw = 860
    bh = int(banner.height * bw / banner.width)
    banner = banner.resize((bw, bh), Image.LANCZOS)
    card.paste(banner, ((W - bw) // 2, 760), banner)
    draw = ImageDraw.Draw(card)
    f1 = ImageFont.truetype(FONTB, 40)
    f2 = ImageFont.truetype(FONTB, 32)
    def _center(txt, f, fill, y):
        tw = draw.textlength(txt, font=f)
        draw.text(((W - tw) / 2, y), txt, font=f, fill=fill)
    _center("FOLLOW FOR MORE COSMIC DISCOVERIES", f1, (232, 220, 200), 1150)
    _center("COMMENT: WHAT IS HIDING DOWN THERE?", f2, (143, 216, 255), 1230)
    p8 = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-vf", "fade=t=in:st=0.3:d=0.7,fade=t=out:st=3.7:d=0.5",
                           "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-an",
                           str(SC / "s8.mp4")], stdin=subprocess.PIPE)
    for _ in range(int(d8 * FPS)):
        p8.stdin.write(card.tobytes())
    p8.stdin.close(); p8.wait()
    print(f"  s8 branding card {d8:.2f}s")

    print("== concat + audio ==")
    lst = WORK / "concat_f4.txt"
    with open(lst, "w") as f:
        for k in order:
            f.write(f"file '{SC / f'{k}.mp4'}'\n")
    video = WORK / "video_f4.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(video)], check=True)
    print(f"  video {dur_of(video):.2f}s")

    # regenerate music bed for the new total (same arc, anchors shifted)
    bed = A / "music" / "bed_f4.wav"
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
             f"atrim=0:{total},asetpts=PTS-STARTPTS,volume=0.30[mus]"]
    labels = ["[mus]"]
    fi = 1
    for k in order:
        inputs += ["-i", segs[k]["file"]]
        st = starts[k]
        parts.append(f"[{fi}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                     f"volume=1.9,adelay={int(st*1000)}|{int(st*1000)}[vo{fi}]")
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
                 f"atrim=0:{total},asetpts=PTS-STARTPTS,"
                 f"acompressor=threshold=-20dB:ratio=2.5:attack=15:release=220:makeup=2,"
                 f"alimiter=limit=0.95[out]")
    mix = WORK / "mix_f4.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", ";".join(parts), "-map", "[out]",
                    "-c:a", "pcm_s16le", str(mix)], check=True)
    print(f"  mix {dur_of(mix):.1f}s")

    raw = WORK / "raw_f4.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(mix),
                    "-i", str(BRAND / "watermark.png"),
                    "-filter_complex",
                    f"[0:v][2:v]overlay=W-w-36:130:format=auto[vwm]",
                    "-map", "[vwm]", "-map", "1:a", "-c:v", "libx264", "-preset", "fast",
                    "-crf", "19", "-c:a", "aac", "-b:a", "192k",
                    "-t", str(total), "-movflags", "+faststart", str(raw)], check=True)
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
