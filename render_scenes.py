#!/usr/bin/env python3
"""Scene renderer v3 — audio-anchored, mixes procedural animations + stills.
Animations land exactly on their narration windows (hook, supernova, timeline, earth)."""
import subprocess, json, shutil
from pathlib import Path

BASE = Path(__file__).parent
IMG = BASE / "images"
PROC = BASE / "scenes"
WORK = BASE / "work"
PROC.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)

W, H = 1080, 1920
FPS = 30

FONT_SRC = BASE / "assets" / "fonts" / "Inter-Bold.ttf"
FONT = Path("/tmp/opencode/Inter-Bold.ttf")
FONT.parent.mkdir(exist_ok=True)
shutil.copy(FONT_SRC, FONT)

# ---------------------------------------------------------------- timings
vm = json.loads((BASE / "audio" / "vo_manifest.json").read_text())
segs = {s["name"]: s["duration"] for s in vm["segments"]}

GAP = 0.75
LEAD = 0.25
ORDER = ["01_hook", "02_different", "03_heavier", "04_explosion", "05_simulation",
         "06_earthshock", "07_water", "08_credibility", "09_possibility", "10_ending"]

starts, t = [], 0.0
for i, key in enumerate(ORDER):
    starts.append(round(t + LEAD, 2) if i else 0.0)
    t = t + (LEAD if i else 0.0) + segs[key] + GAP
TOTAL = round(t - GAP + 0.9, 2)

c01, c02, c03, c04, c05, c06, c07, c08, c09, c10 = starts
S02 = round(c02 - 0.25, 2); S03 = round(c03 - 0.25, 2); S04 = round(c04 - 0.25, 2)
S05 = round(c05 - 0.25, 2); S06 = round(c06 - 0.25, 2); S07 = round(c07 - 0.25, 2)
S08 = round(c08 - 0.25, 2); S09 = round(c09 - 0.25, 2); S10 = round(c10 - 0.25, 2)
S03_MID = round(S03 + 5.0, 2)          # pillars -> tarantula inside VO-03
S12 = round(S10 + 2.2, 2)
S13 = round(S12 + 2.2, 2)

scene_defs = [
    ("s01", 0.0, S02, 0.0, 0.0),        # anim_hook (has own title)
    ("s02", S02, S03, 0.0, 0.0),        # HUDF (VO02)
    ("s03", S03, S03_MID, 0.0, 0.0),    # pillars (VO03 elements)
    ("s04", S03_MID, S04, 0.0, 0.0),    # tarantula (VO03 first stars)
    ("s05", S04, S05, 0.0, 0.0),        # anim_supernova (VO04 full)
    ("s06", S05, S06_MID if False else round(S05 + 4.25, 2), 0.0, 0.0),  # dust (VO05 first)
    ("s07", round(S05 + 4.25, 2), S06, 0.0, 0.0),  # HL Tau (VO05 disk)
    ("s08", S06, S07, 0.0, 0.0),        # disk dive (VO06)
    ("s09", S07, S08, 0.0, 0.0),        # water (VO07)
    ("s10", S08, S09, 0.0, 0.0),        # credibility (VO08)
    ("s11", S09, S10, 0.0, 0.0),        # simulation not discovery (VO09)
    ("s12", S10, S12, 0.0, 0.0),        # timeline part 1
    ("s13", S12, S13, 0.0, 0.0),        # timeline part 2 (question)
    ("s16", S13, TOTAL, 0.0, 0.7),      # anim_earth pull-back (CTA)
]
D = {n: (a, b, fi, fo) for n, a, b, fi, fo in scene_defs}

