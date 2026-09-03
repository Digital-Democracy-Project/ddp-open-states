# usa fully succeeded (both chambers) — the 9-jurisdiction canary batch is now at its final state

*Replies to `notes/open252-ma-vote-dedupe-root-cause-20260903.md`.*

Good news to close this batch out: `usa` retried cleanly with SYNC-54's fix.

- Lower chamber: `cloud_scrape: done`, 14377.2s (~4h, collection + load both succeeded).
- Upper chamber: `cloud_scrape: done`, 218.7s (Senate, far fewer bills -- makes sense it was
  much faster).

**Both chambers confirmed real end-to-end success, not just a clean exit code** -- this closes
the loop on SYNC-54.

## Final state of the 9-jurisdiction canary batch

| Jurisdiction | Result |
|---|---|
| fl | done (proven earlier, includes the 123-object recovery) |
| wa | done -- 3535.0s |
| va | done -- 159.0s |
| mi | done -- 222.9s (WAF cookie independently confirmed genuinely fresh) |
| ut | done -- 4507.7s |
| az | done -- 5245.4s |
| usa | done -- both chambers, 14377.2s + 218.7s |
| ma | failed at load (OPEN-252, root-caused, not fixed/retried yet -- manifest safe in S3) |
| nc | still blocked -- no individual trigger target in `triggers.py`'s `_OPENSTATES_SINGLE_JURISDICTION`/`_OPENSTATES_JOB_TARGETS` |

**7 of 9 fully clean end to end, 1 root-caused-but-not-yet-fixed (ma, real data safely staged
in S3 for whenever OPEN-252 lands), 1 structurally untriggerable via this endpoint (nc).**

Nothing further from this side right now -- `ddp-sync` stays up healthy, `cloud_path`
config unchanged. Whenever OPEN-252's fix lands, the `ma` recovery is a single
`cloud_loader.py ma ma-f08d7646b9fe` call against the existing manifest, no re-collection
needed, same as tonight's earlier 123-object recovery.
