const WEBHOOK_URL = "https://leader-onboarding-pipeline.vercel.app/api/onboard";
const WEBHOOK_SECRET = "E0K8pVj7j8w5oZpA97pNrSdoiv14nRjy"; // keep whatever you already had set
const DELIVERABLES_FOLDER_ID = "1IFShUARasyGL21FAALhfXr9inbirO-5H";

const FORM_WITH_PHOTO_ID = "1OcsZTE2epS8Iwxz7JEZ0kMrixU30xVJHkCMA99ZxLkk";
const FORM_NO_ACCOUNT_ID = "10RodpCslCDyt43SbgtlOg5Yx-RiVoyw78GYRyThqsnk";

function installTriggers() {
  // Remove any old triggers with these handler names first so re-running is safe.
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var fn = t.getHandlerFunction();
    if (fn === "onFormSubmit" || fn === "onFormSubmit_WithPhoto" || fn === "onFormSubmit_NoAccount") {
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

function mimeTypeFor(filename) {
  if (filename.endsWith(".pdf")) return "application/pdf";
  if (filename.endsWith(".xlsx")) return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  return "application/octet-stream";
}

function saveFilesToDrive(leaderName, filesBase64) {
  const parent = DriveApp.getFolderById(DELIVERABLES_FOLDER_ID);
  const existing = parent.getFoldersByName(leaderName);
  const folder = existing.hasNext() ? existing.next() : parent.createFolder(leaderName);

  const blobs = [];
  for (const filename in filesBase64) {
    const bytes = Utilities.base64Decode(filesBase64[filename]);
    const blob = Utilities.newBlob(bytes, mimeTypeFor(filename), filename);
    folder.createFile(blob);
    blobs.push(blob);
  }
  return { folderUrl: folder.getUrl(), blobs: blobs };
}

function getPhotoBase64(headshotAnswer) {
  if (!headshotAnswer) return null;
  var idMatch = headshotAnswer.match(/[-\w]{25,}/); // Drive file IDs are long alphanumeric strings
  if (!idMatch) return null;
  try {
    var file = DriveApp.getFileById(idMatch[0]);
    var blob = file.getBlob();
    var bytes = blob.getBytes();
    // Vercel's request size limit is a hard 4.5MB and cannot be raised.
    // Base64 inflates size by about a third, so cap the raw photo well
    // under that, leaving room for the rest of the payload plus overhead.
    var MAX_PHOTO_BYTES = 3 * 1024 * 1024; // 3MB raw -> ~4MB base64
    if (bytes.length > MAX_PHOTO_BYTES) {
      return { tooLarge: true, sizeMB: (bytes.length / 1024 / 1024).toFixed(1) };
    }
    return {
      base64: Utilities.base64Encode(bytes),
      filename: file.getName(),
    };
  } catch (e) {
    return null; // file not accessible for some reason - treat as no photo, don't crash the whole submission
  }
}

function formatWarning(w) {
  // QA report items look like {deliverable, status, check} - description is in .check
  // AI report items look like {check, status, detail} - description is in .detail, category in .check
  if (w.detail !== undefined) {
    return `- [${w.check}] ${w.detail}`;
  }
  return `- [${w.deliverable}] ${w.check}`;
}

function sendWelcomeEmail(leaderName, leaderEmail, liveUrl, blobs) {
  const firstName = leaderName.split(" ")[0];
  const hasCard = blobs.some(function(b) { return b.getName().indexOf("Card_front") !== -1; });
  const subject = `Your Bob Ferguson Longevity toolkit is ready, ${firstName}!`;
  const attachmentLine = hasCard
    ? `Attached: your business card (front and back), your "How Do You Feel Today?" wellness checklist, and your prospect tracker.`
    : `Attached: your "How Do You Feel Today?" wellness checklist and your prospect tracker. Your business card isn't ready yet since I don't have a photo from you - send one over and I'll get it made.`;
  const body =
    `Hi ${firstName},\n\n` +
    `Welcome to the team! Everything's built and ready.\n\n` +
    `Your personal landing page is live: ${liveUrl}\n\n` +
    `${attachmentLine}\n\n` +
    `One thing worth knowing: your landing page doesn't have an email sign-up form connected yet. That's next on the list whenever you're ready, and I'll send a short doc on setting that up.\n\n` +
    `Let me know if anything looks off and I'll fix it.\n\n` +
    `Bob`;

  GmailApp.sendEmail(leaderEmail, subject, body, { attachments: blobs, name: "Bob Ferguson" });
}

function notifyBobForReview(leaderName, rowNum, sheetUrl, folderUrl, warnings) {
  const bobEmail = Session.getActiveUser().getEmail();
  const subject = `Needs review: ${leaderName}'s onboarding kit`;
  const relevant = (warnings || []).filter(function(w) { return w.status !== "PASS"; });
  const warningLines = relevant.length
    ? relevant.map(formatWarning).join("\n")
    : "(no specific details returned - check the Drive folder directly)";
  const body =
    `${leaderName}'s kit did not clear both automated checks and was held back.\n\n` +
    `What failed:\n${warningLines}\n\n` +
    `Sheet row: ${rowNum}\n` +
    `Sheet: ${sheetUrl}\n` +
    `Generated files (for review): ${folderUrl}\n\n` +
    `Nothing was published and no email was sent to her yet.`;
  GmailApp.sendEmail(bobEmail, subject, body);
}

/** Finds a column by its header text in row 1, creating it at the end of
 * the sheet if it doesn't exist yet. Safer than a fixed column number -
 * this sheet's actual header row has more real columns than originally
 * expected (a duplicate "Headshot photo" column exists, most likely from
 * the form's edit history - deleted/restored, then the "Business card
 * style" question inserted), so a fixed position can land on top of
 * genuine form data instead of safely past it. That's exactly what
 * happened before this fix: status text ended up visually under a
 * "Headshot photo" header. */
function getOrCreateColumn(sheet, headerName) {
  const lastCol = sheet.getLastColumn();
  const headerRow = sheet.getRange(1, 1, 1, Math.max(lastCol, 1)).getValues()[0];
  const existingIndex = headerRow.indexOf(headerName);
  if (existingIndex > -1) return existingIndex + 1; // 1-indexed

  const newCol = lastCol + 1;
  sheet.getRange(1, newCol).setValue(headerName);
  return newCol;
}

function normalizeColorScheme(raw) {
  raw = (raw || "").toLowerCase();
  return raw.indexOf("sage") > -1 ? "sage_forest" : "wine_gold";
}

/** Shared by both forms: sends the payload, saves deliverables, emails
 * the leader or notifies Bob, and writes status back using safe
 * header-based columns. */
function processSubmission(payload, sheet, rowNum) {
  const options = {
    method: "post",
    contentType: "application/json",
    headers: { "X-Webhook-Secret": WEBHOOK_SECRET },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
  const status = response.getResponseCode();

  const statusCol = getOrCreateColumn(sheet, "Pipeline Status");
  const urlCol = getOrCreateColumn(sheet, "Live URL");
  const qaCol = getOrCreateColumn(sheet, "QA / AI Review Status");
  const folderCol = getOrCreateColumn(sheet, "Deliverables Folder");

  if (status !== 200) {
    sheet.getRange(rowNum, statusCol).setValue("FAILED - check webhook logs");
    sheet.getRange(rowNum, urlCol).setValue("HTTP " + status);
    return;
  }

  const result = JSON.parse(response.getContentText());
  const saved = saveFilesToDrive(result.leader_name, result.files_base64 || {});

  sheet.getRange(rowNum, urlCol).setValue(result.live_url || "");
  sheet.getRange(rowNum, qaCol).setValue(result.qa_status + " / " + result.ai_review_status);
  sheet.getRange(rowNum, folderCol).setValue(saved.folderUrl);

  let statusNote;
  if (result.status === "shipped") {
    sendWelcomeEmail(result.leader_name, result.leader_email, result.live_url, saved.blobs);
    statusNote = "Onboarded \u2713 (emailed)";
  } else {
    statusNote = "NEEDS REVIEW - not shipped";
    notifyBobForReview(result.leader_name, rowNum, sheet.getParent().getUrl(), saved.folderUrl, result.warnings);
  }
  if (payload._photoTooLarge) {
    statusNote += ` (photo was ${payload._photoTooLargeSizeMB}MB, too large to process automatically - ask her to resend a smaller one)`;
  }
  sheet.getRange(rowNum, statusCol).setValue(statusNote);
}

/** Form A: has the photo option and the "Business card style" question. */
function onFormSubmit_WithPhoto(e) {
  const nv = e.namedValues;
  const get = (title) => (nv[title] && nv[title][0]) ? nv[title][0] : null;

  const colorScheme = normalizeColorScheme(get("Color scheme for business cards") || get("Color scheme"));

  const cardStyle = get("Business card style") || "";
  const noPhotoChosen = cardStyle.indexOf("No-photo") > -1;

  const photoInfo = noPhotoChosen ? null : getPhotoBase64(get("Headshot photo"));
  const photoTooLarge = photoInfo && photoInfo.tooLarge;

  const payload = {
    name: get("Full name"),
    email: get("Email address"),
    phone: get("Phone number"),
    shaklee_storefront_handle: get("Shaklee storefront handle"),
    color_scheme: colorScheme,
    photo_base64: (photoInfo && !photoTooLarge) ? photoInfo.base64 : null,
    photo_filename: (photoInfo && !photoTooLarge) ? photoInfo.filename : null,
    bio: get("Short personal note"),
    submitted_at: get("Timestamp"),
    no_photo: noPhotoChosen || !(photoInfo && !photoTooLarge),
    _photoTooLarge: !!photoTooLarge,
    _photoTooLargeSizeMB: photoTooLarge ? photoInfo.sizeMB : null,
  };

  processSubmission(payload, e.range.getSheet(), e.range.getRow());
}

/** Form B: no Google account, no file upload, always the no-photo layout. */
function onFormSubmit_NoAccount(e) {
  const nv = e.namedValues;
  const get = (title) => (nv[title] && nv[title][0]) ? nv[title][0] : null;

  const payload = {
    name: get("Full name"),
    email: get("Email address"),
    phone: get("Phone number"),
    shaklee_storefront_handle: get("Shaklee storefront handle"),
    color_scheme: normalizeColorScheme(get("Color scheme for business cards")),
    photo_base64: null,
    photo_filename: null,
    bio: get("Short personal note"),
    submitted_at: get("Timestamp"),
    no_photo: true,
    _photoTooLarge: false,
    _photoTooLargeSizeMB: null,
  };

  processSubmission(payload, e.range.getSheet(), e.range.getRow());
}
