#!/usr/bin/env python3
"""
Generate a personalized Bio-Age Prospect Tracker workbook for a leader.

Usage:
    python3 generate_leader_tracker.py "Leader Name" "output.xlsx"

Requires Bio-Age_Master_Prospect_Tracker_TEMPLATE.xlsx in the same folder.
Never edit that master directly - this script reads it fresh every time.

After running, recalculate cached formula values:
    python3 /mnt/skills/public/xlsx/scripts/recalc.py output.xlsx
"""

import sys
import os
import openpyxl

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(SCRIPT_DIR, "Bio-Age_Master_Prospect_Tracker_TEMPLATE.xlsx")

TITLE_SPOTS = [
    ("Prospect Tracker", "A1", "Bio-Age\u2122 Reset Stack Prospect Tracker"),
    ("Priority View", "A1", "Priority View"),
    ("Pipeline Summary", "A1", "Pipeline Summary"),
]


def generate(leader_name, output_path):
    wb = openpyxl.load_workbook(MASTER)
    for sheet_name, cell_ref, suffix in TITLE_SPOTS:
        ws = wb[sheet_name]
        ws[cell_ref] = f"{leader_name} \u2014 {suffix}"
    wb.save(output_path)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    _, name, out = sys.argv
    generate(name, out)
