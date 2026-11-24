# status: Maine archive PASSES; WY done; HI and MO results; OK 2026 loading; read d8df145 (Arizona canary), nothing of it started

## Maine archive (OPEN-871), started 20:31:30 UTC, ddp-scrapers-db:18 (v89, core with the Maine PDF reader)
- ddp-sync: "openstates_archive: fargate task done duration_seconds=5836.3" (22:08:47 UTC). The task's own counts line (CloudWatch, stream bd2da7b2...): `me: 2450 bills checked | fetched=5131 skipped=0 archived=5131 fetch_errors=0 blocked=0 extract_errors=0 conflicts=0 concurrent_writes=0 s3_verified=5131 s3_unverified=0 persist_errors=0`; JSON run_id me-archive-747c4f40243a, status "ok", duration_s 5740. Your pass line (N about 5,131, 0 blocked, few fetch errors): met on its face. (The 18-second `fetched=0` line from earlier today is the old run, me-archive-cb9439c6c6ce.) I did not start recompute or relabel for ME (they are your dry runs first).

## Other archives and runs since 20:30
- **MO archive** (started by hand 22:06:48): task done 151.3 s at 22:09:19. Counts: `mo: 3161 bills checked | fetched=47 skipped=4809 archived=47 fetch_errors=0 blocked=0 extract_errors=0 ... s3_verified=47 s3_unverified=0 persist_errors=0`.
- **WY** (wy-10cc60087579, v90 rev 92): collection done 22:14:08, load done 22:15:52 (589.6 s in all), archive 91.2 s, "openstates_pipeline: done archived=True duration_seconds=683.0 failed=0 sessions=1 status=completed". Archive counts: `wy: 335 bills checked | fetched=0 skipped=1295 archived=0 ... errors 0`. Your numbers (276 -> 382 etc.) are yours to read.
- **HI** (hi-715d5f8d0991, rev 91, loaded on core 70146fac): collection done 22:00:26, "done" 22:29:16, duration 7,999.6 s (load about 29 min). Resumed run, so no archive of its own; I started openstates-archive/hi by hand at 22:29:58 (202). End line to come.
- **OK 2026** (ok-3f164c3f15c1): collection done 22:27:52, loading now. I will not restart ddp-sync into it. After it ends: its done line and counts for you, and an archive by hand (resumed run). Oklahoma 2025+2026 on v90 starts after that, then I report its revision (92 or later).
- NE and UT (v90, rev 92) still collecting; IA (rev 90) collecting.

## Resource reading (9e63a3d)
- 22:07: load 1.79 / 1.18 / 1.41, 7.0 of 15.7 GB. 22:28: load 3.70 / 2.40 / 1.84 (while HI loaded and WY, NE, UT ran). 22:30: load 2.42 / 2.30 / 1.84, 6.9 of 15.7 GB. Highest run count at once so far: 7 (wy, ne, ut, ia, ok, me archive, hi load). No loader failure, no RDS error. Peak after the NE/UT loads still to come.

## Arizona canary request d8df145 (OPEN-633): read in full, NOTHING started
- Each of its four steps needs Ramon's go in my session; I put it to him. Step 1 (read the `ddp-scrapers-db` task definition names): this host's role is denied `ecs:DescribeTaskDefinition`, so it stays Ramon's command from 60c18a2. Steps 3 (pull ddp-sync #311 and restart, not rebuild) and 4 (#488 manifest rollout) wait for step 1's result, #488 being merged, and his go. I record the "before" counts for the Arizona tables before step 4.
