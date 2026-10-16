# Reply to OPEN-381, Part 1 (read-only preflight and the Arizona dry run). Nothing written, nothing deployed. (prod agent, EC2 host, 2026-10-16 04:52 UTC)

Followed `request-open381-arizona-final-recompute-HOLD-until-ramon-says-go-20261016.md` (`dc6da59`), as the Mac's reply told me to. Ramon confirmed Part 1 in this session. Only Part 1 was done: no deploy, no commit, no restart, no flag, schedule, scrape, archive, embedding or LegBot run, no change to any existing install.

## G1 (code): PASS
Throwaway `git worktree` of `/opt/ddp-open-states/openstates-core` at exactly `53feef5bdde1f277195719a9144f88f6c38fe4dc` (`rev-parse HEAD` printed it; origin/main is the same commit), first on `PYTHONPATH`, the existing venv's Python and `os-text-extract`, `DATABASE_URL` from the environment only (never printed). Your snippet printed:
`OK <worktree>/openstates/__init__.py` (the path is inside the new worktree).
Worktree removed afterwards; the host's own core checkout is still `5c79b47d`.

## G2 (rollback points)
* **RDS `ddp-openstates`:** latest restorable time **2026-10-16T04:46:46Z** (read at 04:51 UTC), 7-day automated backups.
* **api-v3 on this host:** container `ddp-openstates-api-1` on image `8b7df04cc29f` (the `5a0ee983` build from Part 2 of OPEN-352, started 2026-10-16T01:25:12Z). Checkout `/opt/ddp-open-states/api-v3` at `5a0ee983ad5ab72dbdaef5f99ab57cfe1d1e2510`. Rollback for the deploy of `ba0b6468` would be a new tag `pre-open381` of `8b7df04cc29f` (created at deploy time); older tags `pre-open352` (`7931f0a5102f`, the `14d3073` build), `pre-open361` and earlier are also kept.

## G3 (baselines on RDS, read-only session)
| check | n | with a diff |
|---|---|---|
| az documents with a failed-amendment note (`^(house\|senate) - .+ failed$`) | **16** (11 distinct notes) | **16** |
| az documents total (not errors) | **8,933** | **4,342** |
| az blank documents with a diff | | **0** |
Matches your expectation (16, all with a diff today; 8,933 documents total = 5,105 + 3,697 + 131). The Part 3 "after" target is: failed-amendment documents with a diff = 0, blank still 0.

## The dry run (writes nothing)
Quiet: no scrape, archive or text-extract process on this host. 04:52 UTC, one command, exit 0:

**`az: [DRY RUN] 2190 bills checked | unchanged=6934 corrected=1982 nulled=17`**

This is **exactly** the line the Mac measured on its replica copy with the same code (`corrected=1982 nulled=17`). Output saved at `/home/bitnami/ops/open381-part1-20261016/az-dry-run.txt`. Nothing was written.

## Quiet window proposal
Nothing is running here now. The Mac's LegBot run for US session 119 stopped sending traffic at 04:45:51 UTC. For Part 3, any time today (Friday) or Saturday UTC works, finishing at least an hour before the Sunday 2026-10-18 01:00 UTC mark (scrape 02:00 UTC, which now uses ddp-scrapers revision 38). The recompute itself took about 25 seconds as a dry run.

## State now / what I am waiting for
Part 2 (deploy api-v3 `ba0b6468` here) and Part 3 (the real Arizona recompute) need a GO note from Ramon for each. The Mac's api-v3 is already confirmed on `ba0b6468` (your notes `1ad153c` and `6dcf3f3`), so that condition is met. The gate for Part 3 will be the line above.
