# REQUEST (not a GO): **two full runs: Georgia's main 2025-26 session, and Iowa's 2026s1 special session.** Both are triggers with an explicit session list. 2026-11-25 ~23:00 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon decides each run in your session by naming this note. Run them one at a time (a state has one run at a time; a second trigger answers 409). Avoid the windows in your own rules (Sunday from 02:00 UTC, each nightly state's start).

## What I need from you
1. **Georgia:** trigger **`ga?full=true&sessions=2025_26`** (the image and code that are live now, v95). Report the task start and end times, the final log lines (counts of bills, votes, people unmatched), and the archive's end line.
2. **Georgia, after 1 finishes:** trigger **`ga?full=true&sessions=2026_ss`** so the 35 "Jason T. Dickerson" Senate votes link (the people fix, people #26, is merged and loaded: the Mac replica has the alias). Expected: about 27 minutes; 176 bills; the 35 unmatched votes drop to 0.
3. **Iowa:** trigger **`ia?full=true&sessions=2026s1`**. It is the one session Iowa's 11-24 run did not load (0 bills on the replica). Report the log's session lines first (that the special session was found), then the end counts.
4. After each: tell me when done; I verify on the Mac replica and post a `reply-verified-` note.

## Why Georgia's full walk has not been limited by the 12 hours
Ramon asked what 12-hour limit applies. What I read (code only; I cannot read ECS task definitions):
* The manifest's `scrape.timeout_s` (21600 for Georgia) is read **only by the local scrape path**, which no state uses now (all 30 use the Fargate path). It does nothing on Fargate.
* On the Fargate path ddp-sync stops a run only after **45 minutes with no new log line** (`stall_seconds` 2700). A walk that keeps logging is not stopped.
* `max_wait_seconds` (12 h shared, or the manifest's `scrape.fargate_max_wait_s`) **only raises one "still running" alert**; it does not stop the task. Massachusetts has 86400 there so it does not alert at 12 h.
* **Not verified:** any limit in the ECS task definition itself, and any source-site throttle. Please read the task definition's runtime limit (if any) and **tell Ramon in your session**, not in a note.

## Why `sessions=2025_26`
The replica has Georgia's `2026_ss` (176 bills) and `2025_26` with **0 bills**: scheduled runs scrape only active sessions, and the main one never loaded. The 176-bill run took 1,594 s (about 9 s a bill), so the main session (about 2,500 to 3,000 bills) is an **unmeasured estimate of 6 to 8 hours**. If you want the 12-hour "still running" alert silenced for it, the manifest's `scrape.fargate_max_wait_s` for Georgia can be set to 86400 (alert only); it is **not** needed for the run and I have not changed it.

## Iowa: why the 11-24 request produced no `2026s1` run
The 11-24 trigger was `ia?sessions=2026,2026s1` (no `full`). It was resumed after the 20:15 restart; **my hypothesis (not verified)** is that the resumed run kept only the sessions it had already started and lost the rest of the list from memory. Please check the log of that run and say whether the `2026s1` session was ever started or skipped. This is the case SYNC-192 (#312, live) fixed for the archive; the scrape trigger may need the same.

## Not authorized
Any other state; `all`; a manifest change; `replica_routing`/`legbot_replica`; a ddp-sync restart; any hand-run scrape outside ddp-sync's path; a retry on failure without telling me first.

## Mac-side checks afterwards
Georgia `2025_26` bill count against Georgia's own site, version stage coverage, vote attribution (unmatched), `2026_ss` Dickerson count 0; Iowa `2026s1` present with bills. Iowa's Stage 3 version-stage gate currently **fails** for a separate reason (OPEN-893, 6.3% against the 5.5% limit, three note kinds); a builder is on it, so do not read that failure as caused by this run.

Tickets: OPEN-610 (Dickerson), OPEN-893 (Iowa stage gate), OPEN-673 (Iowa go-live), OPEN-146. Georgia's go-live ticket follows once `2025_26` is verified.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
