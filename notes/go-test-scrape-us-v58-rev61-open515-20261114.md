# Request (GO): a second test scrape on v58 (revision 61), the United States, so a run that SAVES bills is proven on Python 3.13 before Sunday, 2026-11-14 about 20:15 UTC (Mac side)

**Ramon's words, 2026-11-14 (after your `ed2d9c4`):** "One more test that saves bills". This adds to his earlier go, "if it works, we'll leave it in place for the sunday scrape".

**What I need from you:**
1. the checks in section 1;
2. one launch for the United States (section 2);
3. the report in section 3, as soon as the run and its archive end, before Sunday 02:00 UTC.

## Why
Your Utah test (`ed2d9c4`) was clean but saved nothing: Utah is out of session, so the incremental run raised `EmptyScrape`, with 0 bills and 0 vote events. Congress is in session; Saturday's 03:00 UTC US nightly touched session 119 (its LegBot trigger fired). Its whole pipeline took 1,550 s. So a US run now should fetch, **yield and import changed bills** on v58, and end long before Sunday 02:00 and its own 03:00 nightly.

**The Mac side is fixed since your `af799e2`.** The Mac's ddp-sync was restarted at 19:31 UTC and logged `Redis connected`; the cause was a reboot race, filed as SYNC-160. So the LegBot trigger after this run should be accepted (202), not 503. Please report what it answers.

## 1. Before you launch (stop and reply if any fails)
1. ddp-sync is healthy, no scraper task is running in `ddp-scrapers`, and the US S3 lock is not held.
2. Clear of the schedule (not within 30 minutes of 02:00, 02:30, 03:00 or 04:00 UTC), and the run should end well before 02:00 UTC.

## 2. Launch
* **One** `POST /ddp-sync/v1/trigger/openstates-scrape/<the United States target>`, the same target the 03:00 UTC nightly uses (its timing key is `usa`; use the name your trigger accepts). Report the answer, the `run_id` and the ECS task id(s). The nightly runs two scrapes (the chamber sessions); report both if the trigger does too.
* **Launch once; never a second time.** Reply to me instead.

## 3. When it ends, report (read-only)
* Python version evidence from the task log, as for Utah;
* start, end, duration and exit status of each scrape, the load and the archive;
* the count and first full line of any `Traceback`, `ERROR`, `ImportError`, `ModuleNotFoundError`, `SyntaxError`, or a serialization or validation error;
* **bills and vote events yielded and imported** (non-zero is the point), next to Saturday's 03:00 nightly;
* the archive summary line, and the LegBot trigger's answer (202 or not).

## Not authorized
* any other state, a second launch, a restart, a manifest change;
* **any change to the task definition, including a rollback.** If it fails, report and stop; Ramon decides.

## What I check on the Mac afterwards
On the replica, US bills updated in the last hour (non-zero), with no other state touched. Then I post a verified note, or tell Ramon to roll back before 02:00 UTC.
