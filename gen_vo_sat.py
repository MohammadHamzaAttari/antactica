#!/usr/bin/env python3
"""Saturn rings reel — 8 segments, word-boundary capture."""
import asyncio, json, subprocess
from pathlib import Path
import edge_tts

BASE = Path(__file__).parent
VO = BASE / "audio" / "vo_sat"
VO.mkdir(parents=True, exist_ok=True)

SCENES = [
    ("s1", "The most beautiful thing in the solar system is dying. "
           "Saturn is eating its own rings. "
           "And NASA just measured how fast."),
    ("s2", "The rings aren't solid. "
           "They're billions of tonnes of ice, orbiting a planet more than a billion kilometers away. "
           "And in 2013, astronomers caught something impossible. "
           "Water, raining down from the rings onto Saturn."),
    ("s3", "Then Cassini flew between the rings and the planet, "
           "closer than any spacecraft in history, "
           "and measured the rain directly. "
           "Enough water to fill an Olympic swimming pool every thirty minutes."),
    ("s4", "But the real shock is the clock. "
           "The rings are losing mass so fast, they can't be old. "
           "The best estimate: they're only ten to a hundred million years old. "
           "Saturn itself is four and a half billion. "
           "The rings shouldn't exist yet. But they do."),
    ("s5", "The leading theory is wild. "
           "Saturn may have had one more moon. "
           "As it drifted too close, the planet tore it apart, "
           "shredding an entire world into billions of icy fragments. "
           "Hubble has watched asteroids shred themselves. "
           "Now we know Saturn did the same."),
    ("s6", "The rings are temporary. "
           "In about a hundred million years, a cosmic instant, they'll be gone. "
           "Out of four and a half billion years of history, "
           "you're alive during the brief window when Saturn wears its rings."),
    ("s7", "So here's my question. "
           "If you could travel a billion kilometers, just once, "
           "to see the rings with your own eyes. Would you go? "
           "Tell me in the comments."),
    ("s8", "Follow Universe Impact."),
]

VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+12%"
PITCH = "-3Hz"


def duration_of(p):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


async def gen_scene(name, text):
    mp3 = VO / f"{name}.mp3"
    words = []
    if not (mp3.exists() and duration_of(mp3) > 0.5 and (VO / f"{name}.words.json").exists()):
        com = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, boundary="WordBoundary")
        with open(mp3, "wb") as f:
            async for chunk in com.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    words.append({"t": chunk["offset"] / 1e7,
                                  "d": chunk["duration"] / 1e7,
                                  "w": chunk["text"]})
        (VO / f"{name}.words.json").write_text(json.dumps(words, indent=1))
    else:
        words = json.loads((VO / f"{name}.words.json").read_text())
    return {"name": name, "file": str(mp3), "duration": duration_of(mp3),
            "words": words, "text": text}


async def main():
    out = []
    for name, text in SCENES:
        s = await gen_scene(name, text)
        out.append(s)
        print(f"  {name}: {s['duration']:.2f}s, {len(s['words'])} words")
    (BASE / "audio" / "vo_sat" / "manifest.json").write_text(json.dumps(out, indent=1))
    print(f"Total VO: {sum(s['duration'] for s in out):.1f}s")

asyncio.run(main())
