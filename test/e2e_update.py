"""End-to-end test of self-update: loads a temp copy of the extension, bumps manifest.json on disk the way a
git pull would, and checks that the running extension reloads itself, re-injects into an open LinkedIn tab and
says so once. Then checks the NEW badge when a reload already happened for that version.

Run: python3 test/e2e_update.py   (CHROME=<path> picks a Chrome build)
"""

import json
import os
import pathlib
import shutil
import sys
import tempfile

from playwright.sync_api import sync_playwright

SRC = pathlib.Path(__file__).resolve().parent.parent
PAGE = """<!doctype html><html><body><main><div data-testid="lazy-column">
<div>12 people viewed your profile</div><div>Sam Lee commented on your post</div>
</div></main></body></html>"""

failures = []


def check(name, got, want):
    ok = got == want
    print(("PASS" if ok else "FAIL"), name, "got", repr(got), "want", repr(want))
    if not ok:
        failures.append(name)


def bump(ext, version):
    p = ext / "manifest.json"
    m = json.loads(p.read_text())
    m["version"] = version
    p.write_text(json.dumps(m, indent=2))


with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
    ext = pathlib.Path(tmp) / "ext"
    shutil.copytree(SRC, ext, ignore=shutil.ignore_patterns(".git", "promo", "test", "node_modules"))
    bump(ext, "1.0.0")
    launch = {"executable_path": os.environ["CHROME"]} if os.environ.get("CHROME") else {"channel": "chromium"}
    ctx = p.chromium.launch_persistent_context(
        str(pathlib.Path(tmp) / "profile"),
        headless=True,
        args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}"],
        **launch,
    )
    ctx.route("https://www.linkedin.com/**", lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE))
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
    ext_id = sw.url.split("/")[2]

    # Like a real install: with Developer mode off, Chrome disables an unpacked extension when it reloads itself.
    dev = ctx.new_page()
    dev.goto("chrome://extensions")
    dev.evaluate("() => new Promise(r => chrome.developerPrivate.updateProfileConfiguration({inDeveloperMode: true}, r))")
    dev.close()

    page = ctx.new_page()
    page.goto("https://www.linkedin.com/notifications/")
    page.wait_for_timeout(800)
    check("no toast on first install", page.evaluate("() => !!document.getElementById('linkedout-toast')"), False)

    opts = ctx.new_page()
    opts.goto(f"chrome-extension://{ext_id}/options.html")
    check("settings page shows the version", opts.text_content("#version"), "v1.0.0")
    check("same version: no reload", opts.evaluate("() => chrome.runtime.sendMessage({type: 'checkUpdate'})"),
          {"running": "1.0.0", "disk": "1.0.0", "reloading": False})

    # A git pull lands a new version; the next check reloads from disk (the options page closes with the reload).
    bump(ext, "1.0.1")
    opts.evaluate("() => { chrome.runtime.sendMessage({type: 'checkUpdate'}).catch(() => {}); }")
    page.wait_for_timeout(1500)

    opts = ctx.new_page()
    for _ in range(20):  # the extension is briefly unavailable while it reloads
        try:
            opts.goto(f"chrome-extension://{ext_id}/options.html")
            break
        except Exception as e:
            last = e
            opts.wait_for_timeout(500)
    else:
        raise last
    check("running the new version after self-reload", opts.text_content("#version"), "v1.0.1")
    check("open LinkedIn tab got the new script and the toast",
          page.evaluate("() => document.getElementById('linkedout-toast')?.textContent"), "LinkedOut updated to 1.0.1")
    check("one pill, still counting", page.evaluate("() => [...document.querySelectorAll('#linkedout-pill')].map(e => e.textContent)"),
          ["LinkedOut hid 1 · show"])
    page.reload()
    page.wait_for_timeout(800)
    check("toast only once per version", page.evaluate("() => !!document.getElementById('linkedout-toast')"), False)

    # If a reload for this disk version already happened and Chrome still runs the old one, show NEW instead of looping.
    bump(ext, "1.0.2")
    opts.evaluate("() => chrome.storage.local.set({reloadedFor: '1.0.2'})")
    check("already reloaded for this version: no loop",
          opts.evaluate("() => chrome.runtime.sendMessage({type: 'checkUpdate'})"),
          {"running": "1.0.1", "disk": "1.0.2", "reloading": False})
    check("NEW badge", opts.evaluate("() => chrome.action.getBadgeText({})"), "NEW")
    ctx.close()

print("FAILED:", failures) if failures else print("ALL PASS")
sys.exit(1 if failures else 0)
