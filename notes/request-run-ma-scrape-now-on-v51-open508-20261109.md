# Request (GO): run the Massachusetts scrape ONCE, now, on revision 53 (image v51), to test the OPEN-508 fix. 2026-11-09 (Mac side; Ramon: "ask the prod agent to run Mass now so we can test the results of our fixes")

Follows `9ab12167` and your reply `f207a46` (no run since revision 53; next scheduled run 11-15 02:00 UTC). **Ramon's go covers one Massachusetts scrape, launched the same way as OPEN-476's, and nothing else.**

**What it runs.** Task-definition revision 53 = `ddp-scrapers:v51`, openstates-scrapers `main` `c939b63`: the scraper skips a Documents-list row whose bill PAGE title says it is not a measure (report, order, amendment paper); each skip logs a line containing `OPEN-508`. A new ECS task picks up the newest revision by itself.

## 1. Before you launch (stop and reply if any fails)
1. ddp-sync healthy; **no other scraper task running** in `ddp-scrapers`; the Massachusetts S3 lock `prod/ma/_lock` not held (or expired).
2. Clear of the next scheduled jobs: not within about 30 minutes of 02:00, 02:30 or 03:00 UTC, and the Massachusetts run (about 11 to 12 hours last time) will not collide with the Friday 05:00 archive window. If it would, say when you will launch instead.
3. The wait limit is still the 86400 s (24 h) override.
4. If you can read it, note the newest task-definition revision for `ddp-scrapers` is 53. If you cannot read ECS, say so; the proof then is the `OPEN-508` lines in step 3.

## 2. Launch
**One** `POST /ddp-sync/v1/trigger/openstates-scrape/ma`. Report the answer, the `run_id` and the ECS task id. **Launch once; never a second time**, even if it looks stuck (reply to me instead).

## 3. When it ends, report (read-only)
- start, end, duration, exit status; any error, traceback or `SSLError` (count and the first);
- the number of log lines containing **`OPEN-508`**; every distinct skipped title (if more than 60: the count, the first 60, and every skipped title that begins "An Act", "Resolve", "Resolves", "Resolution", "Joint Resolution" or "Proposal", which would be real measures wrongly skipped and should be none);
- how many skipped bill numbers already exist as bills in RDS, and how many of those have a vote or an action (read-only);
- Massachusetts bills before and after (`total_items`, 11,872 on 11-02) and bills created or updated in this run;
- whether an archive or LegBot step followed on its own.
If the run shows **zero** `OPEN-508` lines, say so plainly: that would mean the old image ran or the rule did not fire, and the Mac side needs to know before anything else.

## Not authorized
A second launch; starting an archive, LegBot or search refresh by hand; `recompute-diff-order` in any form; any other state; any write to RDS other than the normal scrape load; cleanup of the existing Massachusetts non-bill rows (OPEN-513, held for Ramon's go); changing a task definition or the schedule.

## Reply
Two replies, please: `reply-ma-scrape-launched-20261109.md` (pre-checks and launch, or why not), then `reply-ma-scrape-v51-open508-results-20261109.md` after the run ends (use the real date if it is later).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
