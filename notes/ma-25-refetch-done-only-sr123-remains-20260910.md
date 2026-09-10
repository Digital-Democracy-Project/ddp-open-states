# MA's 25 rows recovered -- archive_location is fixed everywhere except SR 123 now

*Replies to `notes/open266-25-mi-sr123-and-ma-refetch-plan-20260910.md`.* Deleted the exact 25
MA rows (natural-key match, pre-checked `is_error=True`/`archive_location=None`, one atomic
transaction, verified 25/25 before committing), confirmed no MA run was in flight, then launched
a real `archive ma` run against task-definition revision 23.

## Clean re-fetch

```
ma: fetched=25 skipped=11672 archived=25 fetch_errors=20 s3_verified=25 s3_unverified=0
    persist_errors=0 duration_s=104
```

All 25 fetched, persisted, uploaded, and verified -- `archive_location` populated for every one.
`fetch_errors=20` are the same pre-existing real 404s from other MA bills, unrelated.

## The honest caveat you flagged in advance: confirmed, not hypothetical

Checked directly: `SD 4144` (one of the 25) is still `is_error=True` even on this freshly
re-downloaded PDF -- same `Syntax Error: Gen inside xref table too large` /
`Couldn't find trailer dictionary` class of failure as before. This rules out "corrupted local
copy" as the cause; the source PDF at `malegislature.gov` itself is genuinely malformed for
these documents, not a persistence artifact. Per your own framing: this is a legitimate,
different-in-kind result (unextractable content), not evidence the re-fetch failed.

**Scope note, worth flagging on its own:** `MA is_error=True with a real archive_location` is
now **676** total (was 651 before this batch, +25 from this run) -- a much bigger population
than OPEN-266's original 30-row estimate for MA's `is_error=True` count. That original 30 was
specifically "is_error=True AND archive_location IS NULL" -- these 676 all already have a valid
archive_location and are a pre-existing, separate MA data-quality question (malformed source
PDFs at scale), not part of this recovery's scope. Not deciding anything about it here, just
making sure it's visible rather than buried in one bill's spot-check.

## Where OPEN-266 stands now

**`archive_location IS NULL` is down to exactly 1 row, database-wide: MI's `SR 123`**, still
waiting on the Mac-side S3 upload (`notes/sr123-upload-needs-mac-access-20260910.md`). Once
that lands and I run the DB update + `reextract mi --commit`, every row that had a null
`archive_location` at the start of this investigation will be resolved one way or another.
