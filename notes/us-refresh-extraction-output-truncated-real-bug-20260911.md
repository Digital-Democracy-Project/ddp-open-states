# us refresh-extraction --dry-run: real bug found, exactly what you asked me to watch for

`us refresh-extraction --dry-run` finally completed after 14,610 seconds (~4h 3.5min) --
by far the largest/longest job in this whole backfill (~89K documents). Result was clean,
but the trigger's own captured `output` field is genuinely broken for a run this size.

## The real result (pulled directly from CloudWatch, not ddp-sync's captured output)

```
us: [DRY RUN] bills_with_stale_docs=37672 stale_docs=46210 diffs_would_change=6977 docs_skipped=0 docs_refused=0
```

Clean -- zero refused documents.

## The bug: ddp-sync's captured `output` never includes the final summary line

`ddp-sync`'s own log line (`openstates_backfill: fargate task done ... output='...'`)
contains ~4.7MB of poppler ligature-parsing warnings but **cuts off before the actual
`click.secho` summary line ever prints**. Confirmed the real summary exists and is the very
last CloudWatch log event before the container exited (`aws logs get-log-events` directly
against the task's log stream) -- so the underlying command finished and logged correctly;
`ddp-sync`'s own capture/truncation logic is what's losing it, presumably a size cap on
however it buffers/stores the `output` string rather than the "wait for 2 quiet CloudWatch
rounds" timing issue you'd flagged before (that one was about arriving late, not being
truncated once captured).

Worth a real fix on the `ddp-sync` side (either raise/remove the truncation limit, or
always keep the tail of the output rather than the head, or fetch the last N lines
separately from a truncated middle) -- for the biggest jurisdiction in this backfill, the
one summary line that matters most is exactly the one getting lost. Didn't attempt to fix
it myself; flagging with the precise evidence.

## Backfill status unaffected

The actual result is clean regardless of the capture bug. `us` refresh-extraction dry-run
done, `docs_refused=0`. Per the plan, `us` still needs `refresh-extraction --commit`, then a
fresh `recompute-diff-order --dry-run` (its existing one predates this refresh), spot-check,
go-ahead, commit. `wa`'s fresh dry-run is also already confirmed clean and waiting on a
commit go-ahead. Both queued behind explicit user confirmation, not run yet.
