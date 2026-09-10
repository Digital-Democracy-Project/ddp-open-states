# fl recompute-diff-order dry-run — spot-check sample needed before --commit

`fl` dry-run: `7685 bills checked | unchanged=17325 corrected=2712 nulled=1` — run inside the
fixed toolchain (throwaway local build, Python 3.10.21/poppler 22.12.0, `main` @ `9b1651e`).
In line with `mi`'s earlier dry-run shape, no red flags. Per the plan, need a spot-check
against the Mac's local Postgres before `--commit` — I have no direct Mac Postgres access
from this EC2 host. Real samples below (via `recompute_bill_diff_order()`, the pure/read-only
half of the command — no DB writes).

## The 1 NULLED doc

- `bill_id=ocd-bill/1772f9c1-53c5-4605-b865-cbf2f0fe338b` (`SB 490`, session `2023`)
- `doc_id=17467`, `version_note='S 490 c1'`, `media_type=text/html`
- currently stored `diff_from_previous_version` is 7,398 chars; recompute says this should
  become `None` (this version's note doesn't match a known stage, or it's a known procedural
  document for FL — `is_unknown_position`/`is_procedural_document()` path)

## 5 CORRECTED doc samples (of 2,712 total)

| bill | doc_id | version_note | media_type | old diff len | new diff len |
|---|---|---|---|---|---|
| SB 364 (2024) | 258 | S 364 e1 | text/html | 1761 | 1153 |
| SB 364 (2024) | 260 | S 364 er | text/html | 1438 | 293 |
| SJR 2F (2026F) | 92 | S 2F c1 | text/html | 33226 | 12561 |
| SB 1206 (2025) | 102 | S 1206 c1 | text/html | 6086 | 4333 |
| SB 7036 (2023) | 115 | S 7036 Filed | text/html | 2161 | 0 |

Full bill UUIDs for the corrected samples, in the same order:
- `ocd-bill/fe91169f-b3d7-4143-8875-eaa137c4cc6b` (SB 364, doc 258 & 260)
- `ocd-bill/a3afb726-fac4-41e7-b428-0cae1f4ddada` (SJR 2F, doc 92)
- `ocd-bill/0df59a09-f5ac-4cea-a3b4-07a296ebaaa6` (SB 1206, doc 102)
- `ocd-bill/70487edd-88ef-4da3-a390-cb387bdecb15` (SB 7036, doc 115)

Once these check out against the Mac's copy, I'll run `recompute-diff-order fl --commit`
(with a fresh dry-run immediately beforehand, per the established discipline), then stop and
report before touching `va`.
