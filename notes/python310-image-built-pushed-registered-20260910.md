# Python 3.10/bookworm image built, pushed, and registered — task-def revision 24 ready

Per the standing build-on-Mac/run-on-EC2 division of labor: built `main` (post-PR #233 merge,
commit `9b1651e`) with `docker build --no-cache --platform linux/arm64`, pushed to ECR, and
registered a new Fargate task-definition revision. Ramon confirmed go-ahead for this before I
touched ECR/ECS.

## What's live now

- **Image:** `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v20`
  (digest `sha256:26e545b980713bbca2330c539f484af958216fa970bd06ab5f4ba0f95e6cbf0b`)
- **Task definition:** `arn:aws:ecs:us-east-1:350941939790:task-definition/ddp-scrapers:24`
- Verified inside the pushed image before registering: `python --version` -> 3.10.21,
  `pdftotext -v` -> 22.12.0
- Everything else in the task definition (env vars, task/execution role ARNs, log group,
  `runtimePlatform` ARM64/LINUX, cpu/memory, network mode) is byte-identical to revision 23 --
  only the image tag changed (`v19` -> `v20`). Built from `aws ecs describe-task-definition
  --task-definition ddp-scrapers` on revision 23, diffed by hand before registering.
- **Revision 23 (`v19`, old Python 3.9/poppler 20.09.0) is untouched and still registered** --
  nothing currently running was disturbed by this; registering a new revision doesn't move
  anything onto it by itself. Rollback is just going back to revision 23.

## What's next (yours, per the earlier handoff)

1. Run the go/no-go check against revision 24: `reextract ma --dry-run` (or a direct
   `run-task` against revision 24 doing the same) and confirm the previously-failing MA document
   now extracts cleanly with no new error classes -- per the release-sequencing plan in
   `notes/python310-bookworm-fix-ready-for-review-20260910.md`.
2. If that's clean, resume the RDS backfill in order: `fl -> va -> wa -> us` (`mi`/`ut` already
   committed), applying the fresh-dry-run-immediately-before-each-commit discipline noted
   earlier.
3. Whatever currently launches scheduled/triggered scraper tasks (ddp-sync's own trigger
   config, if it pins a specific task-def revision rather than always resolving `ddp-scrapers`
   to its latest ACTIVE revision) may need updating to point at revision 24 once you're
   satisfied -- I don't have visibility into that trigger config from this side, so flagging
   it rather than assuming either way.

Not run from this side: no `ecs run-task`, no RDS access, no verification against the real
production database -- staying in the build/push/register lane per the established split.
