/**
 * One-time script: generates pre-filled form links where the "Short
 * personal note" question already contains Bob's own note as a default,
 * ready for the new leader to accept as-is or edit before submitting.
 *
 * Run generatePrefilledLinks() once, then check View > Logs (or
 * Executions) for the two URLs. Use those links - not the plain form
 * links - anywhere the forms are shared (the /duplicate redirect page,
 * etc.), since only the pre-filled link carries the default text.
 */

const FORM_WITH_PHOTO_ID = "1OcsZTE2epS8Iwxz7JEZ0kMrixU30xVJHkCMA99ZxLkk";
const FORM_NO_ACCOUNT_ID = "10RodpCslCDyt43SbgtlOg5Yx-RiVoyw78GYRyThqsnk";

const DEFAULT_NOTE =
  "Hi, I'm [Your Name]. I share the same routine and research you just read about " +
  "because it's made a real difference in my own life, and I love helping others " +
  "find their own starting point. If you have questions, or just want to talk it " +
  "through before you order, reach out any time.";

function buildPrefilledUrl(formId) {
  const form = FormApp.openById(formId);
  const items = form.getItems();
  const noteItem = items.find(function (i) { return i.getTitle() === "Short personal note"; });

  if (!noteItem) {
    Logger.log("Could not find a 'Short personal note' question on form " + formId + " - check the exact title matches.");
    return null;
  }

  const formResponse = form.createResponse();
  // Works whether the question is set up as Short Answer or Paragraph.
  const type = noteItem.getType();
  const typedItem = (type === FormApp.ItemType.PARAGRAPH_TEXT)
    ? noteItem.asParagraphTextItem()
    : noteItem.asTextItem();
  const itemResponse = typedItem.createResponse(DEFAULT_NOTE);
  formResponse.withItemResponse(itemResponse);

  return formResponse.toPrefilledUrl();
}

function generatePrefilledLinks() {
  const withPhotoUrl = buildPrefilledUrl(FORM_WITH_PHOTO_ID);
  const noAccountUrl = buildPrefilledUrl(FORM_NO_ACCOUNT_ID);

  Logger.log("=== WITH PHOTO FORM (pre-filled) ===");
  Logger.log(withPhotoUrl);
  Logger.log("");
  Logger.log("=== NO ACCOUNT FORM (pre-filled) ===");
  Logger.log(noAccountUrl);
}
