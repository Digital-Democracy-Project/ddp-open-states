# Both PRs open for the vote-person backfill Fargate wiring -- awaiting review/merge

**Re:** `hr9576-backfill-wire-into-existing-fargate-trigger-20260922.md` (this branch).
**Jira:** SYNC-74, linked to VOTEBOT-7/OPEN-2.

Filed a small parallel trigger route rather than a fourth `ALLOWED_SUBCOMMANDS` value on the
existing `openstates-backfill` endpoint, since `backfill-vote-person-resolution.py` has a
genuinely different CLI shape (no jurisdiction/subcommand, just `--dry-run`/`--commit`).

* `ddp-open-states` #257: https://github.com/Digital-Democracy-Project/ddp-open-states/pull/257
  -- `backfill-vote-person-resolution.py` connects via `DATABASE_URL` when set, copied into the
  deployed image alongside `cloud_collector.py`/`cloud_archiver.py`/`cloud_text_extract.py`.
* `ddp-sync` #164: https://github.com/Digital-Democracy-Project/ddp-sync/pull/164 -- new
  `POST /trigger/vote-person-backfill?mode=dry-run|commit`, modeled directly on
  `openstates_backfill.py`'s existing `run_backfill_job`/`trigger_openstates_backfill`. 10 new
  tests, full suite (1303 tests) green, ruff clean.

**Nothing merged yet, nothing run against real RDS.** Once both are reviewed and merged (and the
`ddp-scrapers` image rebuilt so the script actually lands in `/app/`), the flow is:

```
POST /trigger/vote-person-backfill?mode=dry-run
```

Report the counts back here, same as the earlier local test (23,047 unresolved rows found,
19,803 would resolve against this Mac's replica -- real RDS numbers will differ). Once that
looks sane, `?mode=commit` applies it for real.

Reply on this branch as usual once you've had a look / once it's merged and run.
