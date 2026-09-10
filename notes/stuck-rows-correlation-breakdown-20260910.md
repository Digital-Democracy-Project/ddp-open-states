# Stuck-row breakdown: no created_at field exists, so correlated by jurisdiction + is_error instead

*Replies to `notes/correlate-stuck-rows-before-backfill-decision-20260910.md`.* First finding
before the breakdown itself: **`BillVersionDocument` has no `created_at`/`updated_at` field at
all** -- checked the model directly (`openstates-core/openstates/data/models/bill.py:285`).
`archived_at` is null for every one of these 747 rows by definition, so there's no timestamp
anywhere on the row to correlate against yesterday's batch windows directly. Used the next-best
signal instead: jurisdiction breakdown (only `az`/`ma`/`mi`/`us` had any real activity in the
rev21 batch that created these) cross-referenced with `is_error`, since yesterday's specific
failure mode was "extraction succeeded, only the S3 upload failed" (`is_error=False`) --
different in kind from an extraction failure, which would predate yesterday's incident entirely.

## Breakdown (747 total)

| jurisdiction | is_error=False | is_error=True | yesterday's rev21 `archived` count |
|---|---|---|---|
| us | 512 | 0 | 506 |
| ma | 149 | 30 | 74 |
| az | 34 | 0 | 32 |
| mi | 13 | 4 | 12 |
| va | 4 | 0 | 0 |
| wa | 0 | 1 | 0 |
| fl / ut / al | 0 | 0 | 0 |

## Reading this

- **`us` (512 vs. 506) and `az` (34 vs. 32) match closely** -- high confidence these are almost
  entirely yesterday's incident, not older nulls.
- **`ma`'s `is_error=False` count (149) is roughly double yesterday's `archived=74`** -- real
  excess beyond yesterday's run, a genuinely separate/older population mixed in.
- **The `is_error=True` rows (`ma`: 30, `mi`: 4, `wa`: 1) are a different failure mode
  entirely** -- extraction itself failed, which has nothing to do with yesterday's S3-permission
  incident (that failure happens *after* a successful extraction). These are older/pre-existing,
  not part of this backfill's scope.
- **`va`'s 4 rows don't fit yesterday's incident at all** -- `va` had `fetched=0` in both of
  yesterday's runs (only `fetch_errors=2`, real 404s, never got far enough to attempt a
  persist/upload). These 4 predate yesterday and are unrelated.
- `fl`/`ut`/`al` show zero, consistent with them having no activity in either run.

## My read, not a decision

Best available signal without a `created_at` field: **yesterday's incident specifically
accounts for roughly the `us`/`az` counts in full, and the `is_error=False` portion of `mi`/`ma`
up to their respective `archived` counts (12 and 74)** -- call it ~624 rows, matching the
rev21 batch's own reported totals almost exactly. The remainder (`ma`'s extra ~75
`is_error=False`, all the `is_error=True` rows, and `va`'s 4) look like a separate, older,
unrelated population -- worth its own look eventually, but not part of "what yesterday broke."

Not deciding scope myself, per your note -- this is the input for that decision, not the
decision.
