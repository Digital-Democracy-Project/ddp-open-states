# Request (GO): one Utah test scrape on the new image v58 (revision 61, Python 3.13) before Sunday's batch, 2026-11-14 about 19:05 UTC (Mac side)

**Ramon's words, 2026-11-14:** "can we build the new image and run a test scrape? if there's a problem, we can roll back to the prior version. if it works, we'll leave it in place for the sunday scrape".

**What I need from you:**
1. the checks in section 1;
2. one Utah launch (section 2);
3. the report in section 3, **before Sunday 11-15 02:00 UTC**.

## Why
Ramon registered **v58 as `ddp-scrapers` revision 61**, about 19:00 UTC today. His script printed: Python 3.13.18, imports OK; the previous image was v57 (revision 60). It is built from `main` at `991c64f`, so it carries:
* the Python 3.13 move (OPEN-515: the image base and openstates-core #95);
* the Massachusetts comparison fix (OPEN-223, core `016fc6b3`);
* the Massachusetts House tally fix (OPEN-442, scrapers `361737d8`).

I checked inside v58 on the Mac that both Massachusetts changes are present. This is the first scrape on Python 3.13, and OPEN-515 requires one clean test scrape before the release stays. **Utah** is the test: live, no WAF, out of session, weekly, and not in a soak.

## 1. Before you launch (stop and reply if any fails)
1. ddp-sync is healthy. **No other scraper task is running** in `ddp-scrapers`, and Utah's S3 lock is not held.
2. **Clear of the schedule:** not within about 30 minutes of 02:00, 02:30, 03:00 or 04:00 UTC. The run (and the archive and LegBot steps that follow it) should end well before **Sunday 02:00 UTC**. Launch as soon as these checks pass.
3. **Revision:** note that the newest `ddp-scrapers` revision is **61** (image v58), if you can read it; otherwise say so.

## 2. Launch
* **One** `POST /ddp-sync/v1/trigger/openstates-scrape/ut`. Report the answer, the `run_id` and the ECS task id.
* **Launch once; never a second time**, even if it looks stuck. Reply to me instead.

## 3. When it ends, report (read-only)
* the revision and image the task ran on, and the Python version if the log shows it;
* start, end, duration and exit status;
* any `Traceback`, `ERROR`, `ImportError`, `ModuleNotFoundError`, `SyntaxError` or `CannotPullContainerError` (the count and the first full one);
* Utah bills and vote events seen and imported, **next to Utah's last clean run** (counts and duration from your records);
* whether the archive and LegBot steps after it ran, and their summary lines.

## Not authorized
* any other state, `all`, a second Utah launch, a restart, a manifest change;
* **any change to the task definition, including a rollback.** If the test fails, **report and stop**. Ramon decides the rollback, which is `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:61`, run from the Mac.

## What I check on the Mac afterwards
On the replica: Utah's newest `updated_at` moves and its bill count is unchanged or up. Then I post `reply-verified-...` or a rollback recommendation to Ramon before 02:00 UTC.
