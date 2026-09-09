# Understanding the 6,270/5,817 refused docs — the tool couldn't tell you why, that's fixed now

*Replies to `notes/rds-backfill-ut-wa-dryrun-results-20260909.md`.*

## Why nobody could see a reason before

Dug into `refresh_extraction()` directly. `_reextract_document()` already computes a specific
`reason` for every document that comes out worse than what's stored (either the actual exception
message it raised, or "no exception, extraction just returned empty") — but `refresh_extraction()`
threw it away, only ever incrementing a bare `docs_refused` counter. There was never a way to see
*why* any of the 6,270/5,817 were refused, dry-run or `--commit` — the information existed one
function down and just never made it into the report.

## Fixed

[openstates-core#42](https://github.com/Digital-Democracy-Project/openstates-core/pull/42) —
mirrors the existing `skip_reasons` grouping/reporting exactly (same top-10-by-count style), so a
real regression affecting many documents shows up as one dominant line instead of disappearing
into an opaque count. Verified against a real extractor failure (confirmed live:
`AssertionError: 0 matches for .//*[@class="WordSection1"]` on malformed MI HTML), not a
synthetic mock — new test asserts the exact reason string now appears in dry-run output.

Also applied OPEN-258's logging fix in the same PR (silencing boto3/botocore/s3transfer/urllib3),
since I needed to run this locally against real data myself and didn't want to repeat the same
credential-leak risk you already flagged. Called out separately in the PR description in case you
want it split into 258's own PR instead.

**Once this lands, re-run `refresh-extraction ut --dry-run` / `wa --dry-run` against RDS again**
— the report will now include lines like `refused N: <the actual reason>` for whatever's actually
happening, which is what actually answers Ramon's question, not just confirming the count is
large.

## One dead end, so you don't have to retrace it

Tried comparing against this Mac's own local production-scale Postgres (not the small dev one —
same container, `openstates` database, 1,021 real UT bills / 3,411 real WA bills). Both come back
**completely clean** (`docs_refused=0`, `stale_docs=0`) — because the Mac already got OPEN-211's
backfill applied back on 2026-08-29. There's no "stale" baseline left there to meaningfully
compare a refusal *rate* against, so this approach can't answer the question either way. Mentioning
so nobody else spends time on the same comparison expecting it to work.
