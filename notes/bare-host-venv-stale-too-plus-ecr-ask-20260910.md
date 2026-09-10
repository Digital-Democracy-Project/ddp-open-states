# Bare-host venv is ALSO stale (same root cause) + requesting ECR pull access — 2026-09-10

## Finding: the RDS backfill has never run inside a fixed toolchain at all

Checked this EC2 host directly while setting up the go/no-go check for rev24: this host
itself is Debian 11 bullseye, `pdftotext` 20.09.0, Python 3.9.2 — identical staleness to
the pre-PR#233 Fargate image. **Every `os-text-extract` command in this whole backfill
thread (including the `mi`/`ut` commits already committed to RDS) ran directly in this
host's own bare venv (`/opt/ddp-open-states/.venv`), not inside any container.** Merging
and redeploying PR #233 to Fargate does nothing for this path — `ddp-sync`'s container is
a different service entirely (it triggers/schedules Fargate tasks, doesn't run
`os-text-extract` itself), so upgrading it wouldn't touch this either (Ramon asked why I
wasn't just doing that; this is the answer).

## Workaround for the go/no-go check specifically

This host's `EC2ServiceAccessReadOnlyRole` lacks `ecr:GetAuthorizationToken` (same gap
noted back on 09-09 during the `v15` push attempt), so I can't `docker pull` the real
pushed `v20` image. Built a throwaway local image instead, straight from `main` post-merge
(`9b1651e`), using this host's own Docker + the existing `GITHUB_PERSONAL_ACCESS_TOKEN`
build secret — no AWS registry permissions needed for a local build against public base
images. Confirmed inside it: Python 3.10.21, `pdftotext` 22.12.0, `os-text-extract` CLI
present and working. Running `reextract ma --dry-run` against this image now
(`--network host`, real RDS `DATABASE_URL`) for the go/no-go check — still in progress,
will follow up with the result.

## Asked Ramon for a permanent unblock: ECR pull access

Requested `ecr:GetAuthorizationToken` + `ecr:BatchGetImage` + `ecr:GetDownloadUrlForLayer`
on this host's role, scoped to `ddp-scrapers` if easy, account-wide read otherwise. This
matters beyond just this check: **the remaining backfill steps (`fl -> va -> wa -> us`)
need to run inside the fixed toolchain too, not this host's stale bare venv** — with ECR
pull access I can run them against the real deployed `v20` image directly instead of a
local approximation that could drift from what's actually on Fargate. Local throwaway
builds are a fine one-off substitute for today's check but not a good long-term plan for
every remaining commit step.

## Not yet resolved

Whether/how to permanently fix `os-text-extract`'s execution environment going forward
(this host's bare venv, once ECR access lands, vs. always running these commands inside a
pulled/local container) — flagging rather than deciding, since it affects how every future
backfill/maintenance run against RDS should be invoked from here on, not just this thread.
