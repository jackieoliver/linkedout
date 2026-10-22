// Self-update (same approach as French Weave): an updater job replaces this folder on disk, but Chrome keeps
// running the loaded copy. Compare the manifest on disk with the running one and reload from disk, once per disk
// version. If the running copy still differs after that, put "NEW" on the toolbar icon so the user reloads by hand.
const RELOADED_KEY = "reloadedFor";
const CHECK_ALARM = "linkedout-update-check";
const CHECK_MINUTES = 5;

async function diskVersion() {
  const res = await fetch(chrome.runtime.getURL("manifest.json"), { cache: "no-store" });
  return String((await res.json()).version || "");
}

async function checkUpdate() {
  try {
    const disk = await diskVersion();
    const running = chrome.runtime.getManifest().version;
    if (!disk || disk === running) {
      await chrome.action.setBadgeText({ text: "" });
      return { running, disk, reloading: false };
    }
    const { [RELOADED_KEY]: tried } = await chrome.storage.local.get(RELOADED_KEY);
    if (tried !== disk) {
      await chrome.storage.local.set({ [RELOADED_KEY]: disk });
      chrome.runtime.reload();
      return { running, disk, reloading: true }; // normally not reached: the worker is gone
    }
    await chrome.action.setBadgeBackgroundColor({ color: "#0A66C2" });
    await chrome.action.setBadgeText({ text: "NEW" });
    return { running, disk, reloading: false };
  } catch (e) {
    return { error: String(e) };
  }
}

chrome.alarms.create(CHECK_ALARM, { periodInMinutes: CHECK_MINUTES });
chrome.alarms.onAlarm.addListener((a) => a.name === CHECK_ALARM && checkUpdate());
chrome.runtime.onStartup.addListener(checkUpdate);
checkUpdate();

// After an update, LinkedIn tabs that were already open still run the old content script (now cut off from the
// extension, so it stops itself). Inject the new one so they pick up the update without a page refresh.
chrome.runtime.onInstalled.addListener(async ({ reason }) => {
  if (reason !== "update") return;
  const tabs = await chrome.tabs.query({ url: "https://www.linkedin.com/*" });
  for (const tab of tabs) {
    try {
      await chrome.scripting.insertCSS({ target: { tabId: tab.id }, files: ["content.css"] });
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["rules.js", "content.js"] });
    } catch {
      // tab closed or not ready; it gets the new script on its next load
    }
  }
});

// For tests and the settings page: run a check now.
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (msg?.type !== "checkUpdate" || sender.id !== chrome.runtime.id) return false;
  checkUpdate().then(reply);
  return true;
});
