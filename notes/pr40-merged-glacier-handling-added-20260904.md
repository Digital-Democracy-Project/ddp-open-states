# PR #40 merged — now also handles Glacier Deep Archive objects, ready to pull

*Follow-up to `notes/refresh-extraction-s3-fallback-fix-20260904.md`.* Two things changed since
that note:

## 1. PR #40 is merged

`openstates-core` PR #40 (S3 fallback for `refresh-extraction`/`reextract`) is merged into
`main`. Nothing further to wait on here — step 1 of "before you re-run Step 1" is done.

## 2. Extended, same PR: Glacier Deep Archive objects get their own reason

While the PR was under review, Ramon asked what happens if a stale document's S3 object is
sitting in Glacier Deep Archive rather than STANDARD_IA — the archive's original upload path
(`_upload_and_verify_via_wrapper`) writes to Deep Archive; only the newer OPEN-192 cloud path
(`_upload_and_verify_direct`) writes at STANDARD_IA specifically to stay immediately readable. A
plain `GetObject` against an un-restored Deep Archive object raises `InvalidObjectState`, which
the first version of this fix would have folded into the generic "may be systemic" bucket —
misleading, since it's a real, expected, per-document condition, not a credentials/network
problem.

Added before merge, same PR, filed as **OPEN-255** (now Done): a Deep Archive object now reports
its own distinct, poolable reason — `"archived in Glacier Deep Archive, needs restore (~12h)
first"` — so if any of RDS's stale documents are old enough to be Deep Archive, the dry-run
report will show them as their own separate count instead of hiding under "systemic." No
`RestoreObject`-and-retry logic was added — that's a separate, ~12h-async, stateful workflow, not
something worth building until we see whether the real numbers make it necessary.

## Before you re-run Step 1

1. Pull the EC2 host's `openstates-core` checkout to `main` (includes both the S3-fallback fix
   and the Glacier handling — one pull covers both).
2. Re-run `refresh-extraction ut/wa/us --dry-run` against RDS exactly as planned in
   `notes/rds-backfill-execution-request-20260904.md`.
3. Read the report's skip-reason breakdown this time, not just the top-line stale count — with
   this fix in place it should distinguish four outcomes instead of reporting nothing:
   genuinely clean (no action), fixed via local disk or S3, `"not found locally or in S3"`
   (a real gap worth its own look), and Deep Archive (`needs restore (~12h) first` — expected for
   older documents, not a bug).
4. If a meaningful number land in the Deep Archive bucket, flag the count here before deciding
   anything — whether a restore-and-retry pass is worth building is a real question, not a
   foregone one.

One more thing for Ramon, not for you to act on: PR #40 shows as merged by `agent-smith-ddp` —
flagging since that's the account I merge under too, but the shared login means it could equally
be Ramon merging directly. Not treating this as a rule violation on either the dev or prod side
without confirming which one it was.
