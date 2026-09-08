#!/usr/bin/env python3
"""
Leader business card generator (v2 - "edit the finished master" pipeline).

Usage:
    python3 generate_card.py \
        "Leader Name" "Brand Suffix" "email@example.com" "555-123-4567" \
        "https://bobfairfield.github.io/leader-landing/" \
        "headshot.jpg" sage out_prefix \
        [--bw] [--website "leaderdomain.com"] [--tagline "Aging Reimagined"]

scheme is one of: sage, wine

Requires masters/sage_front_clean.png, masters/wine_front_clean.png,
masters/sage_1.png, masters/wine_1.png (run build_masters.py once if the
*_front_clean.png files are missing or the raw master PDFs change).

Never hand-edit a generated card. If something needs to change for one
leader, change the input to this script. If something needs to change
for every leader, edit build_masters.py / the raw masters instead.
"""
import argparse
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from pypdf import PdfWriter, PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
MASTERS = os.path.join(HERE, "masters")


def _font_path(filename):
    """Resolve a font file: prefer the repo's bundled ../../fonts/ dir
    (portable for serverless deployment where system fonts don't exist),
    fall back to the system path (Claude's own sandbox)."""
    bundled = os.path.join(HERE, "..", "..", "fonts", filename)
    if os.path.exists(bundled):
        return bundled
    return f"/usr/share/fonts/truetype/crosextra/{filename}"


FONT_BOLD = _font_path("Caladea-Bold.ttf")
FONT_SANS = _font_path("Carlito-Regular.ttf")
FONT_SANS_BOLD = _font_path("Carlito-Bold.ttf")
FONT_ITALIC = _font_path("Caladea-Italic.ttf")

WHITE = (240, 240, 235)
GOLD = (0xC6, 0x97, 0x4F)
GOLD_TOP = (204, 165, 88)
GOLD_BOTTOM = (150, 109, 38)

LEFT_MARGIN = 68
ICON_X = 64
TEXT_X = 146

# Diagonal gold-band centerline, identical across schemes (measured from
# Bob's own finished cards). x = CENTER(y); band half-width ~9.5px.
def CENTER(y):
    return 838.57 - 0.1857 * y


def photo_x_left():
    # leftmost point of the diagonal across the full card height (y=685)
    return int(CENTER(685) - 9.5 + 2)


def draw_gradient_text(base, xy, text, font, top_color, bottom_color):
    d = ImageDraw.Draw(base)
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    top = np.array(top_color)
    bot = np.array(bottom_color)
    arr = np.zeros((th, tw, 3), dtype=np.uint8)
    for yy in range(th):
        frac = yy / max(th - 1, 1)
        arr[yy, :, :] = top * (1 - frac) + bot * frac
    grad_img = Image.fromarray(arr)
    mask_img = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(mask_img).text((-bbox[0], -bbox[1]), text, font=font, fill=255)
    base.paste(grad_img, (xy[0] + bbox[0], xy[1] + bbox[1]), mask_img)


def make_handset_icon(size=200, color=GOLD):
    color_rgba = color + (255,)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    p0 = np.array([size * 0.30, size * 0.72])
    p1 = np.array([size * 0.15, size * 0.30])
    p2 = np.array([size * 0.70, size * 0.18])
    steps = 60
    tube_r = size * 0.085
    for i in range(steps + 1):
        t = i / steps
        pt = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
        d.ellipse([pt[0] - tube_r, pt[1] - tube_r, pt[0] + tube_r, pt[1] + tube_r], fill=color_rgba)
    cap_r = size * 0.115
    for p in (p0, p2):
        d.ellipse([p[0] - cap_r, p[1] - cap_r, p[0] + cap_r, p[1] + cap_r], fill=color_rgba)
    return layer


