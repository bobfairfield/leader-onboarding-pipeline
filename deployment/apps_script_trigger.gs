/**
 * Handles onFormSubmit for BOTH onboarding forms and sends a normalized
 * payload to the Vercel webhook, then saves the returned deliverables into
 * Drive. This code belongs in the Apps Script bound to the ORIGINAL form's
 * response Sheet (open that Sheet -> Extensions -> Apps Script) - that's
 * where the real WEBHOOK_SECRET already lives. A single bound script can
 * still hold a trigger for a second, unrelated form via forForm(), so the
 * no-account form's trigger lives here too - no separate script needed.
 *
 * Replaces the old single-form version: that one sent `photo_drive_url`,
 * but the webhook only ever reads `photo_base64` / `photo_filename` - the
 * two never matched, so every submission's photo was silently dropped.
 * This version fetches the actual file bytes via DriveApp and sends those.
 *
 * Setup:
 *   1. Open the ORIGINAL form's response Sheet -> Extensions -> Apps Script.
 *   2. Select all the existing code, copy out the current WEBHOOK_SECRET
 *      value first (you'll need to paste it back in below).
 *   3. Replace everything with this file, then paste your real
 *      WEBHOOK_SECRET back in below.
 *   4. Run installTriggers() once (asks for permissions the first time).
 *   5. Test both forms end to end before telling leaders to use them.
 */

const WEBHOOK_URL = "https://leader-onboarding-pipeline.vercel.app/api/onboard";
const WEBHOOK_SECRET = "REPLACE_WITH_YOUR_ACTUAL_SECRET"; // must match Vercel's WEBHOOK_SECRET env var
const DELIVERABLES_FOLDER_ID = "1IFShUARasyGL21FAALhfXr9inbirO-5H";

const FORM_WITH_PHOTO_ID = "1OcsZTE2epS8Iwxz7JEZ0kMrixU30xVJHkCMA99ZxLkk";
const FORM_NO_ACCOUNT_ID = "10RodpCslCDyt43SbgtlOg5Yx-RiVoyw78GYRyThqsnk";

function installTriggers() {
  // Remove any old triggers on these two forms first so re-running this is safe.
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "onFormSubmit_WithPhoto" ||
        t.getHandlerFunction() === "onFormSubmit_NoAccount" ||
        t.getHandlerFunction() === "onFormSubmit") {
      ScriptApp.deleteTrigger(t);
    }
  });

  ScriptApp.newTrigger("onFormSubmit_WithPhoto")
    .forForm(FormApp.openById(FORM_WITH_PHOTO_ID))
    .onFormSubmit()
    .create();

  ScriptApp.newTrigger("onFormSubmit_NoAccount")
    .forForm(FormApp.openById(FORM_NO_ACCOUNT_ID))
    .onFormSubmit()
    .create();

  Logger.log("Both triggers installed.");
}

/** Decodes the webhook's returned files_base64 map and saves each file
 * into a per-leader subfolder of DELIVERABLES_FOLDER_ID. Returns that
 * subfolder's URL (or "" if there were no files to save). */
function saveDeliverablesToDrive(leaderName, filesBase64) {
  if (!filesBase64 || Object.keys(filesBase64).length === 0) return "";

  const parent = DriveApp.getFolderById(DELIVERABLES_FOLDER_ID);
  const subfolder = parent.createFolder(leaderName + " - " + new Date().toISOString().slice(0, 10));

  Object.keys(filesBase64).forEach(function (filename) {
    const bytes = Utilities.base64Decode(filesBase64[filename]);
    const blob = Utilities.newBlob(bytes, MimeType.PDF, filename);
    // MimeType.PDF is a safe default; Drive infers the real type from the
    // filename extension for display purposes regardless.
    subfolder.createFile(blob);
  });

  return subfolder.getUrl();
}

function normalizeColorScheme(raw) {
  raw = (raw || "").toLowerCase();
  return raw.indexOf("sage") > -1 ? "sage_forest" : "wine_gold";
}

/** Fetches the uploaded file's bytes and base64-encodes them, given the
 * value Google Forms puts in a File Upload response (a Drive file ID). */
function fetchPhotoAsBase64(fileId) {
  if (!fileId) return null;
  try {
    const file = DriveApp.getFileById(fileId);
    return {
      photo_base64: Utilities.base64Encode(file.getBlob().getBytes()),
      photo_filename: file.getName(),
    };
  } catch (err) {
    Logger.log("Could not fetch uploaded photo (" + fileId + "): " + err);
    return null;
  }
}

function sendToWebhook(payload, sheet, rowNum) {
  const options = {
    method: "post",
    contentType: "application/json",
    headers: { "X-Webhook-Secret": WEBHOOK_SECRET },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
  const status = response.getResponseCode();

  if (status === 200) {
    const result = JSON.parse(response.getContentText());
    const folderUrl = saveDeliverablesToDrive(payload.name, result.files_base64);

    sheet.getRange(rowNum, 9).setValue("Onboarded \u2713");
    sheet.getRange(rowNum, 10).setValue(result.live_url || "");
    sheet.getRange(rowNum, 11).setValue(result.qa_status || "");
    sheet.getRange(rowNum, 12).setValue(result.ai_review_status || "");
    sheet.getRange(rowNum, 13).setValue(folderUrl);
  } else {
    sheet.getRange(rowNum, 9).setValue("FAILED - check webhook logs");
    sheet.getRange(rowNum, 10).setValue("HTTP " + status);
  }
}

/** Form A: has the photo option and the "Business card style" question. */
function onFormSubmit_WithPhoto(e) {
  const v = e.namedValues;

  const cardStyle = (v["Business card style"] || [""])[0];
  const noPhoto = cardStyle.indexOf("No-photo") > -1;

  const payload = {
    name: (v["Full name"] || [""])[0],
    email: (v["Email address"] || [""])[0],
    phone: (v["Phone number"] || [""])[0],
    shaklee_storefront_handle: (v["Shaklee storefront handle"] || [""])[0],
    color_scheme: normalizeColorScheme((v["Color scheme for business cards"] || [""])[0]),
    bio: (v["Short personal note"] || [""])[0] || null,
    no_photo: noPhoto,
  };

  if (!noPhoto) {
    // Google Forms records an uploaded file's Drive ID in the response value.
    const fileId = (v["Headshot photo"] || [""])[0];
    const photo = fetchPhotoAsBase64(fileId);
    if (photo) {
      payload.photo_base64 = photo.photo_base64;
      payload.photo_filename = photo.photo_filename;
    }
  }

  const sheet = e.range.getSheet();
  const rowNum = e.range.getRow();
  sendToWebhook(payload, sheet, rowNum);
}

/** Form B: no Google account, no file upload, always the no-photo layout. */
function onFormSubmit_NoAccount(e) {
  const v = e.namedValues;

  const payload = {
    name: (v["Full name"] || [""])[0],
    email: (v["Email address"] || [""])[0],
    phone: (v["Phone number"] || [""])[0],
    shaklee_storefront_handle: (v["Shaklee storefront handle"] || [""])[0],
    color_scheme: normalizeColorScheme((v["Color scheme for business cards"] || [""])[0]),
    bio: (v["Short personal note"] || [""])[0] || null,
    no_photo: true,
  };

  const sheet = e.range.getSheet();
  const rowNum = e.range.getRow();
  sendToWebhook(payload, sheet, rowNum);
}
