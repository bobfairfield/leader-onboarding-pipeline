#!/usr/bin/env python3
"""
Generate a personalized Bio-Age / Vivix+ business card (front + back) for a
Bob Ferguson Longevity leader, starting from the clean master templates.

Usage:
    python3 generate_leader_card.py "Leader Name" "phone" "email" "website_display" \\
        "landing_url" "photo.jpg" "wine_gold|sage_forest" "output_prefix"

Example:
    python3 generate_leader_card.py "Torah Torres" "805-223-1885" \\
        "Shaklee@TorahTorres.com" "Scan to visit my page" \\
        "https://bobfairfield.github.io/torah-torres-landing/" \\
        torah_photo.jpg wine_gold Torah_Torres_Card

Produces <output_prefix>_front.pdf and <output_prefix>_back.pdf, print-ready
at 3.5"x2", 300+ DPI.

Requires the master PNGs already built by build_masters.py:
    front_master_<scheme>.png, back_master_<scheme>.png, left_edge.npy,
    right_edge.npy -- run build_masters.py once if those are missing.
Never hand-edit a generated card. If something needs to change for one
leader, change the input to this script. If something needs to change for
every leader, edit the master build (build_masters.py) instead.
"""
import sys
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import qrcode
from qrcode.constants import ERROR_CORRECT_H

HERE = os.path.dirname(os.path.abspath(__file__))

def _font_path(filename):
    """Resolve a font file: prefer a bundled ./fonts/ dir (portable for
    serverless deployment), fall back to the system path (this sandbox)."""
    bundled = os.path.join(HERE, "..", "..", "fonts", filename)
    if os.path.exists(bundled):
        return bundled
    bundled_local = os.path.join(HERE, "fonts", filename)
    if os.path.exists(bundled_local):
        return bundled_local
    return f"/usr/share/fonts/truetype/crosextra/{filename}"

FONT_BOLD = _font_path("Caladea-Bold.ttf")
FONT_ITALIC = _font_path("Caladea-Italic.ttf")
FONT_SANS_BOLD = _font_path("Carlito-Bold.ttf")
FONT_SANS = _font_path("Carlito-Regular.ttf")

GOLD = (0xC6, 0x97, 0x4F)
GOLD_LIGHT = (0xDC, 0xC1, 0x90)
CREAM = (0xF7, 0xF3, 0xEB)

SCHEME_WINE = {"wine": (0x4F, 0x10, 0x26), "gold": GOLD, "gold_light": GOLD_LIGHT}
SCHEME_SAGE = {"wine": (0x1E, 0x33, 0x27), "gold": GOLD, "gold_light": GOLD_LIGHT}
SCHEMES = {"wine_gold": SCHEME_WINE, "sage_forest": SCHEME_SAGE}

LEFT_MARGIN = 34

# --- front card layout: pil draw-y values are pre-offset so the actual ink
# lands exactly at the position measured from the original artwork ---
NAME_Y = 66
LONGEVITY_Y = 168
TAGLINE_Y = 284
PRODUCT_Y = 391
EMAIL_Y = 458
PHONE_Y = 525
WEB_Y = 593
ICON_X = 65
ICON_D = 40
TEXT_X = 140

NAME_SIZE = 100
TAGLINE_SIZE = 50
PRODUCT_SIZE = 30
CONTACT_SIZE = 38

GOLD_TOP = (204, 165, 88)
GOLD_BOTTOM = (150, 109, 38)


