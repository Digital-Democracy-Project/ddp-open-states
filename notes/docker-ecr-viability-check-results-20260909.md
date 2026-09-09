# Docker/ECR viability check for the "run refresh-extraction via the scraper image" idea

*Replies to `notes/check-docker-availability-on-host-20260909.md`.* Ran the three checks, no
pull attempted. Mixed result — one clean blocker, one real constraint to weigh.

## 1. Docker itself: yes, usable

`docker --version` → `20.10.5+dfsg1`. `docker ps` works with no `sudo` needed, currently running
`ddp-sync`, its buildx builder, `ddp-openstates-api`, and `ddp-broker-py-celery-beat` alongside
whatever else is on this box.

## 2. ECR: blocked, cleanly

This host's instance role (`EC2ServiceAccessReadOnlyRole`) has neither
`ecr:GetAuthorizationToken` nor `ecr:DescribeImages` — `docker login`/`describe-images` both came
back `AccessDeniedException`, not a network or config issue. This is the same shape of gap
[[iam_verify_by_invocation]] already describes: whatever policy exists for this role just never
granted ECR read at all. Would need that added before this idea goes anywhere (the OPEN-200
Fargate-spike IAM policy has an ECR grant already, scoped to a specific repo — something like
that, applied to this role, would probably be enough for `docker pull` without going broader).

## 3. Resources: disk is fine, memory is tight

Disk: 218GB free of 296GB (24% used) — no concern there. Memory: **530MB free / 1.5GB "available"
of 7.7GB total, 5.9GB already in use** by `ddp-sync`, `api-v3`, `ddp-broker-py`, and the buildx
builder daemon that's apparently been running continuously for 6 days. An interactive
`ddp-scrapers` container alongside all of that is a real question, not a formality — worth
sizing what that image actually needs at runtime before assuming it fits, rather than finding
out by OOM-killing something else already running here.

## Bottom line

Not a dead end, but not free either: needs an ECR grant on this role first, and the memory
headroom question answered before it's a real plan rather than a nice idea. No action taken
beyond checking — still treating the RDS re-runs as the priority, per your note.
