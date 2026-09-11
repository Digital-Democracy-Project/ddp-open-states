# us refresh-extraction: the failed commit got ~56% done before crashing

Fresh `refresh-extraction us --dry-run` completed clean (no repeat of the dropped-connection
crash -- watched it carefully via CloudWatch recency + `pg_stat_activity` throughout, real
active connection the whole way):

```
us: [DRY RUN] bills_with_stale_docs=16560 stale_docs=20343 diffs_would_change=3118 docs_skipped=0 docs_refused=0
```

Compared against the original pre-commit dry-run (`bills_with_stale_docs=37672
stale_docs=46210 diffs_would_change=6977`):

| | original | remaining | resolved |
|---|---|---|---|
| bills_with_stale_docs | 37,672 | 16,560 | 21,112 (~56%) |
| stale_docs | 46,210 | 20,343 | 25,867 (~56%) |
| diffs_would_change | 6,977 | 3,118 | 3,859 (~55%) |

The failed commit (dropped connection, `notes/us-refresh-extraction-commit-failed-dropped-
connection-20260911.md`) made real, substantial progress before it died -- roughly 56% of
the work, cleanly (`docs_refused=0`), matching the idempotent/per-bill-transaction design's
expectation of no corruption. The remaining commit should cover the other ~44% and,
proportionally, take less time than the original ~4.5h attempt -- though the same
dropped-connection bug remains unfixed and could recur on this retry too.

**Holding on re-running the commit until Ramon gives explicit go-ahead** (same discipline
as every other jurisdiction). The recurring connection-drop bug is still open and
unaddressed -- worth considering whether to fix that first, or just accept the retry risk
given a shorter remaining runtime now.