# ---------------------------------------------------------------- content
SCENES = {
    "s01": dict(
        src=[("video", BASE / "proc" / "anim_hook.mp4", 0.0)],
        cap="EARTH MAY NOT HAVE BEEN\nONE OF THE FIRST\nROCKY WORLDS", side="right"),
    "s02": dict(
        src=[("img", IMG / "hudf.jpg", (0.42, 0.30, 0.42))], move="zoom_in",
        cap="A VERY DIFFERENT\nCOSMOS", side="left",
        labels=[("HYDROGEN", 2.2, 5.2, 0.30), ("HELIUM", 3.6, 6.6, 0.38),
                ("NO MATURE SOLAR SYSTEMS", 7.4, 11.3, 0.34)]),
    "s03": dict(
        src=[("img", IMG / "pillars.jpg", (0.30, 0.20, 0.55))], move="zoom_in_fast",
        cap="ROCKY PLANETS\nNEED MORE", side="right",
        labels=[("CARBON", 0.6, 1.9, 0.30), ("OXYGEN", 1.3, 2.6, 0.38), ("IRON", 2.0, 3.3, 0.46),
                ("FORGED IN THE FIRST STARS", 3.4, 4.9, 0.38)]),
    "s04": dict(
        src=[("img", IMG / "tarantula.jpg", (0.45, 0.30, 0.50))], move="zoom_in_fast",
        cap="THE VERY FIRST STARS\nSOME OF THEM ENORMOUS", side="left"),
    "s05": dict(
        src=[("video", BASE / "proc" / "anim_supernova.mp4", 0.0)],
        cap="EXTRAORDINARY\nSUPERNOVAE", side="right",
        labels=[("HEAVY ELEMENTS SCATTERED", 6.3, 11.4, 0.30)]),
    "s06": dict(
        src=[("img", IMG / "proc_dust.jpg")], move="zoom_in",
        cap="", side="center",
        labels=[("UNIVERSITY OF PORTSMOUTH", 0.6, 3.9, 0.30),
                ("A NEW SIMULATION", 1.4, 3.9, 0.35)]),
    "s07": dict(
        src=[("img", IMG / "disk_hltau.jpg", (0.50, 0.50, 0.92))], move="zoom_in_fast",
        cap="A PLANET-FORMING\nDISK APPEARED", side="left",
        labels=[("ALMA IMAGE: DISK AROUND HL TAURI", 4.5, 8.7, 0.88, "small")]),
    "s08": dict(
        src=[("img", IMG / "disk_hltau.jpg", (0.50, 0.50, 0.60)),
             ("img", IMG / "disk_hltau.jpg", (0.50, 0.50, 1.60))], move="pan_right",
        cap="", side="center",
        labels=[("SEVERAL EARTH MASSES OF MATERIAL", 2.0, 6.0, 0.30),
                ("AT THE EARTH-SUN DISTANCE", 6.5, 10.3, 0.36)]),
    "s09": dict(
        src=[("img", IMG / "webb_carina.jpg", (0.35, 0.35, 0.50))], move="zoom_in",
        cap="AND ANOTHER SURPRISE:\nWATER", side="left",
        labels=[("AN INGREDIENT OF HABITABILITY", 4.5, 9.4, 0.32)]),
    "s10": dict(
        src=[("img", IMG / "proc_credibility.jpg")], move="zoom_in",
        cap="SCIENTISTS HAVE NOT\nDISCOVERED AN ANCIENT\nEARTH", side="center"),
    "s11": dict(
        src=[("img", IMG / "orion.jpg", (0.5, 0.35, 0.45))], move="zoom_in_fast",
        cap="A SIMULATION\nNOT A DISCOVERY", side="left",
        labels=[("CONDITIONS FOR ROCKY WORLDS", 4.0, 9.3, 0.34)]),
    "s12": dict(
        src=[("video", BASE / "proc" / "anim_timeline.mp4", 0.0)],
        cap="THE FIRST ROCKY WORLDS\nMAY HAVE ASSEMBLED\nIN COSMIC INFANCY", side="left"),
    "s13": dict(
        src=[("video", BASE / "proc" / "anim_timeline.mp4", 5.5)],
        cap="HOW EARLY COULD THE\nINGREDIENTS FOR LIFE\nHAVE APPEARED?", side="right"),
    "s16": dict(
        src=[("video", BASE / "proc" / "anim_earth.mp4", 2.6)],
        cap="THE UNIVERSE MAY HAVE BEEN\nBUILDING WORLDS\nFROM THE VERY BEGINNING", side="center",
        cap_end=1.9,
        labels=[("FOLLOW UNIVERSE IMPACT", 2.0, 6.3, 0.60, "cta"),
                ("FOR MORE COSMIC DISCOVERIES", 2.5, 6.3, 0.665, "sub"),
                ("SOURCE: UNIVERSITY OF PORTSMOUTH", 0.8, 6.3, 0.735, "small"),
                ("THE ASTROPHYSICAL JOURNAL LETTERS", 0.8, 6.3, 0.760, "small")]),
}

