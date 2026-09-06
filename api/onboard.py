"""
Vercel Python serverless function: receives the Apps Script webhook, runs
the full onboarding pipeline, pushes the landing page to GitHub, and
returns a status JSON - including the four generated deliverables as
base64 - which Apps Script decodes and saves into a Drive folder.

Deploy with the rest of /pipeline alongside this /deployment folder so the
relative imports below resolve. See DEPLOYMENT_README.md for the exact
folder layout Vercel expects.

Env vars required (set in Vercel project settings):
    GITHUB_TOKEN      - fine-grained PAT, see github_push.py's docstring
                          for the exact permissions it needs
    GITHUB_OWNER      - "bobfairfield"
    WEBHOOK_SECRET    - must match the Apps Script's WEBHOOK_SECRET

Note on the entrypoint: Vercel's Python runtime looks for a top-level
`handler` class that subclasses http.server.BaseHTTPRequestHandler (or an
`app`/`application` WSGI object) - a plain `def handler(request)` function,
which an earlier draft of this file used, is not a valid entrypoint and
would 404 in production. This version uses the class-based form.
"""

import os
import sys
import json
import uuid
import base64
import shutil
import tempfile
import urllib.request
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "orchestrator"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "landing-template"))

from onboard_leader import onboard, slugify  # noqa: E402
from qa_check import run_qa  # noqa: E402
from github_push import push_leader_site  # noqa: E402

PIPELINE_ROOT = os.path.join(os.path.dirname(__file__), "..")

# Files to read back and return as base64 so Apps Script can save them to
# Drive. Keep this list in sync with what onboard_leader.py names its
# outputs. Total is normally under 2MB base64-encoded - comfortably inside
# Vercel's response size limits - but if a future leader photo pushes a
# business card PDF unusually large, drop the card from this list first.
DELIVERABLE_GLOBS = [
    "*_How_Do_You_Feel_Today.pdf",
    "*_Bio-Age_Prospect_Tracker.xlsx",
    "*_Card_front.pdf",
    "*_Card_back.pdf",
]


def _download_drive_photo(drive_url, dest_dir):
    """Google Forms file-upload answers are Drive view links, not direct
    downloads. Convert to a direct-download URL and pull the bytes."""
    if not drive_url:
        return None
    file_id = None
    if "/d/" in drive_url:
        file_id = drive_url.split("/d/")[1].split("/")[0]
    elif "id=" in drive_url:
        file_id = drive_url.split("id=")[1].split("&")[0]
    if not file_id:
        return None
    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    dest_path = os.path.join(dest_dir, "photo.jpg")
    urllib.request.urlretrieve(direct_url, dest_path)
    return dest_path


def _collect_deliverables_base64(out_dir):
    import glob
    files = {}
    for pattern in DELIVERABLE_GLOBS:
        for path in glob.glob(os.path.join(out_dir, pattern)):
            with open(path, "rb") as f:
                files[os.path.basename(path)] = base64.b64encode(f.read()).decode()
    return files


def process_onboarding(payload):
    """Pure function with the actual pipeline logic, kept separate from the
    HTTP plumbing in `handler` below so it can be unit tested (or run from
    a plain script) without spinning up a server."""
    work_dir = tempfile.mkdtemp(prefix=f"onboard-{uuid.uuid4().hex[:8]}-")
    out_dir = os.path.join(work_dir, "out")
    os.makedirs(out_dir, exist_ok=True)

    try:
        photo_path = _download_drive_photo(payload.get("photo_drive_url"), work_dir)

        leader = {
            "name": payload["name"],
            "email": payload["email"],
            "phone": payload["phone"],
            "shaklee_storefront_handle": payload["shaklee_storefront_handle"],
            "color_scheme": payload.get("color_scheme", "wine_gold"),
            "photo_path": photo_path,
            "bio": payload.get("bio"),
        }
        leader["repo_slug"] = slugify(leader["name"])

        onboard(leader, PIPELINE_ROOT, out_dir)
        qa_report = run_qa(leader, out_dir)

        live_url = push_leader_site(
            leader, out_dir,
            owner=os.environ["GITHUB_OWNER"],
            token=os.environ["GITHUB_TOKEN"],
        )

        return {
            "status": "ok",
            "leader_name": leader["name"],
            "live_url": live_url,
            "qa_status": qa_report["overall"],
            "qa_summary": f"{qa_report['passed']}/{qa_report['total_checks']} passed",
            "warnings": [r for r in qa_report.get("results", []) if r["status"] != "PASS"],
            "files_base64": _collect_deliverables_base64(out_dir),
        }
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


class handler(BaseHTTPRequestHandler):
    """Vercel Python runtime entrypoint. Vercel looks for this exact name -
    a class named `handler` subclassing BaseHTTPRequestHandler."""

    def do_POST(self):
        secret = self.headers.get("X-Webhook-Secret")
        if secret != os.environ.get("WEBHOOK_SECRET"):
            self._respond(401, {"error": "bad secret"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:
            self._respond(400, {"error": f"bad request body: {e}"})
            return

        try:
            result = process_onboarding(payload)
            self._respond(200, result)
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _respond(self, status_code, body_dict):
        body = json.dumps(body_dict).encode()
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
