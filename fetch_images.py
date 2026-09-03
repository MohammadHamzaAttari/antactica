#!/usr/bin/env python3
"""Download public-domain space imagery via Wikipedia API URL resolution + ESA CDN fallbacks."""
import subprocess, json, os, time
from pathlib import Path

IMG = Path(__file__).parent / "images"
IMG.mkdir(parents=True, exist_ok=True)
UA = "UniverseImpactBot/1.0 (educational video production)"

# name -> (list of Commons filenames, list of ESA CDN ids e.g. ('esahubble','heic1501a'))
IMAGES = {
    "disk_hltau":   (["HL Tau protoplanetary disk.jpg", "HL_Tau_protoplanetary_disk.jpg"], []),
    "disk_twhya":   (["The planet-forming disk around the young star TW Hydrae.jpg", "TW Hydrae disk.jpg"], [("esahubble", "opo1804a")]),
    "snr_crab":     (["Crab Nebula.jpg", "A Large Stone Eye in Space.jpg"], [("esahubble", "heic0515a")]),
    "snr_casa":     (["Cassiopeia A labeled.jpg", "CassiopeiaA.jpg"], []),
    "tarantula":    (["Tarantula Nebula.jpg"], [("esahubble", "heic1202a")]),
    "carina_mystic":([["Heic0707a.jpg"][0]], [("esahubble", "heic0707a")]),
    "pillars":      (["Pillars of creation 2014 HST WFC3-UVIS full-res denoised.jpg", "Pillars of creation.jpg"], [("esahubble", "heic1501a")]),
    "orion":        (["Orion Nebula.jpg", "Orion Nebula Hubble.jpg"], [("esahubble", "heic0601a")]),
    "hudf":         (["HUDF.jpg", "Hubble ultra deep field.jpg"], [("esahubble", "heic0406a")]),
    "earth_apollo17":(["The Earth seen from Apollo 17.jpg", "Blue Marble 2002.jpg"], []),
    "milkyway_vlt": (["ESO VLT Laser and the Milky Way.jpg", "Laser Towards Carina.jpg"], []),
    "hh_jets":      (["HH 24.jpg", "HH24.jpg"], [("esahubble", "heic1518a")]),
    "nebula_lmc":   (["Hubble image of star-forming region N159.jpg", "N63A Remnant.jpg"], [("esahubble", "opo2036a")]),
    "webb_carina":  (["Cosmic cliffs.jpg", "Cosmic Cliffs in the Carina Nebula (NIRCam).jpg"], [("esawebb", "weic2216a")]),
}

API = "https://en.wikipedia.org/w/api.php"

def api_resolve(fname, width=1800):
    """Resolve Commons filename -> direct thumb URL via Wikipedia API."""
    r = subprocess.run(
        ["curl", "-sL", "--fail", "--max-time", "20", "-A", UA,
         "-G", API,
         "--data-urlencode", "action=query",
         "--data-urlencode", f"titles=File:{fname}",
         "--data-urlencode", "prop=imageinfo",
         "--data-urlencode", "iiprop=url",
         "--data-urlencode", f"iiurlwidth={width}",
         "--data-urlencode", "format=json",
         "--data-urlencode", "redirects=1"],
        capture_output=True, text=True, timeout=25)
    try:
        d = json.loads(r.stdout)
        pages = d["query"]["pages"]
        for p in pages.values():
            ii = p.get("imageinfo", [])
            if ii:
                return ii[0].get("thumburl") or ii[0].get("url")
    except Exception:
        pass
    return None

def download(url, out):
    tmp = out.with_suffix(".tmp")
    r = subprocess.run(["curl", "-sL", "--fail", "--max-time", "120", "-A", UA, "-o", str(tmp), url],
                       capture_output=True)
    if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 30000:
        with open(tmp, "rb") as f:
            if f.read(2) == b"\xff\xd8":
                tmp.rename(out)
                return out.stat().st_size
    if tmp.exists():
        tmp.unlink()
    return 0

def esa_fetch(cdn, id_, out, variant="medium"):
    url = f"https://cdn.{cdn}.org/archives/images/{variant}/{id_}.jpg"
    return download(url, out)

ok, miss = [], []
for name, (files, esa) in IMAGES.items():
    out = IMG / f"{name}.jpg"
    if out.exists() and out.stat().st_size > 30000:
        print(f"SKIP {name}")
        ok.append(name)
        continue
    size = 0
    # ESA CDN first (reliable) — try medium (small), then large (bigger)
    for cdn, id_ in esa:
        for variant in ("medium", "large"):
            size = esa_fetch(cdn, id_, out, variant)
            if size:
                print(f"OK  {name} <- esa:{cdn}/{variant}/{id_} ({size/1024:.0f}KB)")
                break
        if size:
            break
    # Wikipedia API resolution
    if not size:
        for fname in files:
            url = api_resolve(fname)
            if url:
                size = download(url, out)
                if size:
                    print(f"OK  {name} <- wiki:{fname} ({size/1024:.0f}KB)")
                    break
            time.sleep(0.3)
    (ok if size else miss).append(name)
    if not size:
        print(f"MISS {name}")

print(f"\n{len(ok)} downloaded, {len(miss)} missing: {miss}")
