# Closing out for the night — Glacier restore is the priority when either of us picks this back up

*Replies to `notes/rds-backfill-paused-deep-archive-restore-20260904.md`.* Nothing for you to do
right now — recording status before I stop for the night, since this is now the top item for
whoever (you or me) picks it back up next.

## What's running

Ramon started an S3 Batch Operations restore against the **entire** `ddp-bill-archive` bucket
(199,240 objects, 52.2 GB) 2026-09-04, described as Standard tier, to be followed by a second
Batch Operations copy job re-tiering everything to Glacier Instant Retrieval permanently — not
just the UT/WA documents `refresh-extraction` happened to flag, and not a one-off restore-and-
retry. Rationale: since essentially the whole pre-OPEN-192 archive is Deep Archive (confirmed by
your dry-run — 100%/99.99% for UT/WA), this fixes the underlying condition once instead of
hitting the same 12h-per-restore wall on every future backfill. One-time cost is small (~$25-30,
dominated by per-request fees on ~200k mostly-small objects, not data volume).

## One open discrepancy — worth confirming when checking completion

Your note estimated ~2 days, which is Bulk-tier timing; the batch job was described to me as
Standard tier (~12h). Don't trust either estimate — when you check back, confirm actual restore
completion by checking real object state (e.g. `HeadObject`'s `Restore` field on a sample), not
by waiting out a number.

## Sequence once the restore is actually done (recorded in full in
`PLAN-rds-data-quality-backfill.md`'s new status section, ddp-infra)

1. Confirm restore completion for real (see above).
2. Run the Batch Operations copy job (`StorageClass=GLACIER_IR`) before the restore window
   expires — restoring only makes objects temporarily readable, it does not change permanent
   storage class on its own.
3. Re-run `refresh-extraction ut/wa/us --dry-run` against RDS for a real evaluation (not just
   Deep-Archive-skip counts) — this is the number that actually tells us what's stale vs. clean.
4. Proceed with the plan's §4 `--commit` sequence once Step 1 comes back clean.

Jira and the plan docs are all updated to match (OPEN-193 comment, `PLAN-rds-data-quality-
backfill.md`, `PLANS-INDEX.md`) — nothing new to communicate there, just flagging so you're not
duplicating the write-up if you get to this before I'm back.
