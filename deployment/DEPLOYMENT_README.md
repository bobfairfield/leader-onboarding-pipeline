# Leader Onboarding Pipeline — Deployment Guide

## What's tested and working right now (ran end-to-end in this session)

- `wellness-template/generate_leader_form.py` — rebuilt from scratch this
  session, tested: 261 fields intact, header/footer personalize correctly.
- `tracker-template/generate_leader_tracker.py` — rebuilt, tested: 8,264
  formulas, clean recalc, all 3 title cells personalize correctly.
- `card-template/Leader-Card-Template/generate_leader_card.py` — your
  existing generator, font paths patched to be portable (see below),
  re-tested after the patch: still produces correct front/back cards.
- `landing-template/clone_landing_page.py` — new, tested: swaps every
  Bob-specific value (name, email, phone, Shaklee path, brand, og:url,
  About section, Constant Contact block), zero leftover references,
  verified against both the "no photo" and "photo + custom bio" paths.
- `orchestrator/onboard_leader.py` — new, runs all four generators from
  one leader JSON. Tested end-to-end on a sample leader; all four files
  produced correctly in one pass.
- `orchestrator/qa_check.py` — new, the "second agent checks the first
  agent's work" step. It re-opens every generated file independently
  (doesn't trust onboard_leader's own report) and checks 18 concrete
  things: no leftover Bob references, correct personalization in every
  file, correct tab/field/page counts, correct card aspect ratio, etc.
  Ran on the sample leader: 18/18 passed.

## What's written but NOT yet tested live (needs your input to finish)

- `orchestrator/github_push.py` — the GitHub automation (create repo,
  push index.html + videos, enable Pages). Code is complete and follows
  the same GitHub API calls you've used manually, but I don't have a
  GitHub token in this session, so it hasn't actually run against your
  account yet. **To finish this: generate a Personal Access Token**
  (GitHub -> Settings -> Developer settings -> Fine-grained tokens,
  scoped to just repo creation/contents on your account) **and hand it
  to me in a fresh session, or run the script yourself locally** —
  either way, it needs one real test run against a throwaway repo before
  you trust it on a real leader.
- `deployment/api/onboard.py` — the Vercel webhook that ties everything
  together for the "zero manual action" version. This is a best-effort
  scaffold, not a confirmed-working deployment — I don't have Vercel
  access from this sandbox, so I couldn't actually deploy or test it.
  Vercel's exact Python function request/response interface may need
  small adjustments once you deploy it for real. Budget a debugging pass
  the first time you wire this up.
- `deployment/apps_script_trigger.gs` — needs `WEBHOOK_URL` and
  `WEBHOOK_SECRET` filled in once the Vercel function is live, then
  `installTrigger()` run once from the Apps Script editor.

## Folder layout for Vercel

Deploy the whole `pipeline/` folder as the Vercel project root, so the
relative imports in `deployment/api/onboard.py` resolve:

```
pipeline/
  fonts/                        <- bundled Caladea/Carlito TTFs
  wellness-template/
  tracker-template/
  card-template/Leader-Card-Template/
  landing-template/              <- includes bob_master.html (re-pull
                                     periodically if you keep editing
                                     your own live page - see below)
  orchestrator/
  shared-videos/                 <- you'll need to add this: copies of
                                     vivix-sizzle.mp4, science-behind-
                                     vivix.mp4, opportunity-video.mp4,
                                     vivix-science-full.mp4, joe-
                                     testimonial.mp4
  deployment/
    api/onboard.py
    vercel.json
    requirements.txt
```

Env vars to set in Vercel project settings: `GITHUB_TOKEN`,
`GITHUB_OWNER=bobfairfield`, `WEBHOOK_SECRET` (match the Apps Script one).

## Important gaps, stated plainly

1. **Recalculating tracker formulas is skipped in the automated path.**
   The `recalc.py` step used in manual sessions needs LibreOffice, which
   doesn't run in a typical serverless function. This is fine in
   practice — Excel/Google Sheets computes formulas live the moment the
   leader opens the file, the cached-value step was only ever needed for
   *my own* visual QA renders inside this sandbox.
2. **`bob_master.html` is a snapshot.** Every time you edit your own live
   landing page (new section, copy change, etc.), the clone template
   drifts out of date. Re-run `curl -o landing-template/bob_master.html
   https://raw.githubusercontent.com/bobfairfield/bob-ferguson-landing/main/index.html`
   after any edit to your own page, or wire that same curl into the
   webhook itself so it always pulls fresh.
3. **No email is sent automatically**, per your call. The webhook leaves
   a status + live URL on the intake Sheet; you pull the generated files
   from wherever the pipeline writes them (a Drive folder, ideally — not
   built yet, see below) and send using `EMAIL_DRAFT_TEMPLATE.md`.
4. **Where do the output files land for you to grab?** Not yet built.
   Vercel functions are stateless/ephemeral, so `onboard_leader.py`'s
   output folder disappears after the function returns. You'll want the
   webhook to upload the four files to a Drive folder (or email them to
   you as attachments via a transactional email API) before it exits —
   this is the one piece of real plumbing still missing before this is
   truly hands-off. Worth a dedicated follow-up session once GitHub push
   is confirmed working.

## Suggested order of operations

1. Get me a GitHub PAT (or run `github_push.py` yourself) and confirm
   live automated repo creation works against a throwaway leader.
2. Build the missing "upload deliverables to Drive" step in
   `onboard.py` (small addition, same pattern as the Drive photo
   download already in there).
3. Deploy to Vercel, fix whatever the real Python runtime interface
   needs vs. what I guessed here.
4. Build the Google Form, link the Sheet, paste in the Apps Script,
   fill in `WEBHOOK_URL`/`WEBHOOK_SECRET`, run `installTrigger()` once.
5. Send yourself one full test submission before pointing it at a real
   leader.
