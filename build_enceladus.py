#!/usr/bin/env python3
"""Enceladus reel — full build in the moon_anomaly viral style.

1. Procedural plume-spray animation (s4a)
2. Per-scene render: NASA imagery + Ken Burns + kinetic word-chunk captions
   (word timings from edge-tts WordBoundary, chunk highlight, HUD metric chips)
3. Audio-anchored concat + music bed + SFX + loudnorm
"""
import subprocess, json, math, os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = Path(__file__).parent
IMGE = BASE / "images_e"
SC = BASE / "scenes_e"
SC.mkdir(exist_ok=True)
PROC = BASE / "proc"
WORK = BASE / "work"
WORK.mkdir(exist_ok=True)
A = BASE / "assets"
FONTB = "/tmp/opencode/Inter-Bold.ttf"
OUT = BASE / "enceladus_alien_ocean_93s_9x16.mp4"

W, H, FPS = 1080, 1920, 30
GAP = 0.55

# ------------------------------------------------------------------ helpers
pil_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
_fc = {}

def get_font(fs):
    if fs not in _fc:
        _fc[fs] = ImageFont.truetype(FONTB, fs)
    return _fc[fs]

def fit_fs(text, start=78, minf=48, maxw=920):
    fs = start
    while fs > minf and pil_draw.textlength(text, font=get_font(fs)) > maxw:
        fs -= 4
    return fs

def esc(t):
    return (t.replace("'", "\u2019")
             .replace(":", r"\:").replace("%", r"\%").replace(",", r"\,"))

def dur_of(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())

