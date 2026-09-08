# Leader Business Card Generator (v2)

Produces print-ready, 343dpi, 3.5"x2" front+back business card PDFs by
compositing onto Bob's own real finished card art (not a redraw), so every
leader card stays pixel-consistent with Bob's and Dubi's originals.

## Setup (already done, included in this zip)
`masters/sage_front_clean.png` and `masters/wine_front_clean.png` are
pre-built, text-erased backgrounds (borders, gold diagonal band, and
texture all intact, ready for a new photo + name to be composited on).
`masters/sage_1.png` / `masters/wine_1.png` are the untouched back-card
masters (12 Hallmarks wheel art).

Only re-run `python3 build_masters.py` if the raw master card PDFs
themselves change (masters/sage_0.png, masters/wine_0.png) - e.g. if
Bob's own card design is revised. It re-derives the clean front
backgrounds from scratch (~30 seconds).

## Usage
```
python3 generate_card.py "Leader Name" "Longevity|Community" \
    "email@example.com" "555-123-4567" \
    "https://bobfairfield.github.io/leader-landing/" \
    "headshot.jpg" sage|wine out_prefix \
    [--bw] [--tagline "Aging Reimagined"] [--website "leaderdomain.com"]
```
- `--bw` renders the headshot in black & white (use for low-res/stylized
  photos that won't hold up well in color at print size).
- `--tagline` adds an italic line under the brand suffix (only if the
  leader's landing page actually uses one - most don't).
- `--website` adds a third contact row with a globe icon (only if the
  leader has a short custom domain; otherwise leave it out and let the
  QR code do the linking).
- Brand suffix is "Longevity" for most leaders, but check the leader's
  own live landing page footer first - Torah and Lohrainne use
  "Community" instead, and that's intentional, not a typo to fix.

Produces `{out_prefix}_front.pdf`, `{out_prefix}_back.pdf`, and
`{out_prefix}_both_sides.pdf` (the one to actually send to print).

## Example (Torah Torres, already produced)
```
python3 generate_card.py "Torah Torres" "Community" \
    "Shaklee@TorahTorres.com" "805-223-1885" \
    "https://bobfairfield.github.io/torah-torres-landing/" \
    torah_headshot.jpg sage Torah --bw
```

## Design constants worth knowing
- Diagonal gold-band centerline: `x = 838.57 - 0.1857*y` (identical on
  both schemes, measured directly from Bob's own card). Photo starts
  ~11.5px to the right of that; text/background must stay ~12.5px to
  the left of it - `build_masters.py` already respects this.
- QR code on the back must stay left of `x=356` in the 1200x686 canvas -
  the "12 Hallmarks" wheel's leftmost point sits at ~x=363 at its
  narrowest (y~350), and going past that flattens the ellipse.
- Never hand-edit a generated PDF/PNG. If something needs to change for
  one leader, change the input. If something needs to change for every
  leader, edit `build_masters.py` or the raw masters and re-run it.

## No-photo card mode (added Sept 2026)

For leaders who don't have a Google account and don't want to create one
just to upload a photo (Google Forms requires sign-in for any file upload,
full stop - not a setting that can be turned off).

```
python3 generate_card.py "Leader Name" "Longevity|Community" \
    "email@example.com" "555-123-4567" \
    "https://bobfairfield.github.io/leader-landing/" \
    none sage|wine out_prefix --no-photo
```

`photo_path` is ignored when `--no-photo` is set (pass anything, e.g. `none`).

Layout: full-bleed color panel (no diagonal cut), same name/brand-suffix/
contact typography as the photo version, with a large low-opacity VIVIX+
watermark on the right in place of the headshot. Masters:
`masters/sage_nophoto_bg.png`, `masters/wine_nophoto_bg.png` (pre-built;
`build_masters.py` regenerates them from the raw masters if ever needed).

### Form side
The onboarding Google Form now asks "Business card style" (With my photo /
No-photo design) right before the headshot upload question, so the choice
is explicit before anyone hits the Google sign-in wall. **The Vercel
webhook (`onboard_leader.py`) needs a matching update** to read that field
and call `generate(..., no_photo=True)` when "No-photo design" is chosen -
that repo isn't available in this session, so that wiring still needs to
happen on Bob's end (or in a session with GitHub access to
`leader-onboarding-pipeline`).
