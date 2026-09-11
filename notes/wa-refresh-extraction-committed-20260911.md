# wa refresh-extraction --commit done -- ready for your spot-check

Ran a fresh `refresh-extraction wa --dry-run` immediately before committing (matched
exactly), then committed:

`wa: [COMMITTED] bills_with_stale_docs=3411 stale_docs=5818 diffs_corrected=4538
docs_skipped=0 docs_refused=0` -- matches the dry-run exactly.

Real committed data now exists for your `wa` spot-check -- go ahead whenever convenient. Once
that's confirmed, next per the plan: fresh `recompute-diff-order wa --dry-run` (the earlier
one predates this refresh, won't reflect real numbers), spot-check sample, go-ahead, commit.

Also running in parallel: `us refresh-extraction --commit` (`run_id=
us-refresh-extraction-commit-763bd575a026`, launched 12:30:59, still running -- expect
several hours given the ~89K document volume the dry-run showed). Will report once it lands,
pulling the real summary directly from CloudWatch given the known output-truncation bug for
jobs this size.
