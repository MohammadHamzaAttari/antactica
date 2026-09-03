# ANTARCTICA FROZE FIRST — production reel (1080×1920 @ 30fps)

A mind-blowing, production-ready vertical science reel:
**"Antarctica froze 25 million years before the Arctic — and science finally knows why."**

**Final deliverable:** `antarctica_froze_first_9x16.mp4` (1:45, 43.5 MB, H.264 High 3.1 Mbps + AAC 190 kbps, loudness −14 LUFS / −1.5 dBTP)

---

## What this pipeline builds

| Layer | Details |
|---|---|
| Cold open | Procedural frost-crystal animation + kinetic "ANTARCTICA FROZE FIRST" title (PIL + numpy, frame-by-frame) |
| Scene 1 | Real NASA/USGS LIMA Antarctica mosaic + real NASA SVS / IceBridge imagery, Ken Burns moves |
| Scene 2 | Procedural "warm Earth" globe animation (34 MYA, +5 °C) + Drake Passage stills |
| Scene 3 | Procedural polar-gateways animation (South America & Australia breaking away, ACC ring forms) |
| Scene 4 | Procedural ACC flow animation (rotating current rings blocking warm water) + **real sea-ice-leads animation** |
| Scene 5 | Procedural LIMA freeze animation (warm→ice grade, CO₂ counter 900→400 ppm) + **real NASA ice-sheet animation** |
| Scene 6 | Procedural Antarctica-vs-Arctic comparison + animated 34→2.6 MYA timeline + **real Arctic sea-ice animation** |
| Scene 7 | Question card (starfield + dimmed LIMA globe + "COMMENT YOUR THEORY" CTA) |
| Scene 8 | Follow card (UNIVERSE IMPACT brand lockup) |
| Captions | Word-synced karaoke captions: white base + cyan word sweep (Inter Bold, drawtext) |
| HUD | Data chips ("FROZE 25M YEARS BEFORE THE ARCTIC", "34 MYA: EARTH +5°C WARMER"…) + per-shot source credits |
| Branding | Procedurally designed orbit-ring "UNIVERSE IMPACT" watermark + end-card banner |
| Transitions | Dip-to-black at every scene boundary (per-scene fade in/out) |
| Audio | Choral-pad music bed (D/F/A drone + pad + air + pulse + riser), whoosh/boom/crack SFX, sidechain ducking under VO, 2-pass loudnorm |

## Files

| File | Purpose |
|---|---|
| `gen_anims_ant.py` | Renders the 6 procedural animations (numpy + PIL → ffmpeg) |
| `prep_assets_ant.py` | Organizes real imagery, converts real GIF clips → MP4, builds VO manifest + brand lockups |
| `build_ant.py` | Master build: stills (zoompan Ken Burns), captions/overlays, assembly, music+SFX mix, loudnorm, watermark, mux |
| `audio/vo_ant/` | 8 AI-narrated scene clips (mp3) + `manifest.json` (word timings) |
| `images_ant/` `scenes_ant/` `work/` | Real assets, rendered scenes, intermediates |
| `brand/` | Generated watermark + banner lockups |
| `work/qa_*.jpg` | QA frames (one per scene) |

## Rebuild (on your machine)

Requirements: `python3`, `pip install pillow numpy`, **ffmpeg with libfreetype/drawtext** (ffmpeg ≥ 4.3, e.g. johnvansickle static build; the scripts auto-detect `ffmpeg` on PATH).

```bash
python3 gen_anims_ant.py      # procedural animations
python3 prep_assets_ant.py    # assets, clips, VO manifest, brand
python3 build_ant.py          # scenes → assembly → audio → master
```

To use a different voiceover, drop scene MP3s into `audio/vo_ant/s1.mp3 … s8.mp3` and
regenerate `manifest.json` (script text is the source of truth for word-timing estimates).

## Credits
NASA/USGS LIMA, NASA SVS, NASA Operation IceBridge, NASA/NSIDC (Arctic sea ice),
ESA/Hubble, EOS imagery via public sources; schematics are procedurally animated.
