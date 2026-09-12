# us refresh-extraction --commit: SUCCEEDED, clean

`run_id=us-refresh-extraction-commit-300e99728ee3`, task
`9ce3c8434684487fb57bb3dbbe15dbf1`. Launched 18:35:47 UTC, finished 22:14:02 UTC
(duration 13096.1s, ~3h38m). ECS task `STOPPED`, essential container exit code `0`.

Real final result, pulled directly from CloudWatch (not the truncated `docker logs`
capture):

```
us: [COMMITTED] bills_with_stale_docs=16560 stale_docs=20343 diffs_corrected=3118 docs_skipped=0 docs_refused=0
```

Clean: `docs_skipped=0`, `docs_refused=0` -- no repeat of the earlier dropped-DB-connection
crash. `pg_stat_activity` showed a real, continuously active connection from the task's own
IP throughout the run.

This closes out `us` alongside mi/ut/fl/va/wa -- all 6 jurisdictions from
`PLAN-rds-data-quality-backfill.md`'s Step 3 now have a clean, committed backfill. Per the
status-check note earlier: this should satisfy OPEN-193's AC6 for `us` (a jurisdiction
confirmed "genuinely, currently RDS-fed"), unblocking OPEN-276's allowlist pilot and,
downstream, OPEN-275/277.
