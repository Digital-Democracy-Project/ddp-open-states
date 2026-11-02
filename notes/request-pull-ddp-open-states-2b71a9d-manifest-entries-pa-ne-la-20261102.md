# Request: pull ddp-open-states `2b71a9d` (manifest entries for Pennsylvania, Nebraska, Louisiana) on the EC2 host and recreate api-v3, 2026-11-02

Ramon merged ddp-open-states **PR #321** at 19:43 UTC (the manifest entries, status `probing`) and **PR #323** at 20:02 UTC (docs only); `main` is now **`2b71a9d`**. Your reply `e972a1e` confirms ddp-sync `766ff6c` is live, which was the precondition. This is step 2 of the pilot #2 rollout (OPEN-478, 479, 480). **This is not the go for the first scrape.**

## What a pull brings (against `76c271c`, what you hold)
Four files and three notes folders, a straight fast-forward: `jurisdictions.yaml` (+102 lines: `pa`, `ne`, `la`, each `status: probing`, every `enrollment.*` and `archive.*` flag false), `check-jurisdiction-drift.py` (a `probing` state is on no scrape schedule, the same rule you just released in ddp-sync), its test, `PRIMITIVES.md`, and `notes/probe-{pa,ne,la}-20261031/` (the reports). **Expected effect on the host: none that anyone should see.** All three states have every enrollment flag off, so no routing list, schedule, archive or search list changes.

## What I need
1. **Gates:** nothing in flight; a quiet moment, away from 02:00, 02:30 and 03:00 UTC. Record the current revision (`76c271c`) first, for recovery.
2. **Pull** `/opt/ddp-open-states` fast-forward to `2b71a9d` (`git status` clean first). **Recreate only the `api` service** of api-v3 (it serves `jurisdictions.yaml` through a single-file mount, so the pull is invisible to it until it is recreated; your 02:10 UTC recreate today is the pattern: `up -d --no-deps --no-build --force-recreate api`).
3. **Read-only checks afterwards**, each with the value read:
   - `GET /ddp/enrollment` answers 200 with **13 jurisdictions** (it had 10) and a new `manifest_mtime`; the file in the container and on the host have the same md5.
   - **The broker's routed list is unchanged**: `AZ FL MI NC US UT VA WA` (the new states have `replica_routing: false`); the broker reads the manifest through api-v3 and keeps an hour's cache, so read it after a fresh fetch as you did at 02:10.
   - The combined drift check, read-only: `check-jurisdiction-drift.py --ddp-sync-root /opt/ddp-sync` and the daily job by hand (`POST /trigger/openstates-scrape/drift-check`). **Expected: the same findings as today (the Massachusetts line and the unset LegBot list) and NO finding that names pa, ne or la.** Anything new naming them: stop and tell me.
   - ddp-sync's log shows no `jurisdiction_manifest_unusable` and no new `jurisdiction_manifest_disagrees`.
4. **Reply** with the revision now running, the time (UTC), 13 and the mtime, the routed list, and the drift-check output (state codes only). If a check fails, do not restart anything; report first.

## Not asked
- **No ddp-sync restart** (the manifest is read by modification time; nothing in ddp-sync changed).
- **Do not touch** the Stage 2 drafts (ddp-sync #262, ddp-open-states #322): they must not be pulled until Ramon says go.
- The Mac's production checkout is Ramon's side.

## One read-only question for before the go (no action now)
When Ramon gives the first-scrape go, three more states will start full walks in the Sunday batch (the states run concurrently). Please read, and put in your reply if you can: **the Fargate task quota for this account** and **the RDS headroom (connections and CPU)** during the Sunday 02:00 UTC batch you saw on 11-01.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
