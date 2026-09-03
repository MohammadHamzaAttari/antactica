#!/usr/bin/env python3
"""Enceladus reel — 6 procedural animation clips (video only, no stills).
Rendered 540x960 -> upscaled 1080x1920. Each clip matches its narration scene duration.
Palette: icy teal/blue, warm vents. Consistent with kinetic-caption build."""
import subprocess
import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path

BASE = Path(__file__).parent
PROC = BASE / "proc"
PROC.mkdir(exist_ok=True)

W, H, FPS = 540, 960, 30
CX, CY = W // 2, int(H * 0.42)


def fbm(shape, octaves=6, base_freq=3.0, persistence=0.55, seed=1):
    r = np.random.default_rng(seed)
    h, w = shape
    out = np.zeros((h, w), dtype=np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        freq = base_freq * (2 ** o)
        gw, gh = max(2, int(freq)), max(2, int(freq * h / w))
        g = r.random((gh, gw)).astype(np.float32)
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * (np.asarray(img, dtype=np.float32) / 255.0)
        total += amp
        amp *= persistence
    return out / total


def encode(frames, name, n):
    out = PROC / name
    p = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-vf", "scale=1080:1920:flags=lanczos,unsharp=5:5:0.3",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    for i, fr in enumerate(frames):
        p.stdin.write(fr)
        if i % 90 == 0:
            print(f"    {name}: {i}/{n}")
    p.stdin.close()
    p.wait()
    print(f"    OK {out.stat().st_size//1024}KB")


def make_glow():
    def box_blur3(a, r=4):
        """Separable box blur x3 (≈ gaussian), float-exact, no clipping."""
        for _ in range(3):
            c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0)), mode="edge"), axis=0)
            a = (c[2 * r + 1:] - c[:-(2 * r + 1)]) / (2 * r + 1)
            c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r)), mode="edge"), axis=1)
            a = (c[:, 2 * r + 1:] - c[:, :-(2 * r + 1)]) / (2 * r + 1)
        return a

    def glow(cv, xs, ys, bs, colr, blur=1.6):
        xi = np.clip(np.asarray(xs, int), 0, W - 1)
        yi = np.clip(np.asarray(ys, int), 0, H - 1)
        b = np.asarray(bs, np.float32)
        ca = np.asarray(colr, np.float32)
        if ca.ndim == 1:
            layer = np.zeros((H, W), dtype=np.float32)
            np.add.at(layer, (yi, xi), b)
            layer = box_blur3(layer, int(max(1, blur)))
            cv += layer[..., None] * ca / 255.0
        else:
            cl = np.zeros((H, W, 3), dtype=np.float32)
            for c in range(3):
                ch = np.zeros((H, W), dtype=np.float32)
                np.add.at(ch, (yi, xi), b * ca[:, c] / 255.0)
                cl[..., c] = box_blur3(ch, int(max(1, blur)))
            cv += cl
        return cv
    return glow


def starbase(seed, n_st=110):
    rng = np.random.default_rng(seed)
    sx, sy = rng.integers(0, W, n_st), rng.integers(0, H, n_st)
    sb = (rng.random(n_st) ** 2 * 150 + 12).astype(np.float32)
    return sx, sy, sb


