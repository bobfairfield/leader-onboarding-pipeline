#!/usr/bin/env python3
"""
Generate a personalized "How Do You Feel Today?" wellness checklist for a
Bob Ferguson Longevity leader.

Usage:
    python3 generate_leader_form.py "Leader Name" "phone" "email" "output.pdf"

Requires template_page1_blank.png, template_page2_blank.png, and
How_Do_You_Feel_Today_TEMPLATE.pdf in the same folder. Never edit these
directly - this script reads them fresh every time.
"""

import sys
import os
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

WINE = (79, 16, 38)      # 4F1026 - BFL primary dark wine
FOREST = (44, 71, 54)    # 2C4736 - BFL sage/forest

def _font_path(filename):
    bundled = os.path.join(SCRIPT_DIR, "..", "..", "fonts", filename)
    if os.path.exists(bundled):
        return bundled
    bundled_local = os.path.join(SCRIPT_DIR, "fonts", filename)
    if os.path.exists(bundled_local):
        return bundled_local
    return f"/usr/share/fonts/truetype/crosextra/{filename}"

CALADEA_B = _font_path("Caladea-Bold.ttf")
CARLITO_R = _font_path("Carlito-Regular.ttf")

HEADER_NAME_XY = (131, 202)
FOOTER_LEFT_XY = (133, 3123)


def draw_tracked(draw, xy, text, font, fill, tracking=0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        w = draw.textlength(ch, font=font)
        x += w + tracking
    return x


def draw_footer_line(draw, leader_name, phone, email):
    f_name = ImageFont.truetype(CARLITO_R, 30)
    x, y = FOOTER_LEFT_XY
    for i, segment in enumerate([leader_name, "Aging Reimagined", phone, email]):
        if i > 0:
            x = draw_tracked(draw, (x, y), "   |   ", f_name, FOREST)
        x = draw_tracked(draw, (x, y), segment, f_name, FOREST)


def build_page1(leader_name, phone, email):
    img = Image.open(os.path.join(SCRIPT_DIR, "template_page1_blank.png")).convert("RGB")
    draw = ImageDraw.Draw(img)
    f_name = ImageFont.truetype(CALADEA_B, 34)
    draw_tracked(draw, HEADER_NAME_XY, leader_name.upper(), f_name, WINE, tracking=5)
    draw_footer_line(draw, leader_name, phone, email)
    return img


def build_page2(leader_name, phone, email):
    img = Image.open(os.path.join(SCRIPT_DIR, "template_page2_blank.png")).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw_footer_line(draw, leader_name, phone, email)
    return img


def generate(leader_name, phone, email, output_path):
    template_pdf = os.path.join(SCRIPT_DIR, "How_Do_You_Feel_Today_TEMPLATE.pdf")

    page1_img = build_page1(leader_name, phone, email)
    page2_img = build_page2(leader_name, phone, email)

    reader = PdfReader(template_pdf)
    writer = PdfWriter()
    writer.append(reader)

    list(writer.pages[0].images)[0].replace(page1_img)
    list(writer.pages[1].images)[0].replace(page2_img)

    with open(output_path, "wb") as f:
        writer.write(f)

    field_count = len(PdfReader(output_path).get_fields())
    print(f"Wrote {output_path} ({field_count} form fields intact)")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    _, name, phone, email, out = sys.argv
    generate(name, phone, email, out)
