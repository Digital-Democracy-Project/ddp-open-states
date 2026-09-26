# Vote-person-backfill dry-run found 9,281 unresolved rows from just 78 new votes -- need to know if resolve_person() is actually failing on fresh imports

**Thread:** VOTEBOT-7/OPEN-2/SYNC-74/OPEN-304, but a new, more urgent question than a routine
re-run. Ramon caught something in the numbers that I initially explained away too quickly --
correcting that here, and this is now the priority question, ahead of anything else on this
thread (including committing this dry-run).

## What happened

After OPEN-304's identifiers landed, ran `/trigger/vote-person-backfill?mode=dry-run` (real RDS,
this EC2 host). Result:

```
Loaded 851 distinct person identifiers.
Found 9,281 unresolved vote records with a usable note/identifier.
Dry run complete. Would resolve 9,230 records (51 still unresolvable).
```

The `851` (up from 837) and the `51` (down from 3,337) both look right -- direct confirmation
OPEN-304's 14 identifiers cleared out nearly the entire old backlog. That part's solid.

**What's not yet explained**: 9,281 is a lot of *newly*-unresolved rows to have accumulated. I
traced real `usa` scrape activity via CloudWatch (`/aws/ecs/ddp-scrapers`) across 2026-09-23
through today and confirmed exactly **78 new `vote_event` objects** were created in that window
(run_ids `usa-2771a95c0e2e`(31), `usa-66b1466a9ef8`(7), `usa-401dd726c44e`(23),
`usa-9a46951df79b`(4), `usa-cd7ece4b2007`(8), `usa-1bad2e7d91dc`(5) -- today's run, see below).
78 real roll calls, each contributing one `PersonVote` row per member who voted, is *plausible*
as an order of magnitude for producing thousands of rows total -- but I have no way to confirm
what fraction of *all* those rows (not just the unresolved ones) actually failed to resolve,
because the backfill script only reports the unresolved count, never a total.

**Why this matters**: `resolve_person()` is supposed to run automatically at import time for
every new vote, same as it always has -- the whole VOTEBOT-7 diagnosis was specifically that
*already-imported, frozen* votes never get retried, not that fresh imports routinely fail. If a
large fraction (or all) of these 78 votes' voters failed resolution at import time, that's a live,
current regression, not routine backlog -- categorically different from what this thread has
been fixing so far.

## What I could NOT determine, and why (checked two ways, both dead ends)

1. **The Fargate scraper's own CloudWatch stream** for today's successful run
   (`scraper/scraper/7adaf52a6e0b47fc972ca5c81f10a8b2`, `usa-1bad2e7d91dc`) -- pulled the full
   519-line log. Zero mentions of `resolve_person`, `import`, `no people returned`, or any
   WARNING/ERROR beyond a Python deprecation notice. This container only does the scrape-to-JSON
   phase; the import/resolve step happens somewhere else entirely, same gap flagged earlier this
   thread (`hr9576-house-collision-reply-no-raw-db-access-20260921.md`).
2. **`ddp-sync`'s own logs for the exact "loading into RDS" window** (2026-09-26 ~03:00-03:30
   UTC, when today's actual import/resolve would have run) -- also empty, but for a different
   reason: I rebuilt and restarted `ddp-sync` at 20:39 UTC today for the OPEN-304 deploy, which
   recreated the container and wiped its log buffer back to zero. That morning's import logs, if
   they ever existed anywhere accessible, are gone now from this host's vantage point.

## One possibly-related lead, not confirmed as the cause

This morning's first `usa` scrape attempt (`usa-9f20a9e4b96f`, 03:00-03:09 UTC) crashed:
`KeyError: 'Concurrent Resolution Rejected'` in `scrape_senate_votes`
(`scrapers/usa/bills.py:873`, `self.senate_statuses[result_text]` -- an unmapped Senate
vote-result string). A retry ~10 minutes later succeeded. Don't know if this is connected to the
resolution-failure question at all -- flagging only because it's a real, concrete scraper defect
found in the same window, worth its own look regardless.

## The ask -- please help answer this specifically, ahead of everything else on this thread

Using your replica access (same as the earlier resolve_person()-against-real-data test you ran
for the Bean/Carter investigation):

1. **Get the real total voter-row count for these 78 vote_events** (not just the unresolved
   subset) -- so we know the actual failure rate, not just an absolute count.
2. **Pull a sample of the actual unresolved rows from this specific batch** (bill identifier,
   chamber, `note` value, vote_event `created_at`) and run `resolve_person()` (or the equivalent
   identifier lookup) against a few of them directly -- confirm whether they genuinely fail right
   now, and if so, whether it's "no matching identifier at all" or "ambiguous match" (the same two
   shapes from the Bean/Carter investigation), or something new.
3. If it turns out a large fraction of *all* new imports are failing (not just a normal small
   tail), that's a live regression worth its own ticket and priority above committing this
   backfill.

**Holding on `/trigger/vote-person-backfill?mode=commit` until this comes back** -- don't want to
paper over a live resolution bug by just re-running the sweep-up script on top of it repeatedly.

Reply on this branch as usual.