# ============================================================ 1. JETS (hook)
def e1(T=16.2):
    glow = make_glow()
    sx, sy, sb = starbase(71)
    rng = np.random.default_rng(711)
    n_p = 480
    jx = np.array([0.16, 0.32, 0.5, 0.68, 0.84]) * W       # 5 vent columns
    pick = rng.choice(5, n_p)
    ang = (np.pi / 2) + (rng.random(n_p) - 0.5) * 0.34
    spd = 90 + rng.random(n_p) * 130
    birth = rng.random(n_p) * (T - 4.0)
    col = np.zeros((n_p, 3))
    col[:, 0] = 195 + rng.random(n_p) * 60
    col[:, 1] = 228 + rng.random(n_p) * 27
    col[:, 2] = 255
    R = 360
    mcx, mcy = CX, int(H * 0.78)
    tex = fbm((H, W), octaves=6, base_freq=5.0, seed=7)
    fyy, fxx = np.mgrid[0:H, 0:W]
    rr = np.sqrt((fxx - mcx) ** 2 + (fyy - mcy) ** 2)
    disk = rr <= R
    shade = np.clip(1.05 - 0.5 * ((fxx - mcx) / R * 0.8 + (fyy - mcy) / R * 0.5), 0.35, 1.1)

    def frames():
        for i in range(int(T * FPS)):
            t = i / FPS
            cv = np.zeros((H, W, 3), dtype=np.float32)
            cv += 6
            cv = glow(cv, sx, sy, sb, [225, 235, 255], blur=0.8)
            # moon disk
            cv += (disk * (120 * shade * (0.8 + 0.2 * tex)))[..., None] * \
                  np.array([0.93, 0.96, 1.0], np.float32)
            limb = np.exp(-((rr - R) ** 2) / (2 * 10 ** 2))
            cv += (limb * 110)[..., None] * np.array([0.9, 0.95, 1.0], np.float32)
            # south pole warm hint
            sp = np.exp(-(((fxx - mcx) ** 2) / (2 * 90 ** 2) + ((fyy - (mcy + R)) ** 2) / (2 * 30 ** 2)))
            cv += (sp * 55)[..., None] * np.array([1.0, 0.75, 0.5], np.float32)
            # slow zoom: scale factor
            zm = 1.0 + 0.10 * t / T
            # jets
            alive = t >= birth
            if alive.any():
                dt = (t - birth)[alive]
                px = jx[pick[alive]] - mcx
                base_y = mcy + R * np.sqrt(np.clip(1 - (px / R) ** 2, 0, 1)) * 0.0  # top of moon
                bx = mcx + px * 0.96
                by = mcy + np.sqrt(np.clip(R ** 2 - px ** 2, 0, None)) * 0.35
                vx = np.cos(ang[alive]) * spd[alive] * 0.35
                vy = -np.sin(ang[alive]) * spd[alive]
                x = bx + vx * dt
                y = by + vy * dt + 26 * dt ** 2
                fade = np.clip(1.0 - dt / 4.6, 0, 1) ** 1.25
                br = fade * 500
                # 3-point streak along velocity for visible motion
                for k, wgt in ((0.0, 1.0), (0.5, 0.55), (1.0, 0.28)):
                    sx_ = x - vx * 0.022 * k
                    sy_ = y - vy * 0.022 * k
                    cv = glow(cv, sx_, sy_, br * wgt, col[alive], blur=1.4)
            yield np.clip(cv, 0, 255).astype(np.uint8).tobytes()

    encode(frames(), "anim_e1_jets.mp4", int(T * FPS))


