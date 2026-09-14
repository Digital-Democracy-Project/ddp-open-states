# NC's real root cause found -- it's not NC-specific: RDS_CREDENTIALS_SECRET_ARN is missing on the Mac, breaking every jurisdiction's Fargate archive launch

Dug into your `nc-document-metadata-gap-found-20260914.md` note. Found the actual mechanism,
confirmed directly in code and logs, not inferred from the table alone.

**The real bug: `_run_archive_fargate()` (`openstates_archive.py`) calls
`resolve_rds_database_url()` unconditionally, first thing, before every jurisdiction's Fargate
launch attempt -- no jurisdiction-specific branching at all:**

```python
rds_url, rds_error = resolve_rds_database_url()
if rds_error:
    error = f"cannot resolve an RDS target: {rds_error}"
    logger.error("openstates_archive: fargate launch refused", jurisdiction=jurisdiction, error=error)
    return {"success": False, "error": error, ...}
```

**`RDS_CREDENTIALS_SECRET_ARN` is not set in the Mac's `ddp-sync/.env`** (confirmed directly,
grep returns nothing). Log evidence, the Mac's own `ddp-sync.log`, three consecutive days,
three different jurisdictions, identical error:

```
2026-09-11 01:00:00 [error] openstates_archive: fargate launch refused
  error='cannot resolve an RDS target: RDS_CREDENTIALS_SECRET_ARN not set -- refusing to guess which secret to read' jurisdiction=ma
2026-09-12 01:00:00 [error] openstates_archive: fargate launch refused
  error='...same...' jurisdiction=al
2026-09-13 01:00:00 [error] openstates_archive: fargate launch refused
  error='...same...' jurisdiction=us
```

Every jurisdiction that's had its daily 01:00 EDT (05:00 UTC) archive slot fire since the
Fargate cutover took effect (`use_fargate: true` merged 2026-09-10 21:13 EDT, after that day's
01:00 slot already ran under the old path) has failed at launch, the same way, for the same
reason. This is not NC-specific -- NC is just the one jurisdiction where it's *visible*.

**Why NC's zero rows stood out while every other jurisdiction's table still "looks fine"**:
checked the Mac's own local Postgres directly -- **NC has zero bills there at all** (MI, by
contrast, has 3,692). NC's real data has only ever lived in RDS (confirmed by your own note's
"6192/6192" catch-up reference and OPEN-231 Stage 4). Every other jurisdiction has real,
pre-cutover rows already sitting in `ddp_bill_version_document` from before this broke, so
their tables don't read as empty -- they just silently stopped getting *new* rows. MI's own
"real weekly entries through Sep 10" you found is consistent with this, not evidence against
it: Sep 10 01:00 EDT is *before* the Fargate flag flipped that same evening, so that's plausibly
MI's last real archive write too, not a still-working case. Worth a direct recency check on MI
(and fl/ut/az/wa/va/ma/al -- everyone) to see whether anyone has gotten a fresh row since the
cutover, or whether this has been silently producing nothing new for everyone since 9/10-9/11.

**This is the same missing value as an earlier thread this session**
(`RDS_CREDENTIALS_SECRET_ARN request is moot -- dropping the content check instead`, PR #150)
-- but that was for an *optional* LegBot freshness check that could be safely dropped instead
of configured. This is a different, load-bearing consumer of the exact same missing value:
archiving itself can't be routed around the same way once `use_fargate: true` is live. The
earlier "moot" resolution doesn't apply here -- this one genuinely needs the real ARN set.

**The actual ask**: same as before -- I can't discover the real Secrets Manager ARN from the
Mac (no AWS console/CLI access to look it up). Could you find the RDS instance's own credential
secret in Secrets Manager (likely an auto-rotated `rds!...`-style ARN, based on
`resolve_rds_database_url()`'s own comment about "RDS's own automatic 7-day credential
rotation") and get `RDS_CREDENTIALS_SECRET_ARN` set in the Mac's `ddp-sync/.env`, then a
restart? Once it's set, every jurisdiction's next scheduled Fargate archive launch should
start succeeding, not just NC's.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
