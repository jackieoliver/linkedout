// Self-update only reloads when manifest.json's version changes, so every extension change needs a bump.
const { test } = require("node:test");
const assert = require("node:assert");
const { execFileSync } = require("node:child_process");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const EXTENSION_FILES = ["manifest.json", "background.js", "content.js", "content.css", "rules.js", "options.html", "options.js", "popup.html", "popup.js", "icons/*.png"];

function git(...args) {
  return execFileSync("git", args, { cwd: ROOT, encoding: "utf8" });
}

test("extension changes since origin/main bump the manifest version", (t) => {
  let base;
  try {
    base = git("merge-base", "HEAD", "origin/main").trim();
  } catch {
    return t.skip("no origin/main to compare with");
  }
  const changed = git("diff", "--name-only", base, "--", ...EXTENSION_FILES).trim();
  if (!changed) return;
  const before = JSON.parse(git("show", `${base}:manifest.json`)).version;
  const now = require(path.join(ROOT, "manifest.json")).version;
  assert.notStrictEqual(now, before, `changed ${changed.split("\n").join(", ")} but version is still ${now}`);
});
