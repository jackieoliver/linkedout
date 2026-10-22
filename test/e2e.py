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

# Top nav as LinkedIn ships it in 2026-10 (hashed classes; the count is a number-only span next to the icon).
FEED = """<!doctype html><html><head><title>(3) Feed | LinkedIn</title></head><body><header><nav><ul>
<li><a href="/messaging/" aria-label="Messaging, 1 new notification"><span><svg></svg><span class="kxhlu9">1</span></span><span><span>Messaging</span></span></a></li>
<li><a href="/notifications/" aria-label="Notifications, 2 new notifications"><span><svg></svg><span class="kxhlu9">2</span></span><span><span>Notifications</span></span></a></li>
</ul></nav></header><main>feed</main></body></html>"""

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
    body = FEED if "/feed" in url else MESSAGING if "/messaging" in url else ALL_NOISE if "allnoise" in url else NOTIFICATIONS
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

    badges = """() => Object.fromEntries([...document.querySelectorAll('nav a')].map(a =>
        [a.getAttribute('aria-label').split(',')[0], getComputedStyle(a.querySelector('.kxhlu9')).display !== 'none']))"""
    page.goto("https://www.linkedin.com/feed/")
    page.wait_for_timeout(800)
    # Smart count: of the 2 newest fixture notifications (profile views, Sam Lee's comment) only the comment counts.
    count = "() => document.querySelector('a[aria-label^=\"Notifications,\"] .kxhlu9').textContent"
    check("smart count shows only wanted new notifications", page.evaluate(count), "1")
    check("smart count visible, message count kept", page.evaluate(badges), {"Messaging": True, "Notifications": True})
    check("count stripped from tab title", page.title(), "Feed | LinkedIn")
    check("pill doesn't count nav badges", state(page)["pill"], None)

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
          "Nothing worth your time. LinkedOut hid 2 notifications.")
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
    opts.uncheck("#smartNotificationBadge")
    opts.uncheck("#hideNotificationBadge")
    opts.check("#hideMessagingBadge")
    opts.wait_for_timeout(300)  # settings save on change
    page.wait_for_timeout(500)
    s = state(page)
    check("live settings change hides InMail too", sorted(s["hidden"]), ["Brand Sender", "Recruiter Bo"])

    page.goto("https://www.linkedin.com/notifications/")
    page.wait_for_timeout(1200)
    s = state(page)
    page.goto("https://www.linkedin.com/feed/")
    page.wait_for_timeout(800)
    check("badge settings switch which count shows", page.evaluate(badges), {"Messaging": False, "Notifications": True})
    check("smart count off: LinkedIn's own number is back", page.evaluate(count), "2")
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

    # Phrase checkboxes: defaults start checked; unchecking one, adding and removing your own take effect live.
    keep_box = 'input[data-phrase="commented on your"]'
    check("default phrases are checked boxes", opts.is_checked(keep_box), True)
    check("hide list has checkboxes too", opts.locator("#hideList input[type=checkbox]").count() > 30, True)
    page.goto("https://www.linkedin.com/notifications/")
    page.wait_for_timeout(1200)
    opts.uncheck(keep_box)
    page.wait_for_timeout(500)
    check("unchecking a show phrase hides its notifications", "Sam Lee comm" in state(page)["hidden"], True)
    opts.fill("form[data-list=keep] input", "Brand New  Kind")
    opts.press("form[data-list=keep] input", "Enter")
    page.wait_for_timeout(500)
    check("added phrase keeps its notifications", "Some brand n" in state(page)["hidden"], False)
    opts.reload()
    check("added phrase persists, checked", opts.is_checked('input[data-phrase="brand new kind"]'), True)
    check("unchecked default persists", opts.is_checked(keep_box), False)
    opts.click('label:has(input[data-phrase="brand new kind"]) .remove')
    page.wait_for_timeout(500)
    check("removed phrase is gone", opts.locator('input[data-phrase="brand new kind"]').count(), 0)
    check("removing it hides again", "Some brand n" in state(page)["hidden"], True)

    # Toolbar popup: quick toggles save live, and the link opens the full settings page.
    pop = ctx.new_page()
    pop.set_viewport_size({"width": 300, "height": 420})
    pop.goto(f"chrome-extension://{ext_id}/popup.html")
    check("popup shows current settings", [pop.is_checked("#enabled"), pop.is_checked("#hideSponsoredMessages"),
                                           pop.is_checked("input[name=notificationMode][value=keep]")], [True, True, True])
    pop.check("#hideInMail")
    pop.wait_for_timeout(300)
    opts.reload()
    check("popup toggle reaches the settings page", opts.is_checked("#hideInMail"), True)
    if os.environ.get("POPUP_SHOT"):
        pop.screenshot(path=os.environ["POPUP_SHOT"], full_page=True)
    opts.close()  # Chrome focuses an already-open settings tab instead of opening one
    with ctx.expect_page() as full:
        pop.click("#all")
    full.value.wait_for_load_state()
    check("popup link opens the full settings page", full.value.url.endswith("/options.html"), True)

    ctx.close()

print("FAILED:", failures) if failures else print("ALL PASS")
sys.exit(1 if failures else 0)
