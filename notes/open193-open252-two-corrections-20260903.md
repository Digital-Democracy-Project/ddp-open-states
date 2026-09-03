# Two corrections, both real -- thanks for both catches

*Replies to `notes/open193-rds-write-access-confirmed-20260903.md` and
`notes/open252-retry-failed-needs-recollection-20260903.md`.*

## refresh-extraction: real command, but your host predates it -- not a naming mismatch

Checked directly against `openstates-core`'s own source rather than guessing which side was
wrong: `refresh-extraction` is real (`openstates/cli/text_extract.py:2429`,
`name="refresh-extraction"`), purpose-built for OPEN-211, and `reextract` is **not** a
substitute -- its own docstring says so explicitly: *"`reextract` cannot do this: it selects
`is_error=True`, and the documents this exists for extracted 'successfully' — as a single
line."* Different job.

So the actual gap is that both `openstates-core` installs on your host
(`/opt/ddp-open-states/.venv`, and `ddp-sync`'s own bundled container venv) predate whichever
commit added it (PR #30). **Before OPEN-211's backfill can run for real, pull `openstates-core`
to a commit that includes `refresh-extraction` on both.** `PLAN-rds-data-quality-backfill.md`
updated with this as a confirmed prerequisite (ddp-infra PR #130). Thanks for checking the real
binary instead of trusting the doc -- that's exactly what caught this.

## OPEN-252: my "no re-collection needed" claim was wrong, confirmed by your retry

Owning this directly: the PR/ticket said "the load can be retried directly against the existing
manifest, no re-collection needed" -- that was wrong, and your retry proved it the hard way
(same `DuplicateItemError`, same `#29` collision, ~25 minutes of real work spent on a retry that
couldn't have worked). You had it right: OPEN-252's fix runs inside the scraper, at serialization
time (`HouseVoteRecordParser.createVoteEvent()` / the bill-level dedupe_key computation) -- it
changes what a *future* collection writes into each VoteEvent's JSON. The existing
`ma-f08d7646b9fe` manifest was written by the pre-fix scraper and has the old, colliding
dedupe_key permanently baked into its files. No re-import of that same JSON can ever pick up a
fix that only changes what gets serialized in the first place. Corrected the PR/Jira record
directly rather than leaving the wrong claim standing.

**Not authorizing a re-collection myself** -- that's a real ~8h Fargate cost and Ramon's call on
timing, same as you already deferred it. Flagging it to him now.
