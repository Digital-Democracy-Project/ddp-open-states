# status: WY, NE, UT re-imports STARTED on v90 (rev 92) at 22:06 UTC; MO loaded, MO archive by hand; KY archive counts; HI loading

Ramon's go in my session (pop-up ~22:05 UTC: "Wyoming, Nebraska, Utah" and "Oklahoma 2025+2026 later"; Rhode Island NOT chosen, so on hold as you recommended).

## v90 re-imports (all 202, "full": true)
- wy?full=true&sessions=2026, ne?full=true&sessions=109, ut?full=true&sessions=2026,2025S2, started 22:06:0x UTC. describe-tasks at +20 s: **wy, ne and ut all on ddp-scrapers:92** (v90). Host before: load 0.65 / 0.94 / 1.35, 7.0 of 15.7 GB memory used; at 22:07 load 1.79 / 1.18 / 1.41. Runs at once: wy, ne, ut, ia, ok, me archive, hi load.
- **Oklahoma:** Ramon said "later". Its current 2026 run (ok-3f164c3f15c1, rev 91) is still collecting; I start `ok?full=true&sessions=2025,2026` only after it ends (the dev's rule), then report the revision (must be 92 or later). RI: on hold.

## MO (mo-0c93ebb3992f, rev 91, loaded on core 70146fac)
- collection done 21:56:07, "done" 22:01:36, duration 6,339.4 s (load about 5.5 min). Resumed run, so no archive started by itself; I started openstates-archive/mo by hand at 22:06:48 (202). End line to come.

## KY archive (started by hand 21:00:59)
- ddp-sync: "openstates_archive: fargate task done duration_seconds=91.2", archiver_triggered_legbot_skipped_legbot_replica_off. The task's own line (CloudWatch): `ky: 1737 bills checked | fetched=0 skipped=2561 archived=0 fetch_errors=0 blocked=0 extract_errors=0 conflicts=0 concurrent_writes=0 s3_verified=0 s3_unverified=0 persist_errors=0`. As with Idaho's, skipped counts versions whose documents already exist.

## Still running
- HI (hi-715d5f8d0991): collection done 22:00:26, loading. IA (ia-7cd1e13ac328, rev 90) and OK 2026 collecting. Maine archive (20:32 start): no end line yet at 22:07 (about 95 minutes; Maryland's took 86).
