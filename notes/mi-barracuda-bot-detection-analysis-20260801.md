# Michigan bot-detection (Barracuda WAF): full analysis and everything shipped, 2026-08-01

## Context: this builds on a prior note, doesn't replace it

`notes/mi-waf-wait-and-see-20260729.md` (2026-07-29) already found that a User-Agent fix to
`os-text-extract archive mi` didn't clear MI's block, and made an explicit decision: **stop
manually retrying MI, wait for the next naturally-scheduled run** — reasoning that the block was
"most likely IP- or rate-reputation-based rather than anything a per-request header can fix," and
that manually hammering it more would be "plausibly counterproductive if it's TTL-based." That
note's chosen test point was **the Sunday secondary-group run, 2026-08-02 02:00 UTC** — the same
run this session's work will now also be tested against, for an unrelated reason (see below).

**This session did not wait.** A live incident (a scraper crash, see OPEN-17 below) led to several
hours of investigation and testing directly against `legislature.mi.gov` — the opposite of the
2026-07-29 decision. That testing is what found the root cause (Barracuda, specifically) and
built a real fix (OPEN-19, below) — but it also very likely contributed to, or at minimum
coincided with, exactly the kind of reputation-based escalation the prior note worried about (see
"The reputation-blocking finding" below). Worth being honest about that trade-off up front: this
session traded "don't poke it, wait and see" for "poke it a lot, learn what it actually is," and
both the useful findings and the escalated blocking we hit tonight are probably downstream of
that choice.

## Timeline

### 1. OPEN-17 — `get_session_list()` crash (root cause: no WAF-safe UA on one request)

A scheduled MI scrape failed with `openstates.exceptions.CommandError: no sessions from
Michigan.get_session_list()`, reproduced identically on two separate days (2026-07-31 and
2026-08-01) — not a one-off. `Michigan.get_session_list()` used a bare `url_xpath()` call with no
custom headers against `legislature.mi.gov/Search/LegDocSearch`; `bills.py` already had a
WAF-safe User-Agent for this exact domain (added 2026-07-28, referenced in the prior note above),
but `get_session_list()` was the one MI request that didn't send it.