CRED_FILL = "white"
CRED_SLATE = "0x9DB4D6"
LABEL_C = "0xFFA860"


def esc(t):
    return t.replace(":", r"\:").replace("%", r"\%").replace(",", r"\,")


def move_filter(move, n):
    if move == "zoom_in":
        z = f"1.0+0.30*on/{n}"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "zoom_in_fast":
        z = f"1.0+0.55*on/{n}"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "zoom_out":
        z = f"1.30-0.30*on/{n}"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "pan_left":
        z = "1.22"
        x, y = f"(iw-ow/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"
    elif move == "pan_right":
        z = "1.22"
        x, y = f"(iw-ow/zoom)*(on/{n})", "ih/2-(ih/zoom/2)"
    elif move == "drift":
        z = f"1.15+0.06*sin(2*PI*on/{n})"
        x = f"iw/2-(iw/zoom/2)+28*sin(2*PI*on/{n})"
        y = f"ih/2-(ih/zoom/2)+20*cos(2*PI*on/{n})"
    else:
        z, x, y = "1.0", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    return z, x, y


def text_filters(cfg, dur):
    from PIL import ImageFont, ImageDraw, Image
    parts = []
    meas = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

    if cfg["cap"]:
        lines = cfg["cap"].split("\n")
        n_l = len(lines)
        block_h = n_l * 78
        base_y = 1216 - block_h // 2 + 20
        cap_end = cfg.get("cap_end", dur - 0.25)
        lx = "56" if cfg["side"] == "left" else ("1024-text_w" if cfg["side"] == "right" else "(w-text_w)/2")
        # auto-fit caption fontsize: longest line must fit with 72px margins
        cap_fs = 58
        while cap_fs > 40:
            fnt = ImageFont.truetype(str(FONT_SRC), cap_fs)
            if max(meas.textlength(l, font=fnt) for l in lines) <= W - 144:
                break
            cap_fs -= 2
        for i, line in enumerate(lines):
            fc = CRED_SLATE if (cfg.get("slate_last") and i == n_l - 1) else CRED_FILL
            parts.append(
                f"drawtext=fontfile={FONT}:text='{esc(line)}':fontsize={cap_fs}:fontcolor={fc}:"
                f"borderw=4:bordercolor=black@0.92:shadowx=3:shadowy=3:shadowcolor=black@0.85:"
                f"x={lx}:y={base_y + i * 78}:"
                f"enable='between(t\\,0.3\\,{cap_end:.2f})'")
        ax = "42" if cfg["side"] == "left" else ("1030" if cfg["side"] == "right" else "(w-8)/2")
        parts.append(
            f"drawbox=x={ax}:y={base_y}:w=8:h={block_h}:color=0xFF6B35@0.9:t=fill:"
            f"enable='between(t\\,0.3\\,{cap_end:.2f})'")
    for lab in cfg.get("labels", []):
        txt, t1, t2 = lab[0], lab[1], lab[2]
        fy = lab[3]
        kind = lab[4] if len(lab) > 4 else ""
        fs = {"small": 30, "cta": 52, "sub": 34}.get(kind, 40)
        col = {"cta": "0xFF8A3D", "sub": "0xE8DCC8"}.get(kind, "0xAFC0DC" if kind == "small" else LABEL_C)
        # auto-fit: shrink font until text + margins fit the frame
        while fs > 18:
            fnt = ImageFont.truetype(str(FONT_SRC), fs)
            if meas.textlength(txt, font=fnt) <= W - 160:
                break
            fs -= 2
        t2 = min(t2, dur - 0.2)
        parts.append(
            f"drawtext=fontfile={FONT}:text='{esc(txt)}':fontsize={fs}:fontcolor={col}:"
            f"borderw=3:bordercolor=black@0.9:"
            f"x=(w-text_w)/2:y={int(fy * H)}:"
            f"enable='between(t\\,{t1}\\,{t2:.2f})'")
    return parts


