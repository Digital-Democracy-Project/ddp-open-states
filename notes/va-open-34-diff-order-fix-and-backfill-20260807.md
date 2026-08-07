# OPEN-34: diff_from_previous_version's undefined version-walk order — audited, fixed, backfilled across every jurisdiction

## Context

Found 2026-08-06 while independently verifying OPEN-33's VA backfill (re-extracting VA's
~24,000 already-archived, errored `BillVersionDocument` rows now that OPEN-15's extractor fix
was live). While replicating `archive_bill_versions()`'s own `diff_from_previous_version`
computation for a 25-bill sample, direct inspection caught a real bug: VA's version-walk order
came back **newest-first** (e.g. `Chaptered → Reenrolled → Governor Substitute → ... →
Introduced`), so the diffs computed were all running backward. `bill.versions.all()` has no
`Meta.ordering` on `BillVersion`, no timestamp column, and `date` is usually blank — the walk
order was whatever Postgres happened to return, an implementation accident, not a guaranteed
signal. OPEN-33's own 604 wrong diffs were nulled out immediately; this ticket tracked the real
fix.

## Audit: the accident is inconsistent across jurisdictions

A quick 1-2-bill-per-jurisdiction spot-check (done while investigating OPEN-33) found FL/MI/AZ
forward-correct, VA/UT/US backward, and WA not fitting either model. CodeBot's implementation
then ran a proper ~10-12-bill-per-jurisdiction audit against real production-derived data and
found the real picture is messier than that spot-check suggested:

