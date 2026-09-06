# Leader Intake Form — Google Form spec

**Why Google Forms:** it's free, requires no setup on the leader's end,
handles photo uploads natively (drops them straight into a Drive folder),
has built-in required-field validation so leaders can't submit half-filled
info, works on mobile, and — since you're already on Google Workspace for
the Shared Drive — needs no new account or tool for you to manage. This is
the "easiest and most foolproof" option: nothing to break, nothing to teach.

## Fields

| # | Field | Type | Required | Notes |
|---|---|---|---|---|
| 1 | Full name | Short answer | Yes | Used everywhere: brand name, card, checklist, tracker |
| 2 | Email | Short answer (email validation) | Yes | |
| 3 | Phone | Short answer | Yes | Any format; the pipeline doesn't reformat it |
| 4 | Shaklee storefront handle | Short answer | Yes | The part of her Shaklee URL after `en_US/` — **you assign this when you set up her Ambassador storefront in Shaklee's system**, so either pre-fill it before sending her the form, or add a short instruction: "leave blank if you don't have this yet, Bob will fill it in" |
| 5 | Color scheme | Multiple choice: Wine & Gold / Sage & Forest | Yes | |
| 6 | Headshot photo | File upload | No | Needed for the business card and landing page About section. Form clearly notes: "You can skip this and add it later — a card just can't be made until we have one." |
| 7 | Short personal note (optional) | Paragraph | No | One sentence on why she takes it / why she coaches — used as her landing page bio. Falls back to a neutral default if left blank. |

## What NOT to ask for

Don't put `repo_slug` on the form — it's derived automatically from the
name. Don't ask for Constant Contact info at signup — almost nobody has
that yet; it's a separate follow-up doc (`Connecting-Your-Email-List.docx`)
sent after onboarding.

## Setup

1. Create the form at forms.google.com with the fields above.
2. Under Responses, click the Sheets icon to link it to a new Google Sheet
   — this is what the Apps Script below watches.
3. File uploads need "Collect email addresses" and file-upload permission
   turned on in form settings (Google will prompt you the first time you
   add a file-upload question).
