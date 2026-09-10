# rev23: clean pass on az/mi/ma, GLACIER_IR confirmed directly -- the literal proof, finally

*Replies to `notes/rev22-regression-root-caused-v19-rev23-ready-20260910.md`.* Ran
`us`/`az`/`mi`/`ma` against task-definition revision 23 (with PR #228 now merged to `main`).

## az/mi/ma: fully clean, first time all-zero on every failure counter

```
az: fetched=34 archived=34 s3_verified=34 s3_unverified=0 persist_errors=0
mi: fetched=13 archived=13 s3_verified=13 s3_unverified=0 persist_errors=0
ma: fetched=149 archived=149 s3_verified=149 s3_unverified=0 persist_errors=0
```

`ma`'s 149 confirms the earlier prediction (`notes/rev22-us-ma-confirm-regression-plus-scope-note-20260910.md`)
-- it recovered the full stuck-row population (both the 2026-09-09 incident's ~74 and OPEN-266's
~75 excess `is_error=False` rows) in one pass, not just the incident subset.

## GLACIER_IR confirmed directly, not inferred from the summary line

Queried RDS for the same `SCM1004` bill flagged as the concrete example throughout this thread --
its `archive_location` is now a real S3 URI (was `None` since the 2026-09-09 incident). Checked
it directly:

```
aws s3api head-object --bucket ddp-bill-archive --key "bills/raw/az/.../Senate_Engrossed_Version_...pdf"
→ StorageClass: GLACIER_IR, LastModified: 2026-09-10T05:41:20Z
```

This is the literal end-to-end proof the original Step 3 ask wanted two days ago: fetch, local
persist, S3 upload, verification, and permanent storage class, all confirmed for real on a
document that was concretely stuck until this run.

## `us`: transient infra hiccup, unrelated to the fix, retrying now

First `us` attempt failed to even start: `CannotPullContainerError ... dial tcp ...: i/o timeout`
pulling `ddp-scrapers:v19` from ECR -- a network blip, not a code or task-def issue (`az`/`mi`/`ma`
pulled the same image fine around the same time). Retried immediately with a fresh RUN_ID,
in flight now, will report separately.

## Where this leaves the thread

`az`/`mi`/`ma` (and once `us` lands clean, presumably that too) close out OPEN-263's own
acceptance criteria for real, with direct evidence rather than a clean-looking summary line
alone. Worth someone re-confirming the ~747-row stuck-row count is now near-zero for the
`is_error=False` subset across all four jurisdictions, per the verification plan
`notes/open266-investigation-status-20260910.md` already laid out -- I can pull that count again
if useful.
