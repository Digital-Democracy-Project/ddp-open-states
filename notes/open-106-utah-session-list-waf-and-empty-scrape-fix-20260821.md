# OPEN-106: Utah `get_session_list()` failure — root cause, fix, and live verification

## Context

The weekly `ut` scrape (`ddp-sync`'s `openstates_scrape.secondary` group, Sundays 02:00 UTC)
failed on 2026-08-15 with:

```
openstates.exceptions.CommandError: no sessions from Utah.get_session_list()
```

auto-filing OPEN-106 within ~20 seconds via the `auto-failure` Jira pipeline. The ticket's
original theory ("page structure changed") turned out to be wrong — this note documents the
actual two-stage root cause, the fix, and the live re-verification after merge.

## Root cause

Two distinct, compounding failure modes, both confirmed against the real `le.utah.gov` site,
not just from reading the traceback:

**1. `Utah.get_session_list()` (`scrapers/ut/__init__.py`) had no resilience of its own.** It
called `url_xpath()` with no `user_agent=`, which falls back to `requests`' bare default UA. A
direct repeated fetch of `https://le.utah.gov/bills/billSearch.jsp` with that default header
came back `200 OK` with a 246-byte `"Request Rejected... Your support ID is..."` WAF page —
zero sessions, no exception raised, nothing for `check_session_list()` to distinguish from a
site with an empty page. The same endpoint is *also* independently flaky/rate-limited on top of
that — a bare-UA request to `billSearch.jsp` failed twice then succeeded a third time with no
change at all, and `billlist.jsp?session=2025S2` failed 5/5 with scrapelib's own default UA
(`"scrapelib 2.2.0 python-requests/2.32.5"`) in one test run while the *same* UA against
`billlist.jsp?session=2026GS` succeeded — so this isn't a clean "UA X is always blocked" rule,
just a WAF that's meaningfully more likely to reject a `python-requests`-shaped UA than a
browser-shaped one.

**2. An incremental scrape of a closed session can legitimately yield zero bills, and that
aborted the whole run.** The weekly run scrapes every "active" session in one invocation —
currently `2025S2` (closed special, ended 2025-12-12) and `2026` (current). Every `2025S2`
bill's most recent action predates the incremental `start=` cutoff, so `UTBillScraper.scrape()`
correctly filtered all of them out via the existing `scrape_bill_details_from_api()` skip logic
— but zero net output from that session's `do_scrape()` call tripped `openstates-core`'s blanket
`ScrapeError("no objects returned...")`, and nothing in the CLI's per-session loop
(`openstates/cli/update.py`'s `do_scrape()`) catches that per-session, so it aborted the entire
run before `2026` — queued right after in the same `active_sessions` loop — was ever reached.
This matches the two-stage production trace exactly (`CommandError` from stage 1 masked what
would otherwise have hit stage 2 first, on a run where `get_session_list()` happened to fail).

## Fix

[PR #36](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/36), merged
2026-08-21 (`chore/OPEN-106` → `main`):

- `get_session_list()` now sends a browser-shaped User-Agent (`get_random_user_agent()`, the
  same helper FL/MI already use for their own bot-detection issues) and retries up to 3× with
  backoff, raising a specific `ScrapeError` naming the last real failure if every attempt still
  comes up empty — instead of silently falling through to `check_session_list()`'s generic,
  undiagnostic message.
- `UTBillScraper` now defaults to the same browser-shaped UA for its own requests, since
  scrapelib's own default UA is confirmed live to be rejected by the same WAF often enough to
  matter.
- `UTBillScraper.scrape()` now tracks candidates-seen vs. objects-yielded. When it found real
  bill-list candidates (proving `billlist.jsp` parsed fine — not a page-structure break) but
  every one predates the incremental cutoff, it raises `EmptyScrape` — the existing,
  designed-for-this escape hatch in `openstates-core`'s `Scraper.do_scrape()` — instead of
  falling through to the blanket `ScrapeError`. A session whose list page itself came back
  empty (a real failure) is unchanged and still raises normally; this relies on
  `scrape_bill_details_from_api()`'s `skip=True` only ever firing after it successfully parses
  a bill's `actionHistoryList` and confirms the date, so a genuine per-bill failure (malformed
  page, parse error) still raises out of `scrape()` rather than being swallowed. Covered by a
  dedicated regression test (`test_incremental_scrape_with_a_real_failure_does_not_raise_empty_scrape`).

Sent through `/pm-review` once before merge. Folded in: a real bug it caught (the retry loop
could report a stale exception from an earlier attempt as the "last error" even when a later
attempt failed cleanly — `last_error` is now reset every attempt) and three regression tests it
flagged as missing (real per-bill failure isn't swallowed as `EmptyScrape`; zero candidates
isn't either; every retry attempt sends the UA, not just the first). Explicitly did not fold in:
redesigning the scraper's boolean skip signal into an explicit sentinel, or adding WAF/rejection-
page detection to per-bill detail fetches — both are speculative hardening beyond this ticket's
confirmed failure mode, not fixes for real bugs found here. Out of scope, left as pre-existing:
`le.utah.gov`'s independent flakiness/rate-limiting beyond what a UA change fixes — a session
whose list page itself comes back genuinely empty still surfaces as the ordinary "no objects
returned" `ScrapeError`, unchanged and intentionally not masked.

## Live verification (post-merge, 2026-08-21)

Pulled `main` into `ddp-open-states-dev`'s `openstates-scrapers` checkout and ran the real
production-shaped command in the isolated dev environment (`source activate-dev.sh` — dev-only
Postgres, no Slack/CAMS side effects):

```bash
os-update ut --scrape bills start=2026-08-09T01:02:43
```

— no session specified, so it goes through the real `get_session_list()` →
`check_session_list()` → per-session `do_scrape()` loop, exactly like the weekly scheduled run.

Result: exit code 0, clean completion report, no `ScrapeError`, no `CommandError`, no traceback.

```
23:51:33 WARNING openstates: no session provided, using active sessions: {'2025S2', '2026'}
23:51:33 INFO scrapelib: GET - 'https://le.utah.gov/billlist.jsp?session=2025S2'
  ... (5 bills checked: HB2001, HJR201, SB2001, SB2002, SJR201)
23:51:43 WARNING openstates: UTBillScraper raised EmptyScrape, continuing without any results
23:51:43 INFO scrapelib: GET - 'https://le.utah.gov/billlist.jsp?session=2026GS'
  ... (1,021 unique bills checked across both sessions total)
00:25:46 WARNING openstates: UTBillScraper raised EmptyScrape, continuing without any results

bills scrape:
  duration:  0:34:13.457397
  objects:
```

`get_session_list()` succeeded on its first attempt (no retry warnings logged — the UA fix
alone was enough this run). `2025S2` raised `EmptyScrape` and the run continued into `2026GS`
exactly as designed — this is the same shape of situation that crashed the scrape on
2026-08-15, now completing cleanly instead of aborting. Both sessions ultimately reported zero
new activity since the `start=` cutoff (a real data fact for this run, not a fix artifact — no
new legislative activity in either session since 2026-08-09), so no bills/votes were imported;
`--scrape` only was used (no `--import`), so nothing was written to any database, dev or prod.

## References

- PR: [Digital-Democracy-Project/openstates-scrapers#36](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/36)
- Jira: OPEN-106 (In Review → closed out by this note; merged by the user, not self-merged, per
  standing process)
- Related known gotcha: see `RUNBOOK.md`'s "Known gotchas" → "Utah blocking..." entry
