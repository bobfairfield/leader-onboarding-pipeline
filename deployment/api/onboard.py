"""
Vercel Python serverless function: receives the Apps Script webhook,
runs the full onboarding pipeline, pushes to GitHub, and returns a status
JSON (which Apps Script writes back onto the intake Sheet).

Deploy with the rest of /pipeline alongside this /deployment folder so the
relative imports below resolve. See DEPLOYMENT_README.md for the exact
folder layout Vercel expects.

Env vars required (set in Vercel project settings):
    GITHUB_TOKEN      - PAT with repo scope
    GITHUB_OWNER      - "bobfairfield"
    WEBHOOK_SECRET    - must match the Apps Script's WEBHOOK_SECRET
"""

import os
import sys
import json
import uuid
import shutil
import tempfile
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "orchestrator"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "landing-template"))

from onboard_leader import onboard, slugify  # noqa: E402
from qa_check import run_qa  # noqa: E402
from github_push import push_leader_site  # noqa: E402

PIPELINE_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


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


def handler(request):
    """Vercel Python runtime entrypoint (WSGI-style)."""
    secret = request.headers.get("X-Webhook-Secret")
    if secret != os.environ.get("WEBHOOK_SECRET"):
        return {"statusCode": 401, "body": json.dumps({"error": "bad secret"})}

    payload = json.loads(request.body)

    work_dir = tempfile.mkdtemp(prefix=f"onboard-{uuid.uuid4().hex[:8]}-")
    out_dir = os.path.join(work_dir, "out")
    os.makedirs(out_dir, exist_ok=True)

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

    try:
        onboard(leader, PIPELINE_ROOT, out_dir)
        qa_report = run_qa(leader, out_dir)

        live_url = push_leader_site(
            leader, out_dir,
            owner=os.environ["GITHUB_OWNER"],
            token=os.environ["GITHUB_TOKEN"],
            videos_dir=os.path.join(PIPELINE_ROOT, "shared-videos"),
        )

        # TODO: notify Bob (Slack webhook / email) that a new leader is
        # ready for review, with a link to the QA report and a note on
        # which files to attach - see EMAIL_DRAFT_TEMPLATE.md. Left as a
        # manual step per your preference: you review + send the email
        # yourself rather than an automated send.

        result = {
            "status": "ok",
            "live_url": live_url,
            "qa_status": qa_report["overall"],
            "qa_summary": f"{qa_report['passed']}/{qa_report['total_checks']} passed",
            "warnings": qa_report.get("results", []),
        }
        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
