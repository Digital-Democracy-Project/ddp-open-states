# rev21 works -- persist fixed, us completed clean, but S3 upload is blocked by a real IAM gap

*Replies to `notes/appdir-permission-fix-rev21-ready-20260909.md`.* Re-ran the full 9-jurisdiction
batch against task-definition `ddp-scrapers:21`, fresh RUN_IDs, credential resolved fresh again.
**All 9 exited 0 this time, including `us`** (SYNC-58's dropped-connection crash didn't recur --
worth confirming whether that was fixed incidentally or just didn't trigger this run).

## The `/app` permission fix works

`archived` is finally nonzero: `az=32`, `ma=74`, `mi=12`, `us=506` (all exactly matching their
`fetched` counts -- the local-persist step that was silently eating every document yesterday now
succeeds for all of them). `fl`/`ut`/`wa`/`al` still `archived=0`, consistent with them having
nothing new all along (not new information, same as every prior run).

## New problem: every single upload is unverified -- real IAM gap, not a config mistake on my end

`s3_verified=0` and `s3_unverified` exactly equals `archived` everywhere (32/74/12/506). Checked
the actual log line rather than guessing:

```
S3 upload failed for bills/raw/az/57th-2nd-regular/upper/SCM1004--.../Senate_Engrossed_Version_...pdf:
An error occurred (AccessDenied) when calling the PutObject operation: User:
arn:aws:sts::350941939790:assumed-role/ddp-scraper-task-role/... is not authorized to perform:
s3:PutObject on resource: "arn:aws:s3:::ddp-bill-archive/bills/raw/az/..."
```

Identical `s3:PutObject` `AccessDenied` confirmed across `az`/`ma`/`mi`/`us` -- not one
jurisdiction's fluke. Also confirmed it's genuinely running `_upload_and_verify_direct()` (a real
boto3 `PutObject`, not the sudo-gated Mac wrapper) -- so `ARCHIVE_S3_MODE` is already correctly
set to `direct` somewhere in the task definition/image default; I didn't need to pass it myself.
The gap is purely `ddp-scraper-task-role` missing `s3:PutObject` (and likely `s3:GetObject`/
`s3:HeadObject`, needed for the ETag-verification half of `_upload_and_verify_direct()`) on
`ddp-bill-archive`.

## Next step

Needs an IAM policy grant on `ddp-scraper-task-role` -- `s3:PutObject` + `s3:GetObject` (for
verification) scoped to `arn:aws:s3:::ddp-bill-archive/bills/raw/*` at minimum. Not something to
self-grant from here (this is a task ROLE, not this host's own instance role -- different
principal entirely, so `iam_verify_by_invocation`-style self-checks don't apply). Once it's
added, re-run the same batch one more time -- if `s3_verified` comes back nonzero and a real
object in `ddp-bill-archive` shows `GLACIER_IR`, that's finally the literal end-to-end proof the
original Step 3 ask wanted, four fixes and two days later.
