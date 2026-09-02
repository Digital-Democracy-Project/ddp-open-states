# fl lock cleared — no new permissions granted anywhere

*Replies to `notes/open187-stale-fl-lock-self-inflicted-20260902.md`.*

Great diagnosis — confirmed your read of `SourceLock.release()`'s exact write shape and
replicated it directly rather than granting the EC2 role `s3:PutObject` on the bucket.
Ramon and I talked this through: that role runs `ddp-broker`/`api-v3`/`ddp-sync`, none of
which have a legitimate reason to write into the scraper's own memory bucket — the Fargate
task's own task role already owns that write path by design. Widening the EC2 role's
permissions for a one-off lock fix would have been a standing grant in the wrong place.

Instead, used the `ddp-scraper` credential (already scoped with `s3:PutObject` on
`ddp-openstates-scraper-memory` for the earlier OPEN-244 deploy) from the Mac:

- Read `prod/fl/_lock`'s current ETag directly.
- Wrote a new version with the same shape `release()` would have written --
  `{"holder": "manual-release-stale-fl-947da322ebd9-lock-OPEN187-20260902", "acquired_at": <now>, "expires_at": <now - 1>}`
  -- conditioned on that exact ETag (`IfMatch`), so the write would have failed cleanly rather
  than clobbering anything if the lock had changed underneath in the meantime.
- Verified: the new version is live, and `now <= expires_at` now correctly evaluates `False`
  -- `acquire()`'s existing reclaim path will pick this up normally on the next attempt, no
  code change needed.

No IAM changes made anywhere. Please re-trigger the FL canary whenever ready -- this should
be the last blocker.

On the broader point you raised (any forcibly-stopped task leaves this same 24h side effect):
agreed it's worth a real look, but that's a separate design conversation, not blocking tonight
-- flagging it's been heard, not deciding anything about it here.
