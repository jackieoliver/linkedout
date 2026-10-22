// Quick settings in the toolbar popup; the full settings page has the phrase lists.
const CHECKBOXES = ["enabled", "smartNotificationBadge", "hideSponsoredMessages", "hideInMail", "hideMessagingBadge"];

function render(s) {
  for (const id of CHECKBOXES) document.getElementById(id).checked = s[id];
  for (const r of document.querySelectorAll("input[name=notificationMode]")) r.checked = r.value === s.notificationMode;
  document.body.classList.toggle("off", !s.enabled);
}

function save(changes) {
  chrome.storage.sync.set(changes, () => {
    const el = document.getElementById("status");
    el.textContent = "Saved";
    clearTimeout(save.timer);
    save.timer = setTimeout(() => (el.textContent = ""), 1200);
  });
  if ("enabled" in changes) document.body.classList.toggle("off", !changes.enabled);
}

for (const id of CHECKBOXES) {
  document.getElementById(id).addEventListener("change", (e) => save({ [id]: e.target.checked }));
}
for (const r of document.querySelectorAll("input[name=notificationMode]")) {
  r.addEventListener("change", () => save({ notificationMode: r.value }));
}
document.getElementById("all").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
  window.close();
});

chrome.storage.sync.get(LINKEDOUT_DEFAULTS, render);
document.getElementById("version").textContent = "v" + chrome.runtime.getManifest().version;
