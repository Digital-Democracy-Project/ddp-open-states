# DEPLOY (supersedes G1 and the run command of `c92ef70`): OPEN-351 via the existing Fargate endpoint (dev side, 2026-10-14 EDT)

**STATUS: GO, conditional, same authorization as `c92ef70`** (Ramon's instruction: RDS is edited only by you). A HOLD note from Ramon or me on this branch overrides it.

Your preflight reply (`d95f260`) found that neither host install has the new Utah rules. Good catch, and it makes the "separate checkout" route in G1 unnecessary. **Use ddp-sync's existing OPEN-268 endpoint instead.** It launches a Fargate task from the latest ACTIVE `ddp-scrapers` task definition (now revision 36, image v33, built from openstates-core `14cc6a5`, the exact code the rehearsal ran), resolves the RDS URL itself from Secrets Manager, and is how the September FL/VA/WA/US run was done (`fl-commit-go-ahead-via-fargate-20260911.md`). **No install on the host is touched and no code is pulled or built.** Do not use host installs A or B for this.

## Gates (replaces G1; G2 to G4 of `c92ef70` stay as written)
- **G1 (new): confirm the task definition.** The latest ACTIVE `ddp-scrapers` revision is 36 (`aws ecs describe-task-definition --task-definition ddp-scrapers`). If it is not 36, stop and report. The dry run below is the real proof of code: with the old rules it cannot print the numbers in G5.
- **G2:** quiet window, at least an hour clear of Sunday 02:00 UTC and Monday 05:00 UTC; no Utah scrape/archive/load in flight.
- **G3:** record the rollback point (LatestRestorableTime) and confirm it predates the commit. Record it again just before the commit.
- **G4:** baseline SQL from `c92ef70`; expect **9,371 / 762 / 6,765 / 2,239 / 368**.
- **G5: dry run through the endpoint** (writes nothing):
  ```bash
  curl -X POST "http://localhost:8001/ddp-sync/v1/trigger/openstates-backfill/ut?subcommand=recompute-diff-order&mode=dry-run" \
      -H "Authorization: Bearer $DDP_SYNC_API_KEY"
  ```
  The endpoint returns 202 and a `run_id`; the task's summary line appears in the ddp-sync log (`openstates_backfill: fargate task done ... output=...`). It must be exactly **`ut: [DRY RUN] 1021 bills checked | unchanged=5137 corrected=1627 nulled=2607`**. Anything else, even slightly: do not commit; report the line and wait.

## The run (only if G1 to G5 all passed)
1. **POST exactly once** (the endpoint has no overlap lock, and nothing else prevents a second launch):
   ```bash
   curl -X POST "http://localhost:8001/ddp-sync/v1/trigger/openstates-backfill/ut?subcommand=recompute-diff-order&mode=commit" \
       -H "Authorization: Bearer $DDP_SYNC_API_KEY"
   ```
   Output must show the same three numbers (`[COMMITTED]`). Name `ut`; never `all`. If you get no answer, check the log and the ECS task list before ever POSTing again.
2. Immediately dry-run again (same dry-run call). It must print **`unchanged=9371 corrected=0 nulled=0`**.
3. Re-run the G4 query. Expect **9,371 / 762 / 4,158 / 0 / 0**.
4. Nothing else: no other jurisdiction, no flag, no trigger, no LegBot, no restart.

If the commit's numbers differ from G5, the task errors, or it stops partway: stop and report with the output. No retry and no rollback without authorization.

## Reply
On this branch: the task-definition revision seen, backup timestamps, G4 rows, each call's `run_id`, exact output lines and times, final query rows. I then verify the Mac replica read-only (Utah diffs 4,158, comparison/excerpt diffs 0, stamped Amended order, 2,042 changelog transitions). Not authorized: everything in section 5 of `c92ef70`.
