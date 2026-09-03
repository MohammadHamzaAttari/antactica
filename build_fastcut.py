#!/usr/bin/env python3
"""Enceladus FAST-CUT v2 — stock clips + fastest camera movements + punchy editing.

Editing style: 1.8-2.6s shots, 3-4 cuts per sentence, alternating punch-zooms,
speed ramps (0.55x/1.6x), white-flash and whip-pan transitions, shake accents.
Keeps: word-synced kinetic captions, HUD chips, music/SFX arc, loudnorm.
"""
import subprocess, json, os, re
from pathlib import Path
from PIL import ImageFont, ImageDraw, Image

BASE = Path(__file__).parent
CL = BASE / "clips_e"
SC = BASE / "scenes_f"
SC.mkdir(exist_ok=True)
WORK = BASE / "work"
A = BASE / "assets"
FONTB = "/tmp/opencode/Inter-Bold.ttf"
OUT = BASE / "enceladus_fastcut_v2_9x16.mp4"

W, H, FPS = 1080, 1920, 30

# ---------------------------------------------------------------- helpers
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

# ---------------------------------------------------------------- captions
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

# ---------------------------------------------------------------- camera
def punch(move, n, z=0.28):
    """Fast camera moves on pre-scaled 2160x3840."""
    if move == "punch_in":
        return f"zoompan=z='1.0+{z}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if move == "punch_out":
        return f"zoompan=z='{1+z}-{z}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if move == "whip_pan":
        # sweep across the valid pan range (no clamping / no frozen tail)
        return (f"zoompan=z='1.22':x='(iw-ow/zoom)*(on/{n})'"
                f":y='ih/2-(ih/zoom/2)'")
    if move == "crash_zoom":
        # hard crash (first ~1s) + continuous slow push afterward: never freezes
        return f"zoompan=z='1.0+{z}*min(1,3*on/{n})+{z*0.5}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if move == "drift":
        return f"zoompan=z='1.10+0.04*sin(2*PI*on/{n})':x='iw/2-(iw/zoom/2)+16*sin(2*PI*on/{n})':y='ih/2-(ih/zoom/2)'"
    return "zoompan=z='1.05':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

