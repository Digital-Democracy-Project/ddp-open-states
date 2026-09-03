# Orphaned data recovery authorized — please run the three loads

*Replies to `notes/open193-canary-closed-plus-orphaned-data-20260902.md`.*

Ramon says yes, recover it. Please run, from inside the working `ddp-sync` container:

```
cloud_loader.py fl fl-1f280053977b session=2026D
cloud_loader.py fl fl-9237033aa89b session=2026E
cloud_loader.py fl fl-c10699ea2180 session=2026F
```

A few things worth doing given this is a real, deliberate write to production RDS:

- Run them one at a time, confirm each completion record (`status: ok`) before moving to the
  next, rather than firing all three at once.
- Same spot-check discipline you already used to catch this in the first place -- confirm via
  api-v3 (or a direct query) that the data actually landed for each session afterward, don't
  just trust the exit code.
- If any of the three fails for a reason unrelated to the bugs already fixed tonight (a fresh
  problem), stop and report back rather than retrying blind -- three manifests still sitting in
  S3 costs nothing to leave alone a little longer if something looks wrong.

Report back with the result of all three once done.
