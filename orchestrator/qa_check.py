#!/usr/bin/env python3
"""
QA pass: opens every deliverable in an onboarding output folder and checks
it against a concrete checklist. This is the "second agent checking the
first agent's work" step - it runs independently of onboard_leader.py and
doesn't trust its report, it re-derives everything from the files
themselves.

Usage:
    python3 qa_check.py leader.json /path/to/output_dir

Exits 0 if everything passes, 1 if anything fails. Prints a human-readable
report either way and writes _qa_report.json into the output dir.
"""

import sys
import os
import json
import re
import glob

import openpyxl
from pypdf import PdfReader


def check_landing_page(leader, out_dir, results):
    matches = glob.glob(os.path.join(out_dir, "*-index.html"))
    if not matches:
        results.append(("landing_page", "FAIL", "No -index.html file found"))
        return
    path = matches[0]
    with open(path) as f:
        html = f.read()

    checks = [
        ("no leftover Bob references", "Bob Ferguson" not in html and "bob@fergleads.com" not in html and "913-208-6357" not in html),
        ("leader name present in brand", f"{leader['name']} Longevity" in html),
        ("leader email present", leader["email"] in html),
        ("leader phone present", leader["phone"] in html),
        ("shaklee path swapped", f"en_US/{leader['shaklee_storefront_handle']}" in html),
        ("no leftover en_US/ferguson", "en_US/ferguson" not in html),
        ("og:url points at leader's repo", leader.get("repo_slug", "") in html),
        ("html well-formed (tag balance)", html.count("<html") == html.count("</html>") and html.count("<section") == html.count("</section>")),
    ]
    if leader.get("photo_path"):
        checks.append(("about section present (photo was provided)", "about-leader-photo" in html))
    else:
        checks.append(("about section correctly omitted (no photo)", "about-leader-photo" not in html))

    for label, ok in checks:
        results.append(("landing_page", "PASS" if ok else "FAIL", label))


def check_wellness_pdf(leader, out_dir, results):
    matches = glob.glob(os.path.join(out_dir, "*How_Do_You_Feel_Today*.pdf"))
    if not matches:
        results.append(("wellness_checklist", "FAIL", "No wellness checklist PDF found"))
        return
    path = matches[0]
    reader = PdfReader(path)
    fields = reader.get_fields() or {}
    checks = [
        ("2 pages", len(reader.pages) == 2),
        ("all 261 checkbox/date fields intact", len(fields) == 261),
    ]
    for label, ok in checks:
        results.append(("wellness_checklist", "PASS" if ok else "FAIL", label))


def check_tracker(leader, out_dir, results):
    matches = glob.glob(os.path.join(out_dir, "*Bio-Age_Prospect_Tracker*.xlsx"))
    if not matches:
        results.append(("prospect_tracker", "FAIL", "No tracker xlsx found"))
        return
    path = matches[0]
    wb = openpyxl.load_workbook(path, data_only=True)
    expected_sheets = {"Prospect Tracker", "Lists", "Priority View", "Pipeline Summary", "How To Use"}
    checks = [
        ("all 5 tabs present", expected_sheets.issubset(set(wb.sheetnames))),
        ("Prospect Tracker title personalized", leader["name"] in str(wb["Prospect Tracker"]["A1"].value)),
        ("Priority View title personalized", leader["name"] in str(wb["Priority View"]["A1"].value)),
        ("Pipeline Summary title personalized", leader["name"] in str(wb["Pipeline Summary"]["A1"].value)),
        ("no leftover [Your Name] placeholder", "[Your Name]" not in str(wb["Prospect Tracker"]["A1"].value)),
    ]
    for label, ok in checks:
        results.append(("prospect_tracker", "PASS" if ok else "FAIL", label))


def check_card(leader, out_dir, results):
    front = glob.glob(os.path.join(out_dir, "*Card_front.pdf"))
    back = glob.glob(os.path.join(out_dir, "*Card_back.pdf"))
    if not leader.get("photo_path"):
        results.append(("business_card", "SKIP", "No photo provided - card intentionally skipped"))
        return
    if not front or not back:
        results.append(("business_card", "FAIL", "Front or back card PDF missing despite photo being provided"))
        return
    for label, path in [("front", front[0]), ("back", back[0])]:
        reader = PdfReader(path)
        page = reader.pages[0]
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        # 3.5x2in at 300dpi = 1050x600pt in PDF points (72pt/in) -> just check aspect ratio ~1.75
        ratio_ok = abs((w / h) - 1.75) < 0.05
        results.append(("business_card", "PASS" if ratio_ok else "FAIL", f"{label} card is 3.5x2in aspect ratio"))


def run_qa(leader, out_dir):
    results = []
    check_landing_page(leader, out_dir, results)
    check_wellness_pdf(leader, out_dir, results)
    check_tracker(leader, out_dir, results)
    check_card(leader, out_dir, results)

    failures = [r for r in results if r[1] == "FAIL"]
    report = {
        "leader": leader["name"],
        "total_checks": len(results),
        "passed": len([r for r in results if r[1] == "PASS"]),
        "failed": len(failures),
        "skipped": len([r for r in results if r[1] == "SKIP"]),
        "results": [{"deliverable": d, "status": s, "check": c} for d, s, c in results],
        "overall": "FAIL" if failures else "PASS",
    }

    with open(os.path.join(out_dir, "_qa_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print(f"QA for {leader['name']}: {report['overall']} "
          f"({report['passed']}/{report['total_checks']} passed, "
          f"{report['skipped']} skipped)")
    for d, s, c in results:
        marker = {"PASS": "\u2713", "FAIL": "\u2717", "SKIP": "-"}[s]
        print(f"  [{marker}] {d}: {c}")

    return report


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    _, leader_json_path, out_dir = sys.argv
    with open(leader_json_path) as f:
        leader = json.load(f)
    report = run_qa(leader, out_dir)
    sys.exit(0 if report["overall"] == "PASS" else 1)
