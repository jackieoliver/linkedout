const CHECKBOXES = ["enabled", "showHiddenPill", "hideSponsoredMessages", "hideInMail", "smartNotificationBadge", "hideNotificationBadge", "hideMessagingBadge"];
// Each phrase list: <key>Patterns holds the checked phrases (what rules.js matches), <key>Extra the user's own.
const LISTS = ["keep", "hide"];

let settings = { ...LINKEDOUT_DEFAULTS };

const unique = (xs) => [...new Set(xs)];
const join = (xs) => xs.join("\n");

function phraseRow(list, phrase, checked, custom) {
  const label = document.createElement("label");
  const box = document.createElement("input");
  box.type = "checkbox";
  box.checked = checked;
  box.dataset.phrase = phrase;
  box.addEventListener("change", () => {
    const active = linkedoutPatterns(settings[list + "Patterns"]).filter((p) => p !== phrase);
    if (box.checked) active.push(phrase);
    save({ [list + "Patterns"]: join(active) });
  });
  const text = document.createElement("span");
  text.textContent = phrase;
  if (custom) text.className = "custom";
  label.append(box, text);
  if (custom) {
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "remove";
    remove.title = "Remove this phrase";
    remove.textContent = "×";
    remove.addEventListener("click", (e) => {
      e.preventDefault();
      save({
        [list + "Patterns"]: join(linkedoutPatterns(settings[list + "Patterns"]).filter((p) => p !== phrase)),
        [list + "Extra"]: join(linkedoutPatterns(settings[list + "Extra"]).filter((p) => p !== phrase)),
      });
    });
    label.append(remove);
  }
  return label;
}

function renderList(list) {
  const defaults = linkedoutPatterns(LINKEDOUT_DEFAULTS[list + "Patterns"]);
  const active = linkedoutPatterns(settings[list + "Patterns"]);
  // Phrases typed into the old free-text box count as the user's own.
  const all = unique([...defaults, ...linkedoutPatterns(settings[list + "Extra"]), ...active]);
  const box = document.getElementById(list + "List");
  box.replaceChildren(...all.map((p) => phraseRow(list, p, active.includes(p), !defaults.includes(p))));
}

function render() {
  for (const id of CHECKBOXES) document.getElementById(id).checked = settings[id];
  for (const r of document.querySelectorAll("input[name=notificationMode]")) r.checked = r.value === settings.notificationMode;
  for (const list of LISTS) renderList(list);
  const keepMode = settings.notificationMode === "keep";
  document.getElementById("hideBlock").classList.toggle("dim", keepMode);
}

function flash(msg) {
  const el = document.getElementById("status");
  el.textContent = msg;
  clearTimeout(flash.timer);
  flash.timer = setTimeout(() => (el.textContent = ""), 1500);
}

function save(changes, msg = "Saved") {
  settings = { ...settings, ...changes };
  render();
  chrome.storage.sync.set(changes, () => flash(msg));
}

for (const id of CHECKBOXES) {
  document.getElementById(id).addEventListener("change", (e) => save({ [id]: e.target.checked }));
}
for (const r of document.querySelectorAll("input[name=notificationMode]")) {
  r.addEventListener("change", () => save({ notificationMode: r.value }));
}
for (const form of document.querySelectorAll("form.add")) {
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const list = form.dataset.list;
    const input = form.querySelector("input");
    const phrase = input.value.trim().toLowerCase().replace(/\s+/g, " ");
    input.value = "";
    if (!phrase) return;
    save({
      [list + "Patterns"]: join(unique([...linkedoutPatterns(settings[list + "Patterns"]), phrase])),
      [list + "Extra"]: join(unique([...linkedoutPatterns(settings[list + "Extra"]), phrase])),
    }, "Added");
  });
}
document.getElementById("reset").addEventListener("click", () => {
  settings = { ...LINKEDOUT_DEFAULTS };
  render();
  chrome.storage.sync.set(LINKEDOUT_DEFAULTS, () => flash("Reset"));
});

chrome.storage.sync.get(LINKEDOUT_DEFAULTS, (stored) => {
  settings = stored;
  render();
});
document.getElementById("version").textContent = "v" + chrome.runtime.getManifest().version;
