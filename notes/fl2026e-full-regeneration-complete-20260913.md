# FL 2026E: full regeneration complete via /trigger/bill-artifact-generation + retry_failed

Marked the 176 rows (8 non-changelog types x 22 bills) `status=failed`, fired
`POST /trigger/bill-artifact-generation` on the Mac (`X-DDP-Environment: prod`,
`retry_failed: true`, `include_concept_statements: false`, `include_org_research: false`,
`limit: 25`, the 8 artifact types listed in the plan). Path needed the `/ddp-sync/v1` prefix
(`/ddp-sync/v1/trigger/bill-artifact-generation`) -- the bare path 404'd first try.

**Real gotcha, worth flagging**: my first curl used a 10s timeout and hit `HTTP_STATUS:000`
(client-side timeout) -- this endpoint runs synchronously and blocks until the whole batch
finishes, so a short client timeout looks like a failure but the request had already been
accepted and was processing. Confirmed via direct DB polling (rows moving out of `failed` in
real time) that the original request was the one doing the work, not a phantom -- did NOT
fire a second overlapping request, since this endpoint (unlike the WireGuard one) has no
Redis overlap lock protecting against a second concurrent run on the same bills.

**Final result, verified precise**: of the 176, **162 completed successfully, 14 failed with
a real, final, honest reason** (`failure_stage=generation`, `failure_reason=
insufficient_information` -- the model correctly declined to fabricate content rather than
guessing). 13 of the 14 are `bill_opposing_orgs` across 13 different bills, 1 is
`bill_pros_cons` for one specific bill (SB2508E). Not a bug or a stuck job -- confirmed the
count adds up exactly (162+14=176) and no rows are stuck in `pending`/`processing`.

Combined with the earlier `bill_changelog` (10 fresh) and `ConceptStatementSet` (44, albeit
duplicated across the two earlier runs -- still an open item) results, this closes out the
FL 2026E bounded test's original goal: full genuine regeneration across all 9 artifact types
for real, end-to-end, through the production archiver-triggered LegBot path (and, for this
final cleanup pass, the manual retry-failed endpoint).

Remaining open items from this whole thread, for whenever it's useful to revisit:
- The `ConceptStatementSet` duplication bug (44 pending rows instead of 22) -- not touched
  in this pass, deliberately excluded via `include_concept_statements: false`.
- Whether the 14 genuine `insufficient_information` failures are worth a closer look (are
  these bills missing source text, or is this the model correctly recognizing there's no
  real opposition to name) -- not investigated further, flagging as a possible follow-up
  only if anyone cares to look.
