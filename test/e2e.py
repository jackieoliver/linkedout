"""End-to-end test: loads the real extension into Chromium and serves fixture pages at linkedin.com URLs.

Run: python3 test/e2e.py   (needs Python Playwright with its Chromium)
Set CHROME=/path/to/chrome to test a specific build instead, e.g. Chrome for Testing.
"""

import os
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

EXT = str(pathlib.Path(__file__).resolve().parent.parent)

NOTIFICATIONS = """<!doctype html><html><body><main><div data-testid="lazy-column">
<div>12 people viewed your profile: See who it is with Premium.</div>
<div>Sam Lee commented on your post: great work</div>
<div>Some brand new kind of notification</div>
<div>Promoted · Acme mentioned you</div>
<div></div>
</div></main>
<script>
setTimeout(() => {
  const col = document.querySelector("[data-testid='lazy-column']");
  const card = document.createElement("div");
  card.textContent = "Ana Ruiz mentioned you in a comment";
  col.insertBefore(card, col.lastElementChild);
  const noise = document.createElement("div");
  noise.textContent = "You appeared in 40 searches this week";
  col.insertBefore(noise, col.lastElementChild);
}, 400);
</script></body></html>"""

MESSAGING = """<!doctype html><html><body><main><ul class="msg-conversations-container__conversations-list">
<li class="msg-conversation-listitem"><div class="msg-conversation-listitem__link msg-conversations-container__convo-item-link msg-conversations-container__convo-item-link--active" data-thread="ad1"><span>Brand Sender</span><span>Sponsored</span><p>A senior developer, without the hire</p></div></li>
<li class="msg-conversation-listitem"><div class="msg-conversation-listitem__link msg-conversations-container__convo-item-link" data-thread="real1"><span>Alex Rivera</span><p>Hi, it's been a while</p></div></li>
<li class="msg-conversation-listitem"><div class="msg-conversation-listitem__link msg-conversations-container__convo-item-link" data-thread="real2"><span>Recruiter Bob</span><span>InMail</span><p>Exciting role</p></div></li>
</ul></main>
<script>
for (const link of document.querySelectorAll(".msg-conversation-listitem__link")) {
  link.addEventListener("click", () => {
    document.querySelectorAll(".msg-conversation-listitem__link").forEach(l => l.classList.remove("msg-conversations-container__convo-item-link--active"));
    link.classList.add("msg-conversations-container__convo-item-link--active");
    history.pushState({}, "", "/messaging/thread/" + link.dataset.thread + "/");
    window.opened = (window.opened || []).concat(link.dataset.thread);
  });
}
</script></body></html>"""

ALL_NOISE = """<!doctype html><html><body><main><div data-testid="lazy-column">
<div>12 people viewed your profile</div><div>You appeared in 40 searches this week</div>
</div></main></body></html>"""

failures = []


def check(name, got, want):
    ok = got == want
    print(("PASS" if ok else "FAIL"), name, "got", repr(got), "want", repr(want))
    if not ok:
        failures.append(name)


def state(page):
    return page.evaluate(
        """() => ({
            hidden: [...document.querySelectorAll('.linkedout-hidden')].map(e => e.textContent.trim().slice(0, 12)),
            pill: document.getElementById('linkedout-pill')?.textContent ?? null,
        })"""
    )


def route(r):
    url = r.request.url
    body = MESSAGING if "/messaging" in url else ALL_NOISE if "allnoise" in url else NOTIFICATIONS
    r.fulfill(status=200, content_type="text/html; charset=utf-8", body=body)


with sync_playwright() as p, tempfile.TemporaryDirectory() as profile:
    ctx = p.chromium.launch_persistent_context(
        profile,
        **({"executable_path": os.environ["CHROME"]} if os.environ.get("CHROME") else {"channel": "chromium"}),
        headless=True,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"],
    )
    ctx.route("https://www.linkedin.com/**", route)
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
    ext_id = sw.url.split("/")[2]

    page = ctx.new_page()
    print("browser", ctx.browser.version if ctx.browser else page.evaluate("() => navigator.userAgent"))

    page.goto("https://www.linkedin.com/notifications/")
    page.wait_for_timeout(1200)
    s = state(page)
    check("keep mode hides noise, unknown and promoted; keeps your post + late mention",
          sorted(s["hidden"]), sorted(["12 people vi", "Some brand n", "Promoted · A", "You appeared"]))
    check("pill text", s["pill"], "LinkedOut hid 4 · show")

    page.click("#linkedout-pill")
    shown = page.evaluate("() => [...document.querySelectorAll('.linkedout-hidden')].filter(e => getComputedStyle(e).display !== 'none').length")
    check("pill reveals hidden items", shown, 4)
    page.click("#linkedout-pill")

    page.goto("https://www.linkedin.com/messaging/")
    page.wait_for_timeout(800)
    s = state(page)
    check("messaging hides only the sponsored row", s["hidden"], ["Brand Sender"])
    check("leaves the hidden sponsored thread for the first real one", page.evaluate("() => window.opened"), ["real1"])
    check("url follows", page.evaluate("() => location.pathname"), "/messaging/thread/real1/")

    page.goto("https://www.linkedin.com/notifications/?allnoise=1")
    page.wait_for_timeout(800)
    check("empty state when everything is hidden", page.evaluate("() => document.getElementById('linkedout-empty')?.textContent"),
          "Nothing here needs you. LinkedOut hid 2 notifications.")
    page.goto("https://www.linkedin.com/notifications/")
    page.wait_for_timeout(1200)
    check("no empty state when something is kept", page.evaluate("() => !!document.getElementById('linkedout-empty')"), False)
    page.goto("https://www.linkedin.com/messaging/")
    page.wait_for_timeout(800)

    # Settings page: switch to hide mode, hide InMail, save, and see both take effect.
    opts = ctx.new_page()
    opts.goto(f"chrome-extension://{ext_id}/options.html")
    icons = opts.evaluate("""async () => {
        const m = chrome.runtime.getManifest();
        const out = {};
        for (const [size, path] of Object.entries(m.action.default_icon)) {
            const img = new Image();
            img.src = chrome.runtime.getURL(path);
            await img.decode();
            out[size] = img.naturalWidth;
        }
        return out;
    }""")
    check("toolbar icons load at their sizes", icons, {"16": 16, "32": 32, "48": 48, "128": 128})
    check("options page loads defaults", opts.is_checked("input[name=notificationMode][value=keep]"), True)
    opts.check("input[name=notificationMode][value=hide]")
    opts.check("#hideInMail")
    opts.click("#save")
    opts.wait_for_timeout(300)
    page.wait_for_timeout(500)
    s = state(page)
    check("live settings change hides InMail too", sorted(s["hidden"]), ["Brand Sender", "Recruiter Bo"])

    page.goto("https://www.linkedin.com/notifications/")
    page.wait_for_timeout(1200)
    s = state(page)
    check("hide mode shows unknown notification", "Some brand n" in s["hidden"], False)
    check("hide mode still hides listed noise", "12 people vi" in s["hidden"], True)

    opts.click("#reset")
    opts.wait_for_timeout(300)
    opts.reload()
    check("reset restores keep mode", opts.is_checked("input[name=notificationMode][value=keep]"), True)
    check("reset restores InMail off", opts.is_checked("#hideInMail"), False)

    ctx.close()

print("FAILED:", failures) if failures else print("ALL PASS")
sys.exit(1 if failures else 0)
