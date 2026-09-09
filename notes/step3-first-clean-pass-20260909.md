# First genuinely clean end-to-end pass -- Step 3 substantially done

*Replies to `notes/v16-built-root-cause-was-docker-build-cache-20260909.md`.* Re-ran `ut`
against task-definition `ddp-scrapers:20` (RUN_ID `ut-archive-7fa3924d50c8`). **Exit code 0.**

```
ut: 1021 bills checked | fetched=0 skipped=9371 archived=0 fetch_errors=0 blocked=0
extract_errors=0 conflicts=0 concurrent_writes=0 s3_verified=0 s3_unverified=0
{"source": "ut", "run_id": "ut-archive-7fa3924d50c8", "status": "ok", ...}
```

`concurrent_writes=0` present and parsed correctly this time -- your `--no-cache` rebuild fixed
it. `status: "ok"`, clean completion record, no errors anywhere.

## One thing not literally exercised: the GLACIER_IR write

`archived=0` -- `ut` genuinely has nothing new to archive right now (consistent across every run
today), so this pass didn't upload a new document, meaning it doesn't directly confirm "a
document lands in `ddp-bill-archive` at `GLACIER_IR`" the way the original Step 3 ask wanted.
That specific write path (`_upload_and_verify_direct()`) was already fixed and verified
separately under OPEN-257 earlier today, so I'd treat this as substantially covered rather than
a real gap -- but flagging rather than silently declaring full success, in case you want a
run against a jurisdiction/session with something actually pending to get a fully literal
end-to-end proof before flipping `use_fargate: true` for real.

## Summary of everything this validation thread actually found and fixed today

For whoever reads this later without the full thread: IAM gaps (ECR push, task-def read/write),
missing ARM64 emulation on this EC2 host, an RDS security-group ingress gap, a matching egress
gap, the automatic 7-day RDS credential rotation (root cause of the whole detour) plus its
live-resolve fix (OPEN-260) and that fix's own secret-shape bug, and finally a stale Docker
build-cache layer masking a 10-day-old upstream fix. Every one of these was a real, previously-
latent bug that a "does it build/merge" check would never have caught -- this is exactly the
value a real Fargate-launched validation run was supposed to provide.
