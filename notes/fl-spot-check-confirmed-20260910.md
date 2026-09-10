# fl spot-check confirmed (all 6, exact match against Mac's real Postgres) -- proceed with commit

Ran `recompute_bill_diff_order()` directly (real Django ORM, no shell-out) against the Mac's
production-scale local Postgres replica (`postgresql://openstates:openstates_dev@localhost:5433/
openstates`) for all 6 documents in your sample. All 6 match your reported values exactly:

| bill | doc_id | your reported new diff len | Mac: stored value | Mac: recompute agrees? |
|---|---|---|---|---|
| SB 490 (2023) | 17467 | `None` (nulled) | `None` (confirmed via `is None`, not just empty) | yes -- unchanged |
| SB 364 (2024) | 258 | 1153 | 1153 | yes -- unchanged |
| SB 364 (2024) | 260 | 293 | 293 | yes -- unchanged |
| SJR 2F (2026F) | 92 | 12561 | 12561 | yes -- unchanged |
| SB 1206 (2025) | 102 | 4333 | 4333 | yes -- unchanged |
| SB 7036 (2023) | 115 | 0 | `''` (confirmed empty string, not `None` -- distinct from the 17467 case, matches your "0" not a null) | yes -- unchanged |

The Mac's copy already has these documents in their post-recompute state, and re-running
`recompute_bill_diff_order()` against them independently produces zero further change for any
of the 6 -- full agreement with your fixed-toolchain dry-run.

**Go-ahead: proceed with `recompute-diff-order fl --commit`** (fresh dry-run immediately before,
per the established discipline, same as always). Report back before touching `va`.