# ============================================================ 2. CASSINI DIVE
def e2(T=16.2):
    glow = make_glow()
    sx, sy, sb = starbase(72, 150)
    rng = np.random.default_rng(722)
    n_st2 = 220
    a2 = rng.random(n_st2) * 2 * np.pi
    r02 = 40 + rng.random(n_st2) * 420
    sp2 = 25 + rng.random(n_st2) * 55
    fyy, fxx = np.mgrid[0:H, 0:W]
    mx, my = int(W * 0.70), int(H * 0.34)      # distant moon w/ rings
    Rm = 95

    def frames():
        for i in range(int(T * FPS)):
            t = i / FPS
            cv = np.zeros((H, W, 3), dtype=np.float32)
            cv += 5
            cv = glow(cv, sx, sy, sb, [225, 235, 255], blur=0.8)
            # streaking stars (approach)
            rr2 = (r02 + sp2 * t) % 520
            a2f = np.clip(1 - rr2 / 520, 0, 1) * 0.5
            x2 = CX + np.cos(a2) * rr2 * 1.1
            y2 = CY + np.sin(a2) * rr2 * (H / W) * 0.9
            cv = glow(cv, x2, y2, a2f * 30, [200, 215, 255], blur=0.6)
            # distant ringed moon (upper right), slow zoom
            zm = 1.0 + 0.06 * t / T
            Rmz = Rm * zm
            mrx, mry = fxx - mx, fyy - my
            rr = np.sqrt(mrx ** 2 + mry ** 2)
            # --- ring with proper occlusion: ellipse, far half behind disk ---
            a_ax, b_ax = Rmz * 1.72, Rmz * 0.58      # semi-axes
            ell = np.sqrt(((mrx / a_ax) ** 2 + (mry / b_ax) ** 2))
            ring_band = np.exp(-((ell - 1.12) ** 2) / (2 * 0.035 ** 2)) * 95
            ring_band2 = np.exp(-((ell - 1.38) ** 2) / (2 * 0.03 ** 2)) * 55
            far = mry < 0                             # upper half -> behind planet
            ring_far = (ring_band + ring_band2) * far
            ring_near = (ring_band + ring_band2) * (~far)
            cv += ring_far[..., None] * np.array([0.95, 0.9, 0.8], np.float32)
            # planet disk drawn AFTER far ring -> occludes it
            disk = rr <= Rmz
            shade = np.clip(1.08 - 0.55 * ((mrx / Rmz) * 0.7 - (mry / Rmz) * 0.5), 0.3, 1.15)
            cv += (disk * (105 * shade))[..., None] * np.array([0.93, 0.96, 1.0], np.float32)
            limb = np.exp(-((rr - Rmz) ** 2) / (2 * 6 ** 2))
            cv += (limb * 70 * disk)[..., None] * np.array([0.9, 0.95, 1.0], np.float32)
            # near ring half passes IN FRONT
            cv += ring_near[..., None] * np.array([0.95, 0.9, 0.8], np.float32)
            # spacecraft silhouette crossing (left->toward moon)
            scx = W * (0.08 + 0.72 * (t / T) ** 1.1)
            scy = H * 0.62 - 60 * (t / T)
            body = np.exp(-(((fxx - scx) ** 2) / (2 * 14 ** 2) + ((fyy - scy) ** 2) / (2 * 7 ** 2)))
            dish = np.exp(-(((fxx - scx - 16) ** 2) / (2 * 8 ** 2) + ((fyy - scy) ** 2) / (2 * 8 ** 2)))
            panel = np.exp(-(((fxx - scx + 22) ** 2) / (2 * 18 ** 2) + ((fyy - scy) ** 2) / (2 * 3.5 ** 2)))
            cv += (body * 190 + dish * 210 + panel * 150)[..., None] * \
                  np.array([0.85, 0.9, 1.0], np.float32)
            # radar pings: expand from beyond the dish so no halo hugs the body
            pr = 45 + (t * 55) % 170
            ping = np.exp(-((np.sqrt(((fxx - scx - 16) / 1.0) ** 2 + (fyy - scy) ** 2) - pr) ** 2) / (2 * 4 ** 2))
            cv += (ping * 45 * max(0, 1 - (pr - 45) / 170))[..., None] * \
                  np.array([0.5, 0.9, 1.0], np.float32)
            yield np.clip(cv, 0, 255).astype(np.uint8).tobytes()

    encode(frames(), "anim_e2_dive.mp4", int(T * FPS))


