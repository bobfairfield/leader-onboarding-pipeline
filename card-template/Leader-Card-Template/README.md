# Bio-Age Reset Stack Leader Card Template

Generates a personalized Vivix+ / Bio-Age Reset Stack business card (front +
back, print-ready PDF) for any leader in two color schemes: **Wine & Gold**
and **Sage & Forest**. Built directly from Bob's original hand-tuned card
artwork, not a redrawn approximation, so the panel gradient, gold border,
hallmarks-of-aging ellipse, and typography all trace back to the real design.

## Quick start

You do NOT need to run `build_masters.py` — the master templates are already
built and included. Just generate a card:

```bash
python3 generate_leader_card.py "Leader Name" "phone" "email" \
    "website or landing-page line" \
    "https://bobfairfield.github.io/leader-landing/" \
    "leader_photo.jpg" "wine_gold" "Leader_Name_Card"
```

This produces `Leader_Name_Card_front.pdf`, `Leader_Name_Card_back.pdf`, and
matching `_preview.png` files for a quick look before printing. Scheme is
`wine_gold` or `sage_forest`.

**Website field:** if the leader has their own domain, use it
(`"leadername.com"`). If not, use something like `"Scan to visit my page"` —
it just needs to read naturally next to the globe icon; it doesn't have to be
a URL.

## Two-person / non-standard photos

The default framing (`photo_region_w=480, photo_vbias=0.22`) is tuned for a
single centered headshot. For a couple photo, a wider shot, or anything that
doesn't crop well by default, call `build_front` directly instead of using
the command line, and adjust:

```python
import generate_leader_card as glc

front = glc.build_front(
    "wine_gold", "Leader Name", "phone", "email", "website",
    "photo.jpg",
    photo_region_w=480,   # larger = zooms OUT (shows more of the original photo)
    photo_vbias=0.15,     # 0 = crop from the very top, 0.5 = crop centered
)
front.save("Leader_front.png")
```

Render a few region_w values (try 480, 650, 800) and eyeball which one keeps
everyone's face fully in frame before committing. Then build the back with
`glc.build_back(scheme_key, landing_url)` and export both to PDF (see
`generate()` in `generate_leader_card.py` for the exact PDF export call).

## What's included

- `generate_leader_card.py` — the per-leader generator. This is the only
  script you run routinely.
- `build_masters.py` — the one-time script that built the master templates
  from the original artwork. You will not normally need to touch this — see
  "If something breaks" below.
- `front_master_wine_gold.png`, `back_master_wine_gold.png` — clean Wine &
  Gold templates: original gradient panel, gold border, ellipse, and icons
  intact, with all of Bob's personal text and photo removed.
- `front_master_sage_forest.png`, `back_master_sage_forest.png` — same, hue-
  shifted to forest green (gold stays constant across both schemes).
- `right_edge.npy`, `left_edge.npy` — the exact diagonal boundary geometry
  (as fitted line equations, sampled per row) that both scheme masters share.
  `generate_leader_card.py` needs `right_edge.npy` at runtime to composite
  photos into precisely the right diagonal frame.
- `front_extracted.png`, `back_extracted.png` — the raw original artwork
  (before border-stripping/recoloring), kept so `build_masters.py` can be
  re-run from scratch if a master ever needs to change.
- `sample_photo.jpg` — Bob's headshot, used for testing only.

## How this was built (for future reference / the agent)

1. **Border removal**: the original flattened export had a black margin
   around all four edges. Detected and cropped it out, rescaled back to the
   canonical 1200×686px (3.5"×2" at ~343 DPI) canvas.
2. **Panel/gold-line geometry**: the diagonal boundary between the color
   panel and the photo isn't a simple fixed line — it was fitted per-row from
   the actual artwork (a wine-colored pixel detector finds the panel's right
   edge; a gold-colored pixel detector finds the divider line's outer edge),
   then straight-line-fit for a clean, non-jittery edge. This geometry is
   identical for both schemes and is what `right_edge.npy` stores.
3. **Recoloring**: only pixels in the wine hue family were hue-shifted (to
   true Shaklee wine 4F1026 for Wine & Gold, or forest green for Sage &
   Forest) — gold, white text, and the photo were left completely alone. The
   recolor is spatially restricted to the panel region only, so it can never
   bleed into a leader's photo.
4. **Clean master (text removal)**: rather than inpainting over Bob's name
   and contact info (which produced ugly ghosting/artifacts), a smooth
   bilinear gradient was fit directly to the actual unobstructed background
   pixels and used to regenerate the entire panel background from scratch.
   This is why the master's panel has zero ghosting — it's not
   reconstructed from damaged pixels, it's a fresh, clean re-render of the
   same gradient.
5. **Text metrics**: every font size, position, and color in
   `generate_leader_card.py` was measured directly from Bob's finished card
   (pixel bounding boxes of each text line), not estimated. This includes
   the vertical gold-to-dark gradient on the word "Longevity", which is a
   real effect in the original artwork (bright gold ~(204,165,88) at the top
   of the letters fading to a darker (150,109,38) at the bottom).

## Known limitations

- **Icons are simplified approximations.** The envelope, phone, and globe
  icons are drawn with basic PIL shapes, not the original artwork's icons.
  They're clean and legible but not pixel-identical to Bob's card.
- **Font size is fixed, not auto-scaling.** A dramatically longer or shorter
  name than "Bob Ferguson" or "Dubi Gordon" may need the `NAME_SIZE` constant
  nudged down/up, or could overflow the panel width. Preview before printing.
- **Photo framing is manual for anything non-standard** (couples, group
  shots, non-headshot crops) — see the section above.

## If something breaks / needs to change

- If a leader's card looks wrong (text position, font size, icon), that's a
  **template** problem — fix it in `generate_leader_card.py` and it fixes
  itself for every future leader.
- If the master template itself needs to change (e.g. a different gold
  tone, a third color scheme), edit `build_masters.py` and re-run it — it
  rebuilds both scheme masters from `front_extracted.png` /
  `back_extracted.png` in about 10 seconds.
- Never hand-edit a generated leader's PNG/PDF directly. If it's wrong,
  fix the input to the script and regenerate.
