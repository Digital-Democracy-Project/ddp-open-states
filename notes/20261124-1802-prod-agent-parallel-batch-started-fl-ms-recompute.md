# status: parallel batch started 17:46:38 UTC (OK, NM, IA); NM done; FL 2026 loaded; MS and MD recompute dry runs; revision correction

Ramon's go in my session (pop-up ~17:45 UTC: parallel re-imports, broker ac13ac7b, recompute previews, reports). One correction first.

## Correction: which image these ran on
- I called the 11:50 and 09:50 runs "v86 / rev 88". The describe-tasks check at 18:00 UTC shows **OK (session 2025), IA (2026) and Maine's current session 132S1 on ddp-scrapers:90 (v88)**: tasks start on the latest revision, as you said in your v88 note. Maine's first two sessions (132R1, 132R2, launched 11:50) and MS and MD ran on rev 88 (v86). So Maine is a mix of v86 and v88 sessions. Loader core on EC2 is still 59dbdaa2. I have not moved core.

## Batch (9e63a3d), started together 17:46:35 to 17:46:38 UTC
- ok?full=true&sessions=2025,2026: 202 "full": true. ia?sessions=2026,2026s1: 202 (no full flag, as in 07f2083; IA 2025 follows as its own run). nm?full=true&sessions=2026: 202 "full": true.
- Host at start: load average 1.17 / 0.97 / 0.89, 6.7 of 15.7 GB memory used (8.6 GB available). At 17:58: load 1.58 / 1.91 / 1.64. Most runs at once so far: 4 plus the Florida archive (me, ok, ia, nm). No loader failure, no RDS error.
- **NM nm-9d7da5b3e18e: done.** Collection done 17:55:13, load done 17:56:33 (596.5 s in all), archive task 91.0 s, "openstates_pipeline: done archived=True duration_seconds=688.6 failed=0 sessions=1 status=completed". LegBot: archiver_triggered_legbot_no_sessions_touched. Not touched by me: verification (yours) and NM's go-live (#480 held).
- OK (ok-...) and IA (ia-7cd1e13ac328): collecting. ME 132S1 still collecting.
- Not started: WY, KY (they need the v88 core rollout and, for KY, the people load), RI stale-document removal, HI.

## FL 2026 (fl-6264ea52502d, resumed after my 04:57 rebuild)
- collection done 17:15:10, "done" 17:20:34, duration 44,609 s (12 h 23 min). No archive started by itself; I triggered openstates-archive/fl by hand at 17:43:30 (202), under Ramon's 11-23 overnight pre-approval for resumed runs. Its end line is still to come.

## MS and MD recompute-diff-order dry runs (core 59dbdaa2, ddp-sync container; nothing written)
- **MD:** 2,677 bills checked, unchanged=5128 corrected=0 nulled=0; is_bill_version set=0 changed=0 not_a_version=0; diff_baseline_id set=0 changed=0 cleared=0; 0 documents. Matches your replica line. I do not run a commit.
- **MS:** 4,014 bills checked, unchanged=15198 corrected=453 nulled=1422; is_bill_version set=0 changed=1429 not_a_version=1429; diff_baseline_id set=0 changed=453 cleared=1422; 1,875 documents; list md5 ca3eea9abacd1f733a509af6f69f7fb1 (ops/ms-recompute-dry-core59dbdaa2-20261124.csv); 0 "Current version" rows in the list. Inside your range (corrected 440-470, nulled 1,400-1,450, not_a_version 1,410-1,450, cleared 1,400-1,450). **The commit waits on Ramon's second go.**

## Still waiting on Ramon's go
- The v88 core rollout (core 0d373728, api-v3 254389aa, ddp-sync eefb1ba; e30bb8e step 1 + 7d4793f + b03def0), the v89 request (a0e5d64), the Missouri/Hawaii/Kentucky/Wyoming re-imports, the MS recompute commit.
- Broker ac13ac7b: DONE (checkpoint on the broker branch).
