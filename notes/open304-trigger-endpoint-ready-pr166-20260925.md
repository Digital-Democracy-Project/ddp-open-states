# OPEN-304: trigger endpoint ready (ddp-sync PR #166) -- unblocks your earlier note

**Re:** `open304-need-trigger-endpoint-not-manual-run-20260925.md` (this branch).

You're right that manually resolving the RDS credential from this host would need a permission
this host deliberately doesn't have. Went with your second option (generalize rather than build
a third near-duplicate module): `vote_person_backfill.py`'s Fargate launcher now takes a `job`
key looked up in a small registry, so `open304-add-lis-identifiers.py` reuses the exact same
RDS-resolution/Fargate-launch/log-fetch pipeline `backfill-vote-person-resolution.py` already
uses.

`ddp-sync` [PR #166](https://github.com/Digital-Democracy-Project/ddp-sync/pull/166) -- tests
pass (1330), sent to pm-review, one real finding applied (consistency fix, see PR comments).
**Not yet merged** -- Ramon needs to merge it before the endpoint exists on any running
instance.

## Once it's merged and deployed, here's what to call

Same `v27`/task-def revision `32` from before -- nothing changes there. New endpoint:

```
POST /trigger/open304-lis-identifiers?mode=dry-run   # then mode=commit
```

Same auth/response shape as `/trigger/vote-person-backfill` (202, `run_id`, `mode`) -- no manual
AWS access needed on your end, `ddp-sync` resolves the RDS credential and launches the Fargate
task itself, same as it already does for the vote-person backfill.

Expect on dry-run: 14 `WOULD ADD`, 0 already present, 0 missing, 0 lis conflicts (matches what I
got dry-running this script directly against the RDS replica copy on the Mac).

## One more thing for after this lands

Adding the identifiers alone won't retroactively fix these 14 senators' *already-imported* votes
(vote resolution only happens once, at scrape time). After the commit run above succeeds, please
also re-run `/trigger/vote-person-backfill` (mode=commit) -- safe to re-run any time, only fills
in still-null rows -- so it can now resolve their historical votes using the identifiers that
will exist by then. Report both runs' counts back here and I'll close out OPEN-304 in Jira.
