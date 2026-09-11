# Stop -- if you've started building the v21 image on this host, cancel it

Ramon caught this: my earlier deploy-instructions note (`open268-deploy-instructions-
20260910.md`) told you to build/push/register the new image yourself, on this EC2 host. That
was wrong, and inconsistent with how the earlier Python 3.10 fix (`v20`/revision 24) was
actually deployed -- that one was built on the Mac, not here, matching the standing division
of labor (build on the resource-rich Mac, only *run* the already-tested artifact on this
resource-constrained host). Building here means real CPU/disk/network load on the exact box
`ddp-broker`/`api-v3` share -- the same category of contention that already held up FL's
commit once this week.

**If a `docker build` for `ddp-scrapers:v21` is running or queued on this host right now,
please stop it.**

I'm building `v21` on the Mac instead (from `main` @ `97441da`, which already has both merged
PRs), and will push it to ECR + register the task-definition revision myself. I'll post the
new image tag/revision number here once that's done -- at that point the only thing left for
you is the actual supervised dry-run canary trigger (same command as the earlier note):

```bash
curl -X POST "http://localhost:8000/trigger/openstates-backfill/mi?subcommand=recompute-diff-order&mode=dry-run" \
    -H "Authorization: Bearer $DDP_SYNC_API_KEY"
```

Sorry for the back-and-forth -- should have caught this before posting the first note.
