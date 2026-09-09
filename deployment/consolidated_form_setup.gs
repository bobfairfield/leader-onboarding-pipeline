/**
 * One-time consolidated setup: run this once to do all of the following
 * on both onboarding forms:
 *   1. Add help text to "Shaklee storefront handle" walking a brand-new
 *      leader through finding their own storefront link.
 *   2. Add a new optional "Google Calendar booking link" question, if
 *      it doesn't already exist (safe to re-run - won't duplicate it).
 *   3. Generate pre-filled links with Bob's own note as the default for
 *      "Short personal note", logged at the end for you to grab and use
 *      wherever these forms are actually shared.
 *
 * Run runConsolidatedFormSetup() once, then check Executions for the
 * two pre-filled URLs to swap in on your /duplicate redirect page.
 */

const FORM_WITH_PHOTO_ID = "1OcsZTE2epS8Iwxz7JEZ0kMrixU30xVJHkCMA99ZxLkk";
const FORM_NO_ACCOUNT_ID = "10RodpCslCDyt43SbgtlOg5Yx-RiVoyw78GYRyThqsnk";

const STOREFRONT_HELP_TEXT =
  "Log in to your My Business site, find the \"My Storefront\" link on the " +
  "top ribbon, click on it, and then copy the link in the address bar.";

const CALENDAR_QUESTION_TITLE = "Google Calendar booking link (optional)";
const CALENDAR_HELP_TEXT =
  "Set up a free Appointment Schedule in your own Google Calendar and paste " +
  "the link here. Leave blank for now if you haven't set this up yet - " +
  "prospects will email you directly until you do.";

const DEFAULT_NOTE =
  "Hi, I'm [Your Name]. I share the same routine and research you just read about " +
  "because it's made a real difference in my own life, and I love helping others " +
  "find their own starting point. If you have questions, or just want to talk it " +
  "through before you order, reach out any time.";

function updateForm(formId) {
  const form = FormApp.openById(formId);
  const items = form.getItems();

  // 1. Storefront help text
  const handleItem = items.find(function (i) { return i.getTitle() === "Shaklee storefront handle"; });
  if (handleItem) {
    handleItem.setHelpText(STOREFRONT_HELP_TEXT);
    Logger.log("[" + formId + "] Storefront help text set.");
  } else {
    Logger.log("[" + formId + "] WARNING: 'Shaklee storefront handle' question not found.");
  }

  // 2. Calendar booking link question (skip if it already exists)
  const alreadyHasCalendarQ = items.some(function (i) { return i.getTitle() === CALENDAR_QUESTION_TITLE; });
  if (!alreadyHasCalendarQ) {
    form.addTextItem()
      .setTitle(CALENDAR_QUESTION_TITLE)
      .setHelpText(CALENDAR_HELP_TEXT)
      .setRequired(false);
    Logger.log("[" + formId + "] Calendar booking link question added.");
  } else {
    Logger.log("[" + formId + "] Calendar booking link question already exists, skipped.");
  }

  // 3. Pre-filled link with the default note
  const refreshedItems = form.getItems();
  const noteItem = refreshedItems.find(function (i) { return i.getTitle() === "Short personal note"; });
  let prefilledUrl = null;
  if (noteItem) {
    const formResponse = form.createResponse();
    const type = noteItem.getType();
    const typedItem = (type === FormApp.ItemType.PARAGRAPH_TEXT)
      ? noteItem.asParagraphTextItem()
      : noteItem.asTextItem();
    formResponse.withItemResponse(typedItem.createResponse(DEFAULT_NOTE));
    prefilledUrl = formResponse.toPrefilledUrl();
  } else {
    Logger.log("[" + formId + "] WARNING: 'Short personal note' question not found, no pre-filled link generated.");
  }

  return prefilledUrl;
}

function runConsolidatedFormSetup() {
  const withPhotoUrl = updateForm(FORM_WITH_PHOTO_ID);
  const noAccountUrl = updateForm(FORM_NO_ACCOUNT_ID);

  Logger.log("");
  Logger.log("=== DONE - pre-filled links to use going forward ===");
  Logger.log("WITH PHOTO FORM: " + withPhotoUrl);
  Logger.log("NO ACCOUNT FORM: " + noAccountUrl);
}
