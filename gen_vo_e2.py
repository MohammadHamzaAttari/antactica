#!/usr/bin/env python3
"""Enceladus v4 script — hard hook, escalation, cliffhanger, 'going back'.
Word-boundary capture for caption highlighting."""
import asyncio, json, subprocess
from pathlib import Path
import edge_tts

BASE = Path(__file__).parent
VO = BASE / "audio" / "vo_e2"
VO.mkdir(parents=True, exist_ok=True)

SCENES = [
    ("s1", "This moon looks completely frozen. "
           "But beneath its surface hides an ocean so vast, "
           "scientists think it could hold the ingredients for life."),
    ("s2", "In 2005, NASA's Cassini spacecraft found the impossible. "
           "More than one hundred geysers, blasting ocean water into space. "
           "And Cassini did what no spacecraft had ever done. It flew through the spray."),
    ("s3", "The water carried salts. Organic molecules. Silica grains from hot vents on the seafloor. "
           "Then in 2023, the last piece. Phosphates. "
           "Every major element life requires is floating in that spray."),
    ("s4", "And the scale is absurd. "
           "The plume stretches nearly 10,000 kilometers into space. "
           "Enceladus loses 200 kilograms of ocean every second. "
           "Saturn's outermost ring is literally made of Enceladus's ocean water."),
    ("s5", "Beneath 10 kilometers of ice, "
           "a global ocean wraps the entire moon, "
           "with warm vents on the seafloor "
           "releasing the same energy that powers Earth's deep sea ecosystems. "
           "No sunlight required. "
           "And at the bottom of that dark water, "
           "hydrothermal vents pump out the exact chemistry "
           "that may have started life on our own planet."),
    ("s6", "So if life exists beyond Earth... "
           "Enceladus may be hiding it. Beneath the ice. Right now."),
    ("s7", "So here's my question. If you could drill through that ice, "
           "what do you think is hiding down there? "
           "Tell me in the comments."),
    ("s8", "Universe Impact."),
]

VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+8%"
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
    (BASE / "audio" / "vo_e2" / "manifest.json").write_text(json.dumps(out, indent=1))
    print(f"Total VO: {sum(s['duration'] for s in out):.1f}s")

asyncio.run(main())
