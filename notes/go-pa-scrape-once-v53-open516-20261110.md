# Request (GO): run the Pennsylvania scrape ONCE, now, on revision 56 (image v53). This replaces tonight's failed nightly; OPEN-516 Part 2 then reports on it. 2026-11-10, about 06:25 UTC (Mac side)

**Ramon's words, 2026-11-10:** "let's ask the prod agent to trigger a pennsylvania scrape".

The go covers **one Pennsylvania scrape**, launched the same way as the Massachusetts one (`ad124d6`, your reply `f26227c`), and nothing else.

## Why
Tonight's 04:00 UTC Pennsylvania nightly never started. Your status note `72521eb` reported `CannotPullContainerError` from a network timeout reaching the image store.

From the Mac (read-only), I checked:
* v52 existed in the image store;
* a revision 55 task started at 05:00 UTC and exited 0, so the pull failure was a passing timeout.

Since then, Ramon registered **v53 as revision 56** (`notes/update-image-v53-rev56-open518-20261110.md`). It still carries the OPEN-516 Pennsylvania OpenDocument reader, and it adds the Massachusetts work (OPEN-517/518), which does not touch Pennsylvania.

Running Pennsylvania now, rather than waiting for 11-11 04:00 UTC, gets the OPEN-516 check done a day sooner.

## 1. Before you launch (stop and reply if any fails)
1. **Health:** ddp-sync is healthy, **no other scraper task is running** in `ddp-scrapers`, and the Pennsylvania S3 lock `prod/pa/_lock` is not held (or has expired).
2. **Clear of the schedule:**
   * not within about 30 minutes of 02:00, 02:30 or 03:00 UTC;
   * the run (6 h 45 min to 7 h 10 min last time) must end well before Pennsylvania's next nightly, 11-11 04:00 UTC.

   Launching by about 08:00 UTC is fine. If it would collide, say when you will launch instead.
3. **Revision:** if you can read it, note that the newest `ddp-scrapers` revision is **56**. If you cannot, say so; the task's log should then show the Pennsylvania OpenDocument handling (Part 3 below).

## 2. Launch
* **One** `POST /ddp-sync/v1/trigger/openstates-scrape/pa`.
* Report the answer, the `run_id` and the ECS task id.
* **Launch once; never a second time**, even if it looks stuck. Reply to me instead.

## 3. When it ends, report (read-only)
**The scrape:**
* start, end, duration and exit status;
* any `Traceback`, `ERROR`, `CannotPullContainerError` or `SSLError` (the count and the first one);
* Pennsylvania bills and vote events loaded. Last clean run: 5,277 bills, 5,858 vote events.

**Then the OPEN-516 Part 2 items from `281dd01`, for the archive that follows on its own:**
1. The revision and image the scrape and the archive ran on.
2. The archive's summary line:
   * `fetched`, `archived`, `blocked`, `extract_errors`, `fetch_errors`, `persist_errors`, `s3_unverified`;
   * any `blocked response ... expected application/msword magic bytes` lines. There should be none.
3. The read-only SQL from `281dd01`: Pennsylvania documents by `media_type` and `is_error`. **Expect:**
   * `application/pdf` false 6,198 (unchanged);
   * about 6,200 `application/vnd.oasis.opendocument.text`, nearly all `is_error` false.
4. Whether the after-scrape LegBot trigger fired for Pennsylvania, and what EC2 logged. LegBot runs on the Mac; just report it.

**If no archive follows on its own,** say so and stop. Do not start one by hand; that would be a separate request.

**Expected and not a problem:** the archive fetches every Pennsylvania DOC printing once, about **6,200 downloads** from palegis.us, at the scraper's normal pace. Do not stop it unless the site blocks it.

## Not authorized
* A second launch.
* Starting an archive, LegBot run, search refresh or text extract by hand.
* `recompute-diff-order` in any form, or any other state.
* Any write to RDS beyond the normal scrape and archive load.
* Changing a task definition, the schedule or the archive list.
* Anything on the Mac.

## Reply
Two replies, please:
1. `reply-pa-scrape-launched-20261110.md`: the pre-checks and the launch, or why not.
2. `reply-pa-scrape-v53-open516-results-20261110.md`: after the archive ends, or after the scrape if no archive follows.

## What I check on the Mac side
After the archive, on the Mac replica:
* Pennsylvania's OpenDocument rows and counts;
* HB 2625 PN3751's text has no §9301 and loses "for definitions and";
* its comparison with PN3586 shows the removal;
* the Mac and EC2 api-v3 both serve the OpenDocument text for HB 2625.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
