# OPEN-85: VA Chaptered + resolution-Enrolled PDF backfill

Follow-up to OPEN-76 (extraction fix, merged `openstates-core` PR #21) — reprocesses the
already-archived rows that fix can't retroactively repair on its own, reusing OPEN-33/34's own
reprocess-in-place mechanism and tooling.

## Affected-row set (re-verified fresh against the live archive, not OPEN-76's original counts)

| Category | Total rows | Garbled (<300 chars) | `is_error=True` |
|---|---|---|---|
| Enacted "Chaptered", `application/pdf` | 1,134 | 1,108 | 482 |
| Resolution (HJ/HR/SJ/SR) "Enrolled", `application/pdf` | 1,521 | 1,521 | 0 |

Combined: 2,655 candidate rows, 2,629 genuinely garbled (26 already had real content and were
left untouched). Larger than OPEN-76's original ~2,173 estimate — more scraping happened between
that investigation and this backfill, as its own note anticipated.

Notably, only 482 of the 1,134 Chaptered rows are `is_error=True` — the rest "succeeded" with
near-empty footer-only text, which is why the existing `reextract` CLI command (OPEN-49, filters
`is_error=True` only) couldn't be used directly here. A custom row-selection (`version_note`
containing "chaptered", or "enrolled" + a resolution-prefixed bill identifier, combined with a
<300-char length heuristic) was used instead, calling `_reextract_document()` directly — the same
underlying reprocess-in-place function, just with different row selection than the generic CLI.

## What was run

1. Dry run: all 2,629 garbled rows reprocessed from the already-downloaded PDF on
   `/Volumes/DDP-HOT` (no live traffic to virginia.gov) via the now-fixed
   `extract_sometimes_numbered_pdf` path — **100% (2,629/2,629) produced real content (>=300
   chars), 0 still garbled.**
2. Committed: `raw_text`/`is_error` updated in place for all 2,629 rows — `archive_location`,
   `archived_at`, `sha256_hash`, and everything else untouched, matching OPEN-33's own
   convention.
3. `recompute_diff_order va --commit` (OPEN-34's tool): 3,937 VA bills checked, 2,636 diffs
   corrected, 0 nulled.

## Verification (direct DB queries, not just the scripts' own printed summaries)

- Chaptered PDF: 1,134/1,134 now have real content (100%), up from 26/1,134 before.
- Resolution Enrolled PDF: 1,521/1,521 now have real content (100%), up from 0/1,521 before.
- All 2,655 real-content rows in the affected set now have a non-null
  `diff_from_previous_version`.
- Blast radius: VA's Introduced stage (7,877 rows, untouched by this backfill's row selection)
  still averages ~12,690 chars, unchanged shape — confirms the targeted selection didn't touch
  anything outside its own scope. FL's version-document count (20,038, unrelated jurisdiction)
  unaffected.

## Spot-checked real content, including OPEN-76's own cited example

- **SB 2, Chaptered: reproduces OPEN-76's own example exactly** — "CHAPTER 981 ... An Act to
  amend and reenact §§ 38.2-107.2, 38.2-135, 38.2-316, and 38.2-1800 of the Code of Virginia..."
  (77,994 chars, up from a footer-only garbage string before).
- HB 1, Chaptered: "CHAPTER 350 ... An Act to amend and reenact § 40.1-28.10 of the Code of
  Virginia, relating to minimum wage." (3,093 chars).
- HJ 1, Chaptered: "CHAPTER 973 ... HOUSE JOINT RESOLUTION NO. 1 ... Proposing an amendment to..."
  (3,626 chars).
- SR 1, Enrolled: "SENATE RESOLUTION NO. 1..." (2,986 chars).
- HB 1, Enrolled: "An Act to amend and reenact § 40.1-28.10 of the Code of Virginia, relating to
  minimum wage." (2,683 chars).

All genuine, readable Virginia statutory/resolution text, not just non-empty strings.

## References

- OPEN-76 — the extraction fix this backfill depends on (Done, `openstates-core` PR #21)
- OPEN-33 (`notes/va-open-33-bill-text-backfill-20260806.md`) — the reprocess-in-place mechanism
  and convention this backfill follows
- OPEN-34 (`notes/va-open-34-diff-order-fix-and-backfill-20260807.md`) — the
  `recompute_diff_order` tool this backfill's step 3 reuses
- `openstates-core/openstates/cli/text_extract.py` `_reextract_document()` (OPEN-49) — the
  generalized reprocess-in-place function this backfill's custom row-selection script called
  directly
