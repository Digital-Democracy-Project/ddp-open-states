# ddp-sync rebuilt against current main, canary in progress — incremental update

Ramon authorized rebuilding/redeploying `ddp-sync` itself (a step up from what I'd been
scoped to before). Before touching anything, checked whether it was safe given a live
in-flight job:

- `ddp-sync`'s own scheduler had launched a real `wa` scrape (`run_id=wa-4c91389f4f90`) via
  Fargate ~20 min earlier. Confirmed via direct check that its completion tracking is
  durably persisted to Redis (`ddp:inflight_fargate_jobs` hash, `ddp-broker-py-redis-1` DB
  3) by the OPEN-251 mechanism, and that `app.py` calls
  `reconcile_inflight_fargate_jobs()` on startup — so a restart wouldn't orphan it.
- Found real local uncommitted work in the `ddp-sync` checkout (staged changes to
  `infrastructure/ddp-sync.service` and `docker-compose.prod.yml`, an untracked
  `render-env.sh`). Confirmed the incoming `main` commits (through PR #130) don't touch
  either staged file, so a fast-forward `git pull` was safe without losing that work.

**Rebuild executed via the host's existing `systemctl restart ddp-sync`** (its installed
unit already runs `render-env.sh` then `docker compose ... up -d --build` — the standard,
already-established mechanism, not something ad hoc). Result:
- Container recreated cleanly at 02:52:26, no errors.
- **Confirmed by direct log evidence** (not assumed): `cloud_scrape: resuming a Fargate job
  orphaned by a previous restart jurisdiction=wa run_id=wa-4c91389f4f90 task_arn=...` — the
  in-flight `wa` job's tracking genuinely survived the restart.
- `openstates-backfill/{jurisdiction}` now appears in `/openapi.json` — the endpoint exists.

**Canary running now.** Corrected the trigger request per the earlier 404 finding (port
8001, `/ddp-sync/v1/` prefix): triggered `mi recompute-diff-order --dry-run`, got
`run_id=mi-recompute-diff-order-dry-run-1d0bfe3af172`, real Fargate task launched
(`arn:...task/ddp-scrapers/b8f6da9a232b4fbeb1b652ed32348fed`). Task is still `RUNNING` as of
this update (confirmed via `DescribeTasks`, not just assumed) — will report the final
result (and whether the log-fetch timing fix holds up for real) once it completes.
