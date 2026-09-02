# OPEN-245 filed and fixed as PR #221 (pm-reviewed) — the no-op manifest gap

*Replies to `notes/open193-cloud-loader-two-new-blockers-20260902.md`.*

Nice catch tracing that back to OPEN-244 exposing an unreachable path. Two blockers, handled
separately:

## #1 (no-op manifest) — fixed

Filed **OPEN-245** and fixed: `cloud_collector.py`'s no-op branch now also publishes an
empty-objects `_manifest.json`, exactly matching the success path's shape/location.
`cloud_loader.py` needs zero changes -- confirmed directly against `openstates-core` that
`os-update --import` against an empty `--datadir` safely imports zero bills and exits 0, and
`test_cloud_loader.py`'s own existing (already-passing) test already proves the loader-side
half end to end.

Ran this one through `/pm-review` too (Ramon's asked that every fix in this thread go through
both a ticket and a review from here on) -- approved, ship, with one test-precision gap
(assertion checked "some key ending in `_manifest.json`" rather than the exact path/payload)
tightened in a follow-up commit.

**PR:** https://github.com/Digital-Democracy-Project/ddp-open-states/pull/221 -- not merged
yet.

## #2 (EC2 role's missing S3 write access) — recommendation, not yet actioned

Your read was right and my earlier reasoning (when clearing the stale lock) was incomplete --
`cloud_loader.py` running from this host genuinely does need its own `s3:PutObject` for the
import lock, routinely, not as a one-off. Recommending a MUCH narrower grant than the literal
ask though: scope it to `arn:aws:s3:::ddp-openstates-scraper-memory/prod/*/_import_lock`
specifically, not `s3:PutObject` on the whole bucket -- this role still has no business writing
scraper memory data or manifests, only its own lock objects. Waiting on Ramon to confirm before
this goes anywhere.

Once both land: pull, restart, re-attempt the canary. Collection has now been proven solid
across all 4 sessions twice in a row -- these two are genuinely the last things standing
between here and closing OPEN-193 item 4.
