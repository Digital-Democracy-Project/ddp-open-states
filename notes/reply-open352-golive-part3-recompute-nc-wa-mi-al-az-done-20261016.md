# Reply to OPEN-352 go-live, Part 3: recompute for nc, wa, mi, al, az DONE. Every gate passed on every state. (prod agent, EC2 host, 2026-10-16 02:24 UTC)

Followed GO note `dc1d8542` and confirmation `3507c8a8`. Ramon confirmed the go in this session. Order nc, wa, mi, al, az; one state per command; never `all`. Window: Friday 2026-10-16 UTC (02:07 to 02:24), long before Sunday 01:00 UTC.

## Method and gates
* **Code:** a throwaway `git worktree` of `/opt/ddp-open-states/openstates-core` at exactly `cbf13925934ac852f3883a4d186e27c5517e7640`, first on `PYTHONPATH`, the existing venv's Python and `os-text-extract`, `DATABASE_URL` from the environment only (never printed; output masked). Worktree removed afterwards; the host's own core checkout is still `5c79b47d`, untouched.
* **G1:** your snippet printed `OK <worktree>/openstates/__init__.py`.
* **G3 baseline before the first commit:** nc stamp pages 54, nc Edition/Ratified/SL 0, al amendment-family 45, mi blank 2, az blank 131 (all as in Part 1).
* **RDS latest restorable time just before the first commit: 2026-10-16T02:01:47Z** (backup window 04:57-05:27 UTC).
* **Quiet:** no scrape, archive or text-extract process on this host before each state. Part 2's api-v3 `5a0ee983` was already live here, and the Mac side confirmed theirs.
* Two start-up crashes of my own runner script (a shell-call bug and a missing database library in the system Python) happened **before any dry run or commit**; they wrote nothing. The run that counts started 02:07:47.

## Exact output lines (dry run = commit, second dry run clean, for each state)
| state | dry run | commit | second dry run |
|---|---|---|---|
| nc | `nc: [DRY RUN] 2338 bills checked \| unchanged=2588 corrected=3550 nulled=54` | `nc: [COMMITTED] 2338 bills checked \| unchanged=2588 corrected=3550 nulled=54` (28 s) | corrected=0 nulled=0 |
| wa | `wa: [DRY RUN] 3411 bills checked \| unchanged=11596 corrected=40 nulled=0` | `wa: [COMMITTED] 3411 bills checked \| unchanged=11596 corrected=40 nulled=0` (108 s) | corrected=0 nulled=0 |
| mi | `mi: [DRY RUN] 4134 bills checked \| unchanged=14336 corrected=32 nulled=2` | `mi: [COMMITTED] 4134 bills checked \| unchanged=14336 corrected=32 nulled=2` (173 s) | corrected=0 nulled=0 |
| al | `al: [DRY RUN] 1507 bills checked \| unchanged=1960 corrected=918 nulled=45` | `al: [COMMITTED] 1507 bills checked \| unchanged=1960 corrected=918 nulled=45` (8 s) | corrected=0 nulled=0 |
| az | `az: [DRY RUN] 2190 bills checked \| unchanged=5105 corrected=3697 nulled=131` | `az: [COMMITTED] 2190 bills checked \| unchanged=5105 corrected=3697 nulled=131` (33 s) | corrected=0 nulled=0 |
Every dry run matched your note's expected line exactly before the commit; every commit printed the same three numbers; no command errored or stopped partway.

## G3 after
| check | before | after |
|---|---|---|
| nc stamp pages with a diff | 54 | **0** |
| nc Edition/Ratified/SL with a diff | 0 | **3,550** |
| al amendment-family with a diff | 45 | **0** |
| mi blank with a diff | 2 | **0** |
| az blank with a diff | 131 | **0** |
(Washington has no G3 row; its commit line is the evidence.) The other states' rows did not move while one state ran.

## Things you asked me to watch
* **NC changelogs:** I did not start or trigger any run. In ddp-sync's log for the 40 minutes covering the recompute I saw no North Carolina changelog activity. The existing schedule and trigger decide from here; I will say if I see one start.
* The new Fargate revision 37 (image v34) was registered by the Mac session at 01:49 UTC, ahead of the Sunday 02:00 UTC scrape.

## Not done
No `recompute-diff-order all`, no other state, no flag, schedule, scrape, archive, embedding or LegBot run, no change to the Fargate task definition, existing installs or `delete_orphans`, no rollback.

Files and full command outputs: `/home/bitnami/ops/open352-part3-20261016/` on this host (`run.log`, `summary.json`, one file per dry run and commit).
