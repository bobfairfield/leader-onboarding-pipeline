"""
Run ONCE (or whenever the raw master PDFs change) to produce clean,
text-erased front backgrounds for each color scheme. generate_card.py
loads these clean masters directly, so per-leader generation never has
to repeat the (slow) inpainting/reconstruction step.

Input:  masters/sage_0.png, masters/wine_0.png   (raw front masters,
        1200x686px, extracted from Bob's own finished card PDFs)
Output: masters/sage_front_clean.png, masters/wine_front_clean.png
"""
import os
import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt

# Diagonal gold-band centerline, identical geometry across both schemes
# (measured directly from Bob's finished cards). x = CENTER(y).
def CENTER(y):
    return 838.57 - 0.1857 * y

LEFT, TOP, BOTTOM = 30, 16, 670


def clean_front(path_in, path_out):
    img = cv2.imread(path_in).astype(np.float32)
    h, w, _ = img.shape
    r = img[:, :, 2]

    def safe_right(y):
        return CENTER(y) - 9.5 - 3  # stop safely before the gold band

    safe = np.zeros((h, w), dtype=bool)
    for y in range(TOP, BOTTOM):
        xr = int(safe_right(y))
        xr = max(LEFT, min(xr, w))
        safe[y, LEFT:xr] = True

    text_mask = np.zeros((h, w), dtype=bool)
    text_mask[safe] = r[safe] > 28

    text_u8 = (text_mask.astype(np.uint8)) * 255
    text_u8 = cv2.dilate(text_u8, np.ones((5, 5), np.uint8), iterations=2)
    text_mask = (text_u8 > 0) & safe  # re-clip to safe zone, never touch border/gold

    valid = safe & (~text_mask)

    img_nan = img.copy()
    for c in range(3):
        img_nan[:, :, c] = np.where(valid, img[:, :, c], np.nan)

    block = 14
    Hc, Wc = h // block + 1, w // block + 1
    coarse = np.zeros((Hc, Wc, 3), dtype=np.float32)
    coarse_valid = np.zeros((Hc, Wc), dtype=bool)
    for by in range(Hc):
        for bx in range(Wc):
            y0, y1 = by * block, min((by + 1) * block, h)
            x0, x1 = bx * block, min((bx + 1) * block, w)
            blockdata = img_nan[y0:y1, x0:x1, :]
            if blockdata.size == 0:
                continue
            m = ~np.isnan(blockdata[:, :, 0])
            if m.sum() > 3:
                for c in range(3):
                    coarse[by, bx, c] = np.nanmean(blockdata[:, :, c])
                coarse_valid[by, bx] = True

    ind = distance_transform_edt(~coarse_valid, return_distances=False, return_indices=True)
    for c in range(3):
        coarse[:, :, c] = coarse[:, :, c][tuple(ind)]

    smooth = cv2.resize(coarse, (w, h), interpolation=cv2.INTER_CUBIC)
    smooth = cv2.GaussianBlur(smooth, (0, 0), sigmaX=6)

    out = img.copy()
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 2.2, size=(h, w, 3)).astype(np.float32)
    fill = smooth + noise
    for c in range(3):
        ch = out[:, :, c]
        chf = fill[:, :, c]
        ch[text_mask] = chf[text_mask]
        out[:, :, c] = ch

    out = np.clip(out, 0, 255).astype(np.uint8)
    cv2.imwrite(path_out, out)
    print(f"wrote {path_out}")


