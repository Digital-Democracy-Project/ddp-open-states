# Spec: what a CAMS-hosted headed Chromium session would need to look like for Michigan

**Status: proposal, not yet built or committed to.** Written after today's live findings
(`notes/mi-ip-reputation-block-confirmed-20260802.md`, and the follow-up correction in chat
history) and a read of GrantBot's existing headed-browser infrastructure in `ddp-agents`. This is
the requested specification for what Playwright/Chromium configuration would be needed to make a
CAMS-hosted approach work for MI — not a decision that this is the right approach yet.

## 0. Read this first: a cheaper, more targeted fix exists and should be ruled out before this

Before building new infrastructure, there's a concrete, already-diagnosed bug worth fixing on its
own merits: **MI's traffic presents three different, inconsistent browser identities across a
single reused cookie session**, independent of headless vs. headed:

1. The cookies (`x-bni-fpc`/`x-bni-rncf`) are minted by whatever Chromium version Playwright's
   headless `p.chromium.launch()` ships (`openstates-core/openstates/utils/cookie_provider.py:183`)
   — a genuine Chromium fingerprint.
2. `MIBillScraper.scrape()` then reuses those cookies with `headers={"User-Agent": USER_AGENT}`
   (`openstates-scrapers/scrapers/mi/bills.py:46,157`) — a **hardcoded string claiming to be
   Firefox 118 on Ubuntu Linux**, nothing to do with the Chromium that minted the cookies.
3. A separate code path (`get_session_list()`'s live-session check) picks a **third, random**
   User-Agent per attempt from a 7-entry pool (`openstates-core/openstates/scrape/base.py:82-95`,
   `get_random_user_agent()` — iPhone Safari, Windows Edge, Mac Safari, Windows Firefox, etc.),
   visible in today's logs as "Created fresh session with user agent: ...", a different one each
   run.

A single cookie session presenting as three unrelated browsers/OSes within one scrape attempt is
a textbook signal bot-mitigation products (Barracuda included) commonly flag — independent of,
and possibly sufficient on its own without, anything below. **Recommend fixing UA consistency
first** (one real UA, matching whatever actually minted the cookies, used everywhere for the
lifetime of that cookie pair) and re-testing live before committing to the infrastructure below.
It's a small, low-risk, same-day change; everything below is a real infrastructure project.

That said, here's the spec for the CAMS-hosted approach, since today's evidence (a headed browser
got through when headless-driven `scrapelib` didn't) is real and worth having ready regardless.

## 1. What today's evidence actually supports — and doesn't

- **Confirmed:** a fresh, headed Playwright/Chromium session got real content from
  `legislature.mi.gov` (homepage + the exact search URL the scraper was failing on) at a moment
  when the scraper's own headless-cookie-minted `scrapelib` traffic was blocked.
- **Also confirmed, same session:** that success was **temporary** — after the scraper's own
  failed burst ran, a *second* headed Playwright check got blocked too, and you independently got
  the CAPTCHA in your own real Chrome. This matches `mi_cookies.py`'s own docstring, already
  written 2026-08-01: heavy automated traffic degrades the whole IP's reputation, overriding
  cookie validity, for real browsers included.
- **Net: headed mode is necessary-but-maybe-not-sufficient.** It gets past whatever check flags
  headless Chromium specifically, but does not appear to get past a volume/reputation-based block
  once that's tripped. Nothing built to this spec should be sold internally as "the fix" —
  it's the next experiment worth running properly, with a real success criterion (does it hold up
  over a sustained period of real MI traffic, not just one clean request).

## 2. Playwright/Chromium configuration

- **`headless=False`**, `launch_persistent_context()` with a dedicated profile directory —
  **not** shared with GrantBot's OAuth profile (`ddp-agents`'s existing persistent context is
  keyed to `agents@digitaldemocracyproject.org`'s Google session; a separate `user_data_dir` for
  MI keeps the two from colliding or cross-contaminating cookies/local storage).
- **One consistent, real User-Agent string, matching this Chromium build's actual UA** (read it
  from `browser.version`/the page's own `navigator.userAgent` at launch, don't hardcode a
  separate string) — used for **every** request that reuses this session's cookies, including any
  handoff to a non-browser HTTP client. This is the single most important correctness property,
  whether or not the UA-consistency fix in §0 ships first.
