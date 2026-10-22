// Default rules and the pure matching logic. Shared by content.js, options.js and the tests.
// Patterns are case-insensitive substrings, one per line in the settings page.

const LINKEDOUT_DEFAULTS = {
  enabled: true,

  // "keep": show only notifications matching a keep pattern (everything else is hidden).
  // "hide": show everything except notifications matching a hide pattern.
  notificationMode: "keep",

  // Things that involve you directly. Keep wins over hide in both modes.
  keepPatterns: [
    "commented on your",
    "replied to your",
    "replied to you",
    "mentioned you",
    "tagged you",
    "accepted your invitation",
    "sent you a message",
    "messaged you",
    "endorsed you",
    "recommended you",
    "reposted your",
    "shared your post",
    "reacted to your comment",
    "your application",
    "invited you",
    "wants to connect",
  ].join("\n"),

  // Used in "hide" mode. Sponsored and promoted items are always hidden.
  hidePatterns: [
    "viewed your profile",
    "profile views",
    "appeared in",
    "search appearances",
    "trending",
    "for the first time in a while",
    "recently posted",
    "new jobs",
    "job alert",
    "jobs you may be interested in",
    "is hiring",
    "people you may know",
    "you might know",
    "premium",
    "top voice",
    "newsletter",
    "is live",
    "upcoming event",
    "work anniversary",
    "birthday",
    "started a new position",
    "might be interested",
    "suggested for you",
    "reacted to your post",
    "liked your post",
    "recommendations for you",
    "posted:",
    "reposted",
    "reacted to a post",
    "commented on",
    "could be your",
    "may want to connect",
    "celebrate",
    "people are engaging",
    "popular with your network",
    "new from",
    "reminder:",
    "you've got an invite",
  ].join("\n"),

  // Phrases the user added on the settings page (shown there even when unchecked).
  keepExtra: "",
  hideExtra: "",

  hideSponsoredMessages: true,
  hideInMail: false,
  showHiddenPill: true,

  // The red counts on the top nav. Most notifications are noise, so its count is hidden; message counts stay.
  hideNotificationBadge: true,
  // Instead, show how many of the new notifications pass the rules (reads the Notifications page in the background).
  smartNotificationBadge: true,
  hideMessagingBadge: false,
};

function linkedoutPatterns(text) {
  return (text || "")
    .split("\n")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

// Returns "keep" or "hide" for one notification card's text.
function linkedoutClassifyNotification(text, settings) {
  const t = (text || "").toLowerCase().replace(/\s+/g, " ");
  if (/\b(sponsored|promoted)\b/.test(t)) return "hide";
  if (linkedoutPatterns(settings.keepPatterns).some((p) => t.includes(p))) return "keep";
  if (settings.notificationMode === "keep") return "hide";
  return linkedoutPatterns(settings.hidePatterns).some((p) => t.includes(p)) ? "hide" : "keep";
}

// Returns true if a messaging conversation row should be hidden.
// labels: short standalone texts found inside the row (e.g. "Sponsored", "InMail").
function linkedoutHideConversation(labels, settings) {
  const ls = labels.map((l) => l.trim().toLowerCase());
  if (settings.hideSponsoredMessages && ls.some((l) => l === "sponsored" || l === "promoted")) return true;
  if (settings.hideInMail && ls.some((l) => l === "inmail")) return true;
  return false;
}

if (typeof module !== "undefined") {
  module.exports = { LINKEDOUT_DEFAULTS, linkedoutClassifyNotification, linkedoutHideConversation, linkedoutPatterns };
}
