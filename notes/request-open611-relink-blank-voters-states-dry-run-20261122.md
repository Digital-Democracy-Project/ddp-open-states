# REQUEST (dry runs only, not a GO for any write): state votes with no person attached, `relink-blank-voters.py` dry run per state with its list (OPEN-611): WA, MA, MI, FL, NC. 2026-11-22 (Mac side, State Specific Handling)

**Ramon, 2026-11-22: "Yes, request test runs".** This covers the **dry runs only**: no `--commit`. Each state's commit needs Ramon's own go, after he has reviewed that state's list.

## Why
* A stored vote with no person behind it drops silently out of that legislator's page and scorecard.
* These votes were imported before the person's name or term reached the database. Incremental scrapes never re-import old roll calls, so they stay blank.
* The script fills a vote only where **exactly one** person of that name held that seat **on the vote's own date** and is not already a voter on that roll call. Anything else stays blank and is reported. Without `--commit` it writes nothing.

## The tool
* `relink-blank-voters.py` at the root of ddp-open-states `main` (#407, #409, #413).
* Run it from a checkout at current `main`, with the host venv and `DATABASE_URL` pointing at RDS, as for earlier one-off tools.

## The dry runs, one state at a time (read only)
```
python3 relink-blank-voters.py --state <st> --list <lasting path>/relink-<st>-dry-rds.csv
```

| State | Case | Mac replica today (`fill` / `left blank`) | Condition |
|---|---|---|---|
| wa | House "Hunt" (Victoria Hunt) | 673 / 0 | none |
| ma | House "Garcia" (Judith García) | 8 / 0 | none |
| mi | House "Myers-Phillips" (Tonya Phillips) | 9 / 2 | the 2 stay blank by design: she is already on those roll calls |
| fl | House "Garcia" (Alina García) | **0 / 0** | the people #27 "Garcia" other name is on RDS, and **every Florida House "Garcia" vote is already linked** (0 blank of 1,038 in 2023, 2023B, 2023C, 2024; most likely the current Florida re-import). The dry run confirms 0 on RDS; nothing to commit if so |
| nc | House "Helfrich" (Beth Gardner Helfrich) | **814** / 0 (was 809; new imports since) | the NC people load is done (your `c1e95c3`) |

**Report per state:**
* the script's summary line;
* the CSV's path and row count.

## Scorecard checks to send with each list (read only, on the production broker)
* `validate_scorecards --jurisdiction <ST> --all`, and `validate_scorecards --bills --all` (once).
* `reconcile_scorecards --jurisdiction <ST>`.
* These are the "before" values; the same checks run again after each commit.
* The Mac side checks a sample of each list against the legislature's journal and assembles the review for Ramon.

## Not authorized
`--commit` for any state; any people load; any other script; any broker change.

Tickets: OPEN-611, OPEN-613, OPEN-233. Plan: PLAN-state-specific-handling §8 (scorecard gate).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