- **Realistic viewport** (e.g. 1280×800 or similar — not headless Chromium's tiny default), a
  real **timezone** (`America/Detroit` or `America/New_York`) and **locale** (`en-US`) via
  `browser.new_context(viewport=..., timezone_id=..., locale=...)` — a persistent context with a
  UTC/blank timezone from a "Michigan legislature" cookie session is its own inconsistency signal.
- **`--disable-blink-features=AutomationControlled`** (already used by GrantBot's standalone
  `GrantBrowserManager`, not its production CAMS browser — worth carrying over here) so
  `navigator.webdriver` doesn't read `true`.
- **Decide explicitly whether this browser only mints cookies, or does the actual fetching too.**
  Two real options, not a foregone conclusion:
  - **(A) Cookie-minting only (current architecture, minimal change):** browser visits
    `legislature.mi.gov` once, hands `(x-bni-fpc, x-bni-rncf)` back to `scrapelib` as today. Cheap,
    but doesn't address a TLS/HTTP2-fingerprint-based check if Barracuda validates the *request's*
    handshake, not just its cookies — plausible given `scrapelib`/`requests`' TLS stack looks
    nothing like Chromium's regardless of which cookies are attached.
  - **(B) Route all MI HTTP traffic through the persistent browser** (`page.goto()` /
    `context.request` for both the search listing and every bill/PDF fetch), never handing off to
    `scrapelib` at all for MI. Directly addresses the fingerprint-mismatch theory, at real cost:
    every fetch becomes a full page load instead of a lightweight GET, MI's scraper logic (HTML
    parsing, PDF handling) would need reworking against Playwright's API instead of
    `requests`/`lxml`, and CAMS would need to expose something richer than "give me cookies" —
    more like "fetch this MI URL for me and return the body."
  - Recommend **(A) first** as the cheap test of the hypothesis (fixes §0 alongside it, gets a
    headed cookie-minting session in place, see if that alone holds up under real cadence over
    days, not just one clean check) before committing to (B)'s much larger scope.

## 3. Where/how this runs (per `ddp-agents`'s own precedent — see prior chat summary for detail)

- Must run against a **real, auto-logged-in macOS console session** on the Mac Studio — not
  Xvfb/VNC/a Docker display. GrantBot's Chromium already depends on this; so would MI's.
- Host it as a **system LaunchDaemon** (like `com.ddp.cams-server`, `com.ddp.openstates-api`), not
  a per-user GUI LaunchAgent — the exact incident `project_gui_agent_migration.md` documents
  (GUI LaunchAgents can't reload over SSH, took nightly scrapes down 4 days in 2026-07-04→07-08)
  would otherwise apply here too.
- **New integration surface, not free:** `ddp-sync`/`ddp-open-states` can't drive this directly —
  it needs a request/response contract against CAMS (an API endpoint: "get fresh MI cookies" for
  option A, or "fetch this MI URL" for option B), with its own timeout budget (a real page load is
  much slower than a raw HTTP GET) and error/retry semantics distinct from `mi_waf_get()`'s
  current in-process retry-once dance.
- **Resource budget:** GrantBot's browser workers are configured at 2048MB (`config/workers.mac.yaml`,
  vs. 512MB for non-browser workers) — budget similarly for a dedicated MI browser resource, on
  top of whatever GrantBot itself is already using.
- **Rate/pacing discipline at least as strict as OPEN-21's** (`MI_SCRAPELIB_RPM`, currently 10/min)
  applies here too, and arguably matters more — a real browser hitting MI too fast or on too
  regular an interval is not obviously less detectable than a rate-limited HTTP client, and we
  have zero evidence yet on what request pattern (not just volume) actually trips the reputation
  system. Whatever cadence is chosen should be treated as another experiment, not assumed safe
  just because it's "a real browser now."

## 4. Explicit open questions before committing engineering time

1. Does fixing UA consistency alone (§0), with no browser-hosting changes at all, already fix
   this? Genuinely unknown — worth testing first since it's nearly free.
2. Is the block driven by TLS/HTTP2 fingerprint (favors option B), a JS-execution/headless
   signal (favors option A), request cadence/volume (favors neither — needs pacing changes
   regardless), or some combination? No test run today isolated these variables from each other.
3. What request pattern from a real, headed, persistent-profile browser — not just "is it headed"
   — actually avoids re-tripping the reputation system over a sustained multi-day period? This is
   the real success criterion, and nothing built so far (today's manual checks included) has run
   long enough to answer it.
4. Given `mi_cookies.py`'s own docstring already flags "sustained high request volume against this
   specific site may make things worse, not better" — does adding a second, independent traffic
   source (a live-browser CAMS resource, in addition to the existing scrapelib path) risk making
   the *aggregate* footprint against this one IP worse, not better, especially during testing?

## References

- `notes/mi-ip-reputation-block-confirmed-20260802.md` — today's live findings this builds on
- `notes/mi-barracuda-bot-detection-analysis-20260801.md`,
  `notes/mi-barracuda-followup-tickets-20260802.md` — prior history
- `openstates-core/openstates/utils/mi_cookies.py`, `cookie_provider.py` — current cookie-minting
  mechanism and its own documented 2026-08-01 finding about IP-reputation overriding cookie
  validity
- `openstates-scrapers/scrapers/mi/bills.py`, `openstates-core/openstates/scrape/base.py` — the
  User-Agent inconsistency detailed in §0
- `ddp-agents`'s `src/cams/api/app.py`, `project_gui_agent_migration.md`,
  `config/workers.mac.yaml` — the existing headed-browser/LaunchDaemon precedent this spec adapts
- Jira: OPEN-19, OPEN-21, OPEN-22
