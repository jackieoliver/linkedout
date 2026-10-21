const CHECKBOXES = ["enabled", "showHiddenPill", "hideSponsoredMessages", "hideInMail"];
const TEXTAREAS = ["keepPatterns", "hidePatterns"];

function render(s) {
  for (const id of CHECKBOXES) document.getElementById(id).checked = s[id];
  for (const id of TEXTAREAS) document.getElementById(id).value = s[id];
  for (const r of document.querySelectorAll("input[name=notificationMode]")) r.checked = r.value === s.notificationMode;
}

function read() {
  const s = {};
  for (const id of CHECKBOXES) s[id] = document.getElementById(id).checked;
  for (const id of TEXTAREAS) s[id] = document.getElementById(id).value;
  s.notificationMode = document.querySelector("input[name=notificationMode]:checked").value;
  return s;
}

function flash(msg) {
  const el = document.getElementById("status");
  el.textContent = msg;
  setTimeout(() => (el.textContent = ""), 1500);
}

chrome.storage.sync.get(LINKEDOUT_DEFAULTS, render);
document.getElementById("save").addEventListener("click", () => chrome.storage.sync.set(read(), () => flash("Saved")));
document.getElementById("reset").addEventListener("click", () => {
  render(LINKEDOUT_DEFAULTS);
  chrome.storage.sync.set(LINKEDOUT_DEFAULTS, () => flash("Reset"));
});
document.getElementById("version").textContent = "v" + chrome.runtime.getManifest().version;
