# Michigan retry confirms the text-extraction fix worked -- 0 total-failure bills now, down from 35

Follow-up to `mi-first-real-test-archiving-lag-20260914.md`. Re-ran the exact same 50 bills
(`bill_candidates` with explicit `gov_id`+`bill_openstates_id` pairs, not a session-wide `limit`
scan, so this is guaranteed the same set, not just probably the same set) with `retry_failed=true`
once the text-extraction fix landed. Same 9 artifact types + `bill_changelog` +
`include_concept_statements=true`, `include_org_research=false`, dev broker.

**Result: 29 of 50 bills now come back completely clean (up from 10), and zero bills fail every
type (down from 35).** The 21 bills with a remaining failure are almost entirely the model
correctly declining `bill_opposing_orgs` (matches the already-known AGENTS-98 pattern -- this
question type declines far more often than its `bill_supporting_orgs` sibling) and a handful of
`bill_pros_cons` declines (AGENTS-101's pattern) -- confirmed these are real per-artifact
declines this time (1-3 real seconds each, not the old instant 0.02-0.09s "no Bill exists"
rejection), not the archiving-lag failure from before.

**One outlier worth a look, not alarming**: SB 1151 failed 7 of 8 content types (only
`bill_topics` succeeded), each after 1-3 real seconds -- so extraction worked, the model just
declined almost everything. `concept_statements_skipped_reason=nothing_to_publish` too. Best
guess, not confirmed: this bill's real text is unusually short/sparse (a minor technical
amendment or similar), giving the model little to summarize while still being enough to infer a
topic tag. Flagging in case anyone wants to check the actual bill text; not chasing further from
this session.

Mechanical note on `bill_candidates`, for whoever uses this endpoint next: each entry needs both
`gov_id` and `bill_openstates_id` (I first sent only `bill_openstates_id`, got a clean 422 with no
side effects -- the request is validated before anything dispatches, so a schema mistake here is
free to retry, not a partial-run risk).

Net: the archiving-lag issue from the first note is confirmed fixed for this sample. Content
quality on the newly-successful bills not yet spot-checked in this note -- can do a follow-up read
if useful.
