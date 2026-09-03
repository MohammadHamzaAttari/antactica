#!/usr/bin/env python3
"""Download ORIGINAL NASA Cassini imagery of Enceladus at highest resolution.
Every image is the real moon / its real plume / its real ring (PIA archive)."""
import subprocess, json, os, time
from pathlib import Path

IMG = Path(__file__).parent / "images_real"
IMG.mkdir(exist_ok=True)

# Real Enceladus shots, grouped by narration beat
BEATS = {
    "jets":   ["PIA14642", "PIA06443", "PIA17198", "PIA17202"],   # actual geysers/plume
    "moon":   ["PIA08258", "PIA06205", "PIA08354", "PIA17205", "PIA17211"],  # globe/flyby/departing
    "stripes":["PIA10352", "PIA11686", "PIA11688", "PIA13620"],   # south-pole fractures
    "ering":  ["PIA12512", "PIA17172", "PIA08921", "PIA08133"],   # E ring / Saturn wide
    "ocean":  ["PIA18071", "PIA14937"],                            # interior ocean graphic, map
}

def try_url(url, out, min_size=15000):
    r = subprocess.run(["curl", "-sL", "--fail", "--max-time", "120", "-A", "Mozilla/5.0",
                        "-o", str(out) + ".t", url], capture_output=True)
    if r.returncode == 0 and os.path.exists(str(out) + ".t") and os.path.getsize(str(out) + ".t") > min_size:
        with open(str(out) + ".t", "rb") as f:
            if f.read(2) == b"\xff\xd8":
                os.replace(str(out) + ".t", out)
                return True
    if os.path.exists(str(out) + ".t"):
        os.remove(str(out) + ".t")
    return False

def fetch(pia, out):
    # images-assets (orig = full res) then photojournal
    for suffix in ("~orig.jpg", "~large.jpg", "~full.jpg", "~medium.jpg"):
        if try_url(f"https://images-assets.nasa.gov/image/{pia}/{pia}{suffix}", out):
            return True
    if try_url(f"https://photojournal.jpl.nasa.gov/jpeg/{pia}.jpg", out):
        return True
    return False

report = {}
for beat, pias in BEATS.items():
    report[beat] = []
    for pia in pias:
        out = IMG / f"{pia}.jpg"
        if out.exists():
            report[beat].append(str(out))
            continue
        if fetch(pia, out):
            report[beat].append(str(out))
            print(f"OK  {beat}/{pia} ({out.stat().st_size//1024}KB)")
        else:
            print(f"MISS {beat}/{pia}")
        time.sleep(1.2)

# report resolutions
from PIL import Image
print("\nRESOLUTIONS:")
for beat, files in report.items():
    for f in files:
        try:
            im = Image.open(f)
            print(f"  {Path(f).stem}: {im.size}")
        except Exception as e:
            print(f"  {Path(f).stem}: BAD {e}")
(IMG.parent / "work" / "real_images.json").write_text(json.dumps(report, indent=1))
