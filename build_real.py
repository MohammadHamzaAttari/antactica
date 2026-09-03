#!/usr/bin/env python3
"""Enceladus v3 — fast cut built 100% from ORIGINAL NASA Cassini imagery.
Every frame shows the real moon / its real jets / its real ring / its real ocean.
Fast editing: 1.4-2.8s shots, crash-zooms into actual features, whip pans across
the real tiger-stripe panorama, flash cuts. Kinetic captions + chips + audio kept."""
import subprocess, json, os, re
from pathlib import Path
from PIL import ImageFont, ImageDraw, Image

BASE = Path(__file__).parent
IMGR = BASE / "images_real"
SC = BASE / "scenes_r"
SC.mkdir(exist_ok=True)
WORK = BASE / "work"
A = BASE / "assets"
FONTB = "/tmp/opencode/Inter-Bold.ttf"
OUT = BASE / "enceladus_real_93s_9x16.mp4"

W, H, FPS = 1080, 1920, 30
GAP = 0.35

pil = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
_fc = {}
def get_font(fs):
    if fs not in _fc:
        _fc[fs] = ImageFont.truetype(FONTB, fs)
    return _fc[fs]

def fit_fs(text, start=78, minf=46, maxw=900):
    fs = start
    while fs > minf and pil.textlength(text, font=get_font(fs)) > maxw:
        fs -= 4
    return fs

def esc(t):
    return (t.replace("'", "\u2019")
             .replace(":", r"\:").replace("%", r"\%").replace(",", r"\,"))

def dur_of(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())

KEYWORDS = {"spraying", "ocean", "geysers", "cassini", "impossible", "spray",
            "salts", "organic", "silica", "phosphates", "life", "ring",
            "water", "spacecraft", "tasted", "hundred", "absurd", "flying"}

def kinetic_filters(words, scene_dur):
    words = [w for w in words if w.get("w")]
    chunks, cur = [], []
    for wd in words:
        cur.append(wd)
        if len(cur) >= 3 or (wd["w"].strip().endswith((".!?",)) and len(cur) >= 2):
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    parts = []
    for i, ch in enumerate(chunks):
        t0 = ch[0]["t"]
        t1 = chunks[i+1][0]["t"] if i+1 < len(chunks) else min(t0 + sum(w["d"] for w in ch) + 0.85, scene_dur - 0.12)
        t1 = min(t1, scene_dur - 0.12)
        text = " ".join(w["w"] for w in ch)
        hit = any(w["w"].strip(".,!?;:").lower() in KEYWORDS for w in ch)
        fs = fit_fs(text)
        col = "0x8FF0FF" if hit else "white"
        parts.append(
            f"drawtext=fontfile={FONTB}:text='{esc(text)}':fontsize={fs}:fontcolor={col}:"
            f"box=1:boxcolor=black@0.45:boxborderw=18:"
            f"borderw=2:bordercolor=black@0.6:"
            f"x=(w-text_w)/2:y=1310:"
            f"enable='between(t\\,{t0:.2f}\\,{t1:.2f})'")
    return parts

def hud_chip(text, t0, t1, y=250, fs=36, color="0x8FD8FF"):
    return (f"drawtext=fontfile={FONTB}:text='{esc(text)}':fontsize={fs}:fontcolor={color}:"
            f"box=1:boxcolor=black@0.55:boxborderw=14:"
            f"x=w-text_w-40:y={y}:enable='between(t\\,{t0}\\,{t1})'")

def pia_credit(pia):
    return (f"drawtext=fontfile={FONTB}:text='NASA\\: {pia}':fontsize=26:fontcolor=0xAFC0DC@"
            f"0.75:x=40:y=120:box=1:boxcolor=black@0.4:boxborderw=10")

def punch(move, n, z=0.34):
    if move == "punch_in":
        return f"zoompan=z='1.0+{z}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if move == "crash_zoom":
        # crash into the feature then keep pushing
        return f"zoompan=z='1.0+{z}*min(1,3*on/{n})+{z*0.45}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if move == "punch_out":
        return f"zoompan=z='{1+z}-{z}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if move == "whip_pan":
        return f"zoompan=z='1.18':x='(iw-ow/zoom)*(on/{n})':y='ih/2-(ih/zoom/2)'"
    if move == "drift":
        return f"zoompan=z='1.12+0.05*sin(2*PI*on/{n})':x='iw/2-(iw/zoom/2)+18*sin(2*PI*on/{n})':y='ih/2-(ih/zoom/2)'"
    return "zoompan=z='1.05':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

