# OPEN-193 — collection now works end to end; RDS load step hardcoded to the Mac Studio path

*Replies to `notes/open193-cloud-collector-noop-misclassified-failed-20260902.md`.*

Good news first: session `2026D` (`mode: "full"`) collected real data cleanly --
`{"source": "fl", ..., "status": "ok", "session": "2026D", "found": 17, "duration_s": 139}`,
6 bills + 7 vote events + jurisdiction/org objects. **The Fargate/ECR/entrypoint path (OPEN-241
+ OPEN-242) is now proven working end to end against real data**, not just a clean exit code --
this is the first genuinely successful cloud collection this whole thread has seen.

## But the RDS load step failed right after, and will fail identically every time

```
cloud_scrape: load failed detail="cloud_loader.py exited 2: python3: can't open file
'/Users/agentsmith/Developer/repos/ddp-open-states/cloud_loader.py': [Errno 2] No such file or
directory" jurisdiction=fl run_id=fl-1f280053977b
```

`_get_root(config)` (`ddp_sync/pipelines/openstates_scrape.py:90-91`) reads
`config.get("openstates_root", DEFAULT_OPENSTATES_ROOT)`, and `DEFAULT_OPENSTATES_ROOT` is the
Mac Studio's absolute path. It *is* set explicitly in `sync_schedule.yaml` too (lines 219 and
706, under `openstates_scrape:` and `openstates_archive:`) -- but to that same Mac path, since
that file is presumably the same one every `ddp-sync` host pulls via git. On this host, the real
path is `/opt/ddp-open-states`.

**Same shape of bug as the Redis DB / per-task-flags bugs already fixed tonight** -- a value
that's inherently per-host, living in a single file every host shares identically. Editing
`sync_schedule.yaml` directly on this host wouldn't actually fix it (next `git pull` overwrites
it), and committing `/opt/ddp-open-states` as the new default would presumably break the Mac
Studio's own copy, which needs its own path. Guessing the right shape of the fix (an env-var
override on `openstates_root`, mirroring `REDIS_URL`'s fix in PR #111) rather than proposing an
exact diff -- not mine to decide.

## Stopped before burning more real Fargate on a guaranteed-repeat failure

Unlike the no-op misclassification above (data-dependent, worth letting play out), this one is
deterministic -- every remaining session's collection would succeed (now that OPEN-241/242 are
fixed) and then hit this exact same load failure, each burning ~2 minutes of real Fargate for a
load step that can't possibly succeed. Stopped `ddp-sync` and the in-flight `2026E` task once
confirmed; cluster is clear.

## Running tally, this canary attempt

- OPEN-241 (assignPublicIp) -- fixed, confirmed by task reaching `RUNNING`.
- OPEN-242 (command double-prefix) -- fixed, confirmed by real scraper output.
- `cloud_collector.py` no-op misclassification -- found, not yet fixed, data-dependent (may not
  block every session).
- `openstates_root` hardcoded to the Mac path -- found, not yet fixed, deterministic (blocks
  every session's load step until it's addressed).

Same holding pattern as every round tonight: not attempting either remaining fix myself, not
re-triggering until at least the path issue lands.
