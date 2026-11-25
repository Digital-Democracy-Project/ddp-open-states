# status: first launch from db:22 PASSED; RI re-import done; IA 2026 archive done and IA 2025 started; read-only network check (7f491a5): given to Ramon in session, no 0.0.0.0/0

## First launch from ddp-scrapers-db:22 (9e6ef40 step 2): PASSED
- The watcher saw the first task on db:22 RUNNING at 00:23:32 UTC; it STOPPED at about 00:24:09 with `stopCode EssentialContainerExited`, container **exit code 0**. It was **RI's archive** (ddp-sync: "openstates_archive: fargate task done duration_seconds=91.2 jurisdiction=ri" at 00:24:57, "archive_after_scrape_succeeded attempt=1"). So ECS read the stored secret with the execution role and started the task; no launch error. The archive still got DATABASE_URL from ddp-sync, as you described. The names-only read-back of db:22 and ddp-scrapers:95 stays Ramon's (this host cannot read task definitions).

## RI (ri-3a21d1532e44, ddp-scrapers:94 = v92)
- collection done 00:18:22, load done 00:23:25 (duration 2,097.6 s in all), archive 91.2 s, `openstates_pipeline: done archived=True duration_seconds=2190.7 failed=0 sessions=1 status=completed`. Your pass lines are yours to read on the replica. The loader core was still 70146fac (the a7035d68 restart has not fired).

## IA
- IA 2026 archive (started by hand 23:29:23): done 00:25:33, 3,369.9 s, `archiver_triggered_legbot_skipped_legbot_replica_off`, `archive_after_scrape_succeeded`. Counts line not read.
- **IA 2025 started 00:26:13 UTC** (`ia?sessions=2025`, 202), task on **ddp-scrapers:95 (v93)**, as Ramon had approved.

## Hawaii and restart
- HI people already loaded (my earlier note). The HI archive (db:19, since 22:29:58) is still running and holds the guarded ddp-sync restart (core a7035d68). The second HI re-import waits for that and Ramon's go.

## 7f491a5 (read-only network exposure check): **given to Ramon in session.** **No 0.0.0.0/0.**
