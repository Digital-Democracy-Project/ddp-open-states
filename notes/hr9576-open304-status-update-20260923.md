# OPEN-304 status update: fix filed both upstream and as a direct patch PR, not run yet

**Thread:** VOTEBOT-7/OPEN-2/SYNC-74/OPEN-304. Catching this branch up -- several attempts to post
here between the last note and this one didn't go through (a local permission issue on this end,
not anything on your side), so there's a gap to fill in.

## What happened since the backfill committed

Investigating the ~3,337 rows the backfill correctly left unresolved (VOTEBOT-7/SYNC-74's own
closing note) surfaced a real, separate cause: 14 senators had a `bioguide` identifier but no
`lis`-scheme identifier at all in our `people` data -- not a bug, a genuine upstream data gap.
Filed as **OPEN-304**.

## Two parallel tracks, neither run yet

1. **Upstream PR**: [openstates/people#4094](https://github.com/openstates/people/pull/4094),
   following this repo's own documented fork convention (`ddp` = staging remote, PRs go straight
   to public `openstates/people`, same as the earlier Susan Valdés precedent). **Not something DDP
   can merge** -- checked two comparable PRs from the same prior batch of identifier/role-date
   fixes: one took 36 days to merge, another has been open 58+ days and is still unmerged. Left
   open regardless, for the community.
2. **Direct patch, in parallel, since we don't control track 1's timing**: a small, idempotent,
   one-off script (`open304-add-lis-identifiers.py`) using the exact same values already verified
   in the upstream PR. Tested locally (both a dry-run against the real replica -- clean, 14/14
   would-add -- and a real write attempt against a throwaway dev database specifically to keep any
   actual commit off anything replica/production-adjacent, which caught a real gap: the dry-run's
   original check didn't verify the person existed first, so a real commit there hit a foreign-key
   error on a dataset that doesn't have these 14 people at all -- rolled back atomically, nothing
   partially written, then fixed to check person existence up front and report that explicitly).
   Wired into the exact same `RUNNER_SCRIPT`/`DATABASE_URL` Fargate pattern
   `backfill-vote-person-resolution.py` already uses -- **PR open, not yet merged**:
   [ddp-open-states#258](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/258).

## Status: waiting on #258 to merge, then a rebuild

Once #258 merges, plan is to build+push+verify a new `ddp-scrapers` image and register a new task
definition revision the same way `v26`/revision 31 got deployed for SYNC-74 -- that whole sequence
(build, version checks, `RUNNER_SCRIPT` smoke test, `docker login`/push, describe/register task
def) worked cleanly from the Mac last time, no reason to expect different this time.

**Not yet determined whether launching the actual one-off task afterward is also doable from the
Mac's own AWS access**, or whether that last step needs you the way the original backfill's real
RDS dry-run/commit did (that one specifically needed `resolve_rds_database_url()` called from
inside `ddp-sync`'s own already-permissioned process -- the Mac's own credentials handle ECR/ECS
image/task-def management fine, but a live `ecs:RunTask` against this cluster hasn't been tried
yet). Will report back either way once #258 merges and the image side is done.

Reply on this branch as usual.
