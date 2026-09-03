#!/usr/bin/env python3
"""110s cosmic music bed (ffmpeg lavfi) + SFX set, keyed to scene cut times.
Arc: mysterious drone -> first-star shimmer -> supernova impact -> wonder build
     -> ducked credibility dip (77.6-78.6) -> question swell -> resolve & fade."""
import subprocess, json
from pathlib import Path

BASE = Path(__file__).parent
A = BASE / "assets"
(A / "music").mkdir(exist_ok=True, parents=True)
(A / "sfx").mkdir(exist_ok=True, parents=True)

tim = json.loads((BASE / "work" / "timings.json").read_text())
T = tim["total"]  # 109.52
DUR = str(int(T) + 2)

# ---------------- SFX (reusable set) ----------------
SFX = A / "sfx"
def sfx(name, args, af):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-af", af, str(SFX / name)],
                   capture_output=True)

# deep boom
sfx("boom.mp3", ["-f", "lavfi", "-i", "sine=frequency=48:duration=1.6"],
    "volume=0.9,afade=t=in:st=0:d=0.01,afade=t=out:st=0.15:d=1.45,lowpass=f=160")
# soft boom
sfx("boom_soft.mp3", ["-f", "lavfi", "-i", "sine=frequency=42:duration=1.8"],
    "volume=0.55,afade=t=in:st=0:d=0.02,afade=t=out:st=0.3:d=1.5,lowpass=f=120")
# riser (2.5s sweep)
sfx("riser.mp3", ["-f", "lavfi", "-i", "sine=frequency=180:duration=2.5"],
    "vibrato=f=6:d=0.6,volume=0.5,afade=t=in:st=0:d=1.8,afade=t=out:st=2.1:d=0.4")
# whoosh
sfx("whoosh.mp3", ["-f", "lavfi", "-i", "anoisesrc=d=1.4:c=pink:r=44100:a=0.35"],
    "highpass=f=250,lowpass=f=3800,afade=t=in:st=0:d=0.35,afade=t=out:st=0.9:d=0.5,tremolo=f=9:d=0.4,volume=0.8")
# impact
sfx("impact.mp3", ["-f", "lavfi", "-i", "sine=frequency=70:duration=1.4"],
    "volume=0.85,afade=t=in:st=0:d=0.01,afade=t=out:st=0.12:d=1.28,lowpass=f=220")
# swell (transition)
sfx("swell.mp3", ["-f", "lavfi", "-i", "anoisesrc=d=2.2:c=white:r=44100:a=0.22"],
    "bandpass=f=900:w=1.6,afade=t=in:st=0:d=1.3,afade=t=out:st=1.6:d=0.6,volume=0.7")
# shimmer hit (question mark moment)
sfx("shimmer.mp3", ["-f", "lavfi", "-i", "sine=frequency=1240:duration=1.2"],
    "tremolo=f=14:d=0.8,volume=0.30,afade=t=in:st=0:d=0.02,afade=t=out:st=0.15:d=1.0")
print("SFX done")

# ---------------- Music bed ----------------
# Timeline anchors (from timings.json):
#   0.0 hook (mystery)   10.2 cosmos   21.9 elements   32.2 supernova (32.25-33.25 has own sfx)
#   44.3 simulation      57.5 earth masses   68.1 water   78.0 credibility (DUCK 77.6-78.6)
#   88.8 question        98.5 timeline      102.9 earth CTA   end fade 107.4
# Voices: D1 drone (36.7Hz) + D2/A2/F3 pad + slow pulse + shimmer
cuts = tim["sfx_cuts"]

adelay_shimmer = ""

fc = f"""
[0:a]volume=0.42,lowpass=f=90[drone0];
[8:a]volume=0.20[drone_w];
[drone0][drone_w]amix=inputs=2:duration=first:normalize=0[drone];
[1:a]volume=0.14,tremolo=f=0.11:d=0.35[pad1];
[2:a]volume=0.13,tremolo=f=0.13:d=0.30[pad2];
[7:a]volume=0.11,tremolo=f=0.12:d=0.25[pad3];
[3:a]adelay=14000|14000,apad=whole_dur={DUR}[sh1];
[3:a]adelay=25000|25000,apad=whole_dur={DUR}[sh2];
[3:a]adelay=38000|38000,apad=whole_dur={DUR}[sh3];
[3:a]adelay=63000|63000,apad=whole_dur={DUR}[sh4];
[3:a]adelay=75000|75000,apad=whole_dur={DUR}[sh5];
[3:a]adelay=95000|95000,apad=whole_dur={DUR}[sh6];
[4:a]volume=0.5,tremolo=f=0.55:d=0.9,lowpass=f=240[pulse];
[5:a]volume=0.5,afade=t=in:st=0:d=2.2,afade=t=out:st=2.3:d=0.2[r1];
[5:a]adelay=30000|30000,apad=whole_dur={DUR},volume=0.5,afade=t=in:st=30:d=2.2,afade=t=out:st=32.3:d=0.2[r2];
[5:a]adelay=86000|86000,apad=whole_dur={DUR},volume=0.5,afade=t=in:st=86:d=2.2,afade=t=out:st=88.3:d=0.2[r3];
[6:a]adelay=56000|56000,apad=whole_dur={DUR},volume=0.5,afade=t=in:st=56:d=1.5,afade=t=out:st=57.2:d=0.3[r4];
[drone][pad1][pad2][pad3][sh1][sh2][sh3][sh4][sh5][sh6][pulse][r1][r2][r3][r4]
amix=inputs=15:duration=longest:normalize=0[mix];
[mix]volume=eval=frame:volume='0.42*lt(t\,77.6)+0.10*between(t\,77.6\,78.6)+0.42*gte(t\,78.6)',
lowpass=f=2400,
afade=t=in:st=0:d=2.5,
volume=eval=frame:volume='0.55+0.45*between(t\,88.8\,98.5)',
afade=t=out:st={T - 2.2:.2f}:d=2.0[out]
"""

cmd = ["ffmpeg", "-y", "-loglevel", "error",
       "-f", "lavfi", "-t", DUR, "-i", f"sine=frequency=36.7:duration={DUR}",       # 0 D1 drone
       "-f", "lavfi", "-t", DUR, "-i", f"sine=frequency=73.4:duration={DUR}",       # 1 D2
       "-f", "lavfi", "-t", DUR, "-i", f"sine=frequency=110.0:duration={DUR}",      # 2 A2
       "-f", "lavfi", "-t", DUR, "-i", "sine=frequency=1240:duration=0.9",          # 3 shimmer burst
       "-f", "lavfi", "-t", DUR, "-i", f"sine=frequency=49:duration={DUR}",         # 4 pulse G1
       "-f", "lavfi", "-t", DUR, "-i", "sine=frequency=200:duration=2.5",           # 5 riser raw
       "-f", "lavfi", "-t", DUR, "-i", "sine=frequency=240:duration=1.5",           # 6 riser short
       "-f", "lavfi", "-t", DUR, "-i", f"sine=frequency=174.6:duration={DUR}",      # 7 F3
       "-f", "lavfi", "-t", DUR, "-i", f"sine=frequency=37.05:duration={DUR}",      # 8 slow beat vs drone
       "-filter_complex", fc, "-map", "[out]", "-ar", "44100", "-ac", "2",
       "-c:a", "pcm_s16le", str(A / "music" / "bed.wav")]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode == 0:
    print(f"bed.wav ok ({(A/'music'/'bed.wav').stat().st_size/1e6:.1f}MB)")
else:
    print("BED ERR:", r.stderr[-600:])
