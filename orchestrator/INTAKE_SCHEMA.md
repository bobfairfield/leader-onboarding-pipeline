# Leader Intake Schema

This is the canonical shape every downstream script expects. The intake
form (whatever it's built on) must ultimately produce this JSON per leader.

```json
{
  "name": "Torah Torres",
  "email": "torah@example.com",
  "phone": "555-123-4567",
  "shaklee_storefront_handle": "torahtorres",
  "color_scheme": "wine_gold",
  "photo_path": "/path/to/uploaded/photo.jpg",
  "bio": "One sentence, her own words, optional",
  "ctct_script_var": null,
  "ctct_form_id": null
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Full name, used everywhere (brand, cards, checklist, tracker) |
| `email` | yes | Contact email, swapped into mailto: links and footers |
| `phone` | yes | Contact phone, swapped into footers and card |
| `shaklee_storefront_handle` | yes | The part of her Shaklee URL after `en_US/` — she gets this when Bob (or Shaklee) sets up her Ambassador storefront. **This is the one field that can't come from the leader herself; it has to be looked up/assigned before the pipeline runs.** |
| `color_scheme` | yes | `wine_gold` or `sage_forest` — ask on the form |
| `photo_path` | no | If missing, landing page About section is omitted (placeholder left) and the card generation step is skipped/flagged for manual follow-up, since a card needs a photo |
| `bio` | no | Falls back to a neutral default line |
| `ctct_script_var` / `ctct_form_id` | no | Almost never known at signup time — leader gets a follow-up doc (`Connecting-Your-Email-List.docx`) instead |

`repo_slug` is *derived*, not collected: `name.lower().replace(' ','-') + '-landing'`.