def draw_email_icon(draw, x, y, size, color):
    draw.ellipse([x, y, x + size, y + size], outline=color, width=3)
    cx, cy = x + size / 2, y + size / 2
    r = size * 0.28
    draw.rectangle([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], outline=color, width=2)
    draw.line([cx - r, cy - r * 0.6, cx, cy + r * 0.15, cx + r, cy - r * 0.6], fill=color, width=2)


def draw_phone_icon(base, x, y, size, color):
    draw = ImageDraw.Draw(base)
    draw.ellipse([x, y, x + size, y + size], outline=color, width=3)
    icon_size = int(size * 0.62)
    icon = make_handset_icon(size=icon_size, color=color)
    cx, cy = x + size / 2, y + size / 2
    base.paste(icon, (int(cx - icon_size / 2), int(cy - icon_size / 2)), icon)


def crop_fit_photo(photo_path, target_w, target_h, bw=False):
    im = Image.open(photo_path).convert("RGB")
    if bw:
        im = im.convert("L").convert("RGB")
    w, h = im.size
    aspect = target_w / target_h
    src_aspect = w / h
    if src_aspect > aspect:
        crop_w = int(h * aspect)
        x0 = (w - crop_w) // 2
        im = im.crop((x0, 0, x0 + crop_w, h))
    else:
        crop_h = int(w / aspect)
        y0 = (h - crop_h) // 2
        im = im.crop((0, y0, w, y0 + crop_h))
    return im.resize((target_w, target_h), Image.LANCZOS)


def composite_photo(base_arr, photo_arr, x_left):
    h, w, _ = base_arr.shape
    out = base_arr.copy()
    for y in range(h):
        b = int(round(CENTER(y) + 9.5 + 2))  # just past the gold band
        b = max(b, x_left)
        if b < w:
            seg_w = w - b
            px_start = b - x_left
            out[y, b:w, :] = photo_arr[y, px_start:px_start + seg_w, :]
    return out


def build_front(scheme, name, brand_suffix, email, phone, photo_path,
                 photo_bw=False, tagline=None, website=None):
    clean_path = os.path.join(MASTERS, f"{scheme}_front_clean.png")
    base = Image.open(clean_path).convert("RGB")
    arr = np.array(base)
    h, w, _ = arr.shape

    x_left = photo_x_left()
    photo = crop_fit_photo(photo_path, w - x_left, h, bw=photo_bw)
    arr = composite_photo(arr, np.array(photo), x_left)
    base = Image.fromarray(arr)
    draw = ImageDraw.Draw(base)

    name_font = ImageFont.truetype(FONT_BOLD, 112)
    draw.text((LEFT_MARGIN, 66), name, font=name_font, fill=WHITE)

    suffix_font = ImageFont.truetype(FONT_BOLD, 112)
    draw_gradient_text(base, (LEFT_MARGIN, 178), brand_suffix, suffix_font, GOLD_TOP, GOLD_BOTTOM)
    draw = ImageDraw.Draw(base)

    row_y = 178  # bottom of brand suffix line, before optional tagline
    if tagline:
        tagline_font = ImageFont.truetype(FONT_ITALIC, 46)
        draw.text((LEFT_MARGIN, 293), tagline, font=tagline_font, fill=WHITE)

    # gold glow rule line
    x0, x1, yc = 68, 700, 332
    center_x, half = (x0 + x1) / 2, (x1 - x0) / 2
    dim = np.array([50, 50, 38])
    bright = np.array([255, 226, 177])
    for x in range(x0, x1):
        t = max(1 - abs(x - center_x) / half, 0) ** 1.4
        col = tuple((dim * (1 - t) + bright * t).astype(int).tolist())
        draw.line([(x, yc - 2), (x, yc + 2)], fill=col)

    vivix_font = ImageFont.truetype(FONT_SANS_BOLD, 30)
    vivix_y = 400
    draw.text((LEFT_MARGIN, vivix_y), "VIVIX+", font=vivix_font, fill=GOLD)
    w1 = draw.textlength("VIVIX+   ", font=vivix_font)
    draw.text((LEFT_MARGIN + w1, vivix_y), "\u2022   BIO-AGE RESET STACK", font=vivix_font, fill=GOLD)

    contact_font = ImageFont.truetype(FONT_SANS, 34)
    rows = [("email", email), ("phone", phone)]
    if website:
        rows.append(("web", website))
    row_ys = [486, 558, 630][:len(rows)]

    for (kind, text), ry in zip(rows, row_ys):
        size = 40
        if kind == "email":
            draw_email_icon(draw, ICON_X, ry - 3, size, GOLD)
        elif kind == "phone":
            draw_phone_icon(base, ICON_X, ry - 3, size, GOLD)
            draw = ImageDraw.Draw(base)
        elif kind == "web":
            draw.ellipse([ICON_X, ry - 3, ICON_X + size, ry - 3 + size], outline=GOLD, width=3)
            cx, cy = ICON_X + size / 2, ry - 3 + size / 2
            draw.ellipse([cx - size * 0.4, cy - size * 0.4, cx + size * 0.4, cy + size * 0.4],
                         outline=GOLD, width=1)
            draw.line([cx - size * 0.4, cy, cx + size * 0.4, cy], fill=GOLD, width=1)
        draw.text((TEXT_X, ry), text, font=contact_font, fill=WHITE)

    return base


