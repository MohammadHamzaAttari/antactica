#!/usr/bin/env python3
"""Final build: concat scenes -> mix VO+music+SFX (audio-anchored) -> merge -> loudnorm."""
import subprocess, json, re
from pathlib import Path

BASE = Path(__file__).parent
PROC = BASE / "scenes"
WORK = BASE / "work"
WORK.mkdir(exist_ok=True)
A = BASE / "assets"
OUT = BASE / "bigbang_worlds_109s_9x16.mp4"

tim = json.loads((WORK / "timings.json").read_text())
vm = json.loads((BASE / "audio" / "vo_manifest.json").read_text())
ORDER = ["01_hook", "02_different", "03_heavier", "04_explosion", "05_simulation",
         "06_earthshock", "07_water", "08_credibility", "09_possibility", "10_ending"]
T = tim["total"]

SCENE_FILES = [s["name"] for s in tim["scenes"]]

# (time, sfx, volume)
SFX_EVENTS = [
    (0.10, "boom", 0.9), (6.30, "impact", 0.8), (10.20, "whoosh", 0.75),
    (21.90, "whoosh", 0.75), (26.90, "riser", 0.7),
    (32.25, "riser", 0.75), (33.50, "boom", 0.95),
    (44.30, "swell", 0.8), (48.55, "whoosh", 0.7), (57.50, "impact", 0.85),
    (68.10, "whoosh", 0.7), (77.90, "boom_soft", 0.9),
    (88.80, "shimmer", 0.9), (98.50, "riser", 0.7), (102.90, "boom_soft", 0.9),
    (105.30, "shimmer", 0.65),
]


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:1200])
    return r


def concat():
    lst = WORK / "concat.txt"
    with open(lst, "w") as f:
        for n in SCENE_FILES:
            f.write(f"file '{PROC / f'{n}.mp4'}'\n")
    out = WORK / "video_concat.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(out)])
    d = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", str(out)]).stdout.strip())
    print(f"  video: {d:.2f}s")
    return out, d


def mix_audio(vdur):
    """VO segments at their starts + ducked bed + SFX events. Master = video length."""
    inputs = ["-i", str(A / "music" / "bed.wav")]
    parts = [
        f"[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
        f"atrim=0:{vdur:.3f},asetpts=PTS-STARTPTS,volume=0.30[mus]",
    ]
    labels = ["[mus]"]

    # VO segments, delayed to exact starts
    fi = 1
    for i, key in enumerate(ORDER):
        seg = next(s for s in vm["segments"] if s["name"] == key)
        start = tim["starts"][key]
        inputs += ["-i", seg["file"]]
        parts.append(
            f"[{fi}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            f"volume=1.9,adelay={int(start*1000)}|{int(start*1000)}[vo{i}]")
        labels.append(f"[vo{i}]")
        fi += 1

    # SFX events
    for i, (t_, name, vol) in enumerate(SFX_EVENTS):
        inputs += ["-i", str(A / "sfx" / f"{name}.mp3")]
        parts.append(
            f"[{fi}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            f"volume={vol},adelay={int(t_*1000)}|{int(t_*1000)}[s{i}]")
        labels.append(f"[s{i}]")
        fi += 1

    parts.append(
        f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0[amix]")
    parts.append(
        f"[amix]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
        f"atrim=0:{vdur:.3f},asetpts=PTS-STARTPTS,"
        f"acompressor=threshold=-20dB:ratio=2.5:attack=15:release=220:makeup=2,"
        f"alimiter=limit=0.95[out]")

    out = WORK / "mix.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
         "-filter_complex", ";".join(parts), "-map", "[out]",
         "-c:a", "pcm_s16le", str(out)])
    d = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", str(out)]).stdout.strip())
    print(f"  audio: {d:.2f}s")
    return out


def merge(vid, aud):
    raw = WORK / "raw_full.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid), "-i", str(aud),
         "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(raw)])
    print(f"  merged: {raw}")
    return raw


def loudnorm(src):
    r = run(["ffmpeg", "-y", "-i", str(src),
             "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^}]+\}", r.stderr)
    s = json.loads(m.group())
    norm = OUT
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-af", (f"loudnorm=I=-16:TP=-1.5:LRA=11:"
                 f"measured_I={s['input_i']}:measured_TP={s['input_tp']}:"
                 f"measured_LRA={s['input_lra']}:measured_thresh={s['input_thresh']}:"
                 f"offset={s.get('target_offset','-0.5')}:linear=true"),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(norm)])
    return norm


if __name__ == "__main__":
    print("=== Final build ===")
    v, d = concat()
    a = mix_audio(d)
    raw = merge(v, a)
    out = loudnorm(raw)
    p = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size:stream=codec_name,width,height,r_frame_rate",
             "-of", "json", str(out)])
    info = json.loads(p.stdout)
    dur = float(info["format"]["duration"])
    sz = int(info["format"]["size"]) / 1e6
    print(f"\n=== FINAL: {dur:.2f}s, {sz:.1f}MB, "
          f"{info['streams'][0].get('width')}x{info['streams'][0].get('height')} "
          f"@{info['streams'][0].get('r_frame_rate')} ===")
    print(f"Path: {out}")
