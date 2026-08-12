# OPEN-63: FL's two data-completeness gaps — root cause, fix, and verification status

## Context

OPEN-63 flagged two independent, unrepaired-since-2026-08-03 FL gaps found by a fresh
`quality_check.py` Tier 1+2 sweep (`notes/az-wa-fl-tier1-tier2-500-sample-20260811.md`):

- **Gap 1 (Tier 1):** 34 of 1,931 live bill identifiers missing locally (1.76%).
- **Gap 2 (Tier 2):** 16/500 randomly-sampled bills with local=0 votes vs. live's 1–3.

This note records the root cause and fix for each, and — per the ticket's own evidence bar
("both counts demonstrably shrink on a fresh sweep, with a diagnosed root cause recorded") —
is explicit about which claim is backed by a real before/after count and which is not yet.

## Gap 1 — root-caused, fixed, and verified: SPB/HPB docket-stage duplicates

**Root cause:** FL Senate/House bills are filed under a temporary SPB/HPB (Senate/House
Proposed Bill) docket number, then replaced *in place* by a permanent SB/HB (or CS/SB, CS/HB)
number once formally read in. Confirmed live: `flsenate.gov/Session/Bill/2026/7000` (an SPB 7000
list entry's own URL) now renders as "CS/SB 7000", with no trace of the old identifier anywhere
on the site. Live's API, however, keeps the frozen SPB/HPB record permanently as its own entity
— so a naive Tier 1 identifier-set diff counts it as "missing" even though the bill is fully
present locally under its current bill number. This is the same shape as the pre-existing MA
HD/SD docket-vs.-bill-number case (`PLAN-coverage-completeness-check.md` §10).

**Fix:** added an `"fl": {"docket_prefixes": ("SPB", "HPB")}` entry to `quality_check.py`'s
`DOCKET_PREFIX_MAP`, reusing the same `split_missing_by_docket_prefix()` machinery MA already
uses. No scraper change needed — this is a false positive in the *quality check's own diffing
logic*, not a real scraper gap.

**Verified, with a real before/after count** (`logs/quality-check/fl_2026.log`, this checkout):

```
live=1931  local=1897  missing=34  extra=0  both=1897
...of which 34 are docket-stage duplicates, not a real gap (see PLAN-coverage-completeness-check.md §10) -- real gap: 0
missing by prefix: {'SPB': 34}
```

All 34 missing identifiers are SPB-prefixed — none are HPB or any other shape. Real gap: **0**.
This fully satisfies the evidence bar for Gap 1: the count demonstrably shrinks (34 → 0 real),
with a diagnosed and confirmed root cause.

## Gap 2 — root-caused and fixed at the code level; count reduction not yet re-verified

**Root cause:** `HouseSearchPage.accept_response()` in `openstates-scrapers/scrapers/fl/bills.py`
had two branches that unconditionally accepted the response (`return True`) on the very first
attempt: a `flhouse.gov` "Request Rejected" WAF page, and a search-results page that came back
with no matching results. Neither is the systemic stale-cookie case PR #5's `_FLHouseWAFSource`
already fixed (that case is a *permanent* rejection once a session cookie passes the ~1-hour
mark, now handled by dropping cookies before every request) — this is a rarer, one-off,
*transient* rejection or empty result unrelated to cookie age. Because `accept_response` gave up
immediately with zero retries at any level, a single bad request permanently and silently zeroed
that bill's House committee votes.

This is explicitly not OPEN-41's WAF-outage list (a specific 540-bill candidate set from the
2026-06-25/26 bad scrape, already verified closed) and not OPEN-27 (the "local has MORE votes
than live" direction) — it's the "local missing vs. live" gap both of those tickets' own
resolution notes anticipated as a separate, pre-existing problem.

**Fix:** `accept_response` now returns `False` (spatula's own retry signal — a fresh
`get_response()` call, re-triggering `_FLHouseWAFSource`'s cookie-drop) for both the WAF-rejected
and empty-results cases, up to `HOUSE_SEARCH_MAX_ATTEMPTS` (3) attempts, before falling back to
today's accept-and-skip behavior on the final attempt. The retry count is deliberately one less
than the source's own `retries` budget passed to spatula, so `accept_response` always gives up
before spatula's own `Page._fetch_data` retry loop would raise `RejectedResponse` and crash the
scrape. See `scrapers/fl/bills.py::HouseSearchPage.accept_response` and its class docstring/
comments for the full logic, and `tests/test_fl_bills.py` for unit coverage of all branches
(bill genuinely not found → no retry; WAF-rejected → retries then succeeds/gives up;
empty-results → retries then succeeds/gives up; real content on the first try → accepted
immediately). All 6 new tests pass.

**Not yet verified: an actual before/after count reduction.** This is a *scraper* fix, not a
quality-check false-positive fix like Gap 1 — the 16 bills already flagged as vote-missing in
the local DB were scraped *before* this fix existed, so no amount of re-running `quality_check.py`
against the current local DB will show improvement; only a fresh scrape of FL (which re-fetches
House committee vote pages using the new bounded-retry logic) can actually recover any of those
16 bills' votes and move the count. That rescrape has not been run as part of this ticket.

A fresh 500-bill Tier 2 baseline run during this investigation
(`logs/quality-check/fl_2026_tier2only.log`, this checkout) reproduces the same rate reported in
the ticket — **16/500** bills with local=0 votes vs. live — confirming the gap is still live and
at the same order of magnitude immediately before this fix, e.g.:

```
FL HB 4023 (2026): local is MISSING votes vs live  [local=0 live=1]
FL HB 285 (2026): local is MISSING votes vs live  [local=0 live=1]
```

(This is a fresh random sample, not necessarily the identical 500 bills or exact bill list from
the ticket's original 2026-08-11/12 sweep — random sampling means the specific bills drawn differ
run to run — but it lands on the same 16/500 rate, and HB 4023 independently recurs in both,
consistent with a stable, reproducible gap rather than sampling noise.)

## Evidence-bar status

| Gap | Root cause diagnosed | Fix implemented | Count demonstrably shrinks |
|---|---|---|---|
| 1 (Tier 1, 34 missing) | Yes — SPB/HPB docket lifecycle | Yes — `DOCKET_PREFIX_MAP` entry | **Yes** — 34 → 0 real, verified this session |
| 2 (Tier 2, 16/500 vote-missing) | Yes — unretried transient WAF/empty-result accept | Yes — bounded retry in `accept_response` | **Not yet** — requires a fresh FL rescrape post-merge |

## Recommendation

- Gap 1 can be considered closed on its own terms — root cause confirmed, fix in place, count
  verified at 0 real gap.
- Gap 2's fix is code-complete and unit-tested but should not be marked closed until a real FL
  rescrape (post-merge) is diffed against a fresh Tier 2 sample and the 16/500 figure is shown to
  have dropped. Re-run `quality_check.py --coverage fl 2026 --tier2-limit 500 --tier2-random`
  after that rescrape, the same way OPEN-41 verified its own fix with a real before/after count.

## References

- Jira: OPEN-63 (this ticket); OPEN-41 (Done, WAF-outage vote-gap, explicitly out of scope for
  this ticket's Gap 2); OPEN-27 (Done, "local has MORE votes" direction, not this ticket's
  concern)
- `notes/az-wa-fl-tier1-tier2-500-sample-20260811.md` — the sweep that surfaced both gaps
- `notes/tier1-coverage-all-jurisdictions-20260803.md` — first sighting of the 34-bill Tier 1 gap
- `notes/fl-tier2-500-bill-random-sample-20260803.md` — first sighting of the vote-missing gap
  (14/500 then)
- `PLAN-coverage-completeness-check.md` §10 — MA's HD/SD docket-vs.-bill-number precedent
- `quality_check.py` — `DOCKET_PREFIX_MAP`, `split_missing_by_docket_prefix()`
- `openstates-scrapers/scrapers/fl/bills.py` — `HouseSearchPage.accept_response`,
  `HOUSE_SEARCH_MAX_ATTEMPTS`
- `openstates-scrapers/tests/test_fl_bills.py` — unit coverage for `accept_response`'s
  retry/give-up branches
- `RUNBOOK.md` — "Florida House votes vanish on long scrapes" section, "Residual gap fixed in
  OPEN-63"
- Raw diff data (this checkout): `logs/quality-check/fl_2026.log` (Tier 1, post-fix),
  `logs/quality-check/fl_2026_tier2only.log` (Tier 2, 500-bill random, pre-rescrape baseline)
