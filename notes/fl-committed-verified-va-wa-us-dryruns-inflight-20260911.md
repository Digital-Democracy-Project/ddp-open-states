# fl committed and verified via the new Fargate trigger — va/wa/us dry-runs in flight

## fl: DONE, verified

`recompute-diff-order fl --commit` run via OPEN-268's new Fargate trigger
(`run_id=fl-recompute-diff-order-commit-88875140e190`), isolated from the nightly
`ddp-broker` job entirely — no resource contention this time.

`fl: [COMMITTED] 7685 bills checked | unchanged=17325 corrected=2712 nulled=1` — matches the
fresh pre-commit dry-run exactly.

**Verified the actual post-commit DB state directly** (not just the summary line), against
the two samples spot-checked earlier: `id=17467` (SB 490/2023) now has
`diff_from_previous_version = None` (nulled, as expected); `id=258` (SB 364/2024) has a
1153-char diff (matches the earlier spot-check exactly).

`fl` is closed out. Backfill progress: `mi`, `ut`, `fl` done. `va`/`wa`/`us` remain.

## va/wa/us dry-runs: launched in parallel, in flight

Since Fargate isolates each run, launched all remaining dry-runs at once rather than one at
a time:
- `va recompute-diff-order --dry-run` (`va`'s only step, per the original plan's scope)
- `wa refresh-extraction --dry-run` and `wa recompute-diff-order --dry-run`
- `us refresh-extraction --dry-run` and `us recompute-diff-order --dry-run`

All 5 still `RUNNING` on ECS as of this update (`wa`/`us` are much larger than `fl`/`mi`
historically, so a longer runtime is expected, not a concern by itself). One nuance: `wa`/
`us`'s `recompute-diff-order` dry-run right now reflects text *before*
`refresh-extraction` is committed — per the original plan, that step needs a fresh re-run
right before its own commit, once `refresh-extraction` actually lands for each. This
parallel run was just an early look at all fronts.

Will report each result as it lands. Not committing anything further without a fresh
dry-run immediately before, and not touching `va`/`wa`/`us` commits without explicit
go-ahead, per the established discipline.
