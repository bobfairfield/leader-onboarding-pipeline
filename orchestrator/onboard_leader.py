#!/usr/bin/env python3
"""
Onboard one new leader: generate all four deliverables (landing page,
business card front/back, wellness checklist, prospect tracker), run a
QA pass on the results, and leave everything in an output folder ready
for review / GitHub push.

Usage:
    python3 onboard_leader.py leader.json /path/to/pipeline/root /path/to/output_dir

leader.json must match INTAKE_SCHEMA.md.

This script does NOT touch GitHub. See github_push.py for that step - kept
separate on purpose so a human (or a review step) can look at the output
folder before anything goes live.
"""

import sys
import os
import json
import re
import shutil
import subprocess

REQUIRED_FIELDS = ["name", "email", "phone", "shaklee_storefront_handle", "color_scheme"]


def slugify(name):
    return name.lower().replace(".", "").replace("'", "").strip().replace(" ", "-") + "-landing"


def underscore(name):
    return name.replace(" ", "_")


def clean_shaklee_handle(raw):
    """
    People will paste their full storefront URL instead of just the handle
    (this already happened once in real testing). Extract just the handle
    whether they gave us the bare word, a full URL, or something in between.
    Returns an empty string if no real handle was actually provided.
    """
    raw = raw.strip()
    match = re.search(r"en_US/([^/?#\s]+)", raw)
    if match:
        return match.group(1)
    raw = re.sub(r"^https?://", "", raw)
    raw = raw.rstrip("/")
    result = raw.split("/")[-1] if raw else raw
    # "en_US" left over from a bare URL prefix isn't a real handle
    if result.lower() in ("en_us", "shaklee.com", "us.shaklee.com", ""):
        return ""
    return result


def run(cmd, cwd=None):
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result.stdout


def onboard(leader, pipeline_root, out_dir):
    missing = [f for f in REQUIRED_FIELDS if not leader.get(f)]
    if missing:
        raise ValueError(f"Missing required intake fields: {missing}")

    name = leader["name"]
    uname = underscore(name)
    repo_slug = leader.get("repo_slug") or slugify(name)
    leader["repo_slug"] = repo_slug
    leader["shaklee_path"] = f"en_US/{clean_shaklee_handle(leader['shaklee_storefront_handle'])}"

    os.makedirs(out_dir, exist_ok=True)
    report = {"leader": name, "repo_slug": repo_slug, "steps": [], "warnings": []}
    if leader["color_scheme"] not in ("wine_gold", "sage_forest"):
        report_note = (
            f"Unrecognized color_scheme value {leader['color_scheme']!r} - "
            "defaulting to wine_gold. This shouldn't happen if Apps Script's "
            "own mapping is intact; if you see this, check that mapping."
        )
        leader["color_scheme"] = "wine_gold"
        report["warnings"].append(report_note)
    if leader["shaklee_path"] == "en_US/":
        report["warnings"].append(
            "Shaklee storefront handle couldn't be extracted from what was entered "
            "(looks like she pasted just the base URL with no actual handle). "
            "Her page links to the generic Shaklee storefront until you get her real handle."
        )

    # ---------- 1. Wellness checklist ----------
    print("[1/4] Wellness checklist...")
    wellness_dir = os.path.join(pipeline_root, "wellness-template")
    out_pdf = os.path.join(out_dir, f"{uname}_How_Do_You_Feel_Today.pdf")
    run([sys.executable, "generate_leader_form.py", name, leader["phone"], leader["email"], out_pdf],
        cwd=wellness_dir)
    report["steps"].append({"deliverable": "wellness_checklist", "file": out_pdf, "status": "generated"})

    # ---------- 2. Prospect tracker ----------
    print("[2/4] Prospect tracker...")
    tracker_dir = os.path.join(pipeline_root, "tracker-template")
    out_xlsx = os.path.join(out_dir, f"{uname}_Bio-Age_Prospect_Tracker.xlsx")
    run([sys.executable, "generate_leader_tracker.py", name, out_xlsx], cwd=tracker_dir)
    recalc_path = "/mnt/skills/public/xlsx/scripts/recalc.py"
    if os.path.exists(recalc_path):
        # Only available in Claude's own sandbox (requires LibreOffice, which
        # doesn't exist on Vercel). Best-effort only - Excel and Google Sheets
        # both recalculate formulas automatically the moment a person actually
        # opens the file, so skipping this doesn't affect the real deliverable.
        run([sys.executable, recalc_path, out_xlsx])
    else:
        report["warnings"].append(
            "Formula recalculation skipped (LibreOffice-based recalc tool isn't "
            "available in this environment). This doesn't affect the tracker "
            "itself - Excel and Google Sheets recalculate formulas automatically "
            "on open."
        )
    report["steps"].append({"deliverable": "prospect_tracker", "file": out_xlsx, "status": "generated"})

    # ---------- 3. Business card ----------
    print("[3/4] Business card...")
    card_dir = os.path.join(pipeline_root, "card-template", "Leader-Card-Template")
    card_prefix = os.path.join(out_dir, f"{uname}_Card")
    landing_url = f"https://bobfairfield.github.io/{repo_slug}/"
    brand_suffix = leader.get("brand_suffix") or "Longevity"
    no_photo = bool(leader.get("no_photo")) or not leader.get("photo_path")

    cmd = [
        sys.executable, "generate_card.py", name, brand_suffix, leader["email"], leader["phone"],
        landing_url,
    ]
    if no_photo:
        cmd += ["none", leader["color_scheme"].replace("_gold", "").replace("_forest", ""), card_prefix, "--no-photo"]
    else:
        photo_abs = os.path.abspath(leader["photo_path"])
        cmd += [photo_abs, leader["color_scheme"].replace("_gold", "").replace("_forest", ""), card_prefix]
    run(cmd, cwd=card_dir)

    report["steps"].append({
        "deliverable": "business_card",
        "file": f"{card_prefix}_front.pdf / _back.pdf",
        "status": "generated_no_photo" if no_photo else "generated",
    })
    if no_photo:
        report["warnings"].append(
            "No photo provided - card generated using the no-photo layout "
            "(full-bleed panel with VIVIX+ watermark, no headshot needed)."
        )

    # ---------- 4. Landing page ----------
    print("[4/4] Landing page...")
    landing_dir = os.path.join(pipeline_root, "landing-template")
    leader_json_path = os.path.join(out_dir, "_leader.json")
    with open(leader_json_path, "w") as f:
        json.dump(leader, f)
    out_html = os.path.join(out_dir, f"{uname}-index.html")
    run([sys.executable, "clone_landing_page.py", leader_json_path, out_html], cwd=landing_dir)
    report["steps"].append({"deliverable": "landing_page", "file": out_html, "status": "generated"})
    if not leader.get("photo_path"):
        report["warnings"].append("No photo provided - landing page About section omitted (placeholder left).")
    if not leader.get("ctct_form_id"):
        report["warnings"].append("No Constant Contact info yet - email capture left as placeholder. Send her Connecting-Your-Email-List.docx.")

    with open(os.path.join(out_dir, "_onboarding_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    _, leader_json_path, pipeline_root, out_dir = sys.argv
    with open(leader_json_path) as f:
        leader = json.load(f)
    report = onboard(leader, pipeline_root, out_dir)
    print(json.dumps(report, indent=2))
