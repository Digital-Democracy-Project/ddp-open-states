# OPEN-110: Florida "Smith" vote misattribution -- what will change and why

Generated 2026-08-19, before running `fix-open110-fl-smith-vote-misattribution.py` for
real against production Postgres.

## What's wrong

**Dave Smith** (Florida House, district 38, Republican) has held that seat continuously
since 2022-11-08. **Carlos Smith** (Florida Senate, district 17, Democrat, serving since
2024-11-05) held a *different* House seat (district 49) until 2022-11-08 -- same last
name, no relation, never in the same chamber at the same time.

423 `opencivicdata_personvote` rows for Florida House ("lower") roll calls carry
`voter_name = "Smith"` but `voter_id` pointing at Carlos Smith. All 423 are dated
**on or after 2022-11-08** -- Carlos's last real day in the House -- so none of them
can be his own legitimate vote; every one belongs to whoever actually held the House
seat on that date, which has been Dave Smith the entire time.

## Why this isn't a currently-live bug

Confirmed directly, by calling the current importer's own person-resolution code
(`BaseImporter.resolve_person`, `openstates-core/openstates/importers/base.py`) against
this exact real data -- same Florida jurisdiction, same `"lower"` chamber classification
-- across **every one of the four legislative sessions the 423 affected rows actually
span** (2025B, 2026, 2026E, 2026F), it resolves a bare `"Smith"` to **Dave Smith**,
correctly, every time. Two independent unit-test reproductions of the Dave/Carlos
membership shape (a clean synthetic case, and the exact real membership rows pulled
from the DB) both resolve correctly under current code as well.

This is the same shape as the Grijalva case (`GRIJALVA-vote-misattribution-fix-20260729.md`):
stale data written by an older import, before some earlier fix to `resolve_person`,
not something the code running today would produce. **No source change to
openstates-core is needed or included in this fix** -- re-running today's importer
against fresh scrapes already gets this right; only the already-written rows need
correcting.

## Scope and safety

- **Rows affected:** 423
- **Date range:** 2025-01-28 to 2026-06-02
- **Change:** `voter_id` Carlos Smith (`ocd-person/df1d6ab6-b2cd-4a6f-b7cc-aa5a63d8011f`)
  -> Dave Smith (`ocd-person/e4bf077a-8468-49a6-a75c-24ee5076352e`). Nothing else on these
  rows changes -- not the vote option, not the voter_name, not the bill or vote event.
- **No row-level conflicts:** confirmed none of the 423 affected `vote_event`s already
  have a separate Dave Smith row -- each currently has exactly one `"Smith"` entry, and
  it's simply attributed to the wrong person. Re-pointing creates no duplicates. The
  script re-checks this itself immediately before writing (aborts if any are found)
  rather than relying solely on this investigation pass, and the UPDATE itself
  re-checks `voter_id` at write time and verifies the updated-row count matches what
  was fetched -- both guard against a row changing underneath the script between
  investigation and execution.
- **No legitimate Carlos Smith House votes are touched:** the query's own date guard
  (`start_date >= 2022-11-08`) would exclude any pre-departure row if one existed;
  confirmed none of the 423 predate his departure.
- **Scoped to this one pair:** this script intentionally only touches
  `voter_name = 'Smith'` rows currently pointing at Carlos Smith in Florida's House --
  it does not attempt a generic "fix every same-surname collision" sweep, and does not
  touch the two other Florida legislators who also share the Smith surname (Jimmie T
  Smith, Christopher L Smith), neither of whose data shows this pattern.

## Out of scope (per the ticket)

The ticket also notes a ~10-row tail (as counted against ddp-broker-py's synced subset,
not this raw replica) that doesn't cleanly fit this same-choice-duplicate pattern, with
at least one case (SB2B, HB949) overlapping a separate, already-filed bug
(ddp-broker-py's BROKER-86, a session-mislinking issue). This fix does not touch that
tail or attempt to resolve BROKER-86 -- both are explicitly out of scope here.

## Verification after running for real

- Dry run: `python3 fix-open110-fl-smith-vote-misattribution.py --dry-run` reports
  423 rows found and no duplicate-voter conflicts, matching this document.
- Re-running the script a second time (without `--dry-run`) should report 0 rows found,
  since the WHERE clause only matches rows still pointing at Carlos.

## Is OPEN-110 closed by this fix?

This corrects every row this investigation could confirm as a genuine misattribution
(423 rows, all provably dated after Carlos's real House departure with no ambiguity).
The ~10-row tail noted above is a separate, unresolved question -- it should not be
read as still-open work under OPEN-110 by omission; it's explicitly out of scope here
because it doesn't fit this fix's provable pattern and at least one case overlaps
BROKER-86. Whether that tail needs its own follow-up ticket is a judgment call for
whoever reviews this, not something this fix resolves one way or the other.
