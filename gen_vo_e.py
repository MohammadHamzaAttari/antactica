#!/usr/bin/env python3
"""Enceladus reel — per-scene VO via edge-tts WITH word boundaries (kinetic captions).
Outputs vo_segments/*.mp3 + words.json (exact word timings per scene)."""
import asyncio, json, subprocess
from pathlib import Path
import edge_tts

BASE = Path(__file__).parent
VO = BASE / "audio" / "vo_e"
VO.mkdir(parents=True, exist_ok=True)

SCENES = [
    ("s1", "This tiny moon is spraying its entire ocean into space. "
           "Enceladus is barely 500 kilometers across. It should be a frozen ball of ice. "
           "Instead, over one hundred geysers are blasting ocean water into space. "
           "And a spacecraft has already flown through it."),
    ("s2", "In 2005, NASA's Cassini spacecraft arrived at Saturn, "
           "and found something impossible. Jets of water vapor erupting from the south pole of Enceladus. "
           "A moon too small to keep an ocean liquid. "
           "So Cassini did what no spacecraft had ever done. It dove through the spray."),
    ("s3", "The plume is not just water. "
           "Cassini found salts. Organic molecules. Silica grains from hot seafloor vents. "
           "The same chemistry as Earth's deepest ocean vents. "
           "And in 2023, the last piece. Phosphates. "
           "Every major element life requires is floating in that water."),
    ("s4", "And the scale is absurd. "
           "This spray reaches nearly 10,000 kilometers into space. "
           "Forty times the width of the moon itself. "
           "Enceladus loses 200 kilograms of ocean every second. "
           "Saturn's outermost ring is literally made of Enceladus's ocean water."),
    ("s5", "Beneath the ice, a global ocean at least 10 kilometers deep wraps the entire moon. "
           "Warm rock on the seafloor may be venting the same energy "
           "that powers Earth's deep sea ecosystems. No sunlight required."),
    ("s6", "We have tasted an alien ocean. "
           "And everything life needs is floating in the spray. "
           "The next spacecraft to fly through it could answer "
           "the biggest question humanity has ever asked. "
           "Follow Universe Impact, and be there when it happens."),
]

VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+20%"
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
    (BASE / "audio" / "vo_e" / "manifest.json").write_text(json.dumps(out, indent=1))
    print(f"Total VO: {sum(s['duration'] for s in out):.1f}s")

asyncio.run(main())
