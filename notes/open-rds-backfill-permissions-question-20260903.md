# RDS is stale relative to the Mac's local Postgres -- do you have RDS write access to fix it?

Ramon asked us to look at how far RDS has drifted from the Mac's local production Postgres since
its seed. Confirmed the seed checkpoint directly (`ddp-prod-s3-openstates-backups ls db/` on the
Mac, not just plan-doc prose): RDS was restored from `openstates_20260829T110005Z.dump`, captured
**2026-08-29 11:00:05 UTC**.

Five closed Data Quality Enhancements tickets backfilled already-bad diff/extraction/procedural-
document data on the Mac's local Postgres *after* that checkpoint -- none of it reflected in RDS:
**OPEN-211** (single-line XML/HTML re-extraction, UT/WA/US), **OPEN-217** (diff-baseline repair,
FL/US then VA/MI), **OPEN-219** (per-jurisdiction text-cleaner fix that unblocked VA/MI), **OPEN-
224** (procedural-document exclusion, VA/UT), **OPEN-246** (VA's committee-amendment exclusion).
Full writeup, scale per ticket, and the exact commands: `PLAN-rds-data-quality-backfill.md`
(ddp-infra PR #130, not yet merged).

Both backfills run through two existing `openstates-core` CLI commands (`os-text-extract
refresh-extraction` / `recompute-diff-order`), both already `DATABASE_URL`-overridable and
`--dry-run`-capable -- no new code needed, just an operator with the right DB target.

**The actual question**: do you (or whatever you run through) have write access to RDS --
`DATABASE_URL` pointed at the `ddp-openstates` RDS instance, reachable through the WireGuard EC2
jump box per `infra/rds/README.md`? `ddp-sync`'s own `RDS_DATABASE_URL` (used by
`cloud_scrape_trigger.py`'s `_run_load()` for OPEN-193's canary loads) is the closest known
credential, but that's scoped to the load pipeline specifically -- unconfirmed whether it's
usable for an arbitrary `os-text-extract` invocation, or whether `openstates-core` is even
installed wherever that credential lives.

Not asking you to run anything yet -- the plan is still DRAFT, unreviewed, and the process it
proposes is dev-rehearse-first regardless. Just need to know whether you're the right operator
for the real run once it's approved, since I have zero RDS connectivity from this dev checkout to
even check myself.
