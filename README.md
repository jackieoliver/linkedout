# LinkedOut

Chrome extension that hides LinkedIn sponsored messages and low-value notifications, so only the ones that involve you stay visible.

- **Messages**: hides conversations tagged "Sponsored" (optionally all InMail).
- **Notifications**: by default shows only notifications matching a keep phrase (comments on your posts, mentions, replies, accepted invitations...). A second mode shows everything except hide phrases. Sponsored or promoted notifications are always hidden.
- Nothing is clicked, deleted or marked read: hidden items get a CSS class, and the "LinkedOut hid N · show" pill at the bottom left reveals them.
- Rules are editable on the settings page (click the toolbar icon). Settings sync through Chrome.

Built in October 2026 because nothing existing covered both: LinkedZen (closest) has fixed toggles and lists configurable notification blocking as roadmap only; LinkedBlock covers sponsored InMail but not notifications. LinkedIn also removed its own "Sponsored Messages" setting.

## Install

1. `git clone https://github.com/jackieoliver/linkedout.git` (a git clone, so updates can be pulled).
2. Chrome → `chrome://extensions` → turn on Developer mode, and leave it on (Chrome can switch off unpacked extensions when it is off).
3. "Load unpacked" → pick the cloned folder.

## Updates

Run `git pull --ff-only` in the folder now and then (by hand, or from a scheduled job such as cron or launchd) to update it. The extension checks every 5 minutes whether the `manifest.json` on disk has a newer version than the copy Chrome is running; if so it reloads itself once, re-injects into open LinkedIn tabs, and LinkedIn shows "LinkedOut updated to X" once. If the reload doesn't take, the toolbar icon shows NEW: click ↻ on `chrome://extensions`.

Releasing: bump `version` in `manifest.json` with every change to the extension files, or nothing reloads. `node --test test/` fails if the extension changed since `origin/main` without a version bump.

## Test

Icons: `python3 icons/make_icons.py`.

`node --test test/` runs the rule tests; `python3 test/e2e.py` loads the real extension in Playwright Chromium against fixture pages (settings page included); `python3 test/e2e_update.py` checks the self-update; `CHROME=<path> python3 test/e2e.py` runs it in a specific Chrome build. LinkedIn's markup changes often; selectors live at the top of `content.js`.
