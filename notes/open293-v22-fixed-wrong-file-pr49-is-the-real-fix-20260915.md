# OPEN-293: correcting my earlier claim -- v22 did NOT fix vote-linking in production. It fixed a file nothing runs.

Important correction to both my `ddp-scrapers-v22-what-to-expect-20260915.md` note and the
backfill-scope note above. While digging into the year-scoping question you flagged, I checked
whether `usa/votes.py`'s `USVoteScraper` (what PRs #47 and #48 both fixed) is actually reachable
in production at all.

**It isn't, and never has been.** Confirmed directly:

```
>>> juris.scrapers
{'events': <class 'usa.events.USEventScraper'>, 'bills': <class 'usa.bills.USBillScraper'>}
```

`"votes"` is commented out of `UnitedStates.scrapers` (`scrapers/usa/__init__.py`) -- has been
since at least Jan 2025. `os-update`'s scraper resolution is a plain dict lookup
(`juris.scrapers[scraper_name]`); there's no other path in. Neither the Fargate cloud path
(`cloud_collector.py` hardcodes `--scrape bills` only) nor `run-scrape.sh` (its own probe checks
this same dict) has ever been able to invoke `USVoteScraper`.

**The real, live vote-scraping code is `usa/bills.py`'s own `scrape_house_votes()`/
`scrape_senate_votes()`** -- a parallel, near-identical reimplementation of the same Clerk/Senate
XML parsing, carrying the identical two bugs, completely unaffected by #47/#48.

**So: v22/task-def revision 26 did not fix US vote-linking in production.** It fixed
`votes.py`, which nothing runs. My "29 House-side votes ready to re-scrape now" status from the
backfill-scope note above was wrong.

## The real fix: PR #49

https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/49 -- same
`normalize_clerk_bill_id`/`normalize_senate_bill_id` helpers, applied to `bills.py` instead
(imported from `usa.votes`, which stays around as a dependency even though `USVoteScraper` itself
is dead code -- flagged with a guard comment so a future cleanup doesn't break the live scraper).
4 new tests, full `usa/` suite 35/35 passing. Sent through pm-review once, approved
ship-with-caution. Not merged by me -- per standing policy, leaving that for review.

## What's actually true right now

- Vote-linking for HJRES/SJRES bills has never worked in production, on either the House or
  Senate side, regardless of v22.
- Once #49 merges and a new image is built/deployed (same process as v22 -- see RUNBOOK.md), it
  will work for the first time, for both chambers, going forward.
- The 35-bill/40-vote backfill target list itself is unaffected -- it was scoped against
  congress.gov directly, not against either scraper's (broken) output -- but the whole backfill
  is further delayed: still needs #49 deployed before any of it is worth re-scraping, House or
  Senate side alike.
- Separate open question this raised, not resolved here: what to do with `usa/votes.py`/
  `USVoteScraper` now that it's confirmed unreachable (register it for real, delete it, leave it) --
  flagging for a decision, not deciding it.

Sorry for the churn -- should have checked whether `votes.py` was actually wired up before
reporting v22 as a real fix in the first place.