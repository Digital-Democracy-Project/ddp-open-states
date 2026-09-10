# OPEN-266 fully closed: archive_location IS NULL is at zero, database-wide

*Replies to `notes/sr123-uploaded-verified-glacier-ir-20260910.md`.* SR 123's row updated
(`archive_location` set to the uploaded S3 URI, `archived_at` set), then `reextract mi --commit`:

```
mi: [COMMITTED] 166 errored docs checked | now_fixed=1 still_error=165 skipped=0
```

`now_fixed=1` -- unlike the MA PDFs, SR 123's content extracted cleanly once it had a real
`archive_location`. `skipped=0` confirms no more null-`archive_location` rows remain for MI.

**Confirmed directly: `BillVersionDocument.objects.filter(archive_location__isnull=True).count()`
= 0, database-wide.** Every one of the original 35 rows from this investigation is now resolved:

- 9 (`us`/`az`/`mi`/`ma` mix) -- already-uploaded objects, DB caught up.
- 25 (MA) -- deleted + genuinely re-fetched; recovered but confirmed unextractable (malformed
  source PDFs), an accepted-loss case, not a retry candidate.
- 1 (MI `SR 123`) -- uploaded from local copy, DB updated, extracted cleanly.

Also confirms your earlier question: yes, `reextract mi --commit` did run before this (the
`now_fixed=3 still_error=165 skipped=1` result reported alongside the 9-row fix) -- this is the
second, final run picking up just `SR 123`.

OPEN-266 has no more open data recovery work. Nothing left in its scope but deciding whether the
676-row MA `is_error=True`-with-real-`archive_location` population (flagged separately,
`notes/ma-25-refetch-done-only-sr123-remains-20260910.md`) is worth its own ticket -- not part of
this one.
