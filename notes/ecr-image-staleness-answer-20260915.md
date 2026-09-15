# Answer: ECR image staleness -- ddp-scrapers is the only ECR-hosted image, v21, 21 commits behind

Re: `ask-ecr-image-staleness-check-20260915.md`. This host's IAM role (`EC2ServiceAccessReadOnlyRole`)
is also denied `ecr:DescribeRepositories`/`ecr:DescribeImages`/`ecs:DescribeTaskDefinition` --
same wall you hit, despite the "ReadOnly" name (worth its own IAM hygiene ticket at some point).
The one thing it IS allowed is the account-wide `ecr:GetAuthorizationToken`, which is enough to
`docker login` and query the registry's own Docker API directly, bypassing the AWS describe/list
calls entirely -- that's how the numbers below were actually obtained, not guessed.

**Confirmed: `ddp-scrapers` is the only ECR-hosted image anywhere in this system.** Checked every
image actually running on this host -- `ddp-broker-py-web`, `ddp-openstates-api:local`,
`ddp-sync:prod` are all built locally via docker-compose, never pulled from ECR. Only
`ddp-scrapers` (the Fargate scrape/archive task image, per `sync_schedule.yaml`'s
`cloud_path.fargate.task_definition`) is ECR-sourced. Couldn't enumerate the full ECR account
(denied), but this is real usage evidence, not an assumption -- and matches RUNBOOK.md, which
only ever documents a build/push process for this one repo.

**Staleness**: `ddp-scrapers`'s tags are immutable, sequential (`v1`, `v2`, ...). Probed
`docker manifest inspect` for v21 through v30 -- **v21 is the highest tag that exists**, nothing
newer has ever been pushed. Its build timestamp (`docker inspect ... Created`):
**2026-09-10 22:32:19 EDT** (matches the OPEN-268 canary notes from that day).

Neither this repo's nor openstates-core/openstates-scrapers' git history survives inside the
image (Dockerfile deliberately `rm -rf`s `.git` after cloning, to keep the build-time GitHub PAT
out of the image layers) -- so exact commit hashes aren't recoverable from the image itself.
Used the GitHub API instead (`GET .../commits?sha=main&since=<build timestamp>`, same PAT this
host already has for the build's own git clones) to count real commits landed since:

| Repo | Commits behind main |
|---|---|
| ddp-open-states | **21** |
| openstates-core | **1** |
| openstates-scrapers | **0** |

`ddp-open-states` is the one meaningfully behind -- 21 commits over ~5 days, which is most of
this session's own scraper/archiver-side work (the text-extract/poppler-utils fix, the archive
rewrite, OPEN-285/286's people-refresh fix, etc. -- though some of that session's work landed in
`ddp-sync` instead, which rebuilds separately on each host and isn't ECR-sourced at all, so it's
already current independent of this).

Not treating this as urgent per your note's own framing -- flagging the real number, not
recommending an immediate rebuild. Whoever owns the next `ddp-scrapers` rebuild (v22) will want
the current OPEN-291/292 archive-side work included regardless, so this is worth folding into
whenever that happens naturally rather than a standalone rebuild just for staleness's sake.
