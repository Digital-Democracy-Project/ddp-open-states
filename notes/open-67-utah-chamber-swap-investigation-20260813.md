# OPEN-67: Utah House/Senate chamber swap investigation

## Context

`ddp-broker-py`'s dev database showed every Utah `Motion` whose own text starts with "House" or
"Senate" filed under the *opposite* chamber for every sync between 2026-03-05 and 2026-04-26
(100% backwards, every date, no exceptions), then 100% correct from 2026-06-15 onward. All other
tracked jurisdictions (VA, FL, WA, MI, US, AZ) showed zero mismatches across the same window --
this is Utah-specific. This ticket asks what changed between 2026-04-26 and 2026-06-15 that fixed
it, whether that fix was deliberate, whether other fields were affected, and to document the root
cause. `ddp-broker-py` itself is not present in this workspace (see "Scope boundary" below).

This is Phase 1 (research, in `ddp-open-states`) -- everything this repo can verify. It builds on
`OPEN-67-architecture-assessment-20260813.md` (produced earlier the same day) and goes further:
resolves a contradiction that assessment left open, checks `openstates-core`'s actual importer
code (not just its static metadata), and runs a live, current-state check against the specific
bug bills using `quality_check.py`'s new `--bill-ids` option.

## Method

1. **`openstates-scrapers` git archaeology** (repeat/confirm of the prior assessment, plus new
   analysis): full upstream history via a temporary read-only `upstream` remote at
   `github.com/openstates/openstates-scrapers` (fetched, inspected, removed -- no repo state
   changed), tracing every commit touching `scrapers/ut/bills.py` and every chamber-mapping site
   in the file at every point in its history.
2. **`openstates-core` git archaeology** (new -- the prior assessment only checked the static
   `metadata/data/ut.py` file): same temporary-upstream-remote technique against
   `github.com/openstates/openstates-core`, this time against the actual import-time chamber
   resolution code (`openstates/importers/vote_events.py`, `openstates/importers/organizations.py`,
   `openstates/scrape/popolo.py`, `openstates/scrape/bill.py`, `openstates/scrape/vote_event.py`),
   full history 2025-10-01 through 2026-08-01.
