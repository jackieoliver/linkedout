// Hides sponsored conversations on /messaging and low-value cards on /notifications.
// Hidden items get a class (never removed from the page), so the pill can reveal them again.

(() => {
  const HIDDEN = "linkedout-hidden";
  const REVEAL = "linkedout-reveal";
  const EMPTY_ID = "linkedout-empty";
  const ROW_LINK = ".msg-conversation-listitem__link, [class*='convo-item-link']";
  const ACTIVE_ROW_LINK = "[class*='convo-item-link--active']";

  // LinkedIn's class names change often; each list is tried in order and the text checks do the real work.
  const NOTIFICATION_CARD_SELECTORS = [
    "[data-testid='lazy-column'] > div",
    "article.nt-card",
    "div.nt-card",
    "[data-finite-scroll-hotkey-item] article",
    "[data-finite-scroll-hotkey-item]",
  ];
  const CONVERSATION_ROW_SELECTORS = [
    "li.msg-conversation-listitem",
    "li[class*='msg-conversation-listitem']",
    "ul[class*='msg-conversations-container'] > li",
  ];

  // After an update the background re-injects this script into open tabs; drop the old copy's pill first.
  document.getElementById("linkedout-pill")?.remove();

  let settings = { ...LINKEDOUT_DEFAULTS };
  let revealed = false;

  function findAll(selectors) {
    for (const sel of selectors) {
      const found = document.querySelectorAll(sel);
      if (found.length) return [...found];
    }
    return [];
  }

  // Short leaf texts inside a row, e.g. the "Sponsored" tag next to the sender name.
  function labelTexts(el) {
    const out = [];
    for (const node of el.querySelectorAll("span, p, div, li")) {
      if (node.children.length) continue;
      const t = node.textContent.trim();
      if (t && t.length <= 20) out.push(t);
    }
    return out;
  }

  function scan() {
    if (!settings.enabled) return;
    const path = location.pathname;
    if (path.startsWith("/notifications")) {
      const cards = findAll(NOTIFICATION_CARD_SELECTORS).filter((c) => c.textContent.trim()); // skip lazy-loading placeholders
      for (const card of cards) {
        card.classList.toggle(HIDDEN, linkedoutClassifyNotification(card.innerText || card.textContent, settings) === "hide");
      }
      updateEmptyState(cards);
    }
    if (path.startsWith("/messaging")) {
      const rows = findAll(CONVERSATION_ROW_SELECTORS).filter((r) => r.textContent.trim()); // skip virtualized placeholders
      for (const row of rows) {
        row.classList.toggle(HIDDEN, linkedoutHideConversation(labelTexts(row), settings));
      }
      leaveHiddenThread(rows);
    }
    updatePill();
  }

  // When every notification is hidden the column is blank; say so instead of looking broken.
  function updateEmptyState(cards) {
    let note = document.getElementById(EMPTY_ID);
    const allHidden = cards.length > 0 && cards.every((c) => c.classList.contains(HIDDEN));
    if (!allHidden) {
      note?.remove();
      return;
    }
    if (!note) {
      note = document.createElement("div");
      note.id = EMPTY_ID;
      cards[0].parentElement.before(note);
    }
    const text = `Nothing here needs you. LinkedOut hid ${cards.length} notifications.`;
    if (note.textContent !== text) note.textContent = text;
  }

  // LinkedIn opens the top conversation on /messaging; if that's a hidden (sponsored) one,
  // open the first visible conversation instead. Done once per hidden thread so it never fights the user.
  let leftThread = null;
  function leaveHiddenThread(rows) {
    if (revealed) return;
    const active = rows.find((r) => r.querySelector(ACTIVE_ROW_LINK));
    if (!active || !active.classList.contains(HIDDEN) || leftThread === location.pathname) return;
    const target = rows.find((r) => !r.classList.contains(HIDDEN));
    const link = target?.querySelector(ROW_LINK);
    if (!link) return;
    leftThread = location.pathname;
    link.click();
  }

  function updatePill() {
    const hiddenCount = document.querySelectorAll("." + HIDDEN).length;
    let pill = document.getElementById("linkedout-pill");
    const onPage = /^\/(notifications|messaging)/.test(location.pathname);
    if (!settings.showHiddenPill || !onPage || hiddenCount === 0) {
      pill?.remove();
      return;
    }
    if (!pill) {
      pill = document.createElement("button");
      pill.id = "linkedout-pill";
      pill.addEventListener("click", () => {
        revealed = !revealed;
        document.documentElement.classList.toggle(REVEAL, revealed);
        updatePill();
      });
      document.body.appendChild(pill);
    }
    const text = revealed ? `LinkedOut: showing ${hiddenCount} hidden · hide again` : `LinkedOut hid ${hiddenCount} · show`;
    if (pill.textContent !== text) pill.textContent = text;
  }

  function unhideAll() {
    for (const el of document.querySelectorAll("." + HIDDEN)) el.classList.remove(HIDDEN);
  }

  let queued = false;
  function queueScan() {
    // An updated or reloaded extension cuts this copy off (chrome.runtime.id goes away); stop and let the new copy run.
    if (!chrome.runtime?.id) {
      observer.disconnect();
      return;
    }
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      scan();
    });
  }

  function load(rescan) {
    chrome.storage.sync.get(LINKEDOUT_DEFAULTS, (stored) => {
      settings = stored;
      if (rescan) unhideAll();
      scan();
    });
  }

  // Say once per version that LinkedOut updated, so a silent self-update is visible. Not on first install.
  function announceUpdate() {
    const version = chrome.runtime.getManifest().version;
    chrome.storage.local.get("seenVersion", ({ seenVersion }) => {
      if (seenVersion === version) return;
      chrome.storage.local.set({ seenVersion: version });
      if (!seenVersion) return;
      const toast = document.createElement("div");
      toast.id = "linkedout-toast";
      toast.textContent = `LinkedOut updated to ${version}`;
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 6000);
    });
  }

  load(false);
  announceUpdate();
  // LinkedIn is a single-page app: rescan on DOM changes, which also covers route changes and infinite scroll.
  // Only childList changes are observed, so toggling classes here doesn't retrigger it.
  const observer = new MutationObserver(queueScan);
  observer.observe(document.body, { childList: true, subtree: true });
  chrome.storage.onChanged.addListener(() => load(true));
})();
