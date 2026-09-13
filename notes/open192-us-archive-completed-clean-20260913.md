# OPEN-192: `us` archive job completed -- clean, first fully automatic success

Real final result, pulled from CloudWatch (task `e547f81775b445ddb3688fad76c093e2`, STOPPED,
exit code 0):

```
us: 37985 bills checked | fetched=108 skipped=89523 archived=108 fetch_errors=0 blocked=507
extract_errors=0 conflicts=0 concurrent_writes=0 s3_verified=108 s3_unverified=0
persist_errors=0
{"status": "ok", "duration_s": 887}
```

Clean: `s3_verified` == `archived` exactly, `persist_errors=0`, `fetch_errors=0`. `blocked=507`
is a real, separate, expected metric (source-site blocks on some requests), not an error --
everything actually fetched made it all the way to a verified S3 upload.

This is the first time archiving has completed on its own real schedule on this host, start to
finish, no manual trigger involved. OPEN-192 Phase 3 is now genuinely, fully live in
production, not just proven-but-dormant.

Also: MA vote-event patch (from `notes/ma-2026-09-06-failure-root-cause-20260913.md`) -- IAM
gap resolved (Ramon granted scoped `s3:PutObject`), both manifest objects patched and
re-uploaded successfully, load retry in progress now. Will report the real result once it
finishes.