| Jurisdiction | Spot-check said | Real audit found |
|---|---|---|
| FL | Forward | Forward in 9/12 bills — 3/12 have "Filed" out of position |
| MI | Forward | Forward only for Resolutions/no-substitute bills — any bill with a Substitute gets it inserted *before* "Introduced Bill" (8/12 real bills) |
| AZ | Forward | 11/12 forward — 1 real exception (a floor-amendment note landed first) |
| VA | Backward | Confirmed at scale (OPEN-33's own 604-row finding) |
| UT | Backward | Doesn't fit a reversal at all — "Enrolled" lands at wildly inconsistent positions |
| US (federal) | Backward | Backward in 10/12, but `BillVersion.date` is ~99.4% populated — a real date-based fix covers this fully |
| WA | Ambiguous | Root-caused: `scrapers/wa/bills.py`'s `_load_versions()` fetches one page per `bill_type` (`Bills, Resolutions, ..., Passed Legislature`, in that dict order) — "Passed Legislature" documents are structurally always walked last, and within the "Bills" page, WA's own site lists "Engrossed \<N\> Substitute" before the plain "\<N\> Substitute" it amends. Deterministic, not scrambled. |

No jurisdiction sampled is 100% one direction, and MI/UT/WA aren't even binary — confirming the
originally-considered "per-jurisdiction reverse config file" fix would not have been
supportable by real data.

## The fix

`openstates-core` PR #12 (merged 2026-08-06): `_note_stage()`/`_version_sort_key()`
(`openstates/cli/text_extract.py`) classify each version by content — `BillVersion.date` when
parseable (covers US federal outright), otherwise a stage table built directly from the real
`version_note` vocabulary audited above. A note matching no known stage is **excluded from the
diff lineage entirely** rather than guessed into a position — a wrong-direction diff is worse
than a missing one. `archive_bill_versions()` now walks `sorted(bill.versions.all(), key=...)`
instead of the raw queryset. A new `recompute_diff_order` CLI command (`--dry-run`/`--commit`)
recomputes already-archived `diff_from_previous_version` values from already-stored `raw_text`
— no re-fetching, mirroring OPEN-33's own reprocess-in-place pattern.

23 new tests (including a fixture bill with intentionally scrambled creation order that fails
pre-fix and passes post-fix) plus the full 400-test suite verified independently before
merging — 0 regressions, flake8/black clean, no schema migration (the `bill.py` change is a
`help_text` update only).

## Production backfill, 2026-08-07

Dry-ran `recompute-diff-order all` first: **29,914 bills checked | unchanged=61,100 |
corrected=20,516 | nulled=1,814**. Broke it down per jurisdiction before committing:

| Jurisdiction | Bills | Unchanged | Corrected | Nulled |
|---|---|---|---|---|
| Virginia | 3,937 | 8,381 | **15,618** | 0 |
| Utah | 1,021 | 6,986 | 2,204 | 181 |
| Washington | 3,411 | 8,591 | 1,953 | 1,092 |
| United States | 5,217 | 4,862 | 697 | 434 |
| Florida | 7,685 | 19,992 | 44 | 2 |
| Michigan | 1,147 | 3,437 | 0 | 66 |
| Massachusetts | 5,307 | 5,307 | 0 | 0 |
| Arizona | 2,190 | 3,545 | 0 | 39 |

This matched the audit closely — FL/AZ needed almost no correction (matching "mostly forward,
rare exceptions"), VA got fully populated for the first time (0 nulled, since nothing existed to
null), and UT/WA showed real, substantial correction (matching "doesn't fit a simple reversal" /
"root-caused two-part mechanism"). Committed: **20,516 corrected, 1,814 nulled**, matching the
dry run exactly.

Verified after commit:
- Per-jurisdiction diff counts confirmed via direct query (e.g. VA: 0 → 15,618).
- System-wide `raw_text`/`is_error` totals unchanged (71,749 success / 11,742 error) — confirms
  the recompute touched only `diff_from_previous_version`, nothing else.
- Read actual diff content directly for VA's `HB 1207` (Introduced → Subcommittee #2
  Substitute): the diff correctly shows the old decorative border artifact being removed and the
  new substitute's real header (`AMENDMENT IN THE NATURE OF A SUBSTITUTE`, `Proposed by the
  House Committee on Labor and Commerce`, `Patron Prior to Substitute—Delegate Sewell`) and
  real substantive clause edits being added — a genuinely correct, forward-reading diff, not just
  a plausible-looking count.

## Massachusetts: not a classifier gap

Before treating MA's 0/0/5,307 dry-run result as "needs classifier coverage," checked its real
`version_note` vocabulary directly: **exactly one distinct value, `"Bill Text"`, appearing
exactly once per bill (5,307 rows, 5,307 distinct bills — a perfect 1:1 ratio).** MA's archive
has no multi-version history at all — there's no "previous version" to diff against regardless
of how well any classifier could rank `"Bill Text"`. This is a separate, likely bigger question
(does MA's scraper/source site support capturing multiple version stages at all?), not a gap in
this ticket's stage table. Filed as its own analysis ticket,
[OPEN-36](https://digitaldemocracyproject.atlassian.net/browse/OPEN-36).

## Disposition

- **OPEN-34: done.** Audit, fix, tests, and the actual production backfill all complete and
  independently verified.
- **OPEN-9** gets a cross-reference (posted by both the fix's author and independently by this
  session) warning its implementer not to trust `bill.versions.all()`'s ordering, and pointing
  at `_version_sort_key()` as a reusable helper.
- **OPEN-36** filed for Massachusetts's separate, unrelated gap.
- `ddp-infra/PLAN-bill-document-provenance.md` updated to reflect this resolution and
  distinguish it clearly from AC11a (LegBot's still-open diff-*format* validation question —
  different problem, not resolved by this ticket).

## References

- [OPEN-33](https://digitaldemocracyproject.atlassian.net/browse/OPEN-33) — where this bug was
  first discovered, during VA's raw_text backfill
- [OPEN-9](https://digitaldemocracyproject.atlassian.net/browse/OPEN-9) — cross-referenced,
  not blocked
- [OPEN-36](https://digitaldemocracyproject.atlassian.net/browse/OPEN-36) — Massachusetts's
  separate multi-version-capture question
- `openstates-core` [PR #12](https://github.com/Digital-Democracy-Project/openstates-core/pull/12)
  — the audit, fix, and tests
- `openstates-core/openstates/cli/text_extract.py` `_note_stage()`/`_version_sort_key()`/
  `recompute_diff_order` — the new reusable classifier and backfill command
- `ddp-infra/PLAN-bill-document-provenance.md` — updated with this resolution
- `notes/va-open-33-bill-text-backfill-20260806.md` — the sibling ticket this was discovered
  during
