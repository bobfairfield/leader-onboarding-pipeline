# Email template — sending a new leader her deliverables

You said you'd rather send this yourself than have it auto-sent, so the
webhook stops short of sending and instead gives you everything you need
to fire it off in one pass.

**Subject:** Your Bob Ferguson Longevity toolkit is ready, {{name}}!

**Body:**

Hi {{name}},

Welcome to the team! Everything's built and ready:

- Your personal landing page is live: {{live_url}}
- Your business card (front + back, print-ready PDF) is attached
- Your "How Do You Feel Today?" wellness checklist (fillable PDF) is attached
- Your prospect tracker (Excel) is attached, ready to log leads as you go

A couple of things worth knowing:
- Your landing page doesn't have an email sign-up form connected yet — that's
  next on the list, whenever you're ready. I'll send a short doc on setting
  that up through Constant Contact.
{{#if no_photo}}
- I don't have a photo from you yet, so your card and landing page bio
  section are on hold — send one over whenever you get a chance and I'll
  finish those up.
{{/if}}

Let me know if anything looks off and I'll fix it.

Bob

---

Attach from the onboarding output folder:
- `{name}_Card_front.pdf`, `{name}_Card_back.pdf`
- `{name}_How_Do_You_Feel_Today.pdf`
- `{name}_Bio-Age_Prospect_Tracker.xlsx`
