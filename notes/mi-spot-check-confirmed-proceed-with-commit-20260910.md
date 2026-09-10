# MI spot-check: all 8 confirmed, proceed with `recompute-diff-order mi --commit`

*Replies to `notes/mi-recompute-diff-order-spot-check-sample-20260910.md`.* Checked all 8 (not
just a couple) directly against the Mac's real local Postgres -- the production-scale replica
(`postgresql://openstates:openstates_dev@localhost:5433/openstates`, 199,302
`ddp_bill_version_document` rows, not the small dev/test database), read-only:

```
id      | your "newly computed" diff len | Mac's actual stored diff len | match
96810   | 545                             | 545                           | yes
98523   | 0                               | 0                              | yes
98861   | 0                               | 0                              | yes
100343  | 0                               | 0                              | yes
93391   | 0                               | 0                              | yes
96359   | 5350                            | 5350                           | yes
90092   | 86905                           | 86905                          | yes
92447   | 592                             | 592                            | yes
```

Exact match on every one. That's the real acceptance check the plan asks for -- RDS's fresh
`recompute_bill_diff_order()` output matches what's already correct on the Mac for these same
documents. Proceed with `recompute-diff-order mi --commit`, then the usual: spot-check one
`nulled` and one `corrected` from the actual commit output, report back, then move to `ut`
(remember `ut` needs `refresh-extraction ut --commit` first, before its own
`recompute-diff-order`, per the plan's sequencing rule).
