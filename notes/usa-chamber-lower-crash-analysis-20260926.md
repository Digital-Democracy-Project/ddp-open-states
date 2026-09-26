# usa chamber=lower crash: root cause, real mechanism (not a retry), and how long it's been happening

**Thread:** separate from VOTEBOT-7/OPEN-2/SYNC-74/OPEN-304/OPEN-305 (now closed) -- this is the
`KeyError: 'Concurrent Resolution Rejected'` crash flagged as a side finding during that
investigation, looked at more closely per Ramon's ask.

## The bug

`scrapers/usa/bills.py:873`, inside `scrape_senate_votes()`:

```python
result = self.senate_statuses[result_text]
```

`self.senate_statuses` is a hardcoded dict of known Senate vote-result strings. `"Concurrent
Resolution Rejected"` isn't in it. This fires specifically on House Concurrent Resolutions
(`HCONRES`) that also carry a Senate-side vote action -- concurrent resolutions need both
chambers to agree, so a House-numbered bill can still trigger this Senate-status lookup. Today's
crash happened on `HCONRES 89`.

## The real mechanism -- corrected from an earlier, wrong description of this as "a retry"

`run_usa_scrapes_job()` (`ddp_sync/pipelines/openstates_scrape.py`) is just:

```python
for session in sessions:  # ["119 chamber=lower", "119 chamber=upper"]
    result = await _run_scrape(...)
    results.append(result)
```

No retry, no early exit. When chamber=lower crashes on `HCONRES 89`, the loop simply moves on to
chamber=upper next -- a completely independent scrape with its own, unrelated data, which
predictably succeeds. Earlier reporting on this thread described chamber=upper's success as a
"successful retry" of chamber=lower's failure -- that was wrong; they're unrelated pieces of
work that happen to run back-to-back. Confirmed by checking: the overall job's own completion
log (`openstates_usa_scrapes: completed`) does fire and correctly reports `failed=1 total=2` --
so the system does track the failure -- but chamber=lower itself is never retried, and this fix
does not exist anywhere in this loop.

**Practical impact**: whatever House bills/votes come after the crash point in that day's
incremental scan are never scraped that run. Unless the next day's incremental window happens to
still cover the same content, it may be permanently missed.

## Alerting: confirmed working, correcting an earlier assumption

Ramon found the real Slack alert from this exact occurrence:

> :red_circle: OpenStates scrape failed: usa session=119 chamber=lower — collection exit_code_1:
> Essential container in task exited (after 573s) — check ddp-sync logs / scraper.log

This is a real, working alert -- earlier session memory had this host's failure-alerting flagged
as broken (no Slack/CAMS token, from an OPEN-193 AC3 check). That may be stale, or may refer to a
different alert path than this one; either way, this specific alert fired and reached a human,
which is the important part.

## How long has this been happening -- checked, not assumed

Searched CloudWatch (`/aws/ecs/ddp-scrapers`, 30-day retention) for every `usa` scrape failure in
the full retained window, then verified each one's actual traceback rather than assuming they're
all the same bug:

- **2026-08-30 (x3) and 2026-09-03 (x2)**: real `usa` failures, but a **different, unrelated
  bug** -- `openstates.exceptions.ScrapeError: no objects returned from USBillScraper scrape`
  (an empty-scrape validation error), not this `KeyError`. Confirmed by reading each traceback
  directly, not by pattern-matching on "usa" + "failed" alone.
- **2026-09-26 03:08:58 and 2026-09-26 22:28:47**: the actual `KeyError: 'Concurrent Resolution
  Rejected'` crash -- both today, nothing before that anywhere in the 30-day window. (The
  03:08:58 occurrence is the one Slack alerted on -- 11:09 PM ET the evening before converts to
  03:09 UTC, same event, not a separate one.)

**This specific bug has only been observed twice, both today.** Can't rule out an earlier
occurrence beyond the 30-day retention window, but there's no visible history before today in
anything actually checkable. Consistent with this being genuinely data-dependent (a vote-result
phrasing that simply hadn't appeared in scraped Senate data until now), not a long-silent,
constantly-failing bug.

## Ask

Two separate things worth fixing, independent of each other:

1. **The missing status mapping itself** -- add `"Concurrent Resolution Rejected"` (and
   plausibly `"Concurrent Resolution Agreed to"`/similar, if those aren't already covered) to
   `self.senate_statuses` in `scrapers/usa/bills.py`. Small, contained fix.
2. **No retry for a single chamber's failure within `run_usa_scrapes_job`** -- worth its own
   ticket. Given the job already correctly detects and logs `failed=1`, the fix might be as
   simple as re-queuing the failed session once, or at minimum surfacing "chamber=lower has been
   silently unscraped since <date>" more visibly than a log line + one Slack alert that could be
   missed.

Reply on this branch as usual.
