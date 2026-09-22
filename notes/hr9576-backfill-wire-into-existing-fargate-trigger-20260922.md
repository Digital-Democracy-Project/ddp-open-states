# Please wire backfill-vote-person-resolution.py into the existing Fargate-trigger pipeline instead -- don't need a new Secrets Manager grant

**Re:** `hr9576-resolution-run-the-backfill-against-rds-20260921.md` (this branch). Ramon's call,
and a good one -- the proposed approach (a human on this EC2 host manually resolving a live RDS
credential via `RESOLVE_RDS_LIVE`, pulling `ddp-scrapers:v25` by hand, running a custom wrapper
script) is real friction for something this team already has a clean, established pattern for.

## What we actually hit

Followed the note's instructions: pulled `v25` (confirmed `linux/arm64`-only, needed
`--platform`), wrote the `resolve_rds_database_url()` wrapper exactly as given, ran it with
`--dry-run`. Got `AccessDeniedException` on `secretsmanager:GetSecretValue` -- this EC2 host's own
instance role (`EC2ServiceAccessReadOnlyRole`) has no Secrets Manager permissions at all (same
narrowly-scoped role that's needed explicit grants for CloudWatch Logs and ECR earlier this
thread). Started drafting a scoped `iam put-role-policy` to fix that, then Ramon stopped and
asked why this doesn't look like the earlier `mi/ut/fl/va/wa/us` RDS text-extraction backfills,
which never needed anything like this.

## The actual answer: it doesn't need to, and shouldn't

Those earlier backfills went through `ddp-sync`'s own existing trigger endpoint --
`POST /ddp-sync/v1/trigger/openstates-backfill/{jurisdiction}?subcommand=...&mode=...`
(`ddp_sync/pipelines/openstates_backfill.py`, OPEN-268). Read the source directly: **`ddp-sync`
itself** calls `resolve_rds_database_url()` (line 249) from inside its own already-running
container, then passes the resolved DSN straight into the launched Fargate task as a
`DATABASE_URL` env var (line 108) -- one authenticated HTTP call from a human, zero manual
Secrets Manager access, zero Docker-pulling-by-hand, isolated on its own Fargate task the whole
time. `ddp-sync`'s container evidently already has whatever IAM permissions this resolution
needs (it's doing it live, successfully, on every one of those historical backfill runs) --
completely separate from this bare EC2 host's own instance role, which is deliberately
narrow/read-only.

**Can't reuse that exact endpoint as-is**, though: `ALLOWED_SUBCOMMANDS` there is hardcoded to
`frozenset({"reextract", "refresh-extraction", "recompute-diff-order"})` -- all three from
`os-text-extract`, a different tool operating on bill *text* (`opencivicdata_billdocument`-shaped
data). `backfill-vote-person-resolution.py` is a separate, standalone script targeting
`opencivicdata_personvote` -- genuinely out of scope for that allowlist, not something a
config change would unlock.

## The ask

Wire `backfill-vote-person-resolution.py` into this same pattern -- either:

1. A fourth allowed value alongside `reextract`/`refresh-extraction`/`recompute-diff-order` on the
   existing `openstates-backfill` endpoint (if it's an easy fit -- the script already accepts
   `--dry-run` the same way the other three do), or
2. A small parallel trigger route following the identical shape (launch on Fargate, resolve RDS
   creds inside `ddp-sync`'s own already-permissioned process, pass as `DATABASE_URL`, same
   dry-run-first discipline) if the vote-person script's shape doesn't fit the existing one
   cleanly.

Either way, the point is reusing `ddp-sync`'s already-working credential path instead of granting
raw Secrets Manager access to a general-purpose EC2 instance role for one ad-hoc job.

## Status: holding here, nothing run against real RDS yet

**Did not apply the Secrets Manager IAM grant** (drafted but not attached -- no
`secretsmanager:GetSecretValue` policy exists on `EC2ServiceAccessReadOnlyRole` as of this note).
**Did not run anything against real RDS** -- only against Ramon's own machine per the previous
note's local-replica dry-run (23,047 unresolved rows, 19,803 would resolve; real RDS numbers will
differ). Once the trigger-endpoint route exists, happy to call it and report the real dry-run
numbers back here the same way the text-extraction backfills worked.

Reply on this branch as usual.
