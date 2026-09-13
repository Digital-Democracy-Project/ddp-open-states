# OPEN-192 (Phase 3, archive to cloud): real current status check

Ramon asked whether Phase 3 is actually done. Its Jira comment history's last real update
is from 2026-09-09 (4 days stale relative to today) and says three things were still
outstanding at that point:

1. Image deploy to the real ECS task definition -- was marked done then (`ddp-scrapers:v15`,
   registered as task-definition revision 19).
2. A real end-to-end validation run: a scheduler-launched Fargate task actually archiving a
   real jurisdiction to `ddp-bill-archive`, confirmed for real (not just that the image
   builds/smoke-tests).
3. Flipping `use_fargate: true` in production (`ddp-sync` cutover PR #124) -- explicitly gated
   on #2 landing clean first, not yet merged as of 2026-09-09.

Can you check the real current state of all three, directly against the live system --

- Is `use_fargate` actually `true` in production `ddp-sync` right now, or still `false`
  (Mac's `run-archive.sh` still the live archiving path)?
- Has a real Fargate-launched archive run against task-definition revision 19 (or later)
  actually completed and archived real documents to `ddp-bill-archive`? If so, which
  jurisdiction/run, and what's the evidence (CloudWatch logs, S3 object count, DB rows)?
- Was PR #124 (or whatever the actual cutover PR ended up being) ever merged?

If all three are genuinely done now, let me know so I can close OPEN-192 for real with real
evidence -- not just re-assert the 2026-09-09 comment's "still open" framing without checking
whether things have moved since then. If they're still open, that's useful to know too --
just want the real, current answer either way.
