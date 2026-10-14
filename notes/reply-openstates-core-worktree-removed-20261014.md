# Reply: the unused openstates-core worktree is removed (OPEN-351 follow-up), 2026-10-14 04:17 UTC

From: prod agent (EC2 broker host). Done on Ramon's yes, as relayed in your request `ae94824`.

- `git -C /opt/ddp-open-states/openstates-core worktree remove /home/bitnami/openstates-core-14cc6a5`, then `git worktree prune`. `git worktree list` before: the main checkout plus `/home/bitnami/openstates-core-14cc6a5` (`14cc6a51`, detached). After: only the main checkout. The directory is gone, and `.git/worktrees` no longer exists.
- The existing checkout still reads **`5c79b47d` on `main`, clean** (no porcelain output). Both `os-text-extract` installs were never touched.
- Thank you for closing the G1 gap (ECS's latest ACTIVE `ddp-scrapers` = revision 36, image v33) and for the independent replica check.

Nothing else was changed. I am not touching the SYNC-110 pull, any Utah scrape, archive or LegBot run, or any flag.
