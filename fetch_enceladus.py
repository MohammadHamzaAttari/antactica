#!/usr/bin/env python3
"""Fetch verified NASA Cassini/JWST Enceladus imagery (public domain). Two sources, retry, delay."""
import subprocess, json, os, time
from pathlib import Path

IMG = Path(__file__).parent / "images_e"
IMG.mkdir(exist_ok=True)

WANTED = {
    "hook_jets":     ["PIA14642", "PIA06443"],             # Sunset on the Jets / plume crescent
    "discovery":     ["PIA17198", "PIA08235"],             # Changing view of plume / Candle in the Dark
    "plume_close":   ["PIA06443", "PIA17205"],             # plume / departing
    "tigerstripes":  ["PIA10352", "PIA11688", "PIA13620"], # south polar fractures / geyser basin
    "jwst_plume":    ["PIA28908", "PIA05076"],             # JWST-ish / bright crescent fallback
    "ering":         ["PIA08133", "PIA17202", "PIA08258"], # wide ring / moon shots
    "ocean_diagram": ["PIA18071", "PIA17202"],             # interior ocean graphic
    "saturn_wide":   ["PIA08258", "PIA11558"],             # Living Moon / rings
}

def try_url(url, out, min_size=12000):
    for attempt in range(2):
        r = subprocess.run(["curl", "-sL", "--fail", "--max-time", "90", "-A", "Mozilla/5.0",
                            "-o", str(out) + ".t", url], capture_output=True)
        if r.returncode == 0 and os.path.exists(str(out) + ".t") and os.path.getsize(str(out) + ".t") > min_size:
            with open(str(out) + ".t", "rb") as f:
                if f.read(2) == b"\xff\xd8":
                    os.replace(str(out) + ".t", out)
                    return True
        if os.path.exists(str(out) + ".t"):
            os.remove(str(out) + ".t")
        time.sleep(2)
    return False

def fetch(nid, out):
    # source 1: photojournal direct
    if try_url(f"https://photojournal.jpl.nasa.gov/jpeg/{nid}.jpg", out):
        return True
    # source 2: images-assets variants
    for suffix in ("~orig.jpg", "~large.jpg", "~medium.jpg", "~small.jpg"):
        if try_url(f"https://images-assets.nasa.gov/image/{nid}/{nid}{suffix}", out):
            return True
    return False

ok, miss = [], []
for key, ids in WANTED.items():
    out = IMG / f"{key}.jpg"
    if out.exists():
        print(f"SKIP {key}")
        ok.append(key); continue
    got = False
    for nid in ids:
        if fetch(nid, out):
            print(f"OK  {key} <- {nid} ({out.stat().st_size//1024}KB)")
            got = True
            break
        time.sleep(1.5)
    (ok if got else miss).append(key)
    if not got:
        print(f"MISS {key}")

for p in IMG.glob("*.jpg"):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p),
                    "-vf", "scale='min(1800,iw)':-2", "-q:v", "4", str(p) + ".s"])
    os.replace(str(p) + ".s", str(p))
print(f"\n{len(ok)} ok, missing: {miss}")