3. **Live-API spot check** (new): added a `--bill-ids JURISDICTION SESSION IDS` option to
   `quality_check.py` (reusing its existing `fetch_bill()`/`compare_bills()` machinery --
   `OPENSTATES_API_KEY` is present in this environment, so no operator input was needed) and ran
   it against the 11 bills the ticket cites (HB392, HB223, HB136, HB68, HB32, HB209, HB479,
   SB189, SB234, SB194, SB153), plus a new `motion_text_chamber_mismatch()` check that reproduces
   the ticket's own methodology directly: does each vote's `motion_text` ("House/ passed 3rd
   reading", "Senate/ failed", ...) agree with its recorded `organization.classification`?
4. Direct query against this repo's local Postgres replica (`localhost:5433/openstates`) to
   establish what historical data is actually available here.

## Findings

### 1. This repo's local DB has no data from the bug window

```
select min(created_at), max(created_at), count(*) from opencivicdata_voteevent v
  join ... where jurisdiction ilike '%utah%'
→ 2026-06-14 02:10:56 through 2026-06-22 20:00:48, 1917 rows
```

Utah vote data in this repo's replica starts **2026-06-14** -- two days *before* the fix commit
below even merged, and entirely after the reported 2026-03-05–2026-04-26 bug window. This repo
cannot replay the historical comparison locally; everything below is either (a) full-history git
archaeology of the code this repo vendors, or (b) a live check against the real production API's
*current* state.

### 2. `openstates-scrapers`: chamber-mapping logic has never been reversed, and the one in-window
   change structurally could not have produced the reported votes at all

Full upstream history of `scrapers/ut/bills.py`, 2025-10-06 through 2026-08-12:

| Date | Commit | What it touched |
|---|---|---|
| 2025-10-06 → 2025-12-30 | 5 commits | Slugs, committee names/referrals, doc URLs, lint -- unrelated |
| **2026-01-01 → 2026-04-12** | **(none)** | No changes to this file for ~3.5 months |
| 2026-04-13 | `a10522814` | SSL verification bypass only -- no chamber logic |
| **2026-04-14 → 2026-06-15** | **(none)** | No changes |
| 2026-06-16 | `5e345a2d0` (PR #5695) | The only candidate -- see below |

Every chamber-mapping site in this file maps the same way at every point in history --
House → `lower`, Senate → `upper` -- with no reversed version ever committed:
- `scrape()` (`bills.py:80-82`): bill-list-page link text prefix `H`/`S` → chamber, assigned
  **per bill** before any vote scraping starts. Unchanged since earliest visible history.
- `parse_status()` (`bills.py:434-437`): per-**action** text, `action.split("/ ")[0]` →
  `"House"` → `lower`, `"Senate"` → `upper`. This is the *exact* same free-text split the
  ticket's own reproduction method uses. Unchanged.
- `parse_html_vote()`/`parse_vote()` (old HTML-table vote path): take `chamber` from their
  caller (`parse_status`, above) -- no independent chamber logic of their own.
- New API-rendered path (`5e345a2d0`, `bills.py:379-381`):
  `"lower" if action_data["voteHouse"] == "H" else "upper"`. Brand new, correct from day one.
- `SPONSOR_HOUSE_TO_CHAMBER = {"H": "lower", "S": "upper"}` -- unchanged.
- `openstates-core`'s `metadata/data/ut.py` (`lower`=House, `upper`=Senate) -- one commit ever,
  unrelated, long predates this window.

**The one real change, `5e345a2d0` (PR #5695, merged 2026-06-16 -- one day after the ticket's
confirmed fix boundary, authored by this same team: co-authored by Ramon Perez and a prior Claude
session):**

Full diff of the relevant hunks:
```python
# before: dead code -- a generator function called but never iterated (missing `yield
# from`), so nothing inside it ever ran, for any 2025+-session Utah bill, ever.
self.scrape_bill_details_from_api(bill, url, session_slug)
# after:
yield from self.scrape_bill_details_from_api(bill, url, session_slug)
```
...plus, inside that now-live function, entirely **new** vote-emission code
(`bills.py:379-397`) with correct chamber logic from day one -- there is no prior version of
this code to have been reversed, because it never existed before this commit. The same commit
also touched two unrelated things, both worth naming for AC3:
- An XPath fix in `parse_html_vote`'s Yeas/Nays/Absent heading selector (`page.xpath("//b")[1:]`
  → `page.xpath('//font[@face="Arial"][@size="5"]')`) -- affects vote-roster parsing, not
  chamber, and only for the *old* HTML-table vote path.
- A new vote-identifier scheme for the *new* code path (`f"{voteID}-{voteHouse}"`, RUNBOOK.md's
  "duplicate vote identifier fix"). This is **not** a fix to a preexisting production duplicate
  -- the new code path had never run before, so it never produced any identifier, duplicate or
  otherwise. It's a from-day-one identifier design, not a regression fix.

**Resolving the contradiction the prior assessment left open:** if the API-rendered path was
dead code before 2026-06-16, it could not have emitted *any* votes -- right or wrong chamber --
for 2025+-session Utah bills before that date. That's consistent with what the live-API check
below actually confirms: the bug bills' current motion text ("House/ passed 3rd reading", etc.,
prefix intact) matches the *new* code path's construction (`action_data["description"]` passed
straight through), not the old HTML-table path (which strips the "House/ "/"Senate/ " prefix off
the stored action/motion text before it ever reaches a `Vote` object -- see `parse_status`,
`bills.py:434-445`). In other words: for these specific 11 bills, the votes the ticket describes
are structurally votes this scraper, as it exists in the vendored fork and real upstream history,
could not have produced *at all* before 2026-06-16 -- not with the right chamber, not with the
wrong one.

### 3. `openstates-core`: no changes to any chamber-relevant import code in this window

The local `openstates-core` checkout is a shallow clone (only 1 commit of history visible on
these files). Added a temporary read-only `upstream` remote at
`github.com/openstates/openstates-core`, fetched full history, checked every file plausibly
involved in resolving a scraped vote's chamber into the database:

```
git log --oneline --since=2025-10-01 --until=2026-08-01 upstream/main -- \
  openstates/importers/vote_events.py openstates/importers/organizations.py \
  openstates/scrape/popolo.py openstates/scrape/vote_event.py openstates/metadata/data/ut.py
→ (no output for any of them -- zero commits in this entire window)
```
`openstates/scrape/bill.py` has 3 commits in this window, all 2025-12-15/16, all about bill
identifier namespacing/prefixing (unrelated to chamber, and outside the March-June bug window
regardless). Temporary remote removed after inspection.

**This rules out `openstates-core`'s import-time chamber resolution entirely** -- it did not
change at all during the bug window, in either direction.

### 4. Live-API spot check: the real production data is correct today, for the historical votes too

Ran `quality_check.py --bill-ids ut 2026 "HB392,HB223,HB136,HB68,HB32,HB209,HB479,SB189,SB234,SB194,SB153"`
against the real `v3.openstates.org` (API key already present in this environment). New
`motion_text_chamber_mismatch()` check reproduces the ticket's own methodology per vote:

**Result: 82/82 checks passed. Every single vote on all 11 bills has its motion text agreeing
with its recorded chamber -- including votes with `start_date`s squarely inside the reported bug
window** (e.g. HB223 2026-03-05, HB136 2026-03-05/03-06, HB68 2026-03-05, HB32 2026-03-05,
HB209 2026-03-04/03-05, SB234 2026-03-05, SB194 2026-03-06, SB153 2026-03-04). Local replica
(scraped from 2026-06-14 onward) and live both agree, 100%.

This means the real production data, as it stands today, is and has been correct for these
specific historical votes -- OpenStates' own vote records were never wrong; only *what
`ddp-broker-py` had stored from an earlier sync* was wrong, until a later sync overwrote it. This
lines up exactly with the ticket's own description: "neither copy ever merges... once a later,
correctly-chambered sync came through" -- i.e. `ddp-broker-py` re-synced the *same* pre-existing
votes more than once, and got the chamber backwards on the earlier sync(s) but right on a later
one, even though the underlying source data didn't change in the way that would explain that.

## Per-AC verdict

**AC1 (what changed 2026-04-26 → 2026-06-15 that fixed it):** Nothing in this repo's controlled
code (`openstates-scrapers`, `openstates-core`) reversed-then-fixed a chamber mapping in this
window -- confirmed by exhaustive upstream git history on both. The one real change in the
window, PR #5695 (merged 2026-06-16), fixed a different, unrelated bug (missing votes for
2025+ API-rendered UT bills) and structurally could not have been the source of *these* bills'
votes before that date. **Cannot be answered from this repo alone** -- see scope boundary below.

**AC2 (deliberate fix or side effect):** PR #5695 is a deliberate, well-documented, fully
attributed fix (co-authored by this same team) -- but for a different bug than the one this
ticket describes. It is very unlikely to be either a deliberate or an accidental fix for the
chamber swap, given it couldn't have touched these bills' votes at all before merging. **Whatever
actually fixed AC1 remains unconfirmed from this repo.**

**AC3 (other fields affected):** Two candidates, independent of the chamber question, both from
PR #5695: the Yeas/Nays/Absent XPath heading-selector change (vote-roster parsing, old HTML path
only) and the new vote-identifier scheme (new code path only, not a fix to a preexisting
duplicate). Neither is confirmed to relate to the chamber swap's root cause, since that cause
itself remains unlocated in this repo's code.

**AC4 (root cause):** Not a chamber-code mapping table, mislabeled scraper output, or
normalization issue anywhere in `openstates-scrapers` or `openstates-core` -- both are
exhaustively ruled out for this window. Combined with the live-API check showing OpenStates'
*current* data is and was correct for these exact historical votes, the evidence points strongly
at `ddp-broker-py`'s own sync-time chamber derivation/caching logic as the actual root cause, not
anything upstream of it.

## Scope boundary

`ddp-broker-py` -- where the bug's evidence, the duplicate Motion rows, and (per the evidence
above) very likely the actual root cause all live -- is not present in this workspace. Per
`project-config.md`'s `repo.path` rule, this is not something to go looking for elsewhere on the
machine; it's a real finding to hand off, not a gap to route around. The next step needs someone
with `ddp-broker-py` access to look at:
- Whatever code derives/caches a Motion's `origin_chamber` at sync time -- specifically whether
  it trusts OpenStates' `Vote`/`VoteEvent.organization.classification` verbatim, or re-derives/
  normalizes it independently in a way that could flip for ~2 months and then stop.
- Deploy history around 2026-06-15 for any change to that derivation code, or to whatever caches
  a previously-synced vote's chamber (would explain "later sync came through correctly" without
  the source data itself having changed).

## Reproducing this check

```bash
DATABASE_URL="postgresql://openstates:openstates_dev@localhost:5433/openstates" \
  python3 quality_check.py --bill-ids ut 2026 "HB392,HB223,HB136,HB68,HB32,HB209,HB479,SB189,SB234,SB194,SB153"
```
