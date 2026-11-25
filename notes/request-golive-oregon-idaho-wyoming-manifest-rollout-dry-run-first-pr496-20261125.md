# REQUEST (not a GO): **go-live for Oregon, Idaho and Wyoming: a manifest rollout, dry run first.** The change is ddp-open-states **#496**, **merged** (merge `27f1d70`, head `33235f88cf3a1c21016aeb6eb90cad8af4f761f0`, CI `validate` green). 2026-11-25 ~23:10 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon decided (11-25, via the PM) that Oregon, Idaho and Wyoming go live; the version-comparison cleanups are committed (your `508bef1`, my read of 0 pending at core a7035d68). **He gives the go in your session naming this note;** please confirm it with him.

## What changes (read from the PR: `jurisdictions.yaml` only, 15 lines, inside the `or:`, `id:` and `wy:` blocks)
For each of the three: `status: scraping` to `live`, and `enrollment.search_refresh`, `embedding`, `api_smoke_test`, `qa_sweep` false to true: the same as #494, #495 and #480. **`replica_routing` and `legbot_replica` stay false** (Ramon's separate call).

## Why they are ready (Mac replica, 11-25; production is your reading)
* **Wyoming:** the v90 re-import fixed the origin chamber (SF/SJ upper 135, HB/HJ lower 200, 335 bills), all 92 "Failed Introduction" actions carry the failure label, 0 backward action steps, 0 unmatched of 45,490 votes.
* **Oregon and Idaho:** your commits read 0 pending (relabel and recompute).

## The steps
1. **Gate:** #496 is on `origin/main`. Read the per-state diff of the deployed copy against main and **report any state other than OR, ID, WY that would change** (the #494/#495 states included if not yet rolled out: they were rolled out 22:27 UTC). Stop if anything else differs.
2. **Pull first, then the script:** `/opt/ddp-open-states` to main, then `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --dry-run` (must exit 0; report its lines).
3. **On the go:** the real run, then the checks as on 11-25: the md5 of the checkout file, the api-v3 copy and the file in the container equal; api-v3 healthy, no restart; drift check exit 0; `/schedule` job count unchanged (report it); ddp-sync's own read shows `live` for the three. **No ddp-sync restart.** The Mac host's copy is not part of this request.
4. **Afterwards:** the first embedding and search-refresh pass for each state runs for hours in ddp-sync's process; apply your narrow restart rule meanwhile, post when each finishes, and report smoke test and QA sweep results by state.

## Not authorized
`replica_routing`, `legbot_replica`; any broker switch (scorecard switches are separate); the Mac host's rollout; a ddp-sync restart; any other state. Rollback: revert the PR's 15 lines, merge, roll out again; tell me first.

Tickets: OPEN-589 (OR), OPEN-664 (ID), OPEN-662 (WY); OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
