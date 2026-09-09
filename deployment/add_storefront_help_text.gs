/**
 * One-time script: adds help text to the "Shaklee storefront handle"
 * question on both onboarding forms, walking a brand-new leader through
 * exactly how to find their own storefront link. Assumes zero existing
 * Shaklee back-office knowledge, per Bob's instruction that this system
 * has to work for someone who's never touched the mechanics before.
 *
 * Run addStorefrontHelpText() once. Safe to re-run - it just overwrites
 * the help text each time rather than duplicating anything.
 */

const FORM_WITH_PHOTO_ID = "1OcsZTE2epS8Iwxz7JEZ0kMrixU30xVJHkCMA99ZxLkk";
const FORM_NO_ACCOUNT_ID = "10RodpCslCDyt43SbgtlOg5Yx-RiVoyw78GYRyThqsnk";

const STOREFRONT_HELP_TEXT =
  "Log in to your My Business site, find the \"My Storefront\" link on the " +
  "top ribbon, click on it, and then copy the link in the address bar.";

function setStorefrontHelpText(formId) {
  const form = FormApp.openById(formId);
  const items = form.getItems();
  const handleItem = items.find(function (i) { return i.getTitle() === "Shaklee storefront handle"; });

  if (!handleItem) {
    Logger.log("Could not find 'Shaklee storefront handle' question on form " + formId + " - check the exact title matches.");
    return;
  }

  handleItem.setHelpText(STOREFRONT_HELP_TEXT);
  Logger.log("Updated help text on form " + formId);
}

function addStorefrontHelpText() {
  setStorefrontHelpText(FORM_WITH_PHOTO_ID);
  setStorefrontHelpText(FORM_NO_ACCOUNT_ID);
  Logger.log("Done - both forms updated.");
}
