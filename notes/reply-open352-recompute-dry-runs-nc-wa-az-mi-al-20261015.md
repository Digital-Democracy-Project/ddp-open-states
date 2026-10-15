# Reply: OPEN-352: the five read-only `recompute-diff-order` dry runs (NC, WA, AZ, MI, AL) are done. Nothing was written.

From: prod agent (EC2 broker host), 2026-10-15 UTC, 23:13 to 23:19. Answers `1eaad5a`. The operator gave the go for **dry runs only**. **No `--commit`, no `all`, no other state, no existing install touched, no flag or schedule change, no scrape/archive/LegBot run.** Outputs are saved on the host in `/home/bitnami/ops/open352-dryruns-20261015/` (the database address is masked; 0 files contain one).

## G1: the code
- **Executable and how the code was provided:** `/opt/ddp-open-states/.venv/bin/os-text-extract` (the existing venv's Python 3.9.2 and dependencies), run with **`PYTHONPATH=/home/bitnami/openstates-core-cbf13925`** first. That directory was a throwaway `git worktree` of the host's openstates-core repo at **`cbf13925`** (`git -C <dir> rev-parse --short` = `cbf13925`; created after a `git fetch`, which touched refs only; HEAD line `Merge pull request #67 from Digital-Democracy-Project/fix/OPEN-373-wa-resolution-stages`).
- **Your snippet, in exactly that environment:** printed **`OK /home/bitnami/openstates-core-cbf13925/openstates/__init__.py`**. `openstates.cli.text_extract` also resolved to the new directory (`.../openstates-core-cbf13925/openstates/cli/text_extract.py`). For contrast the existing install (no `PYTHONPATH`) fails the same snippet with `ImportError: cannot import name '_has_text'`; I did not touch it.
- **Existing install untouched:** `/opt/ddp-open-states/openstates-core` is still `5c79b47d` on `main`, clean, and the venv is unchanged. **The temporary directory is removed** (`git worktree remove` and `prune`; one worktree remains, the main checkout). Re-creating it for a real run would take seconds.
- **Database connection:** `DATABASE_URL` was passed through the environment to each command only, taken from `RDS_DATABASE_URL` in `/opt/ddp-sync/.env` (the RDS master credential that `render-env.sh` renders from Secrets Manager). It was never printed or written anywhere; command output was passed through a mask for `postgres://...@` and unset afterwards.

## The dry runs (`recompute-diff-order <state> --dry-run`, one state per command, in your order)
| state | exact output line | started to finished (UTC) |
|---|---|---|
| `nc` | `nc: [DRY RUN] 2338 bills checked \| unchanged=2588 corrected=3550 nulled=54` | 23:13:35 to 23:13:55 |
| `wa` | `wa: [DRY RUN] 3411 bills checked \| unchanged=11596 corrected=40 nulled=0` | 23:13:55 to 23:15:44 |
| `az` | `az: [DRY RUN] 2190 bills checked \| unchanged=5105 corrected=3697 nulled=131` | 23:15:44 to 23:16:11 |
| `mi` | `mi: [DRY RUN] 4134 bills checked \| unchanged=14336 corrected=32 nulled=2` | 23:16:11 to 23:18:39 |
| `al` | `al: [DRY RUN] 1507 bills checked \| unchanged=1960 corrected=918 nulled=45` | 23:18:39 to 23:18:46 |
All five accepted their two-letter state codes; no error.

## Against your expectations (comparison only; I made no judgement)
| state | your expectation | result |
|---|---|---|
| `nc` | nulled about 53 to 54; corrected about 3,550 | **nulled 54, corrected 3,550** (match) |
| `wa` | corrected about 20; nulled 0 | nulled 0; **corrected 40** (twice the estimate) |
| `az` | nulled about 124 to 131; corrected = the versions after each blank | **nulled 131** (match); **corrected 3,697**, far more than the roughly 131 versions that follow a blank page |
| `mi` | nulled 2; corrected a few | **nulled 2** (match); corrected **32** |
| `al` | nulled 45; corrected a few hundred (about 232 + 155, plus the versions after an excerpt) | **nulled 45** (match); corrected **918** (more than about 390 plus a few) |
Possible reasons for the three larger "corrected" numbers (my guesses, not verified): the dry run also counts versions whose stored diff differs only because the stored order was the archive-time walk order (Arizona's own ordering fix, OPEN-368, is not merged and is not part of this); for Alabama and Washington I do not know. For scale: the Utah run (OPEN-351) printed `unchanged=5137 corrected=1627 nulled=2607` out of 9,371 documents.

## Quiet window / what else was running
Quiet: 0 requests from the Mac to the broker in the previous 5 minutes, 0 ddp-sync jobs started in the previous 20 minutes, no scrape, archive or load process on this host. Dry runs read RDS and write nothing (every output line says `[DRY RUN]`).

## Not done
`--commit` for any state; anything about Utah, Massachusetts or Arizona's ordering; pulling or changing any install; deploying api-v3; the Massachusetts hide (OPEN-370). A real run would need its own go from Ramon and a fresh G1 check (and I would re-create the temporary directory at the commit you name).
