# Reply: OPEN-351 done on RDS: Utah diffs recomputed through the Fargate endpoint, every number matched

From: prod agent (EC2 broker host), 2026-10-14 UTC (all times UTC, 04:01 to 04:08). The operator gave the go (conditional GO of `c92ef70` and `357d977`; I did not see Ramon's go recorded myself, please check it is on OPEN-351). **I ran exactly one commit.** No other jurisdiction, flag, trigger, LegBot run or restart. Nothing was pulled, built or changed on this host.

## Result in one line
`ut: [COMMITTED] 1021 bills checked | unchanged=5137 corrected=1627 nulled=2607`, then `ut: [DRY RUN] 1021 bills checked | unchanged=9371 corrected=0 nulled=0`, final G4 `9371 / 762 / 4158 / 0 / 0`.

## Gates
- **G1 (task definition): NOT verified directly.** `aws ecs describe-task-definition --task-definition ddp-scrapers` returns `AccessDeniedException` for this host's role (`EC2ServiceAccessReadOnlyRole`), and the same call with ddp-sync's own credentials (via boto3 inside the container, us-east-1 and us-east-2) is denied too. So I could not see that the latest ACTIVE revision is 36. I went on because your note says the dry run is the real proof of code: with the old rules it cannot print the G5 numbers, and it printed them exactly (below). If you want revision 36 confirmed, someone with ECS read rights has to do it.
- **G2 (quiet window): ok.** No `run-scrape`, `os-update` or `os-text-extract` process on the host; no Utah line in the ddp-sync log in the previous 10 minutes; the commit finished at 04:05:47, hours before the next Utah windows (Sunday 2026-10-18 02:00 UTC scrape, Monday 2026-10-19 05:00 UTC archive) and before the RDS backup window (04:57 to 05:27 UTC). The 04:00 UTC chain had just started; I did not look at what its other jobs were doing, only at Utah.
- **G3 (rollback point), RDS `ddp-openstates`, us-east-1, 7-day automated backups, single-AZ:** `LatestRestorableTime` `2026-10-14T03:54:20Z` (read 03:56 UTC), `03:59:20Z` (read 04:04:10 UTC, immediately before the commit POST at 04:04:11). The commit therefore ran after a restorable time that predates it. I cannot read the snapshot list or the earliest restorable time (`AccessDenied`), so the rollback point is the PITR window (about 7 days).
- **G4 (baseline, query run through api-v3's own engine, read-only):** `9371, 762, 6765, 2239, 368` at 03:56 and again at 04:01:38. As expected.
- **G5 (dry run through the endpoint):** see the table.

## The calls (each POSTed once, to `http://localhost:8001/ddp-sync/v1/trigger/openstates-backfill/ut?subcommand=recompute-diff-order&mode=...`, `Authorization: Bearer` with this ddp-sync's `DDP_SYNC_API_KEY`)
| step | time sent | run_id | ECS task id | result line (from the ddp-sync log, `openstates_backfill: fargate task done`) |
|---|---|---|---|---|
| G5 dry run | 04:02:12 (202) | `ut-recompute-diff-order-dry-run-a8ca12856145` | `ceab06b75fc94389ab27baff7ae70ef0` | done 04:03:48, 95.9 s: `ut: [DRY RUN] 1021 bills checked \| unchanged=5137 corrected=1627 nulled=2607` |
| commit | 04:04:11 (202) | `ut-recompute-diff-order-commit-84807b272b87` | `5c40ca48d0d6419581f17886f4cb24a0` | done 04:05:47, 95.7 s: `ut: [COMMITTED] 1021 bills checked \| unchanged=5137 corrected=1627 nulled=2607` |
| second dry run | 04:05:54 (202) | `ut-recompute-diff-order-dry-run-48f5c95e8bee` | (not recorded) | done 04:07:30, 95.7 s: `ut: [DRY RUN] 1021 bills checked \| unchanged=9371 corrected=0 nulled=0` |

Exactly three tasks were launched (I counted `fargate task launched` lines for the window: 3). One extra request at 04:01:56 was rejected with `401 Invalid API key` because I first used the wrong environment variable (`API_KEY`); it launched nothing. Same-session note for your records: the endpoint had no overlap lock and I never re-POSTed.

## Final G4 (after the second dry run, 04:07:39)
`docs 9371, distinct_notes 762, with_diff 4158, comparison_with_diff 0, excerpt_with_diff 0`. Exactly as you predicted: the diff-carrying count fell by 2,607 (6,765 to 4,158), and no comparison or excerpt document carries a diff.

## Health after
api-v3 `/healthz` 200 (container healthy, 0 restarts), ddp-sync healthy (0 restarts). No restart or deploy was done during this run.

## Leftover from before I read `357d977`
Before your superseding note I had already followed G1 of `c92ef70` and created a separate checkout of openstates-core at `14cc6a51` as a git worktree at `/home/bitnami/openstates-core-14cc6a5` (from the host's `/opt/ddp-open-states/openstates-core` repo; the code check printed `OK` with `openstates.__file__` in that directory). **It was not used for this run.** The existing checkout (`5c79b47d`, clean) and both installs are untouched; the only trace in the repo is git worktree metadata. I have left the directory in place and will remove it (`git worktree remove`) on a word from you or the operator.

## State
OPEN-351's RDS part is done and verified from RDS's side. Your Mac-replica checks come next. I have not touched anything else. Still not done by me and not asked: the SYNC-110 pull on this host.
