# OPEN-193 — request: deploy, configure, and canary-test the new Fargate/RDS trigger

Phase 2 (OPEN-191, database + api-v3 cutover) has been re-blocked since 2026-09-01: its own
"keep loading to both, permanently" rollback policy was decided but never implemented, and RDS
has had no ongoing feed since the one-time 2026-08-29/30 rehearsal. Rather than build a
throwaway dual-write bridge just to unblock Phase 2 early, Ramon decided the same day that the
cutover waits until Phase 4 (OPEN-193) actually lands — stand up `ddp-sync` on EC2 for real,
trigger scraping via the already-proven Fargate path, load straight into RDS. This note is that
handoff: the ddp-sync-side code is written and tested, but everything past that needs
production AWS access this checkout doesn't have.

## What's already done — the code

`ddp-sync` PR **#104** (branch `feat/open193-cloud-scrape-trigger`,
https://github.com/Digital-Democracy-Project/ddp-sync/pull/104), reviewed once through
`pm_review_artifact` and fixed up (see the PR's own comment for what that round found and how
it was triaged — an uncaught-exception gap, an orphaned-ECS-task-on-timeout gap, and a
missing loader timeout, all real and fixed; a same-jurisdiction concurrency lock was judged
redundant with one `cloud_collector.py` already has, and a full activation checklist is this
note instead of new code).

`_run_scrape()`'s cloud-path branch (`_cloud_path_owns()`, OPEN-208) used to just skip a
cloud-owned jurisdiction and do nothing — every cloud-owned run so far (the OPEN-191 rehearsal)
was a human running `aws ecs run-task` and `cloud_loader.py` by hand. The PR replaces that with
a real trigger: launch the Fargate task (`cloud_collector.py`, OPEN-201), poll it to
completion, and on success run `cloud_loader.py` (OPEN-190) against RDS specifically via a
dedicated `RDS_DATABASE_URL` env var — never `DATABASE_URL`, which stays the local Postgres URL
for every jurisdiction still Mac-owned. **Neither `cloud_collector.py` nor `cloud_loader.py`
were touched** — both already exist in this repo and are already proven correct by the
rehearsal (`infra/rds/README.md`); the PR only builds the missing piece, an automated caller.

`sync_schedule.yaml`'s `cloud_path.fargate` block (cluster/task_definition/subnets/
security_groups/container_name/memory_bucket/memory_prefix/max_wait_seconds/
load_timeout_seconds) was added with every value blank or a generic default — this checkout's
`ddp-scraper` credential can't see far enough into the account to know the real ones, and
`cloud_path.enabled` stays `false` with no jurisdiction listed, so **merging PR #104 alone
changes nothing in production**. 1025 tests pass, ruff is clean.

## What's needed from your side

### 1. Review and, if it holds up, merge PR #104

Independent review, the same way PR #207/#208/#213 got it on this branch before — I'm not
merging my own PR (standing rule). The PR body and its pinned comment cover what pm-review
found and how each finding was triaged; happy to answer follow-ups here if anything reads as
under- or over-scoped from where you're sitting.

### 2. IAM — the EC2 instance role `ddp-sync` runs under needs, and doesn't yet have

- `ecs:RunTask` / `ecs:DescribeTasks` / `ecs:StopTask`, scoped to the existing
  `ddp-scrapers-prototype` cluster and `ddp-scraper-prototype` task definition family (same
  scoping pattern as `infra/fargate-spike/README.md`'s own bootstrap policy).
- `iam:PassRole` for the task's `execution_role_arn`/`task_role_arn` (required by
  `RegisterTaskDefinition`/`RunTask` when overriding container command/environment — see that
  same README for the exact two ARNs already in use).
- Whatever RDS credential `cloud_loader.py` should connect with, injected as
  `RDS_DATABASE_URL` into `ddp-sync`'s own process environment (`infrastructure/ddp-sync.service`
  or however its env is currently supplied on EC2) — **not** into `sync_schedule.yaml`, which
  never carries credentials. `infra/rds/README.md`'s own gotcha about the Secrets Manager
  password needing `urllib.parse.quote()` before it's valid in a `postgresql://` URL still
  applies here.
- `secretsmanager:GetSecretValue` if that RDS credential is going to be fetched at deploy/start
  time rather than baked in by hand — your call on which pattern matches how the other
  EC2-hosted jobs (Webflow CMS, Pinecone, Brevo) already get their own credentials.

`ddp-scraper` (this checkout's own credential) deliberately gets none of this — see OPEN-240's
closure. The whole point of doing this on EC2 is that production RDS access never touches the
dev Mac's shared interactive credential.

### 3. Fill in the real config

In `sync_schedule.yaml` on the EC2 deploy, `cloud_path.fargate`:

```yaml
cloud_path:
  enabled: false          # flip per-jurisdiction below, once the canary in step 4 passes
  jurisdictions: []
  fargate:
    cluster: ""            # real value, e.g. "ddp-scrapers-prototype"
    task_definition: ""    # real value, e.g. "ddp-scraper-prototype" or "...:<revision>"
    subnets: []             # the private subnet IDs the existing Fargate task already uses
    security_groups: []     # the security group IDs already allowing egress to source sites + RDS
    memory_bucket: ""       # the same MEMORY_BUCKET the existing task definition's env already names
```

`container_name` (`"scraper"`), `memory_prefix` (`"prod"`), `max_wait_seconds` (12h),
`load_timeout_seconds` (2h) are already reasonable defaults in the PR — override only if
something about the real deploy needs a different value.

### 4. Canary one jurisdiction before flipping the fleet

Pick something small and NOT Michigan — MI is the fleet's most WAF-sensitive jurisdiction and
the wrong place to find a bug in a brand-new trigger path (per the standing scraping-resilience
practice). FL or a single small state is a better first real run.

1. List that one jurisdiction under `cloud_path.jurisdictions`, `enabled: true`, restart the
   `ddp-sync` systemd service so it picks up the new config.
2. Trigger it — either wait for its next scheduled run, or use the existing manual endpoint
   (`POST /trigger/openstates-scrape/<state>`, which funnels through the same `_run_scrape()`
   this PR changed, so it exercises the identical code path a scheduled run would).
3. Watch: the ECS task actually launches (console or `aws ecs list-tasks --cluster ...`), stops
   with exit code 0, and `ddp-sync`'s own logs show `cloud_scrape: done` with a `cloud_run_id`.
4. Confirm the load landed: row count for that jurisdiction in RDS before/after (should
   increase or stay flat with `noop`s, never decrease or duplicate — matching the rehearsal's
   own zero-duplication result), and a spot-check bill via api-v3 against RDS.
5. If it fails anywhere, the dict `run_cloud_scrape()` returns (and `ddp-sync`'s own
   Slack/CAMS alert, which now fires from inside this path too — see the PR, `cloud_collector.py`/
   `cloud_loader.py` have no alerting of their own) should say which stage failed and why.

### 5. Report back here

Whichever way it goes — clean pass, or something the canary surfaces that the PR's tests didn't
catch. If it's the latter, this branch has been the right place for exactly that kind of
catch on every PR before this one (#207/#208/#213); no reason to break that pattern now.

## Why this is the fix, not a bridge

OPEN-191's freshness gap only closes once something keeps RDS fed on an ongoing basis. Building
a throwaway dual-write mechanism just to let Phase 2 go first would mean the same amount of
work happening twice, and it would put production RDS credentials on the dev Mac's shared
interactive credential to verify it — the exact thing OPEN-240's closure was about avoiding.
This is the real fix, done once.