def full_bleed_background(path_in, path_out):
    """No-photo layout background: same smooth reconstruction as clean_front,
    but extrapolated across the FULL card width (no diagonal, no photo)."""
    img = cv2.imread(path_in).astype(np.float32)
    h, w, _ = img.shape
    r = img[:, :, 2]

    def safe_right(y):
        return CENTER(y) - 9.5 - 3

    safe = np.zeros((h, w), dtype=bool)
    for y in range(TOP, BOTTOM):
        xr = int(safe_right(y))
        xr = max(LEFT, min(xr, w))
        safe[y, LEFT:xr] = True

    text_mask = np.zeros((h, w), dtype=bool)
    text_mask[safe] = r[safe] > 28
    text_u8 = (text_mask.astype(np.uint8)) * 255
    text_u8 = cv2.dilate(text_u8, np.ones((5, 5), np.uint8), iterations=2)
    text_mask = (text_u8 > 0) & safe

    valid = safe & (~text_mask)  # only ever sample true background pixels

    img_nan = img.copy()
    for c in range(3):
        img_nan[:, :, c] = np.where(valid, img[:, :, c], np.nan)

    block = 14
    Hc, Wc = h // block + 1, w // block + 1
    coarse = np.zeros((Hc, Wc, 3), dtype=np.float32)
    coarse_valid = np.zeros((Hc, Wc), dtype=bool)
    for by in range(Hc):
        for bx in range(Wc):
            y0, y1 = by * block, min((by + 1) * block, h)
            x0, x1 = bx * block, min((bx + 1) * block, w)
            blockdata = img_nan[y0:y1, x0:x1, :]
            if blockdata.size == 0:
                continue
            m = ~np.isnan(blockdata[:, :, 0])
            if m.sum() > 3:
                for c in range(3):
                    coarse[by, bx, c] = np.nanmean(blockdata[:, :, c])
                coarse_valid[by, bx] = True

    ind = distance_transform_edt(~coarse_valid, return_distances=False, return_indices=True)
    for c in range(3):
        coarse[:, :, c] = coarse[:, :, c][tuple(ind)]

    smooth = cv2.resize(coarse, (w, h), interpolation=cv2.INTER_CUBIC)
    smooth = cv2.GaussianBlur(smooth, (0, 0), sigmaX=10)

    rng = np.random.default_rng(1)
    noise = rng.normal(0, 2.2, size=(h, w, 3)).astype(np.float32)
    out = np.clip(smooth + noise, 0, 255).astype(np.uint8)
    cv2.imwrite(path_out, out)
    print(f"wrote {path_out}")


def build_nophoto_front(bg_path, out_path, gold_top=(204, 165, 88), border_color=(0, 0, 0)):
    """Adds the border frame + translucent VIVIX+ watermark on top of a
    full-bleed background. Text is drawn later, per-leader, by generate_card.py."""
    base = cv2.imread(bg_path)
    base = cv2.cvtColor(base, cv2.COLOR_BGR2RGB)
    from PIL import Image, ImageDraw
    base = Image.fromarray(base)
    w, h = base.size
    draw = ImageDraw.Draw(base)

    bt = 14
    draw.rectangle([0, 0, w - 1, bt], fill=border_color)
    draw.rectangle([0, h - 1 - bt, w - 1, h - 1], fill=border_color)
    draw.rectangle([0, 0, bt, h - 1], fill=border_color)
    draw.rectangle([w - 1 - bt, 0, w - 1, h - 1], fill=border_color)
    draw.rectangle([bt + 6, bt + 6, w - 1 - bt - 6, h - 1 - bt - 6], outline=gold_top, width=1)

    mask = Image.open("masters/vivix_mask.png")
    scale = 1.65
    wm = mask.resize((int(mask.width * scale), int(mask.height * scale)), Image.LANCZOS)
    wm_gold = Image.new("RGBA", wm.size, gold_top + (0,))
    wm_alpha = wm.split()[3].point(lambda p: int(p * 0.11))
    wm_gold.putalpha(wm_alpha)
    wx = w - wm.width - 70
    wy = int(h * 0.62 - wm.height / 2)
    base.paste(wm_gold, (wx, wy), wm_gold)

    base.save(out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    clean_front("masters/sage_0.png", "masters/sage_front_clean.png")
    clean_front("masters/wine_0.png", "masters/wine_front_clean.png")

    full_bleed_background("masters/sage_0.png", "masters/_sage_fullbleed_tmp.png")
    full_bleed_background("masters/wine_0.png", "masters/_wine_fullbleed_tmp.png")
    build_nophoto_front("masters/_sage_fullbleed_tmp.png", "masters/sage_nophoto_bg.png")
    build_nophoto_front("masters/_wine_fullbleed_tmp.png", "masters/wine_nophoto_bg.png")
    os.remove("masters/_sage_fullbleed_tmp.png")
    os.remove("masters/_wine_fullbleed_tmp.png")