# ------------------------------------------------------------------ 1. spray anim
def gen_spray(T=7.8):
    """Enceladus limb bottom + icy plume jets feeding an E-ring arc."""
    rng = np.random.default_rng(555)
    n_p = 900
    ang0 = -np.pi / 2 + (rng.random(n_p) - 0.5) * 0.9
    spd = 130 + rng.random(n_p) * 220
    birth = rng.random(n_p) * 1.6
    col = np.zeros((n_p, 3))
    col[:, 0] = 200 + rng.random(n_p) * 55
    col[:, 1] = 225 + rng.random(n_p) * 30
    col[:, 2] = 255
    cx, cy = W // 2, int(H * 0.86)
    R = 520
    fyy, fxx = np.mgrid[0:H, 0:W]
    el = (fxx - W / 2) * 0.55 + (fyy - int(H * 0.30))
    band = np.exp(-(el ** 2) / (2 * 60.0 ** 2)) * 0.5

    def _blur_layer(layer, blur):
        return np.asarray(Image.fromarray(np.clip(layer * 8, 0, 255).astype(np.uint8))
                          .filter(ImageFilter.GaussianBlur(blur)), np.float32) / 8.0

    def _glow(cv, xs, ys, bs, colr, blur=1.6):
        xi = np.clip(np.asarray(xs, int), 0, W - 1)
        yi = np.clip(np.asarray(ys, int), 0, H - 1)
        b = np.asarray(bs, np.float32)
        ca = np.asarray(colr, np.float32)
        if ca.ndim == 1:
            layer = np.zeros((H, W), dtype=np.float32)
            np.add.at(layer, (yi, xi), b)
            cv += _blur_layer(layer, blur)[..., None] * ca / 255.0
        else:
            cl = np.zeros((H, W, 3), dtype=np.float32)
            for c in range(3):
                ch = np.zeros((H, W), dtype=np.float32)
                np.add.at(ch, (yi, xi), b * ca[:, c] / 255.0)
                cl[..., c] = _blur_layer(ch, blur)
            cv += cl
        return cv

    N = int(T * FPS)
    out = PROC / "anim_spray.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-vf", "scale=1080:1920:flags=lanczos,unsharp=5:5:0.3",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                          "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    for i in range(N):
        t = i / FPS
        cv = np.zeros((H, W, 3), dtype=np.float32)
        cv += 5
        cv[..., 2] += 8
        cv += (band * (20 + 30 * min(1, t / 4)))[..., None].astype(np.float32) * \
              np.array([0.75, 0.85, 1.0], np.float32)
        rr = np.sqrt((fxx - cx) ** 2 + (fyy - cy) ** 2)
        limb = np.exp(-((rr - R) ** 2) / (2 * 26 ** 2))
        terr = 0.75 + 0.25 * np.sin(fxx * 0.11) * np.sin(fyy * 0.09)
        cv += (limb * terr * 120)[..., None] * np.array([0.95, 0.97, 1.0], np.float32)
        disk = np.clip(1.0 - rr / R, 0, 1)
        cv += (disk ** 1.6 * 38)[..., None] * np.array([0.85, 0.9, 1.0], np.float32)
        sp = np.exp(-(((fxx - cx) ** 2) / (2 * 120 ** 2) + ((fyy - (cy - R)) ** 2) / (2 * 40 ** 2)))
        cv += (sp * 40)[..., None] * np.array([1.0, 0.8, 0.55], np.float32)

        alive = t >= birth
        if alive.any():
            dt = (t - birth)[alive]
            a = ang0[alive]
            vx = np.sin(a) * spd[alive] * 0.55
            vy = -np.cos(a) * spd[alive]
            x = cx + vx * dt
            y = (cy - R) + vy * dt + 30 * dt ** 2
            fade = np.clip(1.0 - dt / 4.4, 0, 1) ** 1.3
            spread = np.clip(1.0 - np.abs(x - cx) / (W * 0.6), 0, 1)
            cv = _glow(cv, x, y, fade * 55 * spread, col[alive], blur=1.5)
            cone = np.clip(1.0 - (cy - fyy) / 700.0, 0, 1) * \
                   np.exp(-((fxx - cx) ** 2) / (2 * (150 + (cy - fyy) * 0.35) ** 2)) * \
                   (fyy < cy - R)
            cv += (cone * 26 * min(1, t / 1.2))[..., None] * np.array([0.8, 0.9, 1.0], np.float32)

        p.stdin.write(np.clip(cv, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    print(f"  spray anim ok ({out.stat().st_size//1024}KB)")

# ------------------------------------------------------------------ 2. kinetic captions
KEYWORDS = {"spraying", "ocean", "geysers", "cassini", "impossible", "spray",
            "salts", "organic", "silica", "phosphates", "life", "ring",
            "water", "spacecraft", "tasted", "100", "hundred", "absurd"}

def kinetic_filters(words, scene_dur):
    words = [w for w in words if w.get("w")]
    chunks, cur = [], []
    for wd in words:
        cur.append(wd)
        t_clean = wd["w"].strip()
        if len(cur) >= 3 or (t_clean.endswith((".", "!", "?")) and len(cur) >= 2):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    parts = []
    for i, ch in enumerate(chunks):
        t0 = ch[0]["t"]
        t1 = chunks[i + 1][0]["t"] if i + 1 < len(chunks) else min(t0 + sum(w["d"] for w in ch) + 0.9, scene_dur - 0.15)
        t1 = min(t1, scene_dur - 0.15)
        text = " ".join(w["w"] for w in ch)
        hit = any(w["w"].strip(".,!?;:").lower() in KEYWORDS for w in ch)
        fs = fit_fs(text)
        col = "0x8FF0FF" if hit else "white"
        parts.append(
            f"drawtext=fontfile={FONTB}:text='{esc(text)}':fontsize={fs}:fontcolor={col}:"
            f"box=1:boxcolor=black@0.45:boxborderw=20:"
            f"borderw=2:bordercolor=black@0.6:"
            f"x=(w-text_w)/2:y=1310:"
            f"enable='between(t\\,{t0:.2f}\\,{t1:.2f})'")
    return parts

def hud_chip(text, t0, t1, y=250, fs=36, color="0x8FD8FF"):
    return (f"drawtext=fontfile={FONTB}:text='{esc(text)}':fontsize={fs}:fontcolor={color}:"
            f"box=1:boxcolor=black@0.55:boxborderw=14:"
            f"x=w-text_w-40:y={y}:enable='between(t\\,{t0}\\,{t1})'")

# ------------------------------------------------------------------ 3. scene renders
def kb(move, n, zmax=0.3):
    if move == "zoom_in":
        z, x, y = f"1.0+{zmax}*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "zoom_in_hard":
        z, x, y = f"1.0+{zmax + 0.25}*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "zoom_out":
        z, x, y = f"{1 + zmax}-{zmax}*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "drift":
        z, x, y = f"1.12+0.05*sin(2*PI*on/{n})", \
                  f"iw/2-(iw/zoom/2)+20*sin(2*PI*on/{n})", "ih/2-(ih/zoom/2)"
    else:
        z, x, y = "1.08", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    return (f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s=1080x1920:fps={FPS}")

GRADE = "eq=saturation=1.14:contrast=1.07:brightness=0.01,vignette=PI/4.3"
GRADE_SOFT = "eq=saturation=1.10:contrast=1.0:brightness=0.04,vignette=PI/6"

def render_scene(name, dur, sources, words, chips, fade_out=0.0):
    out = SC / f"{name}.mp4"
    n = int(dur * FPS)
    grade = GRADE_SOFT if name in ("s3", "s5") else GRADE
    vf = [grade]
    if fade_out > 0:
        vf.append(f"fade=t=out:st={dur - fade_out:.2f}:d={fade_out}")
    vf += kinetic_filters(words, dur)
    vf += list(chips)
    vfs = ",".join(vf)

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    chains = []
    for i, (kind, path, move) in enumerate(sources):
        if kind == "img":
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur + 0.6), "-i", str(path)]
            chains.append(f"[{i}:v]scale=2160:3840:force_original_aspect_ratio=increase,"
                          f"crop=2160:3840,{kb(move, n)},format=yuv420p[c{i}]")
        else:
            cmd += ["-stream_loop", "-1", "-i", str(path)]
            # slow camera push-in on video clips: guarantees visible motion
            z = f"1.0+0.14*in/{n}"
            chains.append(f"[{i}:v]fps={FPS},scale=2160:3840:force_original_aspect_ratio=increase,"
                          f"crop=2160:3840,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                          f":d=1:s=1080x1920:fps={FPS},format=yuv420p[c{i}]")
    cur = "c0"
    if len(sources) > 1:
        xoff = round(dur / len(sources) - 0.5, 2)
        for i in range(1, len(sources)):
            nxt = f"x{i}"
            chains.append(f"[{cur}][c{i}]xfade=transition=fade:duration=0.7:offset={xoff:.2f}[{nxt}]")
            cur = nxt
    chains.append(f"[{cur}]{vfs}[vout]")
    cmd += ["-filter_complex", ";".join(chains), "-map", "[vout]"]
    cmd += ["-t", str(dur), "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-pix_fmt", "yuv420p", "-an", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [ERR] {name}: {r.stderr[-400:]}")
    else:
        print(f"  [ok] {name} {dur:.2f}s ({out.stat().st_size//1024}KB)")

# ------------------------------------------------------------------ main
def main():
    print("== 1. spray animation ==")
    gen_spray(7.8)

    print("== 2. scenes ==")
    man = json.loads((BASE / "audio" / "vo_e" / "manifest.json").read_text())
    segs = {s["name"]: s for s in man}
    order = ["s1", "s2", "s3", "s4", "s5", "s6"]
    starts, t = {}, 0.0
    for i, k in enumerate(order):
        starts[k] = round(t, 2)
        t += segs[k]["duration"] + (GAP if i < 5 else 1.0)
    total = round(t, 2)
    print(f"  total {total}s, starts {starts}")

    SCENES = [
        ("s1", [("video", PROC / "anim_e1_jets.mp4", "static")],
         [hud_chip("DIAMETER: ~500 KM", 4.0, 9.0),
          hud_chip("GEYSERS: 100+", 10.0, 15.0, y=250)]),
        ("s2", [("video", PROC / "anim_e2_dive.mp4", "static")],
         [hud_chip("CASSINI - 2005", 3.5, 8.5),
          hud_chip("FIRST PLUME DIVE: 2005", 11.5, 15.2)]),
        ("s3", [("video", PROC / "anim_e3_chem.mp4", "static")],
         [hud_chip("SALTS + ORGANICS + SILICA", 4.0, 9.0),
          hud_chip("PHOSPHATES: 2023", 12.0, 16.8)]),
        ("s4", [("video", PROC / "anim_e4_ring.mp4", "static")],
         [hud_chip("PLUME: ~10,000 KM", 1.5, 6.5),
          hud_chip("LOSS: 200 KG / SEC", 9.0, 15.5)]),
        ("s5", [("video", PROC / "anim_e5_ocean.mp4", "static")],
         [hud_chip("OCEAN DEPTH: 10+ KM", 3.0, 10.5)]),
        ("s6", [("video", PROC / "anim_e6_cta.mp4", "static")],
         [hud_chip("FOLLOW UNIVERSE IMPACT", 6.0, 12.3, fs=44, color="0xFFA860")]),
    ]
    for f in SC.glob("s*.mp4"):
        f.unlink()
    for name, sources, chips in SCENES:
        dur = round(segs[name]["duration"] + (GAP if name != "s6" else 1.0), 2)
        srcs = [(k[1:], p, m) for k, p, m in sources]
        render_scene(name, dur, srcs, segs[name]["words"], chips,
                     fade_out=0.7 if name == "s6" else 0.0)

    print("== 3. audio ==")
    bed = A / "music" / "bed_e.wav"
    T = total
    fc = f"""
[0:a]volume=0.34,lowpass=f=100[dr1];
[1:a]volume=0.15,tremolo=f=0.14:d=0.3[p1];
[2:a]volume=0.12,tremolo=f=0.17:d=0.3[p2];
[3:a]volume=0.10,tremolo=f=0.12:d=0.3[p3];
[4:a]adelay=6000|6000,apad=whole_dur={T},volume=0.4,afade=t=in:st=6:d=1.5,afade=t=out:st=8:d=0.3[sh1];
[4:a]adelay=35000|35000,apad=whole_dur={T},volume=0.4,afade=t=in:st=35:d=1.5,afade=t=out:st=37:d=0.3[sh2];
[4:a]adelay={int(starts['s6']*1000)}|{int(starts['s6']*1000)},apad=whole_dur={T},volume=0.45,afade=t=in:st={starts['s6']}:d=1.0,afade=t=out:st={starts['s6']+2}:d=0.4[sh3];
[5:a]volume=0.42,tremolo=f=0.6:d=0.85,lowpass=f=260[pulse];
[6:a]adelay=14000|14000,apad=whole_dur={T},volume=0.4,afade=t=in:st=14:d=1.8,afade=t=out:st=15.8:d=0.2[r1];
[6:a]adelay=44000|44000,apad=whole_dur={T},volume=0.4,afade=t=in:st=44:d=1.8,afade=t=out:st=45.8:d=0.2[r2];
[6:a]adelay={int((starts['s6']-2)*1000)}|{int((starts['s6']-2)*1000)},apad=whole_dur={T},volume=0.45,afade=t=in:st={starts['s6']-2}:d=1.8,afade=t=out:st={starts['s6']-0.2}:d=0.2[r3];
[dr1][p1][p2][p3][sh1][sh2][sh3][pulse][r1][r2][r3]amix=inputs=11:duration=longest:normalize=0[m];
[m]lowpass=f=2600,afade=t=in:st=0:d=2,afade=t=out:st={T-2.4:.2f}:d=2.2[out]"""
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

    sfxd = A / "sfx"
    def sfx(name, args, af):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-af", af,
                        str(sfxd / name)], capture_output=True)
    sfx("boom.mp3", ["-f", "lavfi", "-i", "sine=frequency=48:duration=1.6"],
        "volume=0.9,afade=t=in:st=0:d=0.01,afade=t=out:st=0.15:d=1.45,lowpass=f=160")
    sfx("whoosh.mp3", ["-f", "lavfi", "-i", "anoisesrc=d=1.4:c=pink:r=44100:a=0.35"],
        "highpass=f=250,lowpass=f=3800,afade=t=in:st=0:d=0.35,afade=t=out:st=0.9:d=0.5,tremolo=f=9:d=0.4,volume=0.8")
    sfx("impact.mp3", ["-f", "lavfi", "-i", "sine=frequency=70:duration=1.4"],
        "volume=0.85,afade=t=in:st=0:d=0.01,afade=t=out:st=0.12:d=1.28,lowpass=f=220")
    sfx("shimmer.mp3", ["-f", "lavfi", "-i", "sine=frequency=1240:duration=1.2"],
        "tremolo=f=14:d=0.8,volume=0.30,afade=t=in:st=0:d=0.02,afade=t=out:st=0.15:d=1.0")

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
    sfx_events = [(0.10, "boom", 0.9)] + \
                 [(starts[k] - 0.12, "whoosh", 0.7) for k in order[1:]] + \
                [(starts["s4"] + 9.6, "impact", 0.85), (starts["s6"] + 0.4, "shimmer", 0.9)]
    for i, (tt, nm, vol) in enumerate(sfx_events):
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
    mix = WORK / "mix_e.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", ";".join(parts), "-map", "[out]",
                    "-c:a", "pcm_s16le", str(mix)], check=True)
    print(f"  mix ok ({dur_of(mix):.1f}s)")

    print("== 4. concat + merge ==")
    lst = WORK / "concat_e.txt"
    with open(lst, "w") as f:
        for k in order:
            f.write(f"file '{SC / f'{k}.mp4'}'\n")
    vc = WORK / "video_e.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(vc)], check=True)
    print(f"  video {dur_of(vc):.2f}s")
    raw = WORK / "raw_e.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vc), "-i", str(mix),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", str(total), "-movflags", "+faststart", str(raw)], check=True)
    r = subprocess.run(["ffmpeg", "-y", "-i", str(raw),
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    import re
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