def build_front_nophoto(scheme, name, brand_suffix, email, phone, tagline=None, website=None):
    """No-photo layout: full-bleed color panel, translucent VIVIX+ watermark
    on the right in place of a headshot. Used when a leader has no Google
    account and doesn't want to set one up just to upload a photo."""
    bg_path = os.path.join(MASTERS, f"{scheme}_nophoto_bg.png")
    base = Image.open(bg_path).convert("RGB")
    draw = ImageDraw.Draw(base)

    name_font = ImageFont.truetype(FONT_BOLD, 112)
    draw.text((LEFT_MARGIN, 100), name, font=name_font, fill=WHITE)

    suffix_font = ImageFont.truetype(FONT_BOLD, 112)
    draw_gradient_text(base, (LEFT_MARGIN, 212), brand_suffix, suffix_font, GOLD_TOP, GOLD_BOTTOM)
    draw = ImageDraw.Draw(base)

    if tagline:
        tagline_font = ImageFont.truetype(FONT_ITALIC, 46)
        draw.text((LEFT_MARGIN, 327), tagline, font=tagline_font, fill=WHITE)

    x0, x1, yc = 68, 700, 366
    center_x, half = (x0 + x1) / 2, (x1 - x0) / 2
    dim = np.array([50, 50, 38])
    bright = np.array([255, 226, 177])
    for x in range(x0, x1):
        t = max(1 - abs(x - center_x) / half, 0) ** 1.4
        col = tuple((dim * (1 - t) + bright * t).astype(int).tolist())
        draw.line([(x, yc - 2), (x, yc + 2)], fill=col)

    vivix_font = ImageFont.truetype(FONT_SANS_BOLD, 30)
    vivix_y = 434
    draw.text((LEFT_MARGIN, vivix_y), "VIVIX+", font=vivix_font, fill=GOLD)
    w1 = draw.textlength("VIVIX+   ", font=vivix_font)
    draw.text((LEFT_MARGIN + w1, vivix_y), "\u2022   BIO-AGE RESET STACK", font=vivix_font, fill=GOLD)

    contact_font = ImageFont.truetype(FONT_SANS, 34)
    rows = [("email", email), ("phone", phone)]
    if website:
        rows.append(("web", website))
    row_ys = [520, 592, 664][:len(rows)]

    for (kind, text), ry in zip(rows, row_ys):
        size = 40
        if kind == "email":
            draw_email_icon(draw, ICON_X, ry - 3, size, GOLD)
        elif kind == "phone":
            draw_phone_icon(base, ICON_X, ry - 3, size, GOLD)
            draw = ImageDraw.Draw(base)
        elif kind == "web":
            draw.ellipse([ICON_X, ry - 3, ICON_X + size, ry - 3 + size], outline=GOLD, width=3)
            cx, cy = ICON_X + size / 2, ry - 3 + size / 2
            draw.ellipse([cx - size * 0.4, cy - size * 0.4, cx + size * 0.4, cy + size * 0.4],
                         outline=GOLD, width=1)
            draw.line([cx - size * 0.4, cy, cx + size * 0.4, cy], fill=GOLD, width=1)
        draw.text((TEXT_X, ry), text, font=contact_font, fill=WHITE)

    return base


