# HOLD: do NOT start the manual scrapes of `1f19165` yet. v60 carries core `e964183b` (OPEN-539's new column), not `96445eb26`, so its archive and text steps need migration `0051` on RDS first. 2026-11-16 (Mac side)

**Supersedes the launch part of `1f19165`.** Nothing else in it changes. If you have already launched any of nc, ne, al or la on revision 63, stop launching more, and report which run ids are running and their state.

**What I found (read-only, on the Mac):**
* The v60 image (`ddp-scrapers:v60`, local image `c4eee8ab2fcb`, the pushed digest) contains `openstates/data/migrations/0051_billversiondocument_diff_baseline_id.py`, and `models/bill.py` has `diff_baseline_id`.
* Its `/opt/openstates-core` matches core **`e964183b`** exactly (OPEN-539, merged 11-16 04:36 UTC). `a774838` said v60 carries `96445eb26`; that was wrong. The image was built from core main after OPEN-539 merged.
* OPEN-539's review: with that core, **every read of `ddp_bill_version_document` fails until the column exists**. That covers the archive, `text_extract`/`refresh-extraction`, `recompute-diff-order` and `remove-stale-documents`.
* Your `35fa65f` says you ran the NC flip and step 7 with core `96445eb26`/`eec94082b` from a worktree, not the image. Those are not affected.

**Also at risk: tonight's scheduled runs on revision 63** (wa 02:30, usa 03:00, pa 04:00 UTC, 11-17). Their archive steps would fail the same way.

## What I need from you (read-only)
1. Has **any** task on revision 63 run since 04:57 UTC? If yes: run id, state, and whether its archive step failed (look for `column ... diff_baseline_id does not exist`).
2. Does RDS have the column? Read-only: `SELECT 1 FROM information_schema.columns WHERE table_name='ddp_bill_version_document' AND column_name='diff_baseline_id'`.

## The fix (waits for Ramon's go; I will post it as a separate GO note)
Migration `openstates.0051` on RDS: one nullable column, no default, index or backfill (`ALTER TABLE ddp_bill_version_document ADD COLUMN diff_baseline_id integer NULL`), with a short `lock_timeout`. It is OPEN-539's release step 1. **Do not run it until that GO note.**

## Not authorized
* Migration 0051 (until the GO note).
* Launching any manual scrape.
* A task-definition change or rollback (that is Ramon's).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
