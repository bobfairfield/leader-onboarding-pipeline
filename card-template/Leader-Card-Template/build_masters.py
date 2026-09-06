"""
Build clean master card templates (no leader-specific text, no leader photo)
from the original ChatGPT artwork, for both color schemes.

This is a ONE-TIME build step. Run it once to produce the master PNGs;
generate_leader_card.py then uses those masters for every leader.
"""
import numpy as np
from PIL import Image
import colorsys

# ---------- helpers ----------

def rgb_to_hsl_np(rgb):
    r, g, b = rgb[..., 0] / 255.0, rgb[..., 1] / 255.0, rgb[..., 2] / 255.0
    maxc = np.max(rgb / 255.0, axis=-1)
    minc = np.min(rgb / 255.0, axis=-1)
    l = (maxc + minc) / 2
    delta = maxc - minc
    s = np.zeros_like(l)
    mask = delta > 1e-6
    s[mask] = np.where(l[mask] < 0.5, delta[mask] / (maxc[mask] + minc[mask] + 1e-8),
                        delta[mask] / (2.0 - maxc[mask] - minc[mask] + 1e-8))
    h = np.zeros_like(l)
    rc = np.zeros_like(l); gc = np.zeros_like(l); bc = np.zeros_like(l)
    rc[mask] = (maxc[mask] - r[mask]) / (delta[mask] + 1e-8)
    gc[mask] = (maxc[mask] - g[mask]) / (delta[mask] + 1e-8)
    bc[mask] = (maxc[mask] - b[mask]) / (delta[mask] + 1e-8)
    h = np.where((maxc == r) & mask, (bc - gc), h)
    h = np.where((maxc == g) & mask, (2.0 + rc - bc), h)
    h = np.where((maxc == b) & mask, (4.0 + gc - rc), h)
    h = (h / 6.0) % 1.0
    return h * 360, s * 100, l * 100


def hls_to_rgb_vec(h, l, s):
    def hue2rgb(p, q, t):
        t = np.mod(t, 1.0)
        res = np.where(t < 1/6, p + (q - p) * 6 * t, p)
        res = np.where((t >= 1/6) & (t < 1/2), q, res)
        res = np.where((t >= 1/2) & (t < 2/3), p + (q - p) * (2/3 - t) * 6, res)
        return res
    q = np.where(l < 0.5, l * (1 + s), l + s - l * s)
    p = 2 * l - q
    r = hue2rgb(p, q, h + 1/3)
    g = hue2rgb(p, q, h)
    b = hue2rgb(p, q, h - 1/3)
    return r, g, b


