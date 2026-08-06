# OPEN-33: Virginia bill-text backfill — from 100% broken to 98% real text, no re-scrape needed

## Context

OPEN-15 fixed Virginia's bill-text extraction (missing `application/pdf` entry in
`CONVERSION_FUNCTIONS`, dead `#mainC` HTML selector, a mojibake encoding bug) — merged
2026-08-02 as `ddp-open-states` PR #52 and `openstates-core` PR #10. That fix only applies to
*newly*-archived documents going forward: `archive_bill_versions()`
(`openstates-core/openstates/cli/text_extract.py`, ~line 415) skips any document that already
has a `ddp_bill_version_document` row, by natural key `(bill, version_note, version_date,
source_url)`, **regardless of `is_error`**. Confirmed 2026-08-06: all 23,999 of 23,999 existing
VA rows were still `is_error=True`, four days after OPEN-15 merged, and no natural future
archive run would ever change that — the fixed extractor never gets a chance to run against
already-archived documents. This blocked OPEN-9 (VA's diff-cleaning ticket), whose AC0/AC2
require real, successfully-extracted, multi-version VA bill text.

## Completeness verified before touching anything

Before backfilling, confirmed the archive itself wasn't gappy — the *only* problem was
extraction, not missing data:

- Cross-checked every VA `opencivicdata_billversionlink` row (the scraper's own record of what
  documents should exist) against `ddp_bill_version_document`: **24,001 total links, only 2
  without any archive row at all**, and both are logged, understood HTTP 404s from
  `legislature.virginia.gov`'s own source (`HB 30` Introduced, both PDF and HTML links) — not
  silent gaps. This matches the 2026-07-29 archive log's own summary exactly:
  `fetched=11423 skipped=12576 ... fetch_errors=2`, and `11423 + 12576 = 23999`.
- Confirmed all 23,999 existing rows have their real archived file present on
  `/Volumes/DDP-HOT` (checked every row, not a sample).

## Mechanism: reprocess in place, no live traffic to Virginia's site

`archive_bill_versions()` always re-fetches from the live source URL for any document it
doesn't skip — there's no "re-extract from the already-downloaded raw bytes" path. Rather than
clearing rows and re-fetching ~24,000 documents live from `legislature.virginia.gov`, backfilled
in place instead: for each errored row, compute its real local file path via the same
`_archive_path()` the original archiver uses, read the already-archived raw bytes directly off
`/Volumes/DDP-HOT`, run OPEN-15's fixed extractor against them, and `UPDATE` only `raw_text` /
`is_error` on the existing row — never delete/recreate, so `archive_location`, `archived_at`,
`sha256_hash`, and everything else stay untouched. Zero requests to Virginia's site; zero S3
involvement (the files were already local).

## Step 1: 25-bill validation sample

Selected 25 real VA 2026-session bills with rich Introduced → committee-substitute(s) →
Enrolled histories (20+ distinct committees represented) — far exceeding OPEN-9 AC2's bar of
"≥20 bills, ≥5 through a committee-substitute stage." Dry-ran, then committed: **647 of 650**
`ddp_bill_version_document` rows extracted real text; the other 3 are genuine empty-text
"Chaptered" cover-page PDFs (3.7-4.5KB, no real text layer) — the same class of benign
placeholder already documented for FL in `ddp-infra/PLAN-bill-document-provenance.md` (a
"DOCUMENT UNAVAILABLE" stamp page). All 25 bills ended up with well more than 2
successfully-extracted versions.

## The diff_from_previous_version bug (split off to OPEN-34)

While replicating `archive_bill_versions()`'s own `diff_from_previous_version` computation for
the sample (walking `bill.versions.all()`, tracking `prior_text` in version order), independent
verification caught a real, pre-existing bug: **`bill.versions.all()` has no explicit ordering**
(no `Meta.ordering` on `BillVersion`, no timestamp column, `date` usually blank), and for VA
that unordered walk returns rows **newest-first** — e.g. `Chaptered → Reenrolled → Governor
Substitute → ... → Introduced` (HB 1207), exactly backward. Checking FL's own already-live diff
chain (`HB 1`: `Filed → c1 → e1 → e2 → er`, monotonically growing text) confirmed the underlying
mechanism is sound *when* the DB happens to return versions in true order — it just isn't
guaranteed to. Spot-checking five more jurisdictions found this is real but inconsistent: FL/MI/AZ
are forward (correct), VA/UT/US are backward, and WA doesn't fit either model. Filed as its own
ticket, **[OPEN-34](https://digitaldemocracyproject.atlassian.net/browse/OPEN-34)**, rather than
guessed at here — a blanket "just reverse it" fix would break the jurisdictions that are
currently correct.

The 604 backward diffs the sample had just computed were nulled out immediately (confirmed via
direct query: 0 remaining non-null `diff_from_previous_version` values anywhere in VA before
proceeding) — `raw_text`/`is_error` were completely unaffected and stayed correct throughout.

## Step 2: full VA backfill

Since `raw_text` extraction has no dependency on version ordering at all — it's a pure
per-document operation — there was no reason to withhold the rest of VA's real text while
OPEN-34 is unresolved. Extended the same validated mechanism to all of VA's remaining ~23,300
errored rows, row-by-row (not walking `bill.versions.all()` at all, so this has zero interaction
with the OPEN-34 bug), explicitly leaving `diff_from_previous_version` untouched (`NULL`) for
every row.

**Result:**

| | Total | Success | Still error | With diff |
|---|---|---|---|---|
| VA, all sessions | 23,999 | **23,516 (98.0%)** | 483 (2.0%) | **0** |
| — 2026 session | 22,795 | 22,312 | 483 | 0 |
| — 2026S1 session | 1,204 | **1,204 (100%)** | 0 | 0 |

The 483 residual errors: 482 are the same benign "Chaptered" empty-text pattern (188-14,825
bytes, avg ~5.9KB — cover-page stamps, not truncated real content), plus 1 similarly-small
`text/html` amendment placeholder. Checked and characterized, not a defect.

Verified after commit: zero blast radius outside VA (every other jurisdiction's error/success
counts are identical to their pre-backfill baseline); random spot-check of 5 bills outside the
original 25-bill sample shows clean, real, legible VA bill text; `archive_location`/
`archived_at`/`sha256_hash` untouched.

## Disposition

- **OPEN-33: done.** VA's archive went from 100% broken to 98% successfully extracted, using a
  mechanism that required zero re-scraping and touched nothing outside VA.
- **OPEN-9** can now proceed — real, multi-version VA text exists for its AC0/AC2 sample
  selection, across the full archive, not just a bounded subset.
- **OPEN-34** filed separately for the `diff_from_previous_version` ordering bug — cross-referenced
  on OPEN-9 so its implementer doesn't trust `bill.versions.all()`'s ordering either when
  selecting version transitions to diff for its own noise-cleaning validation.

## References

- [OPEN-15](https://digitaldemocracyproject.atlassian.net/browse/OPEN-15) — the extraction fix this backfill depends on
- [OPEN-9](https://digitaldemocracyproject.atlassian.net/browse/OPEN-9) — unblocked by this ticket
- [OPEN-34](https://digitaldemocracyproject.atlassian.net/browse/OPEN-34) — the diff-ordering bug discovered and split off
- `ddp-infra/PLAN-bill-document-provenance.md` — Phase 1 acquisition pipeline design, and its
  own stated completeness bar ("every version link... has a corresponding archive row"), verified
  against here before backfilling
- `openstates-core/openstates/cli/text_extract.py` `archive_bill_versions()` (~line 415),
  `_archive_path()` (~line 292) — the natural-key skip logic and path convention this backfill
  replicated
