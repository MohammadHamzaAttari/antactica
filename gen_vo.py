#!/usr/bin/env python3
"""Per-scene VO via edge-tts (Andrew — deep, natural American male).
Audio-anchored: writes vo_manifest.json with exact durations."""
import asyncio, json, subprocess, os
from pathlib import Path
import edge_tts

BASE = Path(__file__).parent
VO = BASE / "audio" / "vo_segments"
VO.mkdir(parents=True, exist_ok=True)

SEGMENTS = [
    ("01_hook",
     "Earth may not have been one of the first rocky worlds. "
     "New simulations suggest the ingredients for planets like Earth may have existed "
     "just one hundred million years after the Big Bang."),
    ("02_different",
     "Back then, the universe looked nothing like today's cosmos. "
     "No mature solar systems. Almost everything was made of the simplest elements. "
     "Hydrogen. And helium."),
    ("03_heavier",
     "But rocky planets need more. Carbon. Oxygen. Iron. "
     "Elements forged inside the universe's very first stars. "
     "Some of them enormous."),
    ("04_explosion",
     "When those stars died, they exploded as extraordinary supernovae, "
     "blasting newly forged elements into space. "
     "The universe now had the raw ingredients to build solid worlds."),
    ("05_simulation",
     "Researchers at the University of Portsmouth modeled what could happen next. "
     "Enriched gas collapsed around a young star, "
     "roughly seventy percent as massive as our Sun. "
     "And around it, a planet forming disk appeared."),
    ("06_earthshock",
     "Inside it, enough solid material accumulated to build several Earth masses "
     "of planetary blocks. "
     "At roughly the same distance from its star, as Earth is from the Sun."),
    ("07_water",
     "And there was another surprise. "
     "The disk also contained substantial water. "
     "An ingredient associated with habitability, appearing astonishingly early."),
    ("08_credibility",
     "But here's the key. "
     "Scientists have not discovered an ancient Earth. "
     "This is a simulation. Showing that the conditions for rocky worlds "
     "may have existed far earlier than we once thought."),
    ("09_possibility",
     "So the first rocky worlds may have begun assembling when the universe was still in its infancy. "
     "How early could the ingredients for life have appeared?"),
    ("10_ending",
     "We don't know yet. And that's what makes this so extraordinary. "
     "The universe may have been building worlds from the very beginning. "
     "Follow Universe Impact, for more discoveries from the cosmos."),
]

VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+15%"
PITCH = "-3Hz"


def duration_of(path):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


async def gen(name, text):
    out = VO / f"{name}.mp3"
    if out.exists() and duration_of(out) > 0.5:
        return duration_of(out)
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(str(out))
    return duration_of(out)


async def main():
    manifest = {"segments": [], "total": 0.0}
    for name, text in SEGMENTS:
        d = await gen(name, text)
        manifest["segments"].append({"name": name, "file": str(VO / f"{name}.mp3"), "duration": d})
        manifest["total"] += d
        print(f"  {name}: {d:.2f}s")
    Path(BASE / "audio" / "vo_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nTotal VO: {manifest['total']:.1f}s")


asyncio.run(main())