# ---------------------------------------------------------------- shot render
def render_shot(clip, out, dur, move, speed=1.0, shake=0.0, flash_in=False,
                ss_pct=0.12,
                grade="eq=saturation=1.16:contrast=1.08,vignette=PI/4.5"):
    """Cut `dur` seconds out of clip (start offset varies per shot), apply camera+speed."""
    n = int(dur * FPS)
    src_d = dur_of(clip)
    ss = min(ss_pct * src_d, max(0, src_d - dur / speed - 0.5))
    vf = []
    # speed via setpts
    if abs(speed - 1.0) > 0.02:
        vf.append(f"setpts={1/speed:.4f}*PTS")
    vf.append(f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840")
    vf.append(punch(move, n) + f":d={n}:s=1080x1920:fps={FPS}")
    if shake > 0:
        vf.append(f"crop=1080:1920:(iw-1080)/2+{shake}*sin(37*t):(ih-1920)/2+{shake}*cos(29*t)")
    vf.append(grade)
    if flash_in:
        # brief white flash on entry: brighten then decay over ~0.12s, then neutral
        # (fade-from-white via luma curve driven by frame number is not supported;
        #  use fade=in from white with tiny duration -> fade filter handles it)
        vf.append("fade=t=in:st=0:d=0.12:color=white")
    vf.append(f"fps={FPS},format=yuv420p")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-ss", f"{ss:.2f}", "-i", str(clip),
           "-vf", ",".join(vf),
           "-t", f"{dur:.3f}",
           "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-an", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [ERR] {out.name}: {r.stderr[-300:]}")
        return False
    return True

# ---------------------------------------------------------------- main
def main():
    man = json.loads((BASE / "audio" / "vo_e" / "manifest.json").read_text())
    segs = {s["name"]: s for s in man}
    order = ["s1", "s2", "s3", "s4", "s5", "s6"]
    GAP = 0.35   # tighter than v1 (fast-cut pacing)
    starts, t = {}, 0.0
    for i, k in enumerate(order):
        starts[k] = round(t, 2)
        t += segs[k]["duration"] + (GAP if i < 5 else 0.9)
    total = round(t, 2)
    print(f"total {total}s | starts {starts}")

    # shots per scene: (clip, weight) — weight = relative share of scene dur
    SHOTS = {
        "s1": [(CL / "b1_ocean_spray_pexels_19923959.mp4", 1.0),
               (CL / "b1_ocean_spray_pexels_27672274.mp4", 0.85),
               (CL / "b1_ocean_spray_mixkit_17752.mp4", 0.7)],
        "s2": [(CL / "b2_space_arrival_pexels_33482346.mp4", 1.0),
               (CL / "b2_space_arrival_pexels_31541421.mp4", 0.9),
               (CL / "b2_space_arrival_mixkit_34352.mp4", 0.6)],
        "s3": [(CL / "b3_chemistry_pexels_32790667.mp4", 1.0),
               (CL / "b3_chemistry_pexels_7639590.mp4", 0.9),
               (CL / "b3_chemistry_pexels_32432976.mp4", 0.7)],
        "s4": [(CL / "b4_epic_scale_pexels_29477450.mp4", 1.0),
               (CL / "b4_epic_scale_mixkit_48402.mp4", 0.8),
               (CL / "b4_epic_scale_pexels_10239476.mp4", 0.65)],
        "s5": [(CL / "b5_hidden_ocean_pexels_31147055.mp4", 1.0),
               (CL / "b5_hidden_ocean_mixkit_10297.mp4", 0.8),
               (CL / "b5_hidden_ocean_pexels_20184113.mp4", 0.65)],
        "s6": [(CL / "b6_journey_cta_mixkit_45229.mp4", 1.0),
               (CL / "b6_journey_cta_mixkit_44962.mp4", 0.85),
               (CL / "b6_journey_cta_pexels_7615680.mp4", 0.5)],
    }
    MOVES = ["punch_in", "punch_out", "crash_zoom", "whip_pan", "drift"]
    SPEEDS = [1.0, 1.3, 0.8, 1.5, 1.15]

    for f in SC.glob("shot_*.mp4"):
        f.unlink()
    for f in SC.glob("s*.mp4"):
        f.unlink()

    print("== rendering fast-cut shots ==")
    for si, k in enumerate(order):
        scene_dur = round(segs[k]["duration"] + (GAP if k != "s6" else 0.9), 2)
        shots = SHOTS[k]
        # cut points: 6-8 shots per scene, uneven rhythm (1.4-2.8s each)
        n_shots = max(4, min(8, int(scene_dur / 2.1)))
        # golden-rhythm pattern: long-short-short-long-short...
        pattern = [1.0, 0.55, 0.7, 0.9, 0.5, 0.75, 1.1, 0.6]
        psum = sum(pattern[:n_shots])
        durs = [scene_dur * p / psum for p in pattern[:n_shots]]
        shots_meta = []
        acc = 0.0
        for i, d in enumerate(durs):
            d = round(d, 3)
            acc += d
            clip = shots[i % len(shots)][0]
            move = MOVES[(si * 3 + i) % len(MOVES)]
            speed = SPEEDS[(si + 2 * i) % len(SPEEDS)]
            # near-static sources (CGI space) need aggressive camera + speed
            if "space_arrival" in clip.name:
                move = "crash_zoom" if i % 2 == 0 else "punch_in"
                speed = max(speed, 1.5)
            shake = 2.5 if move == "crash_zoom" else (1.5 if move == "whip_pan" else 0.0)
            # vary in-point so repeats of the same clip look different
            ss_pct = 0.10 + 0.11 * ((si * 7 + i * 13) % 5)
            out = SC / f"shot_{k}_{i}.mp4"
            okk = render_shot(clip, out, d, move, speed=speed, shake=shake,
                              flash_in=(i > 0 and durs[i-1] > d),
                              ss_pct=ss_pct)
            if okk:
                shots_meta.append((out, acc - d, acc))
                print(f"  {k} shot{i} {d:.2f}s {move} x{speed} <- {clip.name[:38]}")
        # concat shots -> scene (with white-flash xfade at cuts)
        lst = WORK / f"concat_f_{k}.txt"
        with open(lst, "w") as f:
            for out, _, _ in shots_meta:
                f.write(f"file '{out}'\n")
        scene = SC / f"{k}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", str(scene)], check=True)
        print(f"  {k} scene {dur_of(scene):.2f}s")

    # overlay captions/chips per scene
    print("== overlays ==")
    for k in order:
        scene = SC / f"{k}.mp4"
        d = dur_of(scene)
        vf = kinetic_filters(segs[k]["words"], d)
        # per-scene chips (from v1 mapping, remapped to fast-cut timings)
        CHIPS = {
            "s1": [hud_chip("DIAMETER: ~500 KM", 4.0, 8.0), hud_chip("GEYSERS: 100+", 9.5, 15.0)],
            "s2": [hud_chip("CASSINI - 2005", 3.0, 7.0), hud_chip("PLUME DIVE: 2005", 11.0, 15.0)],
            "s3": [hud_chip("SALTS + ORGANICS", 3.5, 7.5), hud_chip("PHOSPHATES: 2023", 11.5, 16.5)],
            "s4": [hud_chip("PLUME: 10,000 KM", 2.0, 6.0), hud_chip("LOSS: 200 KG/SEC", 9.5, 15.5)],
            "s5": [hud_chip("OCEAN: 10+ KM DEEP", 3.0, 10.0)],
            "s6": [hud_chip("FOLLOW UNIVERSE IMPACT", 5.0, 12.5, fs=44, color="0xFFA860")],
        }
        vf += CHIPS.get(k, [])
        if k == "s6":
            vf.append(f"fade=t=out:st={d-0.7:.2f}:d=0.7")
        tmp = SC / f"{k}_ov.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(scene),
                        "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "fast",
                        "-crf", "19", "-an", str(tmp)], check=True)
        tmp.replace(scene)
        print(f"  {k} overlaid ({d:.2f}s)")

    # concat scenes
    print("== concat + audio ==")
    lst = WORK / "concat_f.txt"
    with open(lst, "w") as f:
        for k in order:
            f.write(f"file '{SC / f'{k}.mp4'}'\n")
    video = WORK / "video_f.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(video)], check=True)
    print(f"  video {dur_of(video):.2f}s")

    # reuse v1 music bed + SFX pipeline (bed_e.wav was generated for 93.22s; total is same VO)
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
    # SFX: whoosh+impact at every scene cut (fast-cut needs accents), shimmer at CTA
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
    mix = WORK / "mix_f.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", ";".join(parts), "-map", "[out]",
                    "-c:a", "pcm_s16le", str(mix)], check=True)
    print(f"  mix {dur_of(mix):.1f}s")

    raw = WORK / "raw_f.mp4"
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
