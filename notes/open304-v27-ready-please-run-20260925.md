# OPEN-304: v27 built + pushed, task-def revision 32 registered -- please run it

**Thread:** VOTEBOT-7/OPEN-2/SYNC-74/OPEN-304.

PR #258 (with the cross-person lis-collision check you asked for) merged to `main` at
`efcd172`. Built and pushed the image on the Mac per RUNBOOK.md's "Deploying a Fargate image
change" section -- verified before pushing, so this is ready to run.

## What's ready

- **Image:** `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v27`
  (digest `sha256:47f1173b75c0357ae69512c1b612bab49049c7e08a83b3cb2c3f55c178df6b37`)
- **Task-definition revision:** `ddp-scrapers:32`
  (`arn:aws:ecs:us-east-1:350941939790:task-definition/ddp-scrapers:32`)
- **Verified inside the image before push:** `python --version` (3.10.21), `pdftotext -v`
  (22.12.0), and `open304-add-lis-identifiers.py --help` (script present, argparse intact).
- Registering the new revision is additive/inert -- the previous revision is untouched and still
  live, so there's nothing to roll back if this doesn't get run.

## What I need you to do

Run the one-off task against real production RDS, same `RUNNER_SCRIPT`/`DATABASE_URL`
override pattern as the SYNC-74/VOTEBOT-7 backfill:

1. Dry-run first:
   ```
   RUNNER_SCRIPT=open304-add-lis-identifiers.py
   # container args: --dry-run
   ```
   Expect: 14 `WOULD ADD` lines, `0` already present, `0` missing, `0` lis conflicts (matches
   what I got dry-running this same script against the RDS replica copy on the Mac).
2. If that matches, run for real (same `RUNNER_SCRIPT`, no `--dry-run`).
   Expect: 14 `ADDED` lines, same zeroes elsewhere.
3. Report the actual counts back here.

Once you confirm the real run's counts, I'll update OPEN-304 in Jira and mark it resolved.
