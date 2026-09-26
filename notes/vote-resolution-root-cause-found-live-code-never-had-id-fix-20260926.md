# Found it -- this is not a new regression, it's a fix that was applied to dead code

**Re:** `vote-person-backfill-rerun-unexpected-volume-20260926.md` (this branch). Answering your
three specific asks below, but leading with the actual root cause since it changes the picture
completely.

## Root cause

`openstates-scrapers` has two Senate/House vote-scraping implementations:

- `scrapers/usa/votes.py` -- has `vote.vote(..., note=bioguide, id=bioguide)` /
  `vote.vote(..., note=lis_id, id=lis_id)`. **This file is dead code** -- its own docstring
  says so directly: `"votes"` is commented out of `UnitedStates.scrapers`, so nothing ever
  invokes it (same finding OPEN-293 already made about this file, just for a different bug).
- `scrapers/usa/bills.py` -- the actual, live, production code path (confirmed: `scrape_votes()`
  dispatches to this file's own `scrape_senate_votes`/`scrape_house_votes`, not `usa/votes.py`'s).
  Its two `vote.vote()` calls are `vote.vote(self.vote_codes[choice], name, note=bioguide)` and
  `vote.vote(self.vote_codes[choice], name, note=lis_id)` -- **no `id=` at all, in either
  chamber.**

`VoteEvent.vote()` (openstates-core, `scrape/vote_event.py`) only includes `"id"` in the
pseudo-id spec `if id:` is truthy. Since `bills.py` never passes it, **every vote import today,
in both chambers, has always resolved people by name-matching alone** -- the bioguide/lis
identifier lookup `resolve_person()` added for OPEN-2 has never actually run at import time in
production. It only ever ran when `backfill-vote-person-resolution.py` re-reads the `note`
column directly (which `bills.py` does still populate correctly) and matches it against
`PersonIdentifier` itself, bypassing the broken pseudo-id path entirely.

This is why OPEN-304 didn't fix newly-scraped Senate votes going forward: new imports were never
using identifier matching to begin with, so adding the 14 missing `lis` rows only helps the
*next backfill sweep*, not the live import. It also explains the chamber asymmetry: Senate
`member_full` text apparently never `iexact`-matches stored Person names/other_names/family_name
at all (100% failure, every senator, every vote you found), while House's `sort-field` format
matches well enough most of the time (~78% success, consistent with the known House
name-ambiguity gap from earlier in this thread).

## Your three questions

1. **Real total voter-row count for the touched vote_events**: 64 distinct `vote_event` rows
   touched (by `updated_at`) since 2026-09-23, not 78 -- likely some of your 78 run_ids re-touched
   the same events without creating new ones. Every Senate one (100 voters) is 100/100
   unresolved, no exceptions. House ones (~429-434 voters) run ~94-100 unresolved each,
   consistent with the existing House gap, not something new.
2. **Sample resolution check**: pulled `note` values for the freshest 100%-unresolved Senate
   vote (`ocd-vote/bb8c15fa...`, S. 4668 cloture) -- `S428`, `S440`, `S354`, etc. Every one of
   those `lis` values already exists correctly in `PersonIdentifier`, matching the right
   `person_id`, with valid `Membership` rows (`upper`, correct jurisdiction, dates covering
   today). Not "no matching identifier" and not "ambiguous match" -- the identifiers and
   memberships are completely correct. The live import path just never looks at them.
3. **Live regression, real, above everything else on this thread**: confirmed, but it's not
   new -- it's been true since OPEN-2 shipped (2026-07-26), silently compensated for by every
   backfill sweep since. Worth its own ticket regardless of age, since it means vote-person
   resolution has never actually worked the way the original fix intended.

## What I'm NOT doing yet

Not touching `usa/bills.py` without confirming with Ramon first -- this reframes the original
OPEN-2 diagnosis (I want to check with him before opening a fix PR). Wanted this on the record
here first since it directly answers what you're blocked on.

Given this, committing `/trigger/vote-person-backfill?mode=commit` now is still safe and correct
-- it will genuinely resolve those 9,230 rows using the identifiers that exist, exactly as
before. It just won't stay fixed for the *next* new vote until `usa/bills.py` itself is patched.
Your call whether to commit now (and let this recur until the real fix lands) or hold for the
code fix first.
