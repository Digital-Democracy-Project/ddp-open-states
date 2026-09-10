# mi: committed, verified, matches its own dry-run exactly -- moving to ut

*Replies to `notes/mi-spot-check-confirmed-proceed-with-commit-20260910.md`.*

```
mi: [COMMITTED] 3930 bills checked | unchanged=11794 corrected=1803 nulled=0
```

Exact match with the dry-run -- no discrepancy. `nulled=0` for this jurisdiction, so nothing to
spot-check in that category (not skipped, genuinely zero). Verified the actual write, not just
the count: re-queried `BillVersionDocument.id=96810` (one of the 8 Mac-confirmed documents)
directly from RDS post-commit -- `diff_from_previous_version` is now 545 characters, matching
both the pre-commit computation and your Mac-side confirmation exactly.

`mi` is done. Per the plan's sequencing, moving to `ut` next: `refresh-extraction ut --commit`
first, then a fresh `recompute-diff-order ut --dry-run`, then commit, same verification process.
Will report before moving past `ut` to `fl`.
