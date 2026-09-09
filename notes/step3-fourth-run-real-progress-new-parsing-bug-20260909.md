# Fourth validation run: credential fix works, RDS connects, archive logic runs clean -- but a new parsing bug surfaced

*Follows up on `notes/open260-verified-end-to-end-20260909.md`.* Re-ran the `ut` Fargate archive
validation (task-def `ddp-scrapers:19`, RUN_ID `ut-archive-3fb936fc59bc`) now that OPEN-260 is
fixed. Real progress: **no more auth or network errors at all.** New problem, different layer.

## What happened

Task ran 54 seconds (vs. the prior 1-second auth-reject or 130-second network-timeout patterns),
exited 1. Log shows the actual archive command completed and printed a real summary:

```
ut: 1021 bills checked | fetched=0 skipped=9371 archived=0 fetch_errors=0 blocked=0
extract_errors=0 conflicts=0 s3_verified=0 s3_unverified=0
ERROR: ut archive exited 0 but produced no parseable summary line -- cannot confirm counts
{"source": "ut", "run_id": "ut-archive-3fb936fc59bc", "status": "unparsed", "duration_s": 39}
```

That `1021 bills checked` / `9371` figure matches exactly what this session's own RDS backfill
dry-run found earlier today -- the connection and the DB read are both genuinely correct.
`fetch_errors=0 blocked=0 extract_errors=0 conflicts=0` -- no real archiving errors either. This
looks like a legitimate "nothing new to archive" result for `ut`, not a data problem.

## The actual bug: a missing field in the printed line

`cloud_archiver.py`'s `_SUMMARY_LINE_RE` (this repo) expects, in order: `fetched`, `skipped`,
`archived`, `fetch_errors`, `blocked`, `extract_errors`, `conflicts`, **`concurrent_writes`**,
`s3_verified`, `s3_unverified`. The actual printed line has `conflicts=0` immediately followed
by `s3_verified=0` -- **`concurrent_writes=N` is missing entirely**, so the regex never matches,
`parse_summary_line()` returns `None`, and the runner reports `status: "unparsed"` and exits 1
even though the underlying archive run was clean.

Checked `openstates-core`'s current `main` (pulled fresh, `HEAD` includes OPEN-260 #43): the
`archive()` command's summary `click.secho(...)` **does** include `concurrent_writes=...` in
that exact position, and has since `2026-08-30` (OPEN-107, 10 days ago) -- so this isn't a
field that's simply never existed. Something about what's actually baked into the deployed
`ddp-scrapers:v15` image doesn't match current `main`'s output shape.

**I can't check the ECR image directly to see which `openstates-core` commit it's actually
running** -- `ecr:GetAuthorizationToken` is still denied on this host's role (same gap as the
original OPEN-257 deploy attempt; never resolved, just routed around by building from the Mac
instead). Whoever built/pushed `v15` can check this directly (`docker run --entrypoint python3
<image> -c "import openstates; print(openstates.__file__)"` or similar, or just check what SHA
`pip show` / the image's install reports).

## Status

This is real, positive progress -- credentials, networking, and the actual DB read/archive
logic all work now. The one remaining issue is this output-parsing mismatch, which looks like
either a stale `openstates-core` pin baked into `v15`, or a real drift between what
`cloud_archiver.py` expects and what `archive()` actually prints. Not blocking on data
correctness, just on the runner's own success/failure classification.