# ============================================================ 3. CHEMISTRY
def e3(T=17.8):
    glow = make_glow()
    rng = np.random.default_rng(733)
    n_m = 46
    mx0 = rng.random(n_m) * W
    spd = 28 + rng.random(n_m) * 52
    phase = rng.random(n_m) * 2 * np.pi
    kinds = rng.choice(3, n_m, p=[0.45, 0.3, 0.25])   # water, CO2, salt-cluster
    fyy, fxx = np.mgrid[0:H, 0:W]
    # vertical light shafts (vent glow from below)
    shafts = np.exp(-((fxx - W / 2) ** 2) / (2 * (W * 0.42) ** 2)) * \
             np.clip((fyy - H * 0.25) / (H * 0.75), 0, 1)

    def frames():
        for i in range(int(T * FPS)):
            t = i / FPS
            cv = np.zeros((H, W, 3), dtype=np.float32)
            # brighter underwater ambience: vertical gradient 14 -> 46 (teal depth)
            grad = np.clip(1.0 - fyy / H, 0, 1) ** 0.8
            cv += (44 + 70 * grad)[..., None] * np.array([0.25, 0.55, 0.85], np.float32)
            cv += (shafts * 62 * (0.8 + 0.2 * np.sin(t * 0.7)))[..., None] * \
                  np.array([0.45, 0.75, 1.0], np.float32)
            # faint particulate haze (marine snow) so the panel never reads as empty black
            ms = 12 + 10 * np.sin(t * 1.7 + fxx * 0.05 + fyy * 0.04)
            cv += (ms * 1.0)[..., None] * np.array([0.5, 0.7, 0.95], np.float32)
            ys = H + 60 - ((t * spd + phase * 120) % (H + 140))
            xs = mx0 + 14 * np.sin(t * 0.9 + phase * 6)
            # batched glow: 3 kinds, each one call
            for k, col in ((0, np.array([120, 200, 255])), (1, np.array([255, 150, 130])),
                           (2, np.array([255, 220, 150]))):
                sel = kinds == k
                if not sel.any():
                    continue
                x = xs[sel]; y = ys[sel]
                if k == 0:      # water: bent 3-point
                    gx = np.concatenate([x, x - 9, x + 9])
                    gy = np.concatenate([y, y - 11, y - 11])
                    gb = np.concatenate([np.full(len(x), 46.0), np.full(len(x), 30.0), np.full(len(x), 30.0)])
                elif k == 1:    # CO2: linear
                    gx = np.concatenate([x, x, x])
                    gy = np.concatenate([y - 10, y, y + 10])
                    gb = np.concatenate([np.full(len(x), 30.0), np.full(len(x), 46.0), np.full(len(x), 30.0)])
                else:           # salt cluster
                    gx = np.concatenate([x, x + 8, x - 8, x])
                    gy = np.concatenate([y, y + 6, y + 6, y - 9])
                    gb = np.concatenate([np.full(len(x), 40.0), np.full(len(x), 26.0),
                                         np.full(len(x), 26.0), np.full(len(x), 26.0)])
                cv = glow(cv, gx, gy, gb * 8.0, np.repeat(col[None, :], len(gx), axis=0), blur=3.0)
                # multi-point shapes read as molecules; no heavy connectors
            # phosphate flash moment (periodic)
            if 11.5 < t < 14.5:
                fa = np.exp(-((t - 13.0) ** 2) / (2 * 0.8 ** 2))
                fx, fy = W * 0.5, H * 0.38
                ring = np.exp(-((np.sqrt((fxx - fx) ** 2 + (fyy - fy) ** 2) - (t - 11.5) * 60) ** 2) / (2 * 6 ** 2))
                cv += (ring * 120 * fa)[..., None] * np.array([1.0, 0.85, 0.5], np.float32)
            yield np.clip(cv, 0, 255).astype(np.uint8).tobytes()

    encode(frames(), "anim_e3_chem.mp4", int(T * FPS))


# ============================================================ 4. E-RING SCALE
def e4(T=17.1):
    glow = make_glow()
    rng = np.random.default_rng(744)
    n_p = 1100
    ang = np.pi / 2 + (rng.random(n_p) - 0.5) * 0.7
    spd = 120 + rng.random(n_p) * 190
    birth = rng.random(n_p) * (T - 4.6)
    col = np.zeros((n_p, 3))
    col[:, 0] = 200 + rng.random(n_p) * 55
    col[:, 1] = 228 + rng.random(n_p) * 27
    col[:, 2] = 255
    fyy, fxx = np.mgrid[0:H, 0:W]
    mcx, mcy, R = int(W * 0.30), int(H * 0.80), 300
    rr = np.sqrt((fxx - mcx) ** 2 + (fyy - mcy) ** 2)
    disk = rr <= R
    shade = np.clip(1.05 - 0.5 * ((fxx - mcx) / R * 0.7 - (fyy - mcy) / R * 0.55), 0.35, 1.1)
    tex = fbm((H, W), octaves=5, base_freq=6.0, seed=44)
    # E-ring band: passes THROUGH the moon center so it reads as its ring,
    # not a floating diagonal stripe
    el = 0.38 * (fxx - mcx) + (fyy - mcy)
    band = np.exp(-(el ** 2) / (2 * 55 ** 2))

    def frames():
        for i in range(int(T * FPS)):
            t = i / FPS
            cv = np.zeros((H, W, 3), dtype=np.float32)
            cv += 5
            cv[..., 2] += 7
            cv += (band * (16 + 40 * min(1, t / 5)))[..., None] * \
                  np.array([0.75, 0.85, 1.0], np.float32)
            cv += (disk * (115 * shade * (0.82 + 0.18 * tex)))[..., None] * \
                  np.array([0.93, 0.96, 1.0], np.float32)
            limb = np.exp(-((rr - R) ** 2) / (2 * 9 ** 2))
            cv += (limb * 105)[..., None] * np.array([0.9, 0.95, 1.0], np.float32)
            alive = t >= birth
            if alive.any():
                dt = (t - birth)[alive]
                px = mcx + (fxx * 0 + 1) * 0  # from south pole region
                a = ang[alive]
                bx = mcx + np.cos(a) * 18
                by = mcy + R * 0.82
                vx = np.cos(a) * spd[alive] * 0.75
                vy = -np.sin(a) * spd[alive] * 1.15
                x = bx + vx * dt
                y = by + vy * dt + 22 * dt ** 2
                fade = np.clip(1.0 - dt / 5.2, 0, 1) ** 1.2
                cv = glow(cv, x, y, fade * 340, col[alive], blur=1.4)
            # slow pan up
            yield np.clip(cv, 0, 255).astype(np.uint8).tobytes()

    encode(frames(), "anim_e4_ring.mp4", int(T * FPS))


