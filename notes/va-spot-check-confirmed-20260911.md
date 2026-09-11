# va spot-check confirmed (all 7, exact match against Mac's real Postgres) -- proceed with commit

Ran `recompute_bill_diff_order()` directly (real Django ORM, no shell-out) against the Mac's
production-scale local Postgres replica for all 7 documents in your sample. All 7 match your
reported proposed values exactly:

| bill | doc_id | your proposed new value | Mac: stored value | Mac: recompute agrees? |
|---|---|---|---|---|
| SJ 60 (2026) | 23753 | `None` (nulled) | `None` (confirmed via `is None`) | yes -- unchanged |
| SJ 60 (2026) | 23756 | `None` (nulled) | `None` (confirmed via `is None`) | yes -- unchanged |
| HR 2002 (2026S1) | 70534 | 6468 | 6468 | yes -- unchanged |
| HR 2002 (2026S1) | 70535 | 897 | 897 | yes -- unchanged |
| HR 2041 (2026S1) | 70578 | 3329 | 3329 | yes -- unchanged |
| HR 2041 (2026S1) | 70579 | 754 | 754 | yes -- unchanged |
| HB 1027 (2027) | 200314 | 2944 | 2944 | yes -- unchanged |

The Mac's copy already has all 7 documents in exactly the state your dry-run proposes moving
production *to* -- confirming the hypothesis from the aggregate-count investigation: this is
production catching up to the OPEN-33/34 ordering fix that was already applied to the Mac's
own data, not a new or uncertain correction.

**Go-ahead: proceed with `recompute-diff-order va --commit`** (fresh dry-run immediately
before, per the established discipline). Report back before touching `wa`/`us`.
