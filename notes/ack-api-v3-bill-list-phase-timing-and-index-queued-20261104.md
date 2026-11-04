# Acknowledgement: `b76c23c` (phase timing) and `6c59836` (build the index) seen; queued behind the Pennsylvania/Louisiana archive trial (OPEN-484, OPEN-489). Written 2026-11-04 05:40 UTC. Nothing has been run for either yet.

I had not seen either request until the user pointed me at them at about 05:30 UTC. Their commit times are 04:52 UTC (`b76c23c`) and 05:18 UTC (`6c59836`), after my last full check at 04:42. I also read `7f33fad` (PR #48 is on main; the index request is otherwise unchanged).

## The user's decisions on this branch's two requests (this session, 05:35 UTC)
- Order: **"Acknowledge now; read-only timing, then index, after the archives finish."**
- Index go: **"Yes, once the gates are clean (no ECS task, no scrape or import writing bills)."** (The user's own go, given here, not only the relayed one.)

## Why they wait
The Pennsylvania and Louisiana archive trial (ddp-sync `28a92da`) is running: Pennsylvania should finish around 06:00 UTC and Louisiana around 07:10 UTC (estimates from the pace so far). `6c59836` says to stop and report if a task is in flight, so its "no ECS task" gate cannot pass now, and a re-time "now" would not be a quiet-host one. So:
1. When both archive tasks have stopped and a final gate check is clean (0 ECS tasks, nothing in flight, no ddp-sync job in the last 10 minutes, away from 02:00, 02:30, 03:00 UTC): run **`b76c23c`** (phase timing, `select 1` connection timing, quiet re-time of the broker's lists), **before** the index so it measures the same plan as the baseline.
2. Then **`6c59836`**: save the running api image id, pull api-v3 to `16c5168b` or later on `main` (not #48), build the api image without recreating the container, run `ensure --bill-list-index` once and record its real duration, then the before/after tables, the identical first-20-ids comparison and the plan nodes, as the request says. On any failed gate, lock timeout or unexpected output I stop and report first; no automatic rollback.
3. Replies: `reply-api-v3-bill-list-phase-timing-20261104.md` and `reply-api-v3-build-the-bill-list-index-on-production-open484-20261104.md` on this branch.

## Notes
- The Pennsylvania/Louisiana tasks write `ddp_bill_version_document`, not `opencivicdata_bill`, but the request's gate is "no ECS task", so I will not argue it away.
- If either archive task runs close to its 4-hour limit (about 08:07 UTC), the two requests wait until it stops; I will say so here.
