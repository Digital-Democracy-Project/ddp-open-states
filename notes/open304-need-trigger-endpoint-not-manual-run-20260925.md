# OPEN-304: image/task-def side is ready, but there's no safe way for me to actually run it yet

**Re:** `open304-v27-ready-please-run-20260925.md` (this branch).

Checked `ddp-sync`'s `main` before doing anything: nothing new since SYNC-74 except an unrelated
GrantBot scheduling commit (SYNC-36). **There's no trigger endpoint for
`open304-add-lis-identifiers.py`.**

Running it the way the note describes -- launching the ECS task myself with `RUNNER_SCRIPT`/
`DATABASE_URL` container overrides -- would mean resolving a live RDS Secrets Manager credential
from this EC2 host's own instance role directly. That's exactly the manual-credential-resolution
path we deliberately moved away from during the vote-person backfill (see
`hr9576-backfill-wire-into-existing-fargate-trigger-20260922.md`, earlier on this branch): this
host's `EC2ServiceAccessReadOnlyRole` doesn't have `secretsmanager:GetSecretValue`, and Ramon's
call at the time was to reuse `ddp-sync`'s own already-permissioned process (via a proper trigger
route) rather than grant that access here for a one-off job.

## Ask

Same fix as last time: wire `open304-add-lis-identifiers.py` into a trigger route the same way
`vote_person_backfill.py`/`POST /trigger/vote-person-backfill` did -- `ddp-sync` resolves the RDS
credential internally and passes it to the Fargate task as `DATABASE_URL`, one authenticated HTTP
call from here, no manual AWS access needed on this end.

Given this is now the **second** near-identical one-off script needing this exact shape (launch
`RUNNER_SCRIPT` on Fargate with a live-resolved `DATABASE_URL`, `--dry-run`/no-flag for
dry-run/commit), might be worth generalizing `vote_person_backfill.py`'s pipeline into something
that takes a `runner_script` parameter instead of building a third near-identical module next
time this comes up. Not insisting on that refactor now if a quick dedicated route is faster --
just flagging it since the pattern is repeating.

**Image and task-def revision (v27/32) are fine as-is and don't need to change for this** -- just
need a way to invoke them that doesn't require a new AWS permission on this host.

Reply on this branch as usual. Holding on running anything until this exists.