def strip_border(img, thresh=30):
    """Remove the flattened-image's black export border and rescale back to
    the original 1200x686 canvas."""
    arr = np.array(img.convert("RGB")).astype(int)
    H, W, _ = arr.shape

    def first_nonblack(vals):
        for i, px in enumerate(vals):
            if px.sum() > thresh:
                return i
        return 0

    top = first_nonblack(arr[:30, W // 2])
    bottom = H - 1 - first_nonblack(arr[::-1, W // 2][:30])
    left = first_nonblack(arr[H // 2, :40])
    right = W - 1 - first_nonblack(arr[H // 2, ::-1][:40])
    cropped = img.crop((left + 2, top + 2, right - 2, bottom - 2))
    return cropped.resize((W, H), Image.LANCZOS)


def recolor_hue(img, target_hue, hue_lo=325, hue_hi=10, light_max=40, sat_min=10):
    """Shift only the wine-family pixels to target_hue, preserving each
    pixel's own saturation/lightness (so gradient + texture survive)."""
    arr = np.array(img.convert("RGB")).astype(float)
    h, s, l = rgb_to_hsl_np(arr)
    mask = (((h >= hue_lo) & (h <= 360)) | (h <= hue_hi)) & (l < light_max) & (s > sat_min)
    new_h = np.where(mask, target_hue, h)
    r, g, b = hls_to_rgb_vec(new_h.flatten() / 360.0, l.flatten() / 100.0, s.flatten() / 100.0)
    out = np.stack([r, g, b], axis=-1).reshape(arr.shape) * 255
    final = np.where(mask[..., None], out, arr)
    return Image.fromarray(np.clip(final, 0, 255).astype("uint8")), mask


def find_panel_edges(front_arr):
    """Fit straight-line equations for the wine panel's right edge (= gold
    line's inner edge) and the gold line's outer edge, per row."""
    H, W, _ = front_arr.shape
    r = front_arr[..., 0].astype(int); g = front_arr[..., 1].astype(int); b = front_arr[..., 2].astype(int)
    gold_mask = (r > 140) & (g > 90) & (g < 225) & (b < 170) & (r > g) & (g >= b - 5)
    lum = (front_arr.max(axis=-1).astype(float) + front_arr.min(axis=-1).astype(float)) / 2
    wine_like = (r > g + 10) & (lum < 40) & (r > 15)

    left_edges = np.full(H, np.nan)
    right_edges = np.full(H, np.nan)
    for y in range(H):
        xs = np.where(wine_like[y, 600:950])[0]
        if len(xs) > 3:
            le = 600 + xs.max()
            xs2 = np.where(gold_mask[y, le:le + 40])[0]
            if len(xs2) > 2:
                re = le + xs2.max()
                w = re - le
                if 5 <= w <= 20:
                    left_edges[y] = le
                    right_edges[y] = re

    good = ~np.isnan(left_edges)
    ys_good = np.where(good)[0]
    lcoef = np.polyfit(ys_good, left_edges[good], 1)
    rcoef = np.polyfit(ys_good, right_edges[good], 1)
    all_y = np.arange(H).astype(float)
    return np.polyval(lcoef, all_y), np.polyval(rcoef, all_y), wine_like


def rebuild_clean_panel(front_arr, left_edge, wine_like):
    """Fit a smooth bilinear gradient to the panel's own background pixels
    (well clear of text and the gold edge) and use it to replace every
    pixel behind the leader's name/contact text, removing it cleanly."""
    H, W, _ = front_arr.shape
    xs_grid = np.arange(W)
    safe_region = (xs_grid[None, :] < (left_edge[:, None] - 45)) & (xs_grid[None, :] >= 10)
    valid = wine_like & safe_region
    ys_v, xs_v = np.where(valid)
    n = len(ys_v)
    rng = np.random.default_rng(0)
    idx = rng.choice(n, size=min(30000, n), replace=False)
    xs_s = xs_v[idx].astype(float); ys_s = ys_v[idx].astype(float)
    xn = xs_s / W; yn = ys_s / H

    def design(xn, yn):
        return np.stack([np.ones_like(xn), xn, yn, xn * yn], axis=1)

    A = design(xn, yn)
    models = []
    for c in range(3):
        vals = front_arr[ys_s.astype(int), xs_s.astype(int), c]
        coef, *_ = np.linalg.lstsq(A, vals, rcond=None)
        models.append(coef)

    full_x, full_y = np.meshgrid(np.arange(W).astype(float) / W, np.arange(H).astype(float) / H)
    A_full = design(full_x.ravel(), full_y.ravel())
    recon = np.zeros((H, W, 3))
    for c in range(3):
        recon[..., c] = (A_full @ models[c]).reshape(H, W)
    recon = np.clip(recon, 0, 255)

    panel_region = xs_grid[None, :] < (left_edge[:, None] - 2)
    final = np.where(panel_region[..., None], recon, front_arr)
    return np.clip(final, 0, 255).astype("uint8")


def strip_back_border_and_clean(back_img, target_hue):
    cropped = strip_border(back_img)
    recolored, _ = recolor_hue(cropped, target_hue, light_max=45)
    return recolored


# ---------- main build ----------

if __name__ == "__main__":
    SCHEMES = {
        "wine_gold": 339.0,
        "sage_forest": 150.0,  # forest green hue
    }

    front_raw = Image.open("front_extracted.png").convert("RGB")
    back_raw = Image.open("back_extracted.png").convert("RGB")

    front_clean_base = strip_border(front_raw)
    back_clean_base = strip_border(back_raw)
    front_clean_base.save("front_border_stripped.png")
    back_clean_base.save("back_border_stripped.png")

    # detect panel geometry ONCE on the original (still-wine) image --
    # the shape is identical across schemes, only the color changes
    orig_arr = np.array(front_clean_base.convert("RGB"))
    left_edge, right_edge, wine_like = find_panel_edges(orig_arr)
    np.save("left_edge.npy", left_edge)
    np.save("right_edge.npy", right_edge)

    for scheme_name, hue in SCHEMES.items():
        front_recolored, _ = recolor_hue(front_clean_base, hue)
        front_arr = np.array(front_recolored.convert("RGB")).astype(float)

        # reuse the SAME wine_like mask/geometry (from the original) to
        # sample the gradient, just pulling colors from the recolored image
        clean_panel_arr = rebuild_clean_panel(front_arr, left_edge, wine_like)
        Image.fromarray(clean_panel_arr).save(f"front_master_{scheme_name}.png")

        back_recolored = strip_back_border_and_clean(back_clean_base, hue)
        back_recolored.save(f"back_master_{scheme_name}.png")

        print(f"built master for {scheme_name}")
