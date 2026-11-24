# status: RI stale docs COMMITTED; GA and AL roll-call backfills APPLIED; KY, HI, MO re-imports started 19:52 UTC on rev 91 (v89)

Ramon's go in my session (pop-ups ~19:50 UTC): RI stale removal, About logo (done, broker branch), KY/HI/MO re-imports, GA and AL backfills.

## RI remove-stale-documents (core 59dbdaa2)
- Dry run again first (identical), then `--commit --expect 3011`: [COMMITTED] documents=6389 stale=3011 removed=3011 kept_last_copy=0 kept_no_file_hash=0; after: documents=3378, distinct (bill, address)=3378, removed_versions=3011. List ops/ri-stale-commit-20261124.csv (3,011 rows). Exit 0. Not run: RI's relabel and recompute dry runs (e30bb8e steps 5 to 7: they need core 0d373728+ on the host, i.e. after the ddp-sync rebuild).

## GA and AL roll-call number backfills (/opt/ddp-open-states pulled b7dbefb1; backfill-vote-rollcall-num.py)
- **ga:** dry run: 280 records (house 245, senate 35), list md5 ea69e3715f5f7aff2058844b0b198e5f = yours. `--apply-list ... --expect 280 --list ...committed`: "Done. Updated 280 records." Second dry run: already numbered 280, would update 0.
- **al:** dry run: 2,550 records (house 1,359, senate 1,191), md5 ad12bf8301a199efd315c92ddf999275 = yours. Apply `--expect 2550`: "Done. Updated 2,550 records." Second dry run: already numbered 2,550, would update 0.
- Lists kept for --undo: ops/rollcall-ga-committed-20261124.csv, ops/rollcall-al-committed-20261124.csv. Nevada's `--nv-result` backfill not run (needs v89 live; the NELIS list file is on your side).

## Re-imports started 19:52:07 UTC (all 202, "full": true, rev 91 = ddp-scrapers:91 per describe-tasks)
- ky?full=true&sessions=2026RS (after its people load), mo?full=true&sessions=2026, hi?full=true&sessions=2026. Together with OK (rev 90) and IA 2026 (rev 90) still running: 5 at once.
- Host at 19:53: load 1.78 / 1.97 / 1.62, 6.9 of 15.7 GB memory used. Highest so far: 5 runs. No loader failure, no RDS error. Loader core is still 59dbdaa2.
- **ddp-sync rebuild (70146fac, b2aa844d) still waits** until every run has finished loading; my watcher covers OK and IA only, so I will wait for KY, HI and MO too. IA 2025 held until after the rebuild.

## Not started
- ND refresh-extraction dry run and RI relabel/recompute dry runs (need the rebuild), Maine archive, Nevada backfill, WY (OPEN-874 image), NE people (OPEN-877 fix).
