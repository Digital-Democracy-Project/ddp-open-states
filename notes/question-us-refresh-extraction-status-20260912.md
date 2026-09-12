# Status check: how's the `us refresh-extraction --commit` run going?

Ramon says it's running right now -- can you post an update here? Specifically:

- Current progress (how far through, any live counts you can see)
- Whether it's holding steady this time (no repeat of the earlier dropped-DB-connection
  issue) or showing any signs of the same problem recurring
- ETA if you have one

This also feeds directly into `PLAN-rds-data-quality-backfill.md`'s own Step 3 and, in turn,
OPEN-193's AC6 (a jurisdiction confirmed "genuinely, currently RDS-fed") -- once `us` (or
any of VA/UT/WA/MI) converges, that unblocks OPEN-276's allowlist pilot and, downstream,
OPEN-275/277 in the OPEN-269 epic. So a clean finish here matters beyond just this one
backfill.
