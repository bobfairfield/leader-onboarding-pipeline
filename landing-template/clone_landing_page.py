#!/usr/bin/env python3
"""
Clone Bob's master landing page into a fully personalized page for a leader.

Usage:
    python3 clone_landing_page.py leader.json output.html

leader.json fields (all required unless marked optional):
    name            "Torah Torres"
    email           "torah@example.com"
    phone           "555-123-4567"
    shaklee_path    "en_US/torahtorres"     (the part after us.shaklee.com/)
    repo_slug       "torah-torres-landing"  (used for og:url)
    photo_path      optional; path to a headshot/couple photo. If omitted,
                    the About section is removed entirely (placeholder
                    comment left behind), matching the established
                    convention for leaders without a photo yet.
    bio             optional; one sentence. Falls back to a neutral
                    default if omitted.
    ctct_script_var optional Constant Contact "_ctct_m" value
    ctct_form_id    optional Constant Contact form UUID
                    If either is omitted, the email-capture section is
                    left as a placeholder comment for the leader to
                    self-serve or send to Bob later.

Never edit bob_master.html directly - this script reads it fresh every
time so the master stays clean for the next leader.
"""

import sys
import os
import json
import base64
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(SCRIPT_DIR, "bob_master.html")


def swap_simple_fields(html, leader):
    brand = f"{leader['name']} Longevity"

    # Title / meta tags
    html = html.replace(
        "Vivix+&trade; Reversed 8 Years of Cellular Aging in 60 Days | Bob Ferguson Longevity",
        f"Vivix+&trade; Reversed 8 Years of Cellular Aging in 60 Days | {brand}",
    )
    html = html.replace(
        'content="https://bobfairfield.github.io/bob-ferguson-landing/"',
        f'content="https://bobfairfield.github.io/{leader["repo_slug"]}/"',
    )
    html = html.replace("Bob Ferguson Longevity", brand)

    # Contact info everywhere
    html = html.replace("bob@fergleads.com", leader["email"])
    html = html.replace("913-208-6357", leader["phone"])

    # Shaklee affiliate path
    html = html.replace("en_US/ferguson", leader["shaklee_path"])

    return html


def swap_about_section(html, leader):
    start_marker = "<!-- ABOUT / PERSONAL INTRO -->"
    end_marker = "<!-- FOOTER -->"
    start = html.index(start_marker)
    end = html.index(end_marker)
    block = html[start:end]

    if leader.get("photo_path"):
        with open(leader["photo_path"], "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(leader["photo_path"])[1].lstrip(".").lower()
        ext = "jpeg" if ext in ("jpg", "jpeg") else ext
        first_name = leader["name"].split()[0]
        bio = leader.get("bio") or (
            f"I share the same routine and research you just read about "
            f"because it's made a real difference in my own life, and I "
            f"love helping others find their own starting point. If you "
            f"have questions, or just want to talk it through before you "
            f"order, reach out any time."
        )
        new_block = f'''{start_marker}
<section class="about-leader">
  <div class="wrap">
    <div class="about-leader-inner">
      <img class="about-leader-photo" src="data:image/{ext};base64,{b64}" alt="{leader['name']}">
      <div class="about-leader-text">
        <p><strong>Hi, I'm {first_name}.</strong> {bio}</p>
      </div>
    </div>
  </div>
</section>

'''
    else:
        new_block = f"{start_marker}\n<!-- No photo on file yet - About section omitted. Add one later by re-running the cloner with photo_path set. -->\n\n"

    return html[:start] + new_block + html[end:]


def swap_constant_contact(html, leader):
    ctct_var = leader.get("ctct_script_var")
    ctct_form = leader.get("ctct_form_id")

    # Inline form div
    old_div_pattern = re.compile(
        r'<div class="ctct-inline-form"[^>]*></div>'
    )
    if ctct_form:
        new_div = f'<div class="ctct-inline-form" data-form-id="{ctct_form}"></div>'
    else:
        new_div = '<!-- Email capture: pending setup. See Connecting-Your-Email-List.docx -->'
    html = old_div_pattern.sub(new_div, html, count=1)

    # Script block near </body>
    old_script_pattern = re.compile(
        r'<!-- Begin Constant Contact Active Forms -->.*?<!-- End Constant Contact Active Forms -->',
        re.DOTALL,
    )
    if ctct_var:
        new_script = (
            "<!-- Begin Constant Contact Active Forms -->\n"
            f'<script> var _ctct_m = "{ctct_var}"; </script>\n'
            '<script id="signupScript" src="//static.ctctcdn.com/js/signup-form-widget/current/signup-form-widget.min.js" async defer></script>\n'
            "<!-- End Constant Contact Active Forms -->"
        )
    else:
        new_script = "<!-- Constant Contact script: pending setup. -->"
    html = old_script_pattern.sub(new_script, html, count=1)

    return html


def clone(leader, output_path):
    with open(MASTER) as f:
        html = f.read()

    html = swap_simple_fields(html, leader)
    html = swap_about_section(html, leader)
    html = swap_constant_contact(html, leader)

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Wrote {output_path} ({len(html)} chars)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    _, leader_json_path, out = sys.argv
    with open(leader_json_path) as f:
        leader = json.load(f)
    clone(leader, out)