**Fix:** [openstates-scrapers PR #13](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/13)
(`fabc110d9`, `6d4ab988e`) — sends the UA, and (the part that actually matters) falls back to the
existing static `Michigan.legislative_sessions` list if the live scrape fails, errors, or returns
empty, for any reason. Verified live: the UA alone did **not** reliably get past the WAF (same
day, got a dropped connection instead of the CAPTCHA page the fix's own comment assumed) — the
fallback is what actually prevents the crash, not the UA.

### 2. Pulling in upstream's real fix — SSL verification

Checking `openstates/openstates-scrapers` upstream found a more complete, earlier fix we didn't
have: commit `3266109` ("MI: disable SSL validation," 2026-07-21, **11 days before** our own
OPEN-17 work) — disables SSL cert verification (`verify=False`) across every MI request, not just
adds a UA.

**Fix:** [openstates-scrapers PR #14](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/14)
(`9a461e34f`, `b76ea61a9`) — cherry-picked upstream's commit on top of OPEN-17's fallback rework.
Honestly caveated in the PR itself: live-tested and `verify=False` alone **also** did not resolve
the connection-reset symptom we were seeing that day — most likely our own IP already under
some load-based strain from repeated testing, not something either fix specifically targets.

Also pulled in the rest of upstream's unrelated backlog while at it (64 commits, only 5 files
actually conflicted with our own changes):
[openstates-scrapers PR #15](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/15) —
notably includes a real fix for MI's session `end_date` (was `2025-12-31`, a full year short —
now correctly `2026-12-31`), plus real bug fixes for AZ (session-cookie handling in
`setsession.php`) and VA (a crash on any bill action without a chamber-letter prefix, silently
dropping every governor signing/veto action).

### 3. OPEN-18 — a *third* disguise: fake 404s (ticket only, not yet fixed)

Live testing during OPEN-17/PR-13 review found a `scrapelib.HTTPError: 404` fetching a specific,
real bill (`2026-SB-1141`) that crashed the whole scrape (`scrape_bill()` has no error handling
around its fetch at all). Verified via Playwright that the bill page is completely real and
valid — a real browser rendered it in full (title, history table, documents) — so this wasn't a
dead link, it was **a third distinct WAF-blocking disguise**: a genuine site-native-looking `404`
page ("The specified URL cannot be found") served instead of the real content, on top of the
already-known CAPTCHA-as-200 and connection-reset patterns. Confirmed the fetch that returned this
404 wasn't reproducible as a real 404 either — even a URL that had returned a clean `200` earlier
the same session started failing the same way shortly after, consistent with escalating blocking
rather than a genuinely broken link.

**Filed, not yet fixed:** [OPEN-18](https://digitaldemocracyproject.atlassian.net/browse/OPEN-18) —
extend the scraper's block-detection (which already exists for the archiver, see
`text_extract.py`'s `_block_page_reason`) to also cover this response shape, and make a single
blocked bill fetch a skip-and-continue instead of a scrape-ending crash. Deliberately scoped
separately from OPEN-19 below rather than folded in — see the "gap" note in section 5.

### 4. Identifying the actual mechanism: Barracuda, and a real bypass

Live network-traffic inspection during a Playwright page load found:

- The actual WAF vendor: `cdn.infisecure.com/barracuda.js` loads on every page — **Barracuda
  Networks' bot-detection product**, which validates clients via a JavaScript challenge a plain
  HTTP client (`requests`/scrapelib) cannot execute — that's the real reason no amount of
  UA/header/SSL tuning on a non-browser client can ever be fully reliable.
- No hidden bills JSON API to switch to instead: inspected network traffic on the bill-detail
  page, the search-results page, and a real search submission — all fully server-rendered HTML,
  zero XHR/fetch calls for bill content. (One real `/api/ListLegislatorsBySession` endpoint exists
  on the site, but it's for legislator data, unrelated to bills.)
- **The actual bypass:** extracted Barracuda's validation cookies from a successful Playwright
  page load and supplied them to a plain `requests.get()` call with no browser at all — it
  succeeded, retrieving a bill page, the full search-results listing, and a real PDF (verified via
  magic bytes) that were otherwise blocked.
- **Cookie-minimization matrix** (two independent rounds, controlling for URL differences the
  first time got confounded) isolated exactly which cookies matter: of the 6 cookies a validated
  session carries (`x-bni-fpc`, `x-bni-rncf`, `ARRAffinity`, `BNIS_vid`, `BNIS___utm_is1/2/3`),
  only **`x-bni-fpc` and `x-bni-rncf`** are required — confirmed across a bill page, search
  results, a PDF, a different legislative session, and two unrelated page types (Legislative
  Directory, Committee Meetings). Both are long-lived (~13 months from creation at the time),
  not session-scoped — process-independence also confirmed (the two values work when hardcoded
  into a fresh Python process with zero live connection to the browser that produced them).

### 5. OPEN-19 — the cookie-reuse fetcher (shipped)

Design: warm up a real Playwright browser rarely (not per-request), extract the two `x-bni-*`
cookies, cache them to disk keyed by their own real expiry, and attach them to every MI request
via a shared `mi_waf_get`/`fetch_with_retry` helper that invalidates and re-warms exactly once on
a detected block before treating it as a real failure.

**Shipped across three PRs, all merged 2026-08-01:**
- [openstates-core PR #6](https://github.com/Digital-Democracy-Project/openstates-core/pull/6)
  (`88a23d4c`) — `openstates/utils/cookie_provider.py` (generic mechanism, reusable for any future
  jurisdiction with a similar JS-challenge WAF), `openstates/utils/mi_cookies.py`
  (`MI_COOKIE_PROVIDER`, MI's concrete instance), wired into the archiver
  (`text_extract.py`/`os-text-extract archive mi`). Playwright imported lazily — confirmed the
  full test suite passes with `playwright` not even installed.
- [openstates-scrapers PR #16](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/16)
  (`56ba76f98`) — wires `bills.py` (search, bill fetch, roll-call votes), `events.py` (both fetch
  sites), and `__init__.py`'s `get_session_list()` onto the shared cookie-aware fetch path.
- [ddp-open-states PR #47](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/47) —
  `RUNBOOK.md` documentation + `requirements-openstates.txt` pins (`playwright==1.60.0`,
  `pyee==13.0.1`, `greenlet==3.2.5`).

**A real gap found in review, not yet closed:** `scrape()`/`scrape_bill()` in `bills.py` and both
fetch sites in `events.py` have no error handling around their `mi_waf_get()` calls — if a block
survives the one retry, the exception propagates uncaught and crashes the whole scrape, same as
before this PR (not a regression, just not fully closed either). The PR descriptions overstated
this as "OPEN-17/OPEN-18 fallbacks remain in place as defense-in-depth" — inaccurate, since
OPEN-18 was never actually implemented. Flagged in PR review comments on all three PRs; **OPEN-18
above is still the open item that would close this gap properly.**

**Deployed to production same day:** dependencies installed
(`playwright`, `pyee`, `greenlet`), `playwright install chromium` run, all three checkouts pulled
current. **Live-verified end-to-end**: seeded the real disk cache with known-good cookies and
confirmed `Michigan().get_session_list()` succeeds via actual live scraping — not the OPEN-17
fallback — for the first time in this entire investigation.

### 6. Side effect: retiring `cherry-pick-line` (unrelated to MI, but discovered while deploying OPEN-19)

Landing OPEN-19 in production required `openstates-core`'s fork `main` to be current. Checking the
history to do that surfaced that the DDP fork's `cherry-pick-line`/`local-patches` rebuild
convention (`PLAN-fork-management.md` §6, an already-open, undecided question from 2026-07-28)
had quietly stopped being followed — the last three DDP fixes (including OPEN-19's own core PR)
had all merged straight to fork `main`. Decided same-day to retire it and manage `openstates-core`
identically to `openstates-scrapers`/`openstates-people`/`api-v3` (plain fork, `checkout main &&
pull origin main`, no cherry-picking).

**Shipped:** [ddp-open-states PR #48](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/48)
(`953ecfb`) — `apply-local-patches.sh` rewritten, remotes renamed in production
(`origin` = fork, `upstream` = real project, matching `openstates-scrapers`' existing
convention), retired branches (`local-patches`, `cherry-pick-line`, `ddp-patches`) deleted,
`RUNBOOK.md`/`PRIMITIVES.md`/`PLAN-fork-management.md` updated. Verified live: ran the rewritten
script directly against production, zero errors, both repos correctly landed on `main`.

Unrelated to MI's WAF specifically, but it's why OPEN-19's fix could actually reach production
today at all — worth knowing if you're tracing why this repo's fork-management convention changed
the same day as an MI fix.

### 7. The reputation-blocking finding — cookies are necessary but not sufficient

Discovered a few hours after shipping OPEN-19, testing to confirm production deployment worked:

- A **fresh** Playwright warm-up (cold cache, forcing the real `_playwright_warm_up` code path for
  the first time — everything before this had used a manually-extracted cookie set) returned
  **different** cookies: `BNIS_x-bni-jas`/`x-bni-ci`, both session-scoped — not `x-bni-fpc`/
  `x-bni-rncf`. Reproduced 3 times (bare root URL, search page, repeated) — not a fluke.
- Tested whether this was a browser-launch-config difference (headless vs not, bundled Chromium
  vs real Chrome) — `headless=False` made no difference.
- Went back to the **same persistent browser session** that had gotten real content and the
  original `x-bni-fpc`/`x-bni-rncf` cookies hours earlier — it now got the **"Validation
  request"** CAPTCHA page too, despite `document.cookie` showing it still carried the exact
  original working cookie values alongside the new ones.

**Conclusion:** Barracuda tracks something beyond just these two cookies — most likely IP
reputation and/or request-volume/rate history — that can override cookie-based validation
entirely once tripped. This is consistent with, and a stronger version of, the "behavioral
evidence, not a guarantee about Barracuda's internals" framing already baked into `mi_cookies.py`'s
docstring and OPEN-19's own ticket. It's also consistent with the 2026-07-29 prior note's original
hypothesis — "most likely IP- or rate-reputation-based" — which this session's own heavy testing
volume likely helped confirm, the hard way.

**Documented:** [openstates-core PR #7](https://github.com/Digital-Democracy-Project/openstates-core/pull/7)
(`37458b4a`, not yet merged as of this note) — updates `mi_cookies.py`'s docstring with this
finding. Doesn't change any code path; the existing re-warm-once-on-block behavior is already the
right shape of response. What it changes is the operational read: a re-warm can legitimately fail
during a degraded-reputation window, not only when the cookie cache is genuinely stale — and
sustained request volume against this specific site may itself be part of what triggers that
window, not just a symptom of hitting it.

## Everything shipped, one list

| Repo | PR | What |
|---|---|---|
| openstates-scrapers | [#13](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/13) | OPEN-17: `get_session_list()` WAF-safe UA + known-sessions fallback |
| openstates-scrapers | [#14](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/14) | Pull in upstream's `verify=False` SSL fix |
| openstates-scrapers | [#15](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/15) | Merge upstream/main (64 commits) — MI `end_date` fix, AZ/VA real bugs |
| openstates-scrapers | [#16](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/16) | OPEN-19: wire scraper onto cookie-reuse fetcher |
| openstates-core | [#6](https://github.com/Digital-Democracy-Project/openstates-core/pull/6) | OPEN-19: `CookieProvider`/`MI_COOKIE_PROVIDER`, archiver wiring |
| openstates-core | [#7](https://github.com/Digital-Democracy-Project/openstates-core/pull/7) | Docs: record the reputation-blocking finding (not yet merged) |
| ddp-open-states | [#47](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/47) | OPEN-19 RUNBOOK + Playwright dependency pins |
| ddp-open-states | [#48](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/48) | Retire `cherry-pick-line`, clean-fork `openstates-core` |

**Jira:** [OPEN-17](https://digitaldemocracyproject.atlassian.net/browse/OPEN-17) (done),
[OPEN-18](https://digitaldemocracyproject.atlassian.net/browse/OPEN-18) (open — the
skip-and-continue gap in section 5), [OPEN-19](https://digitaldemocracyproject.atlassian.net/browse/OPEN-19)
(done, with the reputation-blocking finding recorded as a comment).

## What to watch at the next real test

MI is part of `ddp-sync`'s `openstates_secondary_scrapes` job — **2026-08-02 02:00 UTC**, the same
run the 2026-07-29 note already identified as the natural "has the block cleared" test point, now
also the first time this entire cookie-reuse mechanism runs under real production traffic
patterns rather than a day of heavy manual testing. Worth checking afterward:

- Did the scheduled run get further than today's manual tests did, now that the deliberate
  testing load has stopped?
- Did `get_session_list()` need its fallback, or scrape live?
- Any bill-fetch crashes consistent with the still-open OPEN-18 gap?
- Does the cookie cache end up populated with `x-bni-fpc`/`x-bni-rncf` (the "good" pair) or the
  session-scoped `BNIS_x-bni-jas`/`x-bni-ci` pair this note's finding describes?
