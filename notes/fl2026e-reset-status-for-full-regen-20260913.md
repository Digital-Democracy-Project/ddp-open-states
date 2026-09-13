# FL 2026E: Ramon wants a full regeneration -- please reset the old rows' generation status

Answering your own question from the last note: Ramon wants the full run, not just proof
the pipeline fires. Please reset the **`status`** field (not `review_status`, which should
stay `rejected` as-is) on the 198 old `BillArtifact` rows back to `pending` -- that's the
field the coverage check in `session_pipeline_runner.py` actually reads to decide "does
this bill still need this artifact type," and it's what caused 8 of the 9 types to be
skipped as already-done last time (179 `complete` + 19 `failed`, both read as "don't
regenerate" by the coverage check without `retry_failed=True`).

No need to delete the rows or touch anything else -- `BillArtifactWriteSerializer`'s own
write path is `update_or_create` on the natural key (bill_version, artifact_type,
model_version, prompt_version), so a fresh dispatch will just overwrite these same rows in
place once `status` no longer reads as already-complete.

**Confirmed directly in the serializer's `create()`** (not just assumed): every write --
new or updating an existing row -- unconditionally sets `review_status` to `APPROVED`
(since `BILL_ARTIFACT_REQUIRE_REVIEW=false` in production) and clears
`reviewed_by`/`reviewed_at`, regardless of the row's prior state. So the currently-rejected
`review_status` on these 198 rows will NOT survive a real regeneration -- once
regenerated, they go live immediately as fresh, approved content, same as the two types
that already regenerated in the first run. That's the intended behavior for genuinely new
content, not a bug, but flagging it plainly since it means "reset status" and "these rows
go live again" happen together, not as two separate steps.

Once reset, re-fire the same FL 2026E dispatch and this should produce genuine fresh
content for all 9 artifact types across all 22 bills, not just the 2 that escaped the
status check last time.
