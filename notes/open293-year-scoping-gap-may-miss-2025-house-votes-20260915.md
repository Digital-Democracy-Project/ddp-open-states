# OPEN-293 backfill: tonight's routine USA scrape may not reach any 2025-dated House votes -- please check the 29-bill date list and fix

Ramon asked whether tonight's regularly-scheduled USA scrape (2026-09-16 03:00 UTC) will actually
backfill the 29 House-side missing votes now that v22/revision 26 is the default. Traced the real
invocation rather than assuming -- found a real gap worth checking before assuming this run
recovers all 29.

## What I found, precisely

`run-scrape.sh`'s scrape invocation:
```
$OS_UPDATE "$STATE" --scrape bills $SESSION_ARG $INCREMENTAL_FLAG $VOTES_SCRAPER $1 $DIR_FLAGS
```
`$VOTES_SCRAPER` is the bare string `"votes"` -- no `session=`/`start=`/`year=` key=value args are
ever attached to it (confirmed by the code's own comment: "the votes scraper ... accepts no
start= at all", and by `do_update()`'s left-to-right k=v-attaches-to-preceding-scraper-name
convention -- nothing appears between `votes` and the trailing flags).

`usa/votes.py`'s `scrape(self, session=None, chamber=None, year=None, start=None)`:
- `start` defaults to `datetime(1980, 1, 1)` when not passed -- so within whatever year IS
  scraped, `scrape_house_rolls_page` walks the House Clerk's full roll-call index for that year
  from the top, no incremental cutoff. Good: this means any 2026-dated missing vote should get
  correctly re-processed and fixed by v22's `normalize_clerk_bill_id`.
- **`year` defaults to `datetime.date.today().year` when not passed** -- i.e. whatever calendar
  year the scrape happens to run in. Since votes receives no explicit `year=` argument at all,
  tonight's run will only fetch `https://clerk.house.gov/evs/2026/index.asp` -- **it will never
  request the 2025 index page at all.**

The 119th Congress spans 2025-2026. If any of the 29 House-side bills in OPEN-293's backfill list
had their missing vote in 2025 (year 1 of this Congress), tonight's routine run -- or any future
routine run, since this is how every scheduled USA scrape works, not a one-off -- will silently
never reach it. Not a new bug distinct from PR #47's fix; the fix is real and correct for votes
the scraper actually visits, but the *scraper's own year-scoping* means "wait for the next
scheduled run" is not equivalent to "this will get backfilled" for anything dated last year.

## Ask

1. Please check the 29-bill list's actual vote dates (kept dev-side per the last note) for any
   2025 entries.
2. If any exist, they'll need an explicit targeted re-scrape with `year=2025` passed to the votes
   scraper specifically (not just waiting on the routine schedule) -- happy to run that myself
   once you confirm which bills/dates need it and give me the right invocation, or you can run it
   directly if that's easier from your side.
3. Worth deciding whether this is worth a small code fix too (e.g., having the incremental
   backfill/one-off path pass an explicit `year=` derived from the target bill's own known date,
   rather than relying on the scraper's "current calendar year" default) so a future cross-year
   gap like this doesn't require someone to notice it by hand each time.

Not blocking anything tonight's run does for the 2026-dated portion -- just flagging so "backfill
complete" isn't declared based on a run that structurally couldn't have touched last year's votes.
