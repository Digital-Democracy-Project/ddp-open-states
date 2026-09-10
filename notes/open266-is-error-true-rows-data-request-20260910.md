# OPEN-266's last item (35 is_error=True rows): need the specific row identifiers before writing anything

*Follow-up to the status check on OPEN-266's remaining `is_error=True` disposition
(`notes/status-check-open266-rds-backfill-mi-cookie-20260910.md`).* Ramon picked a direction --
a targeted, one-off fix rather than waiting on a bigger tool -- but a real finding changed the
shape of it before any code got written, worth recording here for the thread.

## Correction to the original OPEN-266 write-up: `reextract` already exists

`openstates-core/openstates/cli/text_extract.py` already has a `reextract <state> [--commit]`
command (OPEN-49, merged 2026-08-09) that generalizes OPEN-33's exact mechanism -- reads the
local archive copy first, S3 on a local miss, re-runs extraction, updates `raw_text`/`is_error`
in place, never re-fetches live. OPEN-229 (build this) is effectively already done; the earlier
write-up calling it "unstarted" was wrong, checked directly against the current code.

**It still doesn't cover these 35 rows, though.** `_reextract_document()`'s first check is `if
not doc.archive_location: return attempted=False` -- it finds the file by reversing the S3 path
stored in `archive_location`. These 35 rows have `archive_location=None` (the upload never
completed, not just extraction failing), so there's no stored path for it to reverse. It was
built for "extraction failed, upload succeeded" -- a different, narrower case than these 35.

## The real open question: are the raw files still findable at all, and where

My first instinct was "the local file is probably still on `/Volumes/DDP-HOT`, since persist
happens before upload in the code" -- **Ramon corrected this directly**: DDP-HOT is populated by
syncing *from* S3, a downstream consumer, not written to directly by the archiver during a normal
run today. A document that never reached S3 has no obvious reason to be on DDP-HOT via that path.
(It's possible some of these 35 predate the Fargate migration, from back when scraping ran
directly on the Mac writing straight to what's now DDP-HOT -- genuinely don't know without
checking, not assuming either way.)

I have direct filesystem access to `/Volumes/DDP-HOT` from this same Mac and can check myself --
but I need the specific rows first, not just jurisdiction counts (currently: ma 30, mi 4, wa 1).

## What I need

For each of the 35 `is_error=True`/null-`archive_location` `BillVersionDocument` rows in
ma/mi/wa: `bill.identifier`, `bill.id` (the `ocd-bill/<uuid>`), `legislative_session.identifier`,
`bill.from_organization.classification` (chamber), `version_note`, `version_date`, `source_url`,
`media_type`. That's exactly what `_archive_path()` needs to compute the expected on-disk path
deterministically (`bills/raw/{abbr}/{session}/{chamber}/{identifier}--{uuid}/{date-}{note}-
{sha256(url)[:16]}.{ext}`) -- once I have it, I'll check each path against DDP-HOT directly and
report back before anyone writes a line of code.

If the files genuinely aren't there, the honest options narrow to: a real (small, rate-limited)
live re-fetch for just these 35 documents, or accepting them as unrecoverable without one and
deciding that's out of scope. Not deciding that now -- want the actual filesystem check first.
