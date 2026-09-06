/**
 * Bound to the Google Sheet that collects Leader Intake Form responses.
 *
 * Setup:
 *   1. Open the linked Sheet -> Extensions -> Apps Script.
 *   2. Paste this in, replacing Code.gs.
 *   3. Set WEBHOOK_URL below to your deployed pipeline endpoint.
 *   4. Set WEBHOOK_SECRET to a random string; set the same value as an
 *      env var on the webhook side so it can verify requests came from
 *      here and not from someone who found the URL.
 *   5. Run `installTrigger` once from the Apps Script editor (it'll ask
 *      for permissions) - this wires onFormSubmit to fire automatically
 *      forever after, with zero manual action needed per submission.
 *
 * Column order below must match your form's field order exactly. If you
 * reorder form questions, update COLUMNS to match.
 */

const WEBHOOK_URL = "https://YOUR-DEPLOYMENT.vercel.app/api/onboard";
const WEBHOOK_SECRET = "REPLACE_WITH_A_RANDOM_STRING";

const COLUMNS = {
  TIMESTAMP: 0,
  NAME: 1,
  EMAIL: 2,
  PHONE: 3,
  SHAKLEE_HANDLE: 4,
  COLOR_SCHEME: 5,
  PHOTO_URL: 6,   // Google Forms writes the Drive file URL here
  BIO: 7,
};

function installTrigger() {
  ScriptApp.newTrigger("onFormSubmit")
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onFormSubmit()
    .create();
  Logger.log("Trigger installed. New form submissions will now fire automatically.");
}

function onFormSubmit(e) {
  const row = e.values;

  const colorSchemeRaw = row[COLUMNS.COLOR_SCHEME] || "";
  const colorScheme = colorSchemeRaw.toLowerCase().includes("sage")
    ? "sage_forest"
    : "wine_gold";

  const payload = {
    name: row[COLUMNS.NAME],
    email: row[COLUMNS.EMAIL],
    phone: row[COLUMNS.PHONE],
    shaklee_storefront_handle: row[COLUMNS.SHAKLEE_HANDLE],
    color_scheme: colorScheme,
    photo_drive_url: row[COLUMNS.PHOTO_URL] || null,
    bio: row[COLUMNS.BIO] || null,
    submitted_at: row[COLUMNS.TIMESTAMP],
  };

  const options = {
    method: "post",
    contentType: "application/json",
    headers: { "X-Webhook-Secret": WEBHOOK_SECRET },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
  const status = response.getResponseCode();

  // Write a status column back onto the row so you can see it worked
  // without leaving the Sheet. Column I = index 8.
  const sheet = e.range.getSheet();
  const rowNum = e.range.getRow();
  if (status === 200) {
    const result = JSON.parse(response.getContentText());
    sheet.getRange(rowNum, 9).setValue("Onboarded \u2713");
    sheet.getRange(rowNum, 10).setValue(result.live_url || "");
    sheet.getRange(rowNum, 11).setValue(result.qa_status || "");
  } else {
    sheet.getRange(rowNum, 9).setValue("FAILED - check webhook logs");
    sheet.getRange(rowNum, 10).setValue("HTTP " + status);
  }
}