# ============================================================ 5. OCEAN CUTAWAY
def e5(T=12.5):
    glow = make_glow()
    rng = np.random.default_rng(755)
    n_b = 60
    bx = rng.random(n_b) * W
    bspd = 20 + rng.random(n_b) * 40
    bph = rng.random(n_b) * 2 * np.pi
    fyy, fxx = np.mgrid[0:H, 0:W]
    ice_bot = int(H * 0.30)
    oc_bot = int(H * 0.74)
    tex = fbm((H, W), octaves=6, base_freq=7.0, seed=55)
    # soft masks: 20px feathered transitions instead of hard boolean seams
    def soft_band(y0, y1, feather=18):
        up = np.clip((fyy - (y0 - feather)) / feather, 0, 1)
        dn = np.clip(((y1 + feather) - fyy) / feather, 0, 1)
        return np.clip(np.minimum(up, dn), 0, 1) ** 1.2
    m_ice = soft_band(0, ice_bot)
    m_ocean = soft_band(ice_bot, oc_bot)
    m_rock = soft_band(oc_bot, H)
    # feathered seafloor height so the floor isn't a flat black cutoff
    floor_h = oc_bot + 26 * np.sin(fxx * 0.018 + tex[0] * 3) + 14 * np.sin(fxx * 0.05 + 2)

    def frames():
        for i in range(int(T * FPS)):
            t = i / FPS
            cv = np.zeros((H, W, 3), dtype=np.float32)
            # ice crust (pale, textured, cracks)
            ice = (m_ice * (150 + 60 * tex) * (0.85 + 0.15 * np.sin(t * 0.5)))
            cv += ice[..., None] * np.array([0.88, 0.94, 1.0], np.float32)
            cracks = ((np.sin(fxx * 0.09 + tex * 9) > 0.96) * m_ice)
            cv += (cracks * 60)[..., None] * np.array([0.5, 0.7, 1.0], np.float32)
            # ocean (glowing teal, gradient + caustic shimmer)
            og = np.clip((oc_bot - fyy) / (oc_bot - ice_bot), 0, 1)
            shimmer = 0.9 + 0.1 * np.sin(t * 1.2 + tex * 5)
            cv += (m_ocean * (62 + 42 * og) * shimmer)[..., None] * \
                  np.array([0.25, 0.75, 1.0], np.float32)
            # bubbles — batched into ONE glow call (60 separate calls were too slow)
            by_ = oc_bot - ((t * bspd + bph * 100) % (oc_bot - ice_bot))
            bxs = bx + 6 * np.sin(t * 1.4 + bph * 8)
            alive_b = (by_ > ice_bot) & (by_ < oc_bot)
            if alive_b.any():
                cv = glow(cv, bxs[alive_b], by_[alive_b],
                          np.full(int(alive_b.sum()), 55.0),
                          np.tile(np.array([180, 230, 255]), (int(alive_b.sum()), 1)), blur=1.0)
            # seafloor: textured rock with warm vent fields, never pure black
            rock_tex = 88 + 40 * tex
            floor_fade = np.clip(1.0 - (fyy - floor_h) / 60.0, 0, 1)
            m_floor = (fyy >= floor_h) * floor_fade + (fyy >= floor_h + 60) * 1.0
            m_floor = np.clip(m_floor, 0, 1)
            cv += (m_floor * rock_tex)[..., None] * np.array([0.62, 0.47, 0.40], np.float32)
            # warm vents on the floor
            for vx_ in (W * 0.3, W * 0.72):
                vx_off = 12 * np.sin(fxx * 0.02)  # floor follows x -> vents sit on it
                vent = np.exp(-(((fxx - vx_) ** 2) / (2 * 26 ** 2) +
                                ((fyy - (oc_bot + 6)) ** 2) / (2 * 22 ** 2)))
                cv += (vent * (85 + 30 * np.sin(t * 2.3 + vx_)))[..., None] * \
                      np.array([1.0, 0.6, 0.3], np.float32)
                # rising warm stream
                stream = np.exp(-((fxx - vx_) ** 2) / (2 * 9 ** 2)) * \
                         np.exp(-((fyy - (oc_bot - 40 - (t * 45 + vx_) % 200)) ** 2) / (2 * 10 ** 2))
                cv += (stream * 65)[..., None] * np.array([1.0, 0.55, 0.35], np.float32)
            yield np.clip(cv, 0, 255).astype(np.uint8).tobytes()

    encode(frames(), "anim_e5_ocean.mp4", int(T * FPS))


