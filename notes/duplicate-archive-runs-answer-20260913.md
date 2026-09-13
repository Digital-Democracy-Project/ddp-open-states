# Duplicate archive-task launches: same visibility gap as OPEN-285, but the exposure is bounded by design regardless

Same wall you hit from the Mac: this EC2 host's own role also gets `AccessDeniedException` on
`ecs:DescribeTaskDefinition`, `logs:DescribeLogGroups`, and `cloudtrail:LookupEvents` -- no
historical ECS task list (ECS itself only retains STOPPED tasks ~1hr, long gone for anything
from the last 3-4 days), no CloudWatch log access, no CloudTrail. `ecs:ListTasks` with
`--desired-status RUNNING` right now returns nothing either way (no archive job in flight at
the moment I checked). **I cannot reconstruct actual historical launch timing from either
host** -- flagging that gap plainly rather than guessing at numbers.

**But I can answer the more important question directly from the code, and it's a solid
answer: even if both hosts' schedulers did fire for the same jurisdiction on the same day, no
duplicate real work would have happened.**

Traced `cloud_archiver.py` (the actual Fargate task both hosts launch) directly:

1. **Cross-machine exclusion is real, not per-host.** It acquires `SourceLock(..., suffix=
   "_archive_lock")` keyed on the bare jurisdiction code (`lock.acquire(state)`) -- an
   S3-conditional-write lock, not a local one. Confirmed both hosts' `ddp-sync` read the exact
   same `sync_schedule.yaml` (`memory_bucket: "ddp-openstates-scraper-memory"`,
   `memory_prefix: "prod"`, same `cluster`/`task_definition`) -- a single shared config file
   both pull identically, so both hosts' launches target the identical S3 lock keyspace. Two
   archive runs of the same jurisdiction, launched from anywhere, contend for the identical
   lock.
2. **A contended second launch does ZERO real work.** If `lock.acquire(state)` fails (another
   run already holds it), `cloud_archiver.py` prints an error, emits
   `status="failed"`, calls `touch_do_not_retry()`, and returns `EXIT_DO_NOT_RETRY` --
   `_archive()` (the function that actually fetches/uploads documents) is **never called at
   all**. Not a partial re-fetch -- the second process exits before touching the jurisdiction's
   site or S3 in any way.
3. **A non-contended "duplicate"** (launched far enough apart that the first had already
   finished and released the lock) would proceed normally, but `archive_bill_versions()`'s own
   natural-key skip-check (version_note, version_date, source_url -- the same idempotency this
   file's own docstring already documents) makes re-processing already-archived documents a
   no-op regardless of which run touched them first. Nothing new would typically have appeared
   between two near-simultaneous scheduled runs, so this shouldn't meaningfully re-fetch
   anything either.
4. **MI specifically** (the WAF concern): scenario 2 never reaches MI's site at all (fails
   before `_archive()`). Scenario 3 repeats the WAF-cookie-freshness check but doesn't re-fetch
   documents already covered by the skip-check -- no unusual extra site engagement from this
   duplication shape either way.

**Bottom line: I can't tell you whether an overlapping launch actually happened in the last few
days (no visibility into that history from here), but I can tell you the exposure was bounded
by design in either direction -- worst case is a fast, clean `EXIT_DO_NOT_RETRY` failure with
zero site/S3 impact, not double real work.** If you want to actually confirm whether one
happened, that needs either CloudWatch Logs access granted to one of our roles, or a Redis
flow-history mechanism for archive jobs (parallel to what scrape jobs already have) -- flagging
both as options, not picking one, since it's your/Ramon's call whether closing this visibility
gap is worth doing given archiving is now off on the Mac and the exposure window is closed
either way.
