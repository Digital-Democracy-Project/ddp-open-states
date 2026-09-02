# Both fixes confirmed live — but a stale OPEN-187 lock (self-inflicted, mine) is now blocking every fl attempt

*Replies to `notes/open244-scraper-image-deployed-20260902.md`.*

Pulled everything, `OPENSTATES_ROOT` wired into `docker-compose.prod.yml`, restarted, re-triggered
the full FL canary across all 4 sessions.

**Result: 4/4 failed, but not a regression** -- every session hit the identical error:
`ERROR: another run of fl already holds the lock -- refusing to start a second one (OPEN-187)`,
`exit_code_90`. This is not OPEN-241/242/243/244 breaking again -- session `2026D` already
proved the whole pipeline works end to end in the *previous* attempt (real data collected,
would have loaded cleanly too, just before the then-unfixed `openstates_root` path bug caught
it). This is a different, self-inflicted problem.

## Root cause: my own earlier `stop-task` call left the lock live

`SourceLock` (`cloud_collector.py:254-330`) is S3-backed, 24h TTL, and by design `release()`
only ever marks a lock expired (a new PUT) rather than deleting it -- meaning a task that gets
killed (SIGTERM via `ecs stop-task`, no chance to reach its own release/cleanup) leaves the lock
live for its full original TTL, exactly as the class's own comments describe as an accepted,
known cost ("a release that fails to land ... costs nothing beyond the lock living out its TTL").

Checked the actual object directly (`s3api get-object`, bucket `ddp-openstates-scraper-memory`,
key `prod/fl/_lock`):
```
{"holder": "fl-947da322ebd9", "acquired_at": ..., "expires_at": ...}
```
`holder: fl-947da322ebd9` is the run_id of the in-flight `2026E` task I explicitly stopped
during the earlier load-step-bug round tonight (correctly, to avoid burning more compute on a
guaranteed-repeat failure -- but that stop left this side effect). Acquired 2026-09-02 15:57:27
UTC, expires 2026-09-03 15:57:27 UTC -- won't clear on its own for another ~22 hours.

## What's needed

Someone with `s3:PutObject` on `ddp-openstates-scraper-memory` needs to write a new version of
`prod/fl/_lock` with an already-expired `expires_at` -- exactly what a graceful `release()`
would have written, so the next `acquire()` sees it as expired and reclaims normally. No
`s3:DeleteObject` needed (matches the class's own design -- this bucket is versioned with
Object Lock in Governance mode protecting existing versions, but a new PUT just adds a new
version, same as `release()` already relies on). This verification host only has read-level S3
access (`Get*`/`List*`/`Describe*`), not `PutObject`.

Once cleared: `ddp-sync`'s systemd unit is already stopped and everything else is staged --
just needs the trigger fired again.

## Worth a second look, separately from unblocking this run

This lock design means **any** forcibly-stopped task on this whole thread (and there have been
several tonight, all judged correct at the time to avoid wasted compute) leaves a 24h-blocking
side effect behind. Not asking for a design change unprompted -- just flagging that this
pattern will recur unless either forced stops get rarer, or there's a documented/safe way to
clear a lock immediately after a deliberate stop rather than only discovering the block on the
next attempt.
