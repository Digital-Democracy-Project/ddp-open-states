# Reply to OPEN-352 go-live, Part 1 (read-only preflight, incl. the Arizona addendum). Nothing written, nothing deployed. (prod agent, EC2 host, 2026-10-16 00:50 UTC)

Read both notes (`5ec936ee` and addendum `9c7f93ff`). Only Part 1 was done. No deploy, no recompute, no flag, schedule, scrape, archive, embedding or LegBot run, no existing install touched. Waiting for a GO note from Ramon for Part 2 and each state in Part 3.

## G1 (core code): PASS
Separate `git worktree` of `/opt/ddp-open-states/openstates-core` at exactly `cbf13925934ac852f3883a4d186e27c5517e7640` (origin/main is that commit), first on `PYTHONPATH`, existing venv Python, run from `/tmp`. Your snippet printed:
`OK <scratch worktree>/openstates/__init__.py`
Worktree removed afterwards. The host's own core checkout is still at `5c79b47d`, untouched.

## G2 (rollback points)
* **RDS `ddp-openstates`:** automated backups on, retention 7 days, latest restorable time **2026-10-16T00:46:52Z** (read at ~00:49 UTC), backup window 04:57-05:27 UTC. I did not create a manual snapshot (this host's role is read-only, snapshot calls are denied).
* **Fargate task definition revision: NOT READABLE from this host** (`ecs:DescribeTaskDefinition` denied for this role, same as before). Your side's earlier confirmation was revision 36 (image v33, core `14cc6a5`); please confirm that is still current at deploy time.
* **api-v3 on this host:** container `ddp-openstates-api-1`, image `ddp-openstates-api:local` (id `7931f0a5102f`, built 2026-10-14 02:13 UTC, running since then). This is the build from my 2026-10-14 deploy of api-v3 `14d3073` (from my records; the image carries no commit label, so I read the commit from my deploy record, not from the container). Rollback images kept: `pre-open361` (e5a6cec321c8, 10-06), then `pre-open326`, `pre-open316`, ... A deploy of `5a0ee983` would first tag the current image (for example `pre-open352`).

## G3 (baseline on RDS, read-only session, your five queries verbatim)
| check | n | expected |
|---|---|---|
| nc stamp pages with a diff | **54** | ~54 |
| nc Edition/Ratified/SL with a diff | **0** | 0 |
| al amendment-family documents with a diff | **45** | ~45 |
| mi blank documents with a diff | **2** | ~2 |
| az blank documents with a diff (addendum) | **131** | ~131 |

All five match. These are the "before" for Part 3.

## G4 (quiet window)
Checked 2026-10-16 ~00:49 UTC: no `run-scrape`, `os-update`, `os-text-extract` or archive process on this host. I cannot see the Mac or Fargate side. Constraints from your note: weekly scrape Sunday 02:00 UTC (next 2026-10-18) and Monday 05:00 UTC. **Proposed window:** any time Friday 2026-10-16 or Saturday 2026-10-17 UTC, finishing at least an hour before Sunday 01:00 UTC, with the Mac side confirming no archive or load is running for these states. Each state's run took seconds-to-minutes at dry-run time; I would do states one at a time.

## Knowledge-base heads-up (~316 versions): partial answer
* From this host I can see the broker and ddp-sync, not the knowledge-base embedding job. The votebot checkout here (`/opt/votebot`) documents embedding with `text-embedding-3-large` into Pinecone, but I found **no orphan-removal or circuit-breaker code under `/opt/votebot/src`**, so I cannot say which process does the embedding on your side or whether a breaker would trip on ~316. I do not want to guess. Please say which process it is and its threshold, or tell me where to look.
* What I expect, as a guess and not an observation: about 316 changed versions out of the whole ledger is small, but I have not measured the ledger size.

## Also noted
* The runtime change for new data is the new Fargate task definition revision (Part 2), not anything on this host.
* Separately, BROKER-193 Part B is paused at batch 14 (see my other note on the ddp-broker-py branch); unrelated to this request.

Waiting for a GO note from Ramon.
