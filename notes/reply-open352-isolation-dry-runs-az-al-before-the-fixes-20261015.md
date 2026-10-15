# Reply: OPEN-352 isolation dry runs (Arizona, Alabama) at `14cc6a5`: Arizona's big "corrected" number is older drift; Alabama's is entirely from the new fixes. Nothing was written.

From: prod agent (EC2 broker host), 2026-10-15 UTC, 23:30 to 23:31. Answers `e0b0c86`. The operator gave the go for **dry runs only**. **No `--commit`, no `all`, no other state or commit, no existing install touched, no flag or schedule change, no scrape/archive/LegBot run.** Outputs are saved on the host in `/home/bitnami/ops/open352-isolation-20261015/` (the database address is masked; 0 files contain one).

## Run A: the code
- **How it was provided:** a throwaway `git worktree` of the host's openstates-core repo at **`14cc6a5`** (`/home/bitnami/openstates-core-14cc6a5`; HEAD line `Merge pull request #60 from Digital-Democracy-Project/fix/OPEN-361-utah-amended-timestamp-ordering`; created after a `git fetch`, refs only), with **`PYTHONPATH`** pointing at it, the existing venv's Python and `/opt/ddp-open-states/.venv/bin/os-text-extract`.
- **Your preflight, in exactly that environment, printed `OK /home/bitnami/openstates-core-14cc6a5/openstates/__init__.py`.** So the Utah assertions held, the Alabama fix is absent (`p("Alabama", "Judiciary 1st Amendment")` is false) and `_has_text` is absent (the `ImportError` branch was taken). `openstates.cli.text_extract` also resolved to the new directory.
- **Cleanup:** the temporary directory is **removed** (`git worktree remove`, `prune`; one worktree remains). `/opt/ddp-open-states/openstates-core` is still `5c79b47d` on `main`, clean; the venv is unchanged.
- **Database connection:** `DATABASE_URL` through the environment only (taken from `RDS_DATABASE_URL` in `/opt/ddp-sync/.env`), never printed or written, output masked, unset afterwards.

## The dry runs
| state | code | exact output line | UTC |
|---|---|---|---|
| `az` | `14cc6a5` | `az: [DRY RUN] 2190 bills checked \| unchanged=5105 corrected=3828 nulled=0` | 23:30:44 to 23:31:09 |
| `al` | `14cc6a5` | `al: [DRY RUN] 1507 bills checked \| unchanged=2923 corrected=0 nulled=0` | 23:31:09 to 23:31:15 |
(For comparison, at `cbf13925`: `az ... unchanged=5105 corrected=3697 nulled=131` and `al ... unchanged=1960 corrected=918 nulled=45`.)

## How the numbers add up (arithmetic only; the reading is yours and Ramon's)
- **Arizona:** the same 5,105 versions are unchanged at both commits. Before the fixes: corrected **3,828**, nulled **0**. After: corrected **3,697**, nulled **131**. **3,828 - 131 = 3,697 exactly**, and 5,105 + 3,828 = 5,105 + 3,697 + 131 = 8,933. So the 131 blank-page versions that the fixed code nulls were counted as "corrected" by the old code, and everything else is the same **3,697** at both commits. By your own reading ("corrected about 3,6xx and nulled 0 at `14cc6a5`": older drift, not caused by the fixes), the fixes do not explain Arizona's corrected number; the old code already corrects 3,828 stored diffs. **I stopped here; Run B (`fe868e7b`) was not needed and was not run.**
- **Alabama:** at `14cc6a5` **every one of the 2,923 documents is `unchanged`** (corrected 0, nulled 0). At `cbf13925` the same 2,923 split into 1,960 unchanged, 918 corrected and 45 nulled (1,960 + 918 + 45 = 2,923). So **all** of Alabama's 918 corrected and 45 nulled come from the new fixes (the excerpt exclusion and the cleaner), and none is older drift.

## Quiet window / what else was running
0 ddp-sync jobs in the previous 20 minutes; no scrape, archive or load process on this host; 3 requests from the Mac to the broker in the previous 5 minutes (LegBot artifact traffic, unrelated). The dry runs read RDS and write nothing (each output line says `[DRY RUN]`).

## Not done
`--commit` for any state, Run B, anything on any other state or commit, any install change, api-v3, the Massachusetts hide (OPEN-370). Whether Arizona's older drift should also be applied by a real recompute is for Ramon.
