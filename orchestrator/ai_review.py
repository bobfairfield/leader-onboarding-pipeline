#!/usr/bin/env python3
"""
Second-layer AI review: asks Claude to actually look at the generated card
image and read the generated landing page bio, judging whether it looks and
reads right. Runs AFTER qa_check.py's deterministic pass - this is the
"second checker" that catches things a script can't (garbled photo crops,
awkward phrasing, a stray em dash), not a replacement for the first one.

Fails closed on purpose: if ANTHROPIC_API_KEY isn't set, or the API call
itself errors out, this reports FAIL. Missing config should never look
identical to "the AI looked and it's fine" - a silent skip here would mean
nothing ever actually got the second check it was supposed to get.

Usage:
    python3 ai_review.py leader.json /path/to/output_dir
"""

import sys
import os
import json
import glob
import base64
import re
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"


def _call_claude(messages, api_key, max_tokens=500):
    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST")
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text[:200]}")
    return json.loads(match.group(0))


def _review_card(leader, out_dir, api_key, results):
    matches = glob.glob(os.path.join(out_dir, "*_front_preview.png"))
    if not matches:
        results.append(("card_image", "FAIL", "No card preview found - card generation may have failed"))
        return
    with open(matches[0], "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    no_photo = bool(leader.get("no_photo")) or not leader.get("photo_path")
    if no_photo:
        photo_check = (
            "This card intentionally uses the no-photo layout (full-bleed color panel "
            "with a large translucent VIVIX+ watermark instead of a headshot) - that is "
            "correct and expected, not a defect. Do not flag the absence of a photo."
        )
    else:
        photo_check = (
            "The photo should not be obviously cropped badly (face cut off, stretched, "
            "or upside down)."
        )

    prompt = (
        f"This is a generated business card front for {leader['name']}. "
        f"Check for: the name is fully legible and not cut off or overlapping "
        f"other text. {photo_check} There should be no visible rendering defect "
        "(garbled text, missing letters, color bleeding onto text). "
        "Respond with ONLY a JSON object: "
        '{"pass": true or false, "issues": ["short description", ...]} '
        "with issues as an empty list if there are none."
    )
    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
            {"type": "text", "text": prompt},
        ],
    }]
    try:
        resp = _call_claude(messages, api_key)
        text = "".join(b["text"] for b in resp["content"] if b["type"] == "text")
        verdict = _extract_json(text)
        status = "PASS" if verdict.get("pass") else "FAIL"
        issues = verdict.get("issues", [])
        results.append(("card_image", status, "; ".join(issues) if issues else "Card looks correct"))
    except Exception as e:
        results.append(("card_image", "FAIL", f"AI review call failed: {e}"))


def _review_copy(leader, out_dir, api_key, results):
    if not leader.get("photo_path"):
        # No About section exists at all in this case (see clone_landing_page.py) -
        # there's no real bio text to review, so don't manufacture one to judge.
        results.append(("landing_copy", "SKIP", "No bio to review (no photo on file, About section omitted)"))
        return

    matches = glob.glob(os.path.join(out_dir, "*-index.html"))
    if not matches:
        results.append(("landing_copy", "FAIL", "No landing page found to review"))
        return
    with open(matches[0]) as f:
        html = f.read()

    bio_match = re.search(r"<p><strong>Hi, I'm [^<]+\.</strong>(.*?)</p>", html, re.DOTALL)
    if not bio_match:
        results.append(("landing_copy", "FAIL", "Photo was provided but no About section found on the page - personalization may have failed"))
        return
    bio_text = bio_match.group(1).strip()

    prompt = (
        f"Here is the About-section bio text generated for {leader['name']}'s "
        f"personalized landing page:\n\n\"{bio_text}\"\n\n"
        "Check for: no leftover placeholder text (like [Your Name] or similar), "
        "it reads as a real sentence in a warm, confident, first-person voice "
        "(not garbled or cut off), and it does NOT use an em dash or en dash "
        "character anywhere, commas or periods only. Respond with ONLY a JSON "
        'object: {"pass": true or false, "issues": ["short description", ...]}.'
    )
    messages = [{"role": "user", "content": prompt}]
    try:
        resp = _call_claude(messages, api_key)
        text = "".join(b["text"] for b in resp["content"] if b["type"] == "text")
        verdict = _extract_json(text)
        status = "PASS" if verdict.get("pass") else "FAIL"
        issues = verdict.get("issues", [])
        results.append(("landing_copy", status, "; ".join(issues) if issues else "Copy reads correctly"))
    except Exception as e:
        results.append(("landing_copy", "FAIL", f"AI review call failed: {e}"))


def run_ai_review(leader, out_dir):
    results = []
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        results.append(("config", "FAIL", "ANTHROPIC_API_KEY not set - AI review cannot run"))
    else:
        _review_card(leader, out_dir, api_key, results)
        _review_copy(leader, out_dir, api_key, results)

    failures = [r for r in results if r[1] == "FAIL"]
    report = {
        "leader": leader["name"],
        "total_checks": len(results),
        "passed": len([r for r in results if r[1] == "PASS"]),
        "failed": len(failures),
        "skipped": len([r for r in results if r[1] == "SKIP"]),
        "results": [{"check": c, "status": s, "detail": d} for c, s, d in results],
        "overall": "FAIL" if failures else "PASS",
    }

    with open(os.path.join(out_dir, "_ai_review_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print(f"AI review for {leader['name']}: {report['overall']} "
          f"({report['passed']}/{report['total_checks']} passed, {report['skipped']} skipped)")
    for c, s, d in results:
        marker = {"PASS": "\u2713", "FAIL": "\u2717", "SKIP": "-"}[s]
        print(f"  [{marker}] {c}: {d}")

    return report


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    _, leader_json_path, out_dir = sys.argv
    with open(leader_json_path) as f:
        leader = json.load(f)
    report = run_ai_review(leader, out_dir)
    sys.exit(0 if report["overall"] == "PASS" else 1)