def render_still(img, out, dur, move, ss_off=0.0, shake=0.0, zmax=0.34):
    """Real NASA still with fast camera move. Pre-scale 2160x3840 for smooth zoompan."""
    n = int(dur * FPS)
    vf = [f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840",
          punch(move, n, z=zmax) + f":d={n}:s=1080x1920:fps={FPS}"]
    if shake > 0:
        vf.append(f"crop=1080:1920:(iw-1080)/2+{shake}*sin(41*t):(ih-1920)/2+{shake}*cos(31*t)")
    vf.append("unsharp=5:5:0.45")
    vf.append("eq=saturation=1.18:contrast=1.08:brightness=0.02,vignette=PI/4.6")
    vf.append(f"fps={FPS},format=yuv420p")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-loop", "1", "-framerate", str(FPS), "-t", str(dur + 0.4), "-i", str(img),
           "-vf", ",".join(vf),
           "-t", f"{dur:.3f}",
           "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-an", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [ERR-DBG] {r.stderr[-400:]}")
    return r.returncode == 0

def main():
    man = json.loads((BASE / "audio" / "vo_e" / "manifest.json").read_text())
    segs = {s["name"]: s for s in man}
    order = ["s1", "s2", "s3", "s4", "s5", "s6"]
    starts, t = {}, 0.0
    for i, k in enumerate(order):
        starts[k] = round(t, 2)
        t += segs[k]["duration"] + (GAP if i < 5 else 0.9)
    total = round(t, 2)
    print(f"total {total}s")

    def im(name):
        return IMGR / f"{name}.jpg"

    # shot lists: GLOBAL FIRST (whole planet), then medium, then INSIDE the feature.
    # (image, move, shake, zmax)  — zmax scales the zoom depth for that shot
    SHOTS = {
        "s1": [("PIA17216", "punch_in", 0, 0.22),        # GLOBAL: whole moon, rings behind
               ("PIA14642", "crash_zoom", 2.5, 0.38),    # the actual jets
               ("PIA06443", "crash_zoom", 2.0, 0.45),    # closer on plume
               ("PIA17198", "whip_pan", 1.5, 0.30),      # plume changing (wide)
               ("PIA17202", "punch_in", 0, 0.34)],       # limb + jets close
        "s2": [("PIA08354", "punch_in", 0, 0.18),        # GLOBAL: fractured world full disk
               ("PIA06205", "crash_zoom", 2.5, 0.42),    # closest flyby shot
               ("PIA17211", "punch_in", 0, 0.38),        # north polar close
               ("PIA17205", "punch_out", 0, 0.30)],      # departing (pull back out)
        "s3": [("PIA17216", "punch_in", 0, 0.20),        # GLOBAL re-anchor
               ("PIA10352", "crash_zoom", 2.5, 0.45),    # tiger stripes from orbit
               ("PIA11688", "whip_pan", 1.5, 0.38),      # geyser basin panorama
               ("PIA13620", "punch_in", 0, 0.50),        # INSIDE a hot stripe
               ("PIA11686", "punch_out", 0, 0.30)],      # tectonics wide pull
        "s4": [("PIA08921", "punch_in", 0, 0.20),        # GLOBAL: crescent + E ring
               ("PIA12512", "whip_pan", 1.5, 0.36),      # E ring wide
               ("PIA17172", "drift", 0, 0.30),           # Saturn system scale
               ("PIA08133", "punch_out", 0, 0.34)],      # moons + ring context
        "s5": [("PIA18071", "punch_in", 0, 0.30),        # GLOBAL interior diagram
               ("PIA18071", "crash_zoom", 2.5, 0.55),    # INTO the ocean layer
               ("PIA18071", "crash_zoom", 2.0, 0.72),    # deeper: core
               ("PIA14937", "whip_pan", 1.5, 0.30)],     # real surface map wide
        "s6": [("PIA17216", "punch_out", 0, 0.26),       # GLOBAL: pull away from moon
               ("PIA14642", "crash_zoom", 2.5, 0.40),    # jets one last time
               ("PIA12512", "drift", 0, 0.28),           # E ring — water becoming ring
               ("PIA08354", "punch_in", 0, 0.24)],       # full disk hold + fade
    }
    PIA_IDS = {
        "s1": ["PIA17216", "PIA14642", "PIA06443", "PIA17198", "PIA17202"],
        "s2": ["PIA08354", "PIA06205", "PIA17211", "PIA17205"],
        "s3": ["PIA17216", "PIA10352", "PIA11688", "PIA13620", "PIA11686"],
        "s4": ["PIA08921", "PIA12512", "PIA17172", "PIA08133"],
        "s5": ["PIA18071", "PIA18071", "PIA18071", "PIA14937"],
        "s6": ["PIA17216", "PIA14642", "PIA12512", "PIA08354"],
    }

    for f in SC.glob("shot_*.mp4"):
        f.unlink()
    for f in SC.glob("s*.mp4"):
        f.unlink()

    print("== rendering real-imagery shots ==")
    for si, k in enumerate(order):
        scene_dur = round(segs[k]["duration"] + (GAP if k != "s6" else 0.9), 2)
        shots = SHOTS[k]
        n_shots = max(4, min(8, int(scene_dur / 2.0)))
        pattern = [1.0, 0.55, 0.7, 0.9, 0.5, 0.75, 1.1, 0.6][:n_shots]
        psum = sum(pattern)
        durs = [scene_dur * p / psum for p in pattern[:n_shots]]
        shots_meta, acc = [], 0.0
        for i, d in enumerate(durs):
            d = round(d, 3)
            acc += d
            img, move, shake, zmax = shots[i % len(shots)]
            img = im(img)
            out = SC / f"shot_{k}_{i}.mp4"
            if not render_still(img, out, d, move, shake=shake, zmax=zmax):
                print(f"  [ERR] {out.name}")
                continue
            shots_meta.append(out)
            print(f"  {k} shot{i} {d:.2f}s {move} <- {img}")
        # concat
        lst = WORK / f"concat_r_{k}.txt"
        with open(lst, "w") as f:
            for out in shots_meta:
                f.write(f"file '{out}'\n")
        scene = SC / f"{k}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", str(scene)], check=True)
        d = dur_of(scene)
        print(f"  {k} scene {d:.2f}s")

        # overlays: captions + chips + rotating PIA credits
        vf = kinetic_filters(segs[k]["words"], d)
        CHIPS = {
            "s1": [hud_chip("DIAMETER: ~500 KM", 4.0, 8.0), hud_chip("GEYSERS: 100+", 9.5, 15.0)],
            "s2": [hud_chip("CASSINI - 2005", 3.0, 7.0), hud_chip("PLUME DIVE: 2005", 11.0, 15.0)],
            "s3": [hud_chip("SALTS + ORGANICS", 3.5, 7.5), hud_chip("PHOSPHATES: 2023", 11.5, 16.5)],
            "s4": [hud_chip("PLUME: 10,000 KM", 2.0, 6.0), hud_chip("LOSS: 200 KG/SEC", 9.5, 15.5)],
            "s5": [hud_chip("OCEAN: 10+ KM DEEP", 3.0, 10.0)],
            "s6": [hud_chip("FOLLOW UNIVERSE IMPACT", 5.0, 12.5, fs=44, color="0xFFA860")],
        }
        vf += CHIPS.get(k, [])
        ids = PIA_IDS[k]
        shot_d = d / max(1, len(shots_meta))
        # rotate the credit line through the shots (shot boundaries)
        for i in range(len(shots_meta)):
            pid = ids[i % len(ids)]
            t0, t1 = i * shot_d + 0.05, min((i + 1) * shot_d - 0.05, d)
            if t1 <= t0:
                continue
            base = pia_credit(pid)
            t0s, t1s = f"{t0:.2f}", f"{t1:.2f}"
            base += f":enable='between(t\\,{t0s}\\,{t1s})'"
            vf.append(base)
        if k == "s6":
            vf.append(f"fade=t=out:st={d-0.7:.2f}:d=0.7")
        tmp = SC / f"{k}_ov.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(scene),
                        "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "fast",
                        "-crf", "19", "-an", str(tmp)], check=True)
        tmp.replace(scene)
        print(f"  {k} overlaid ({d:.2f}s)")

    print("== concat + audio ==")
    lst = WORK / "concat_r.txt"
    with open(lst, "w") as f:
        for k in order:
            f.write(f"file '{SC / f'{k}.mp4'}'\n")
    video = WORK / "video_r.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(video)], check=True)
    print(f"  video {dur_of(video):.2f}s")

    bed = A / "music" / "bed_e.wav"
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
    for k in order[1:]:
        events.append((starts[k] - 0.08, "whoosh", 0.8))
        events.append((starts[k] + 0.02, "impact", 0.6))
    events += [(starts["s4"] + 9.5, "impact", 0.8), (starts["s6"] + 0.4, "shimmer", 0.9)]
    for i, (tt, nm, vol) in enumerate(events):
        inputs += ["-i", str(sfxd / f"{nm}.mp3")]
        parts.append(f"[{fi}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                     f"volume={vol},adelay={int(max(0,tt)*1000)}|{int(max(0,tt)*1000)}[x{fi}]")
        labels.append(f"[x{fi}]")
        fi += 1
    parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0[a1]")
    parts.append(f"[a1]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                 f"atrim=0:{total},asetpts=PTS-STARTPTS,"
                 f"acompressor=threshold=-20dB:ratio=2.5:attack=15:release=220:makeup=2,"
                 f"alimiter=limit=0.95[out]")
    mix = WORK / "mix_r.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", ";".join(parts), "-map", "[out]",
                    "-c:a", "pcm_s16le", str(mix)], check=True)
    print(f"  mix {dur_of(mix):.1f}s")

    raw = WORK / "raw_r.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(mix),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
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
