# OPEN-81 + OPEN-30 backfill: MI's 2026-07-03 missing votes recovered

OPEN-30 (merged 2026-08-06) fixed `parse_roll_call()`'s silent WAF-failure swallowing, but
explicitly deferred the actual data recovery on the assumption that `scrape_votes()` re-reads a
bill's entire history on every scrape, so an ordinary scheduled MI re-scrape would organically
pick up the missing 2026-07-03 votes. **That assumption was checked today and found false**: MI
was re-scraped 2026-08-09 (3 days after the fix), and all 16 previously-identified bills still
showed zero July 3 votes, unchanged. Likely reason: these bills' `latest_action` had already
fallen behind live (per OPEN-28's own note), so they'd dropped out of MI's incremental `start=`
scrape window entirely -- a bill that isn't re-visited never gets a chance to retry its per-vote
fetch, no matter how many times the fix's own retry logic would have worked if given one.

## OPEN-81: built MI's bill_no= targeting to make this fixable at all

No existing mechanism could target just these 16 bills without a full MI session rescrape.
Added `bill_no=` to `MIBillScraper.scrape()` (comma-separated list), scoping the single
`ExecuteSearch` results fetch's per-bill loop to just the requested identifiers -- same
single-scrape/circuit-breaker-context rationale as FL's OPEN-77.

**A live test caught a real bug before merge**: the first version assumed search-result link
text was the long form ("House Bill No. 4023") seen on the bill *detail* page's heading --
actually the search-results *list* page uses short form ("HB 0001 of 2025"), a different page
entirely. That assumption matched zero real links and crashed with "no objects returned". Fixed
(`_mi_bill_id_to_no()` now matches the real short form, stripping leading zeros for comparison)
and re-verified live before merging: `bill_no=HB4023` alone correctly recovered its missing
2026-07-03 vote (Roll Call #210), zero WAF issues. `openstates-scrapers` PR #30.

## The actual backfill

Ran `os-update mi --scrape bills session=2025-2026 bill_no=<all 16 identifiers>` -- **39 vote
events recovered, 21 dated 2026-07-03 (the previously-missing date), zero WAF rejections across
the whole run.** Imported into production: 21 new vote events, 18 updated (already-known votes
refreshed), 0 noop. Verified directly: all 16 bills now show their 2026-07-03 vote in the
database, confirmed via query (previously 0/16).

## A separate, narrower issue found along the way -- not part of OPEN-30's scope, flagged for its own ticket

Several (not all) of the 21 newly-recovered July 3 vote events show a `VoteCount` aggregate that
doesn't match the real tally already preserved in the vote's own `motion_text` -- e.g. HB 4023's
new vote reads "YEAS 36 NAYS 0" in its `motion_text`, but its `VoteCount` rows show only 4 yes /
2 no. Root cause narrowed down, not fully diagnosed: this is `openstates/importers/base.py`'s
`no people returned for spec` path -- specific legislators' names, as extracted from that
particular roll call's journal HTML, matched zero `Person` records. **This is not a general MI
person-resolution problem** -- a pre-existing Senate vote on the same bill (HB 4023, 2025-06-05)
and a pre-existing Senate vote on a different bill (SB 205, 2026-04-22) both resolve their full
tallies correctly (104/2/0 and 35/0/2, exactly matching their own `motion_text`). Several of the
21 new July 3 votes *also* resolve correctly (e.g. HB 4101, one of HB 4750's two votes, one of
SB 418's two votes, one of SB 966's two votes) -- so this isn't "every July 3 vote" either.
Multiple different bills' broken votes show the *identical* under-resolved tally ("Y=4 N=2"),
suggesting these are actually the same underlying Senate floor roll call applying to several
companion/tie-barred bills at once, and something specific to that one journal document's name
formatting is why only a handful of names resolve. Not root-caused further here -- flagged as its
own follow-up rather than folded into this ticket's closure, since the vote_event itself (date,
real tally as text) is correct either way and nothing here represents new data loss.

## References

- OPEN-30 (Done, `openstates-scrapers` PR #22 / `ddp-open-states` PR #84) -- the circuit-breaker
  fix this backfill depends on
- OPEN-28 (`notes/mi-open-28-missing-vote-root-cause-20260805.md`) -- the original 16-bill list
  and root-cause investigation
- OPEN-81 (`openstates-scrapers` PR #30) -- the `bill_no=` targeting this backfill used
- `openstates/importers/base.py` (~line 626-663) -- the `no people returned for spec` path for
  the follow-up finding above
