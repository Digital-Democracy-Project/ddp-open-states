# REQUEST (not a GO): OPEN-611 commits: fill the blank voters from your dry runs (`2d4e5a8`): WA 673, MA 8, MI 9, NC (Helfrich 814 + Tillett 5, gated), and the US vote-person backfill (15). 2026-11-23 (Mac side, State Specific Handling)

**Not a GO.** Ramon's go comes in your session.
* **His decision:** "Yes, all of them" (OPEN-611, via the PM session's /ask-me, 2026-11-23), after reviewing your lists in `notes/open611-lists-20261122/`.
* **Florida** is not in this request: its dry run filled 0.

## Gates (stop and report if one fails)
1. **Same tool, same data:**
   * run from a scratch checkout of ddp-open-states `main` (it holds #459; `bbfd8c16f` or later), with the host venv and `DATABASE_URL` on RDS, as for the dry runs;
   * **before each commit, re-run that state's dry run.** Its `fill` must equal the reviewed number (wa 673, ma 8, mi 9, nc 814 + 5). If it differs, stop and report both numbers; do not commit.
2. **North Carolina only: OPEN-765 is live on RDS.** The NC case fills Helfrich and Tillett together (`--state nc` runs both; the script cannot run one alone).
   * **Check, read only:**
     ```
     select s.end_date from opencivicdata_legislativesession s
       join opencivicdata_jurisdiction j on j.id = s.jurisdiction_id
      where j.name = 'North Carolina' and s.identifier = '2025';
     ```
     It must be `2026-12-18`.
   * **Why:** with the old date (2026-07-01), the next NC import blanks Tillett's 5 again (the script's own note).
   * **Where it stands:** #219 is in v79 (rev 81, live per your `3cef331`), but the stored date changes only when North Carolina's next import runs on rev 81. The Mac replica still reads 2026-07-01, and the replica lags.
   * **If it is not `2026-12-18` yet, hold NC entirely** (Helfrich too) and do the rest. Tell me, and NC goes after NC's next import.
3. **The US backfill runs through ddp-sync:** do not start it while ddp-sync on EC2 is being rebuilt (your core rebuild plan in `3cef331`).

## The commits, one state at a time, each followed by its checks
```
python3 relink-blank-voters.py --state wa --commit --list <lasting path>/relink-wa-commit-rds.csv
python3 relink-blank-voters.py --state ma --commit --list <lasting path>/relink-ma-commit-rds.csv
python3 relink-blank-voters.py --state mi --commit --list <lasting path>/relink-mi-commit-rds.csv
python3 relink-blank-voters.py --state nc --commit --list <lasting path>/relink-nc-commit-rds.csv     # gate 2
POST /ddp-sync/v1/trigger/vote-person-backfill?mode=commit                                          # US, gate 3
```
* **US answer:** `202` with `"mode": "commit"` and a run id. The log must say it resolved 15 records (0 still unresolvable). If it says another number, report it.
* **MI:** 9 are filled and 2 stay blank by design (she is already a voter on those roll calls), as in the dry run.

## After each commit (read only)
* **The commit CSV must have the same rows as that state's dry-run CSV** (same personvote ids). Report the row count.
* **When the scorecards show it:** the broker sees the filled votes at its next full sync of tracked bills, the nightly chain (05:00 UTC), not on the after-scrape sync. That sync picks bills whose own or vote-event timestamp changed, and these scripts change only the voter column.
* **After that chain**, the same checks as your BEFORE file (`before-checks.txt`), per state:
  * `validate_scorecards --jurisdiction <ST> --all`;
  * `reconcile_scorecards --jurisdiction <ST>`;
  * once, `validate_scorecards --bills --all`.
* **Expected:**
  * every check still clean: 0 eligible votes missing, 0 not-up-or-down, and reconcile agreeing;
  * each state's "votes checked" may rise by up to its fill count, but only where the filled vote is a counting passage vote. I have no per-state prediction of how many count.
  * Report before → after for each.
* **US:** there are 0 US legislator scorecards on the broker, so only the bill check and the chamber/undecided checks apply.
* **The 53 Utah chamber/text mismatches** in `--bills --all` are known and are being fixed under OPEN-776; they are not caused by this request.

## Not authorized
* Any other state or case.
* Any people load.
* Florida.
* Any broker change.
* A retry with a different count.

Tickets: OPEN-611 (OPEN-765 for Tillett). Plan: PLAN-state-specific-handling §8 (scorecard gate).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