def build_back(scheme, landing_url):
    back_path = os.path.join(MASTERS, f"{scheme}_1.png")
    back = Image.open(back_path).convert("RGB")
    arr = np.array(back)
    cream = tuple(int(c) for c in arr[230, 20])

    x0, y0, y1 = 77, 245, 489
    x1_safe = 356  # stays clear of the wheel's leftmost point (~363px)
    pad = 6

    patch = Image.new("RGB", ((x1_safe - x0) + 2 * pad, (y1 - y0) + 2 * pad), cream)
    back.paste(patch, (x0 - pad, y0 - pad))

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(landing_url)
    qr.make(fit=True)
    fill_color = (30, 60, 42) if scheme == "sage" else (0x4F, 0x10, 0x26)
    qr_img = qr.make_image(fill_color=fill_color, back_color=cream).convert("RGB")

    side = min(x1_safe - x0, y1 - y0)
    qr_resized = qr_img.resize((side, side), Image.NEAREST)
    cx, cy = (x0 + x1_safe) // 2, (y0 + y1) // 2
    back.paste(qr_resized, (cx - side // 2, cy - side // 2))
    return back


def generate(name, brand_suffix, email, phone, landing_url, photo_path,
             scheme, out_prefix, photo_bw=False, tagline=None, website=None,
             no_photo=False):
    if scheme not in ("sage", "wine"):
        raise ValueError("scheme must be 'sage' or 'wine'")

    if no_photo:
        front = build_front_nophoto(scheme, name, brand_suffix, email, phone,
                                     tagline=tagline, website=website)
    else:
        front = build_front(scheme, name, brand_suffix, email, phone, photo_path,
                             photo_bw=photo_bw, tagline=tagline, website=website)
    back = build_back(scheme, landing_url)

    front.save(f"{out_prefix}_front.pdf", "PDF", resolution=343.0)
    back.save(f"{out_prefix}_back.pdf", "PDF", resolution=343.0)
    front.save(f"{out_prefix}_front_preview.png")  # for the AI review step to look at

    w = PdfWriter()
    w.append(PdfReader(f"{out_prefix}_front.pdf"))
    w.append(PdfReader(f"{out_prefix}_back.pdf"))
    out_path = f"{out_prefix}_both_sides.pdf"
    with open(out_path, "wb") as f:
        w.write(f)
    print(f"wrote {out_path}")
    return out_path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("brand_suffix", help="'Longevity' or 'Community'")
    p.add_argument("email")
    p.add_argument("phone")
    p.add_argument("landing_url")
    p.add_argument("photo_path", help="path to headshot, or 'none' if --no-photo")
    p.add_argument("scheme", choices=["sage", "wine"])
    p.add_argument("out_prefix")
    p.add_argument("--bw", action="store_true", help="render photo in black & white")
    p.add_argument("--no-photo", action="store_true",
                    help="use the full-bleed no-photo layout instead (leader has no Google account)")
    p.add_argument("--tagline", default=None)
    p.add_argument("--website", default=None)
    args = p.parse_args()

    generate(args.name, args.brand_suffix, args.email, args.phone, args.landing_url,
              args.photo_path, args.scheme, args.out_prefix,
              photo_bw=args.bw, tagline=args.tagline, website=args.website,
              no_photo=args.no_photo)
