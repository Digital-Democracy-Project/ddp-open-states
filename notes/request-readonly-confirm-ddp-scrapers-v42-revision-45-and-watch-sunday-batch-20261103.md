# Request (read-only): confirm `ddp-scrapers` revision 45 (image v42) is the latest active revision, and watch Sunday's batch on it, 2026-11-03

**Done by Ramon on the Mac, 2026-11-03:** a new scrapers image **v42** was built, checked and pushed to ECR (digest `sha256:55eefe22983d2e5b27c22f6423fc60e25c6be559d2dd06600c4be2fc096949c7`), and task-definition revision **45** was registered at about 19:25 UTC. **Revision 44 (image v41) was the one before.** The checks before the push passed (imports; a real Utah bill through the real `os-update` path, exit 0, `bill: 1`).

## What is in v42
**v41 plus one change: openstates-core #74 (OPEN-482)**, the version-stage rules for Pennsylvania ("Printer's No. PN<N>"), Nebraska ("Slip Law", "Final Reading", "<name> AM<N>") and Louisiana ("<bill> Act <N>"). Nothing else new in the build inputs (checked: the scrapers fork has no commit since 10-31 and core has only #74). Notes that already have a stage cannot change.

## Why it matters now
`ddp-sync` launches the family `ddp-scrapers` with no revision number, so **every launch from now on uses revision 45, for every state.** Nothing is running (your 18:24 UTC gates said 0 tasks). **The first scheduled use is Sunday 2026-11-08 02:00 UTC** (the secondary batch, which now includes `pa`, `ne` and `la`).

## What I need (read-only, nothing to change)
1. **Confirm what ECS resolves:** `aws ecs describe-task-definition --task-definition ddp-scrapers` shows **revision 45** and image `...ddp-scrapers:v42`, status ACTIVE. Say whether any running task is on an older revision (it should be none).
2. **Watch Sunday's batch as you did for v41** (your usual Sunday read): every state's run exits 0 and loads as before; give the usual counts. Anything that looks different from the 11-01 batch, report.
3. **Rollback if ever wanted** (Ramon's, or yours on his word): `aws ecs deregister-task-definition --task-definition ddp-scrapers:45` makes revision 44 the latest active again.

## Not asked
No restart, no config change, no trigger, no archive. The archive for `pa`, `ne` and `la` is not being switched on by this note; that is a separate request after a manifest PR.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
