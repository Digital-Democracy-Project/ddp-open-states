# MI WAF: a real browser session bypasses it cleanly — narrows the block down to client fingerprint, not just cookies

Follow-up to `notes/mi-ip-reputation-block-confirmed-20260802.md` and tonight's ScrapeBot
Phase 4b work (`ddp-agents`' `PLAN-scrapebot.md` §8.11). Earlier tonight, re-running the real
production MI scrape (`ddp-sync`'s `/trigger/openstates-scrape/mi`, with PR #26's proactive
ScrapeBot cookie pre-seed) failed twice in a row — once because ScrapeBot's own mint hit a
CAPTCHA it couldn't clear (a safety guardrail blocking the "Submit" click), and once even after
ScrapeBot successfully minted genuinely fresh cookies (`cookie_count=2`), the actual scrape
(`scrapelib`/`requests`) was still blocked on its very first request. A controlled repeat of the
exact scrape that had succeeded hours earlier (`test-mi-scrape-sample.py --mint-via-scrapebot
--count 5`, identical query, identical library versions, identical code path) also failed this
time — ruling out query differences and confirming the block is real, active, and worsening with
repeated attempts, not anything in our request construction.

## The test

Used the Playwright MCP browser directly (a separate browser context from both the shared CAMS/
GrantBot browser and the operator's own manual browsing) to navigate straight to the same 4 bills
`test-mi-scrape-sample.py` had scraped successfully earlier tonight (SB 0001, SR 0001, HR 0001,
HJR A — the "4 bills + 1 vote_event" from the `--count 5` run), with **no prior cookies, no
special warm-up, cold session**.

## Result: one CAPTCHA, solved on the first try, then nothing further

First navigation (`.../Bills/Bill?ObjectName=2025-SB-0001`) hit Barracuda's "User validation
required" challenge page — same page every blocked scrapelib request has hit all night. Critically:
**"Number of attempts left: 5"** — a full, un-depleted count, not a residual 0 or 1. Solved the
CAPTCHA (read the distorted text, typed it, clicked Submit) on the first attempt; the real bill
page loaded immediately (`Senate Bill 1 of 2025 - Michigan Legislature`).

**Every subsequent request in that same session succeeded with zero further validation
challenges** — navigating to 2 more bill pages (SR 0001, HR 0001) and fetching 9 real PDF
documents via in-page `fetch()` calls (not full navigations), all without hitting the CAPTCHA
again:

| Bill | Documents downloaded |
|---|---|
| SB 0001 | Introduced bill, As Passed by Senate, 3 fiscal agency analyses (5 files) |
| SR 0001 | Introduced resolution, Adopted resolution (2 files) |
| HR 0001 | Introduced resolution, Adopted resolution (2 files) |

All 9 verified as real, valid PDFs (`file` confirms `PDF document, version 1.x`), saved under
`_archive_scratch/mi-manual-pdf-test/` in this checkout. Stopped there (operator call) before
reaching the 4th bill (HJR A) — not needed to confirm the finding.

## What this narrows down

This is the cleanest evidence yet that the block is **not** a blanket IP-level ban (which would
have rejected this cold browser session too) and **not** primarily about cookie validity (ScrapeBot
proved minutes earlier that even genuinely fresh, successfully-minted cookies don't save a
`scrapelib`/`requests` call). What's different here:

- **The full session, cookies included, was obtained by solving the challenge from inside a real
  browser** — not handed to a separate plain HTTP client afterward.
- **Every request after that, including programmatic `fetch()` calls, still runs through Chrome's
  own network stack** — same TLS fingerprint, same HTTP/2 behavior, same header set a real browser
  produces, not `scrapelib`'s/`requests`' distinct client signature.

Put together, the most likely explanation: Barracuda validates a session via cookies obtained
after a challenge *and* keeps checking that the underlying client's network-level fingerprint
stays consistent with a real browser on every subsequent request. `scrapelib`/`requests` cookies
alone can't satisfy that second part no matter how they were obtained — the fingerprint mismatch
persists regardless of cookie freshness. A real browser (Playwright, or presumably ScrapeBot's own
shared browser if it made the actual page fetches itself, rather than just harvesting cookies for a
separate HTTP client) doesn't have that problem, because it never stops looking like a browser.

## Implication for ScrapeBot's design

ScrapeBot's whole mechanism — mint cookies via a real browser, hand them to `scrapelib` — targets
the cookie half of validation but not the fingerprint half. If this diagnosis is right, no amount
of fresher cookies fixes MI's block; the durable fix would need the actual page fetches themselves
to go through something with a real-browser fingerprint (e.g. routing MI's scrape requests through
a real browser/Playwright directly, or an HTTP client library that mimics browser TLS/HTTP
fingerprints such as `curl_cffi`), not just borrowing a browser's cookies for a plain HTTP client
afterward. Not scoped or built here — this is a diagnosis, not a fix; a fix of this shape is a
meaningfully bigger design change than tonight's cookie-pre-seed work and deserves its own
plan/ticket rather than a quick patch.

## Net

- Confirms (again) the block is real, active, and not solvable by cookie freshness alone.
- New, more specific finding: it's very likely at least partly a client-fingerprint check, not a
  blanket network-level ban — a cold real-browser session gets a full 5-attempt CAPTCHA budget and
  sails through cleanly once solved, while `scrapelib` fails immediately even with valid cookies.
- No ticket filed yet for the "route real fetches through a real browser" idea — flagging it here
  as the next real candidate fix, pending an explicit decision on scope (this is a materially
  bigger architectural change than anything shipped tonight).

## References

- `notes/mi-ip-reputation-block-confirmed-20260802.md` — the original IP-reputation-block finding this refines
- `notes/quality-check-vote-date-matching-fix-20260803.md`, `PLAN-open-states.md` §2.5 — the broader MI WAF saga
- `ddp-agents`' `scrapebot/plans/PLAN-scrapebot.md` §8.11 — tonight's Phase 4b live validation this follows up on
- `ddp-sync` PR #25/#26 — the single-jurisdiction wiring and proactive pre-seed this evening's real-scrape tests exercised
- Downloaded PDFs: `_archive_scratch/mi-manual-pdf-test/` (this checkout, untracked scratch area — not committed)
