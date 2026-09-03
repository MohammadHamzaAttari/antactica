#!/usr/bin/env python3
"""Prepare page-identity assets:
 watermark.png  — square page logo, luminance-keyed alpha (for corner overlay)
 banner.png     — wide page wordmark, cleaned for the branding card"""
from PIL import Image, ImageFilter
import numpy as np
from pathlib import Path

OUT = Path(__file__).parent / "brand"
OUT.mkdir(exist_ok=True)

def luminance_key(src, dst, width, lo=14, hi=90, gain=2.4):
    """Dark-bg logo -> RGBA where bright elements survive, dark bg fades out."""
    im = Image.open(src).convert("RGB")
    a = np.asarray(im, dtype=np.float32)
    luma = a.mean(axis=2)
    alpha = np.clip((luma - lo) / (hi - lo), 0, 1) ** 0.85 * 255 * gain
    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    rgba = np.dstack([a.astype(np.uint8), alpha])
    img = Image.fromarray(rgba, "RGBA")
    img = img.resize((width, int(width * im.height / im.width)), Image.LANCZOS)
    # feather alpha slightly
    al = img.getchannel("A").filter(ImageFilter.GaussianBlur(1.2))
    img.putalpha(al)
    img.save(dst)
    print(dst, img.size)

luminance_key("/home/hamza/Pictures/709425665_1024432986593296_6113995259880750219_n.jpg",
              OUT / "watermark.png", 190)
luminance_key("/home/hamza/Pictures/711474726_1024432236593371_4137007094451626603_n.jpg",
              OUT / "banner.png", 880)
