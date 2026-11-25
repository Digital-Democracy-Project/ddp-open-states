# REQUEST (not a GO): **the v95 release.** Image v95 (scrapers `4b7d0a3c`, core unchanged `a7035d68`), the ddp-sync rebuild that brings the archive in-flight record and the two new launch paths, and ONE re-import each of Rhode Island and Oklahoma. Each step on Ramon's go. 2026-11-25 ~02:40 UTC (Mac side, Onboard New States)

**Not a GO.** Please confirm each step with Ramon in your session. Every merge below was checked on GitHub just now. Arizona's first Fargate load is its scheduled run **Wed 12:00 UTC** (about 9 h from now): nothing here should land between about 11:30 and 12:30 UTC.

## What is merged (and not yet live)
| Repo | main now | New since what is live |
|---|---|---|
| openstates-scrapers | **`4b7d0a3c24d6cfb4066d38cbf48dba9e2190d331`** | #291 (OPEN-883, RI: a reconsidered re-vote counts as passage), #292 (OPEN-885, OK: seven final votes labelled passage). Core stays **`a7035d68d1344f99783042e2492ba120d110e603`** |
| ddp-sync | **`da9641d41563e2d8e23c56fbfec6a3cf3a6036f4`** | #312 (SYNC-192: a running archive is in the in-flight record, so a restart waits for it and its follow-ups fire), #313 (OPEN-881: the unmatched-voter check as a launched task), #314 (OPEN-882: the weekly people refresh as a launched task), and #310 (SYNC-191, the draft cleanup endpoint; its code becomes live with the rebuild but **stays untriggered**) |
| ddp-open-states | `38e5b31be…` (already on EC2) | #490, #491 (`cloud_unmatched_voters.py`), #492 (`cloud_people_refresh.py`); the runners are already in v94 |
| api-v3 | `254389aa` (unchanged) | nothing |

## Step 1: image v95 (Ramon, Mac)
* `bash ~/Developer/repos/ddp-open-states/deploy-scrapers-image.sh`, built from scrapers main **`4b7d0a3c…`** with core **`a7035d68…`**. The RDS entries on `ddp-scrapers-db` copy forward (no `TASK_RDS_*` needed, as for v94).
* **I check on the Mac:** `DDP_CORE_COMMIT` = `a7035d68…`, #291 and #292 in the image, both runners still there; I post the revisions for you.

## Step 2: ddp-sync rebuild (after Step 1; the usual rules)
* `/opt/ddp-sync` to main **`da9641d4…`**; build with **`DDP_CORE_SHA=a7035d68…`** and **`DDP_SCRAPERS_SHA=4b7d0a3c…`** (so `DDP_SCRAPERS_COMMIT` matches v95); the import check must pass; rollback tag first.
* **Guard (the same one, with your fix):** no run in its load phase; no local `cloud_loader`; **no `ddp-scrapers-db` task up, read from `lastStatus`, not the desired status**; and **no archive running** (with #312 this is the first deploy that records archives; an archive already running when it goes live has no record, so the restart must wait for it). Never 02:15–04:45 UTC; **not between about 11:30 and 12:30 UTC** (Arizona's first Fargate load). A restart mid-load resumes it (the record holds the task), but there is no reason to test that on the canary.
* **Both new switches stay OFF:** `openstates_scrape.unmatched_voter_alert.on_fargate: false` and `openstates_scrape.people_refresh.on_fargate: false` in `sync_schedule.yaml` (the defaults). Nothing changes in behaviour except that archives are now recorded and resumed. Do **not** trigger #310's endpoint.
* **After:** healthy, 0 Tracebacks, `/schedule` still 35 jobs, `check-core-pin-drift.py --image-core a7035d68…` exit 0, `DDP_SCRAPERS_COMMIT` reads `4b7d0a3c…`. Please post the first archive's `in-flight` record behaviour if you see one (an archive after the rebuild should add a `kind: archive` record and clear it when its follow-ups finish).

## Step 3: ONE re-import each, on v95's revision or later (each on Ramon's go; one run per state)
| State | Request | Pass (I read it on the replica) |
|---|---|---|
| **RI** | `ri?full=true&sessions=2026`, 202 with `"full": true` | **exactly one roll call changes**: SB 2045's 31-6 re-vote becomes `passage` (it replaces the earlier 32-6); passage events stay **1,323** and counted bill-chambers do not change; HB 7127 Senate roll calls 14; unmatched 0 of about 79,412 |
| **OK** | `ok?full=true&sessions=2025,2026`, **only after the OK 2025 retry (ok-1dc8b007733e) has loaded and archived** | **exactly seven** roll calls change label; counted bill-chambers **2,771 → 2,778**, none replaced; **all 8,767 roll-call numbers still present**; unmatched 2025 **44** (SB 920 only, OPEN-884), 2026 **0**; person votes **331,234**; 0 double votes |
* Revision check: every task must run v95's revision or later; report any that started earlier. A failure stops that state only; two states with the same error stop further starts. If Oklahoma times out again (as 2025 did): stop and report, no third try.

## Not authorized
Any step before its go; a ddp-sync rebuild at any sha other than `da9641d4…` or a core other than `a7035d68…`; turning on either new `on_fargate` switch; #310's endpoint; the archive block's `rds_from_task_secret`; a second run of RI or OK; any other state's re-import.

## What I check on the Mac side
v95's contents (Step 1), RI and OK per the table (Step 3), and Arizona's counts after its Wednesday run. Tickets: OPEN-883, OPEN-885, SYNC-192, OPEN-881, OPEN-882, OPEN-633.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
