#!/usr/bin/env python3
"""Download ORIGINAL NASA Cassini/Hubble imagery for the Saturn rings reel."""
import subprocess, os, time
from pathlib import Path

IMG = Path(__file__).parent / "images_sat"
IMG.mkdir(exist_ok=True)

BEATS = {
    "global":  ["PIA17110", "PIA14934", "PIA12513", "PIA05389", "PIA17172"],  # iconic globals
    "rings":   ["PIA12794", "PIA14629", "PIA11657", "PIA06175", "PIA11613"],  # ring close-ups
    "rain":    ["PIA16842", "PIA11674"],                                      # ring rain concept/plot
    "finale":  ["PIA21439", "PIA22767", "PIA21886", "PIA21897"],              # grand finale dives
    "shatter": ["GSFC_20171208_Archive_e001167", "GSFC_20171208_Archive_e001165"],  # Hubble asteroid breakup
}

def try_url(url, out, min_size=20000):
    r = subprocess.run(["curl", "-sL", "--fail", "--max-time", "180", "-A", "Mozilla/5.0",
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
    for suffix in ("~orig.jpg", "~large.jpg", "~full.jpg", "~medium.jpg"):
        if try_url(f"https://images-assets.nasa.gov/image/{pia}/{pia}{suffix}", out):
            return True
    if try_url(f"https://photojournal.jpl.nasa.gov/jpeg/{pia}.jpg", out):
        return True
    return False

from PIL import Image
for beat, pias in BEATS.items():
    for pia in pias:
        out = IMG / f"{pia}.jpg"
        if out.exists():
            print(f"SKIP {beat}/{pia}")
            continue
        if fetch(pia, out):
            try:
                im = Image.open(out)
                print(f"OK  {beat}/{pia} {im.size} ({out.stat().st_size//1024}KB)")
            except Exception as e:
                print(f"BAD {beat}/{pia}: {e}")
                out.unlink()
        else:
            print(f"MISS {beat}/{pia}")
        time.sleep(1.0)
