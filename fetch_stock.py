#!/usr/bin/env python3
"""Multi-platform stock clip fetcher for the Enceladus fast-cut reel.

Platforms: Pexels (API, HD portrait) + Mixkit (scrape, 360p).
Per narration beat: search every platform, score results by exact keyword
match against the beat's query terms, rank, download top candidates.
Outputs: clips_e/<beat>_<platform>_<id>.mp4 + fetch_report.json
"""
import subprocess, json, os, re, time
from pathlib import Path

BASE = Path(__file__).parent
CL = BASE / "clips_e"
CL.mkdir(exist_ok=True)

def pexels_key():
    for envf in ["/home/hamza/Videos/dkist_reel/.env", "/home/hamza/Videos/mirzaEngineer/.env", BASE / ".env"]:
        try:
            for line in Path(envf).read_text().splitlines():
                if line.startswith("PEXELS_API_KEY="):
                    return line.split("=", 1)[1].strip()
        except Exception:
            pass
    return ""

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# ---------------------------------------------------------------- beats
# Each beat: key, search terms per platform, exact-match keywords (scored),
# need_seconds, orientation preference.
BEATS = [
    dict(key="b1_ocean_spray",
         terms_pexels=["geyser erupting", "water spray splash", "ocean waves crashing"],
         terms_mixkit=["geyser", "water-splash", "ocean-wave"],
         must=["geyser", "spray", "splash", "erupt", "water", "wave", "ocean", "mist", "fountain"],
         need=8.0),
    dict(key="b2_space_arrival",
         terms_pexels=["saturn", "planet saturn", "saturn rings"],
         terms_mixkit=["planet", "space"],
         must=["saturn", "planet", "space", "galaxy", "star", "cosmos", "universe", "nebula", "ring"],
         need=8.0),
    dict(key="b3_chemistry",
         terms_pexels=["underwater bubbles", "particles water", "underwater light rays"],
         terms_mixkit=["underwater", "bubble", "particles"],
         must=["underwater", "bubble", "particle", "light", "ray", "dive", "sea", "ocean", "water"],
         need=8.0),
    dict(key="b4_epic_scale",
         terms_pexels=["iceberg underwater", "iceberg ocean", "glacier ice water"],
         terms_mixkit=["iceberg", "ice", "glacier"],
         must=["iceberg", "ice", "glacier", "frozen", "underwater", "arctic", "sea", "water"],
         need=8.0),
    dict(key="b5_hidden_ocean",
         terms_pexels=["ice cave blue", "underwater ice", "frozen cave"],
         terms_mixkit=["ice-cave", "underwater-ice", "cave"],
         must=["ice", "cave", "underwater", "blue", "frozen", "glacier", "tunnel"],
         need=8.0),
    dict(key="b6_journey_cta",
         terms_pexels=["rocket launch space", "space stars travel", "earth from space"],
         terms_mixkit=["rocket", "space-travel", "earth"],
         must=["rocket", "launch", "space", "star", "earth", "travel", "galaxy", "shuttle"],
         need=8.0),
]

STOP = set("the a an of in on at to for with and or from free stock video videos hd 4k".split())


def score_text(text, must_words):
    t = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    words = set(w for w in t.split() if w not in STOP)
    s = 0.0
    for m in must_words:
        if m in words:
            s += 2.0
        elif any(m in w for w in words):
            s += 1.0
    return s


# ---------------------------------------------------------------- Pexels
def pexels_search(query, per_page=12):
    key = pexels_key()
    r = subprocess.run(["curl", "-s", "--max-time", "25", "-H", f"Authorization: {key}",
                        "-G", "https://api.pexels.com/videos/search",
                        "--data-urlencode", f"query={query}",
                        "--data-urlencode", f"per_page={per_page}",
                        "--data-urlencode", "min_duration=3",
                        "--data-urlencode", "max_duration=45"],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout).get("videos", [])
    except Exception:
        return []


def pexels_pick(v):
    """Choose best portrait-ish file: prefer height>=1080."""
    files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4"]
    files = [f for f in files if f.get("height") and f.get("width")]
    if not files:
        return None
    files.sort(key=lambda f: -(f["height"] if f["height"] <= f["width"] * 1.6 else 0) * 10000 + f["height"])
    return files[0]["link"], files[0]["width"], files[0]["height"]