def render(name):
    a, b, fi, fo = D[name]
    dur = round(b - a, 2)
    cfg = SCENES[name]
    out = PROC / f"{name}.mp4"

    is_video = cfg["src"][0][0] == "video"
    move = cfg.get("move", "static")
    n = int(dur * FPS)

    base_fx = []
    if is_video:
        base_fx.append(f"fps={FPS}")
        # clone-extend if source shorter than window
        vid_path = cfg["src"][0][1]
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(vid_path)], capture_output=True, text=True)
        vdur = float(r.stdout.strip())
        need = dur + 0.1
        if need > vdur:
            base_fx.append(f"tpad=stop_mode=clone:stop_duration={need - vdur + 0.05:.2f}")
    else:
        base_fx += ["scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840"]
        z, x, y = move_filter(move, n)
        base_fx.append(f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s=1080x1920:fps={FPS}")
    base_fx += ["eq=saturation=1.12:contrast=1.06:brightness=0.01", "vignette=PI/4.2"]
    if fi > 0:
        base_fx.append(f"fade=t=in:st=0:d={fi}")
    if fo > 0:
        base_fx.append(f"fade=t=out:st={dur - fo:.2f}:d={fo}")
    base_fx += text_filters(cfg, dur)
    vf = ",".join(base_fx)

    srcs = cfg["src"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for s in srcs:
        if s[0] == "img":
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur + 0.5), "-i", str(s[1])]
        else:
            if len(s) > 2 and s[2] > 0:
                cmd += ["-ss", str(s[2])]
            cmd += ["-stream_loop", "-1", "-i", str(s[1])]

    print(f"  [render] {name} {dur:.2f}s ({move}{'+video' if is_video else ''})")
    if len(srcs) == 1:
        cmd += ["-vf", vf]
    else:
        chains = []
        for i, s in enumerate(srcs):
            cx, cy, cz = s[2]
            cw, ch = int(1080 / cz), int(1920 / cz)
            px = int(min(max(0, 1080 * cx - cw / 2), max(0, 1080 - cw)))
            py = int(min(max(0, 1920 * cy - ch / 2), max(0, 1920 - ch)))
            pre = (f"scale=1080:1920:force_original_aspect_ratio=increase,"
                   f"crop=1080:1920,zoompan=z='{cz}':x='{px}':y='{py}'"
                   f":d=1:s=1080x1920:fps={FPS}")
            chains.append(f"[{i}:v]{pre},format=yuv420p[c{i}]")
        cur = "c0"
        xoff = round(dur / len(srcs) - 0.8, 2)
        for i in range(1, len(srcs)):
            nxt = f"x{i}"
            chains.append(f"[{cur}][c{i}]xfade=transition=fade:duration=0.8:offset={xoff}[{nxt}]")
            cur = nxt
        chains.append(f"[{cur}]{vf}[vout]")
        cmd += ["-filter_complex", ";".join(chains), "-map", "[vout]"]

    cmd += ["-t", str(dur), "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-pix_fmt", "yuv420p", "-an", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [ERR] {name}: {r.stderr[-400:]}")
    else:
        print(f"    ok {out.stat().st_size/1024:.0f}KB")


if __name__ == "__main__":
    for f in PROC.glob("s*.mp4"):
        f.unlink()
    print(f"TOTAL={TOTAL:.2f}s | cuts: " + " ".join(f"{n}:{a:.1f}" for n, a, _, _, _ in scene_defs))
    timings = {
        "total": TOTAL,
        "scenes": [{"name": n, "start": a, "end": b} for n, a, b, _, _ in scene_defs],
        "starts": dict(zip(ORDER, starts)),
        "cred_start": c08, "cred_end": c08 + segs["08_credibility"],
        "sfx_cuts": [S02, S03, S04, S05, S06, S07, S08, S09, S10],
    }
    (WORK / "timings.json").write_text(json.dumps(timings, indent=2))
    for n, *_ in scene_defs:
        render(n)
    print("Done.")
