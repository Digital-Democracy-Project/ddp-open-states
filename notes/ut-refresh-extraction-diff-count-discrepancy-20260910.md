# ut refresh-extraction --commit: real discrepancy in diff count, holding here before recompute-diff-order

*Follow-up to `notes/mi-committed-verified-moving-to-ut-20260910.md`.* Ran
`refresh-extraction ut --commit` per the plan's Step 1. Result:

```
ut: [COMMITTED] bills_with_stale_docs=1021 stale_docs=3835 diffs_corrected=4110 docs_skipped=0 docs_refused=0
```

**`bills_with_stale_docs` and `stale_docs` match the 2026-09-09 dry-run exactly (1021 / 3835)**
-- same documents found stale, same new text/is_error results. But `diffs_corrected=4110` here
vs. that dry-run's `diffs_would_change=4671` -- a real gap I don't have a confirmed explanation
for. Checked the code (`text_extract.py`): both counters call the same underlying diff-recompute
logic (`recomputed_diffs_for_documents`/`recompute_bill_diff_order`) against what should be
identical inputs, so a difference with the stale-doc set unchanged is genuinely unexpected to me,
not obviously explained by data drift (checked `ddp-sync`'s logs -- no UT scrape activity logged
since 2026-09-09, so it isn't a scheduled scrape changing the underlying data in between).

Didn't run a fresh `refresh-extraction ut --dry-run` immediately before this commit (the plan's
explicit "run a fresh dry-run right beforehand" instruction was written for the
`recompute-diff-order` step specifically) -- in hindsight, worth doing for every commit step in
this backfill, not just that one, and I'll do that going forward rather than trusting a
day(s)-old number.

## Not proceeding to recompute-diff-order ut until this is understood

Pulled a real sample instead -- 6 `BillVersionDocument` rows this commit actually touched
(`updated_at` within the last hour), full identifiers plus the diff now stored:

```
HB 443  | ocd-bill/ba8ddea2-1c3f-41d1-b39a-928d0c6672af | id 44576 | Introduced
  | https://le.utah.gov/Session/2026/bills/introduced/HB0443.xml | diff len: 0
SB 285  | ocd-bill/140f797c-d506-4f3a-95d9-1c5b16a57158 | id 44658 | Introduced
  | https://le.utah.gov/Session/2026/bills/introduced/SB0285.xml | diff len: 0
HB 113  | ocd-bill/bacfff46-32b7-4d5c-836b-16d3f54a73f8 | id 56132 | Substitute #1
  | https://le.utah.gov/Session/2026/bills/introduced/HB0113S01.xml | diff len: 8177
HB 113  | ocd-bill/bacfff46-32b7-4d5c-836b-16d3f54a73f8 | id 56167 | Substitute #2
  | https://le.utah.gov/Session/2026/bills/introduced/HB0113S02.xml | diff len: 11364
HB 113  | ocd-bill/bacfff46-32b7-4d5c-836b-16d3f54a73f8 | id 56173 | Substitute #2
  | https://le.utah.gov/Session/2026/bills/introduced/HB0113S02.pdf | diff len: 11312
SB 214  | ocd-bill/f14c1c27-ed7e-4c15-bf1b-bbfa5360f388 | id 66816 | Amended 2/20/2026 17:02:129
  | https://le.utah.gov/Session/2026/bills/amended/AV_SB0214_2026-02-20_17-31-21.pdf | diff len: 689
```

## Ask

1. If you can, spot-check any of these 6 (or run your own `refresh-extraction ut --dry-run` on
   the Mac's production-scale replica and compare its `diffs_would_change` against a similar
   number) -- I want confirmation the actual diff content is correct, not just that the counts
   look plausible.
2. Any idea what could cause `diffs_would_change`/`diffs_corrected` to differ in count while
   `bills_with_stale_docs`/`stale_docs` stay identical? I couldn't find an obvious reason in the
   code myself.

Holding at `ut` -- not running `recompute-diff-order ut` (Step 2/3) or moving to `fl` until
this is resolved one way or the other.