# ============================================================ 6. CTA DEPARTURE
def e6(T=13.7):
    glow = make_glow()
    sx, sy, sb = starbase(76, 170)
    rng = np.random.default_rng(766)
    n_s = 240
    a2 = rng.random(n_s) * 2 * np.pi
    r02 = 30 + rng.random(n_s) * 380
    sp2 = 45 + rng.random(n_s) * 130
    fyy, fxx = np.mgrid[0:H, 0:W]

    def frames():
        for i in range(int(T * FPS)):
            t = i / FPS
            cv = np.zeros((H, W, 3), dtype=np.float32)
            cv += 5
            cv = glow(cv, sx, sy, sb, [225, 235, 255], blur=0.8)
            # receding streaks (leaving)
            rr2 = (r02 + sp2 * t * (0.6 + 0.4 * t / T)) % 500
            af = np.clip(1 - rr2 / 500, 0, 1) * 0.45
            x2 = CX + np.cos(a2) * rr2 * 1.05
            y2 = CY + np.sin(a2) * rr2 * (H / W) * 0.92
            cv = glow(cv, x2, y2, af * 85, [200, 215, 255], blur=0.7)
            # distant warm destination star (Saturn system ahead)
            stx, sty = W * 0.5, H * 0.30
            d2 = (fxx - stx) ** 2 + (fyy - sty) ** 2
            pulse = 0.9 + 0.1 * np.sin(t * 2.0)
            cv += (np.exp(-d2 / (2 * 90 ** 2)) * 30 * pulse)[..., None] * \
                  np.array([1.0, 0.85, 0.6], np.float32)
            cv += (np.exp(-d2 / (2 * 14 ** 2)) * 210)[..., None] * \
                  np.array([1.0, 0.92, 0.75], np.float32)
            # departing probe: tiny bright dot with a fading motion trail
            # (replaces the old grey oval blob that read as a leftover element)
            p = min(1.0, t / (T * 0.85))
            scx = W * 0.5 + (stx - W * 0.5) * p
            scy = H * 0.72 + (sty - H * 0.72) * p
            trail_len = 60
            for k in range(6):
                fk = k / 5.0
                tx = scx + (scx - (W * 0.5 + (stx - W * 0.5) * max(0.0, p - 0.06))) * fk * 2.2
                ty = scy + (scy - (H * 0.72 + (sty - H * 0.72) * max(0.0, p - 0.06))) * fk * 2.2
                b = 550 * (1.0 - fk) ** 1.6
                cv = glow(cv, [tx], [ty], [b], [235, 240, 255], blur=1.2)
            cv = glow(cv, [scx], [scy], [900], [255, 250, 240], blur=1.0)
            # end fade
            if t > T - 1.2:
                cv *= max(0.0, (T - t) / 1.2)
            yield np.clip(cv, 0, 255).astype(np.uint8).tobytes()

    encode(frames(), "anim_e6_cta.mp4", int(T * FPS))


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["1", "2", "3", "4", "5", "6"]
    fn = {"1": e1, "2": e2, "3": e3, "4": e4, "5": e5, "6": e6}
    for k in which:
        print(f"  [anim_e{k}]")
        fn[k]()
    print("All enceladus anims done.")