def draw_gradient_text(base_img, xy, text, font, top_color, bottom_color):
    """Draw text filled with a vertical gradient (used for "Longevity",
    which fades from bright gold at the top of the letters to a darker,
    near-black-edged gold at the bottom in the original artwork)."""
    mask = Image.new("L", base_img.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.text(xy, text, font=font, fill=255)
    bbox = mask.getbbox()
    if bbox is None:
        return
    y0, y1 = bbox[1], bbox[3]
    grad = Image.new("RGB", base_img.size, top_color)
    gdraw = ImageDraw.Draw(grad)
    for y in range(y0, y1 + 1):
        t = (y - y0) / max(1, (y1 - y0))
        col = tuple(int(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(3))
        gdraw.line([(0, y), (base_img.size[0], y)], fill=col)
    base_img.paste(grad, (0, 0), mask)


def draw_icon(draw, x, y_center, kind, color, d=ICON_D):
    x0, y0 = x, y_center - d / 2
    x1, y1 = x + d, y_center + d / 2
    draw.ellipse([x0, y0, x1, y1], outline=color, width=2)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = d * 0.27
    if kind == "email":
        draw.rectangle([cx - r, cy - r * 0.65, cx + r, cy + r * 0.65], outline=color, width=2)
        draw.line([cx - r, cy - r * 0.55, cx, cy + r * 0.15, cx + r, cy - r * 0.55], fill=color, width=2)
    elif kind == "phone":
        # simple diagonal receiver: thick rounded line with circular ends
        x_s, y_s = cx - r * 0.9, cy + r * 0.9
        x_e, y_e = cx + r * 0.9, cy - r * 0.9
        draw.line([x_s, y_s, x_e, y_e], fill=color, width=4)
        rr = r * 0.35
        draw.ellipse([x_s - rr, y_s - rr, x_s + rr, y_s + rr], outline=color, width=2)
        draw.ellipse([x_e - rr, y_e - rr, x_e + rr, y_e + rr], outline=color, width=2)
    elif kind == "web":
        draw.ellipse([cx - r * 1.3, cy - r * 1.3, cx + r * 1.3, cy + r * 1.3], outline=color, width=2)
        draw.line([cx - r * 1.3, cy, cx + r * 1.3, cy], fill=color, width=1)
        draw.ellipse([cx - r * 0.6, cy - r * 1.3, cx + r * 0.6, cy + r * 1.3], outline=color, width=1)


def build_front(scheme_key, name, phone, email, website_display, photo_path,
                 photo_region_w=480, photo_vbias=0.22):
    scheme = SCHEMES[scheme_key]
    base = Image.open(os.path.join(HERE, f"front_master_{scheme_key}.png")).convert("RGB")

    f_name = ImageFont.truetype(FONT_BOLD, NAME_SIZE)
    f_tagline = ImageFont.truetype(FONT_ITALIC, TAGLINE_SIZE)
    f_product = ImageFont.truetype(FONT_SANS_BOLD, PRODUCT_SIZE)
    f_contact = ImageFont.truetype(FONT_SANS, CONTACT_SIZE)

    draw = ImageDraw.Draw(base)
    draw.text((LEFT_MARGIN, NAME_Y), name, font=f_name, fill=CREAM)
    draw_gradient_text(base, (LEFT_MARGIN, LONGEVITY_Y), "Longevity", f_name, GOLD_TOP, GOLD_BOTTOM)
    draw = ImageDraw.Draw(base)
    draw.text((LEFT_MARGIN, TAGLINE_Y), "Aging Reimagined", font=f_tagline, fill=CREAM)
    draw.line([(LEFT_MARGIN, TAGLINE_Y + 68), (LEFT_MARGIN + 328, TAGLINE_Y + 68)],
               fill=scheme["gold"], width=2)
    draw.text((LEFT_MARGIN, PRODUCT_Y), "VIVIX+   \u2022   BIO-AGE RESET STACK",
               font=f_product, fill=scheme["gold_light"])

    for y, kind, text in [(EMAIL_Y, "email", email), (PHONE_Y, "phone", phone), (WEB_Y, "web", website_display)]:
        draw_icon(draw, ICON_X, y + 12, kind, scheme["gold"])
        draw.text((TEXT_X, y), text, font=f_contact, fill=CREAM)

    # composite the leader photo into the exact diagonal region
    right_edge = np.load(os.path.join(HERE, "right_edge.npy"))
    W, H = base.size
    region_w = photo_region_w
    photo = Image.open(photo_path).convert("RGB")
    photo = ImageOps.exif_transpose(photo)
    pw, ph = photo.size
    scale = max(region_w / pw, H / ph)
    new_w, new_h = int(pw * scale) + 1, int(ph * scale) + 1
    photo_resized = photo.resize((new_w, new_h), Image.LANCZOS)
    offx = (new_w - region_w) // 2
    offy = int((new_h - H) * photo_vbias)
    photo_crop = photo_resized.crop((offx, offy, offx + region_w, offy + H))

    base_arr = np.array(base).astype(float)
    full_photo = np.zeros((H, W, 3))
    x_offset = W - region_w
    full_photo[:, x_offset:x_offset + region_w] = np.array(photo_crop).astype(float)

    xs = np.arange(W).astype(float)
    xx, yy = np.meshgrid(xs, np.arange(H).astype(float))
    blend = 1.0
    alpha = np.clip((xx - right_edge[:, None]) / blend + 0.5, 0, 1)
    final = full_photo * alpha[..., None] + base_arr * (1 - alpha[..., None])
    return Image.fromarray(np.clip(final, 0, 255).astype("uint8"))


def build_back(scheme_key, landing_url):
    scheme = SCHEMES[scheme_key]
    base = Image.open(os.path.join(HERE, f"back_master_{scheme_key}.png")).convert("RGB")

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=20, border=1)
    qr.add_data(landing_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#%02X%02X%02X" % scheme["wine"], back_color=CREAM).convert("RGB")
    qr_box = (76, 245, 329, 489)
    qr_resized = qr_img.resize((qr_box[2] - qr_box[0], qr_box[3] - qr_box[1]), Image.LANCZOS)
    base.paste(qr_resized, (qr_box[0], qr_box[1]))

    draw = ImageDraw.Draw(base)
    draw.rectangle((30, 530, 370, 625), fill=CREAM)
    font = ImageFont.truetype(FONT_SANS_BOLD, 30)

    def draw_centered(text, cy, cx=204):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text((cx - w / 2, cy), text, font=font, fill=scheme["wine"])

    draw_centered("Scan to see", 548)
    draw_centered("the 8-year reversal", 585)
    return base


def generate(name, phone, email, website_display, landing_url, photo_path, scheme_key, out_prefix,
             photo_region_w=480, photo_vbias=0.22):
    if scheme_key not in SCHEMES:
        raise ValueError(f"Unknown scheme '{scheme_key}'. Choose from: {', '.join(SCHEMES)}")

    front = build_front(scheme_key, name, phone, email, website_display, photo_path,
                         photo_region_w=photo_region_w, photo_vbias=photo_vbias)
    back = build_back(scheme_key, landing_url)

    dpi = 343
    front.save(f"{out_prefix}_front.pdf", "PDF", resolution=dpi)
    back.save(f"{out_prefix}_back.pdf", "PDF", resolution=dpi)
    front.save(f"{out_prefix}_front_preview.png")
    back.save(f"{out_prefix}_back_preview.png")
    print(f"Wrote {out_prefix}_front.pdf and {out_prefix}_back.pdf ({scheme_key})")


if __name__ == "__main__":
    if len(sys.argv) != 9:
        print(__doc__)
        sys.exit(1)
    _, name, phone, email, website_display, landing_url, photo_path, scheme_key, out_prefix = sys.argv
    generate(name, phone, email, website_display, landing_url, photo_path, scheme_key, out_prefix)
