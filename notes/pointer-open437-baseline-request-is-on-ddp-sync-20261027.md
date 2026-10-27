# Pointer: OPEN-437 baseline request (read-only) is waiting on the ddp-sync notes/ops-handoff branch

2026-10-27 about 22:15 UTC. Ramon asked me to point you at it because it has had no reply and you were last seen on this repo's branch.

The scrapers image **`v38` was registered as `ddp-scrapers` revision 41 at 22:06 UTC** (previous: revision 40 on `v37`; no Fargate task was running). Nothing has been launched on it yet. Rollback: `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:41`. Stop and report; do not roll back on your own.

**Please read and answer, read-only:** `notes/request-open437-cutover-baseline-before-image-deploy-20261027.md` on branch `notes/ops-handoff` of **ddp-sync** (commit 71111d4): live revision/tag, per-state counts, newest pre-cutover run ids, check-script outputs, in-flight tasks and launches due until Thursday 00:00 UTC. The first launches on `v38` are 00:30 UTC (cadence review), 02:30 UTC (WA) and 03:00 UTC (USA), so the counts and newest run ids are most useful before then. This does not change your 63d1a132 follow-ups (ddp-sync write 2xx after 02:30/03:00 UTC, 03:15 cleanup).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
