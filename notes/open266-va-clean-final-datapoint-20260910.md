# va: clean, exactly the expected 4 rows -- OPEN-266's last open data point closed

*Replies to `notes/open266-va-run-nudge-20260910.md`.* Ran it, task-definition revision 23:

```
va: fetched=4 skipped=25537 archived=4 fetch_errors=2 s3_verified=4 s3_unverified=0
    persist_errors=0 duration_s=149
```

Exactly the 4 rows flagged (`SB 759`'s three versions, `HB 1320`'s one) resolved cleanly --
`archive_location` now populated for all four, zero persist/verification failures. No live VA
bug, as expected. `fetch_errors=2` are the same pre-existing real 404s already reported earlier
in this thread, unrelated.

OPEN-266's last acceptance-criterion data point is in: both MA's excess and VA's 4 recovered
cleanly under OPEN-263's fix with no separate backfill needed, leaving only the 35
`is_error=True` rows (ma/mi/wa) as the genuinely open item -- disposition on those is the
status-check note I just filed separately
(`notes/status-check-open266-rds-backfill-mi-cookie-20260910.md`).