# ---------------------------------------------------------------- Mixkit
def mixkit_search(tag, per_page=20):
    r = subprocess.run(["curl", "-sL", "--max-time", "25", "-A", UA,
                        f"https://mixkit.co/free-stock-video/{tag}/"],
                       capture_output=True, text=True)
    html = r.stdout
    slugs = re.findall(r'href="(/free-stock-video/[a-z0-9-]+-\d+/)"', html)
    vids = re.findall(r"https://assets\.mixkit\.co/videos/(\d+)/\d+-360\.mp4", html)
    slug_by_id = {}
    for s in slugs:
        m = re.match(r"/free-stock-video/(.+)-(\d+)/", s)
        if m:
            slug_by_id[m.group(2)] = m.group(1).replace("-", " ")
    out, seen = [], set()
    for vid in vids:
        if vid in seen:
            continue
        seen.add(vid)
        title = slug_by_id.get(vid, tag.replace("-", " "))
        out.append({"id": vid, "title": title})
    return out[:per_page]


# ---------------------------------------------------------------- download
def dl(url, out, min_size=300_000):
    for _ in range(2):
        r = subprocess.run(["curl", "-sL", "--fail", "--max-time", "240", "-A", UA,
                            "-o", str(out) + ".t", url], capture_output=True)
        if r.returncode == 0 and os.path.exists(str(out) + ".t") and os.path.getsize(str(out) + ".t") > min_size:
            os.replace(str(out) + ".t", out)
            return True
        if os.path.exists(str(out) + ".t"):
            os.remove(str(out) + ".t")
        time.sleep(1.5)
    return False


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        return float(d["format"]["duration"]), d["streams"][0]["width"], d["streams"][0]["height"]
    except Exception:
        return 0, 0, 0


def main():
    report = []
    for beat in BEATS:
        print(f"== {beat['key']}")
        cands = []
        # Pexels
        for q in beat["terms_pexels"]:
            q_score = score_text(q, beat["must"])
            for v in pexels_search(q):
                text = v.get("url", "") + " " + " ".join(v.get("tags", []) or [])
                # Pexels gives no text metadata -> candidate inherits its query score
                s = max(score_text(text, beat["must"]), q_score)
                pick = pexels_pick(v)
                if pick:
                    cands.append(dict(platform="pexels", id=v["id"], title=v.get("url", "").split("/")[-2] if "/" in v.get("url", "") else "",
                                      dur=v.get("duration", 0), score=s, url=pick[0],
                                      w=pick[1], h=pick[2]))
            time.sleep(0.4)
        # Mixkit
        for tag in beat["terms_mixkit"]:
            for m in mixkit_search(tag):
                s = score_text(m["title"], beat["must"])
                cands.append(dict(platform="mixkit", id=m["id"], title=m["title"][:60],
                                  dur=0, score=s,
                                  url=f"https://assets.mixkit.co/videos/{m['id']}/{m['id']}-360.mp4",
                                  w=640, h=360))
            time.sleep(0.4)
        # rank: score desc, then resolution desc (Pexels priority on ties)
        cands.sort(key=lambda c: (-c["score"], -c.get("h", 0)))
        # download top 2; try to keep platform diversity when scores are close
        chosen = []
        for c in cands:
            if len(chosen) >= 2:
                break
            if not chosen:
                chosen.append(c)
                continue
            if c["platform"] != chosen[0]["platform"] and chosen[0]["score"] - c["score"] <= 2.0:
                chosen.append(c)   # swap-in diverse platform on near-tie
            elif len(chosen) == 1 and c["platform"] == chosen[0]["platform"]:
                chosen.append(c)
        got = []
        for rank, c in enumerate(chosen):
            out = CL / f"{beat['key']}_{c['platform']}_{c['id']}.mp4"
            if not out.exists():
                if not dl(c["url"], out):
                    print(f"   dl FAIL {c['platform']} {c['id']}")
                    continue
            d, w, h = probe(out)
            if d < 1.5:
                print(f"   too short {out.name}")
                out.unlink(missing_ok=True)
                continue
            got.append(dict(**c, file=str(out), real_dur=d, real_w=w, real_h=h))
            print(f"   [{c['platform']} s={c['score']:.0f}] {out.name} {d:.1f}s {w}x{h}")
        report.append(dict(beat=beat["key"], candidates=len(cands), picks=got))
    (BASE / "work" / "fetch_report.json").write_text(json.dumps(report, indent=1))
    print("\nReport: work/fetch_report.json")
    for b in report:
        line = ", ".join(f"{p['platform']}#{p['id']}(s{p['score']:.0f})" for p in b["picks"]) or "NONE"
        print(f"  {b['beat']}: {line}")


if __name__ == "__main__":
    main()
