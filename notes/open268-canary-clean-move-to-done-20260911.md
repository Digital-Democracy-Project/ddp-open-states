# OPEN-268 canary: clean success — both acceptance criteria met, can move to Done

The `mi recompute-diff-order --dry-run` canary completed:

```
run_id=mi-recompute-diff-order-dry-run-1d0bfe3af172
duration_seconds=368.9
output: mi: [DRY RUN] 3930 bills checked | unchanged=13597 corrected=0 nulled=0
```

`output` came back fully populated (not empty) — the log-fetch fix (waiting for 2
consecutive quiet CloudWatch rounds) holds up against real CloudWatch timing, not just the
unit tests' fake client.

Also checked the numbers are internally consistent, not just non-empty: `mi` was already
fully `--commit`ed earlier this session (`unchanged=11794 corrected=1803`), and
`11794 + 1803 = 13597` exactly matches this fresh dry-run's `unchanged` count, with
`corrected=0` now — exactly the shape you'd expect if the earlier commit landed cleanly and
nothing has drifted since. Good end-to-end sanity check across two separate deploys/sessions.

**Both OPEN-268 acceptance criteria are now met:**
1. `v21` built, pushed, task-def revision 25 registered (done by the dev agent, verified
   independently by me: `python --version` 3.10.21, `pdftotext -v` 22.12.0, digest match).
2. This supervised dry-run canary via `ddp-sync`'s new trigger endpoint — clean.

Recommend moving OPEN-268 to Done.

## Also worth logging: `ddp-sync` itself got rebuilt/redeployed as part of getting here

Ramon authorized this. Full details in
`notes/ddp-sync-rebuilt-canary-in-progress-20260911.md` -- short version: confirmed the
live in-flight `wa` scrape job's completion tracking was durably persisted to Redis before
restarting (OPEN-251's mechanism), confirmed the incoming `main` commits didn't touch this
host's uncommitted local config (`ddp-sync.service`/`docker-compose.prod.yml` staged
changes), restarted via the host's existing `systemctl restart ddp-sync` unit, and directly
confirmed via logs that the `wa` job's tracking survived the restart
(`cloud_scrape: resuming a Fargate job orphaned by a previous restart ... run_id=
wa-4c91389f4f90`).
