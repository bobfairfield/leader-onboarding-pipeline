#!/usr/bin/env python3
"""
Create a new leader's GitHub repo, enable Pages, and push her landing page
(as index.html) plus the shared video assets - fully automated.

Requires a GitHub Personal Access Token with 'repo' scope in the
GITHUB_TOKEN environment variable.

Usage:
    export GITHUB_TOKEN=ghp_xxxxxxxx
    python3 github_push.py leader.json /path/to/output_dir bobfairfield

Only pushes: index.html (renamed from the *-index.html the pipeline made)
and the shared video files (vivix-sizzle.mp4, science-behind-vivix.mp4,
opportunity-video.mp4, vivix-science-full.mp4, joe-testimonial.mp4 for the
testimonial section) if present in a --videos-dir. Business card PDFs and
the wellness checklist/tracker are NOT pushed to GitHub - those go out by
email, not onto the public site.
"""

import sys
import os
import glob
import base64
import json
import time
import urllib.request
import urllib.error

API = "https://api.github.com"


def gh_request(method, path, token, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def create_repo(owner, repo_slug, token):
    status, resp = gh_request("POST", "/user/repos", token, {
        "name": repo_slug,
        "private": False,
        "auto_init": True,
        "description": "Leader landing page - Bob Ferguson Longevity network",
    })
    if status == 422:
        print(f"  Repo {repo_slug} already exists, continuing.")
        return
    if status not in (201,):
        raise RuntimeError(f"create_repo failed ({status}): {resp}")
    print(f"  Created repo {owner}/{repo_slug}")
    time.sleep(2)  # let GitHub settle before first push


def put_file(owner, repo_slug, path_in_repo, local_path, token, message):
    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    get_status, get_resp = gh_request(
        "GET", f"/repos/{owner}/{repo_slug}/contents/{path_in_repo}", token
    )
    sha = get_resp.get("sha") if get_status == 200 else None

    body = {"message": message, "content": content_b64}
    if sha:
        body["sha"] = sha

    status, resp = gh_request(
        "PUT", f"/repos/{owner}/{repo_slug}/contents/{path_in_repo}", token, body
    )
    if status not in (200, 201):
        raise RuntimeError(f"put_file failed for {path_in_repo} ({status}): {resp}")
    print(f"  Uploaded {path_in_repo}")


def enable_pages(owner, repo_slug, token):
    status, resp = gh_request("POST", f"/repos/{owner}/{repo_slug}/pages", token, {
        "source": {"branch": "main", "path": "/"}
    })
    if status in (201, 204, 409):  # 409 = already enabled
        print("  Pages enabled (or already was).")
    else:
        print(f"  WARNING: could not enable Pages ({status}): {resp}")


def push_leader_site(leader, out_dir, owner, token, videos_dir=None):
    repo_slug = leader["repo_slug"]

    create_repo(owner, repo_slug, token)

    html_matches = glob.glob(os.path.join(out_dir, "*-index.html"))
    if not html_matches:
        raise FileNotFoundError("No -index.html found in output dir")
    put_file(owner, repo_slug, "index.html", html_matches[0], token,
             f"Add {leader['name']}'s landing page")

    if videos_dir and os.path.isdir(videos_dir):
        for video in glob.glob(os.path.join(videos_dir, "*.mp4")):
            fname = os.path.basename(video)
            put_file(owner, repo_slug, fname, video, token, f"Add {fname}")

    enable_pages(owner, repo_slug, token)

    live_url = f"https://{owner}.github.io/{repo_slug}/"
    print(f"  Live at: {live_url}")
    return live_url


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    leader_json_path, out_dir, owner = sys.argv[1], sys.argv[2], sys.argv[3]
    videos_dir = sys.argv[4] if len(sys.argv) > 4 else None

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: set GITHUB_TOKEN environment variable first.")
        sys.exit(1)

    with open(leader_json_path) as f:
        leader = json.load(f)

    url = push_leader_site(leader, out_dir, owner, token, videos_dir)
    print(json.dumps({"live_url": url}))
