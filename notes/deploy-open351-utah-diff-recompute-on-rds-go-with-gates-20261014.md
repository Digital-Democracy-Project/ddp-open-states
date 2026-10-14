# DEPLOY: OPEN-351, recompute Utah's stored diffs on RDS. GO, with gates. (dev side, 2026-10-13 EDT)

**STATUS: GO, conditional.** Ramon asked for this deployment note in the Mac session (2026-10-13 EDT), in answer to the question whether to authorize the real run, and noted that RDS can only be edited by you. Treat it as the go for section 3, **only if every gate in section 2 passes**. A failed gate is not permission to improvise: stop and report. If a HOLD note from Ramon or me appears on this branch before you start, follow it instead.

Jira: **OPEN-351** (this), blocks SYNC-111. Evidence and rehearsal: ddp-open-states PR #274, `notes/open351-utah-recompute-rehearsal-and-run-procedure-20261014.md`. Plan: `ddp-infra/PLAN-rds-data-quality-backfill.md` §4 and §5, the standing process this follows. This supersedes my read-only preflight request on ddp-sync's branch (`3d6e908`); answer its questions inside your reply to this note.

## 1. What this does and why
It runs `os-text-extract recompute-diff-order ut --commit` **on RDS, once**. Utah's source of truth is RDS; the Mac reads a replica of it. The new Utah rules (OPEN-350 and OPEN-361) change only newly archived data, so Utah's already-stored `diff_from_previous_version` values must be recomputed once. It changes only that one column, only for Utah, from the text already stored (no re-fetching). On a full-size copy of the data it reported `unchanged=5137 corrected=1627 nulled=2607`, took about half a minute, changed nothing outside Utah, did **not** change `updated_at` (so ddp-sync's archive hook and the knowledge-base ledger will not see it as new work), and a second pass reported `unchanged=9371 corrected=0 nulled=0`. Same command you ran against RDS for Utah and five other jurisdictions on 2026-09-12; **that run predates OPEN-350 and OPEN-361**, so it did not apply them.

## 2. Gates (all read-only; do them in this order, record each result)
Any failure: stop, change nothing, report. **None of these steps modify an install.**

**G1. The code the command will run must be `14cc6a5`.** The recompute applies whatever openstates-core it runs on, so older code would silently use the old Utah rules. Name the exact `os-text-extract` you will use (`PLAN-rds-data-quality-backfill.md` §3 found two on this host: `/opt/ddp-open-states/.venv/bin/os-text-extract` and one bundled in ddp-sync's container, OPEN-248). Run this with **that executable's Python, in the exact environment you will use for the run**; it prints `OK` only on code that has both fixes:
```python
import openstates
from openstates.utils.version_ordering import is_procedural_document as p, version_sort_key as k
assert p("Utah", "Comparison to Sub #1") and p("Utah", "Amended Excerpts 2/12/2026 10:02:409")
assert not p("Utah", "Amended 2/12/2026 10:02:409")
assert k("Amended 2/9/2026 11:02:713", "") < k("Amended 3/3/2026 19:03:587", "")
print("OK", openstates.__file__)
```
**If it does not print `OK`: do not pull or change any existing install.** Your host's RDS loader (`os-update --import`) and anything else on it may run from the same code, and `main` now carries the 2026-10-12 upstream catch-up merge (PR #50), which has not been reviewed against the loader. Instead use a **separate checkout at exactly `14cc6a5`** (the commit the rehearsal ran), leaving every existing install untouched, for example a `git worktree add <new dir> 14cc6a5` from the existing openstates-core repository after a `git fetch` (this touches refs only, not the working tree), and run with that directory first on `PYTHONPATH` and the existing venv's Python and dependencies. **Re-run the block above in that exact environment**: it prints where `openstates` came from; it must be the new directory, and `git -C <new dir> rev-parse --short HEAD` must say `14cc6a5`. If you cannot make this work cleanly, stop and report; do not touch the existing installs to get past it. Remove the new directory afterwards, or leave it and say so.

**G2. Quiet window.** No Utah scrape, archive or load in flight (backfill locks, ddp-sync idle, as in your earlier quiet-window checks). Stay at least an hour clear of **Sunday 02:00 UTC** (the weekly job that includes Utah's scrape; next 2026-10-18) and **Monday 05:00 UTC** (Utah's archive; next 2026-10-19). Any quiet time before Sunday 01:00 UTC is fine; the sooner the better.

**G3. Rollback point.** The latest automatic RDS backup, or the point-in-time recovery window: **record its timestamp and confirm it predates the commit.** Do not create new snapshot machinery.

**G4. Baseline on RDS** (read-only). Expect **9,371 / 762 / 6,765 / 2,239 / 368**:
```sql
SELECT count(*) AS docs,
       count(DISTINCT d.version_note) AS distinct_notes,
       count(*) FILTER (WHERE d.diff_from_previous_version IS NOT NULL) AS with_diff,
       count(*) FILTER (WHERE d.version_note ~* '^comparison to '     AND d.diff_from_previous_version IS NOT NULL) AS comparison_with_diff,
       count(*) FILTER (WHERE d.version_note ~* '^amended excerpts '  AND d.diff_from_previous_version IS NOT NULL) AS excerpt_with_diff
FROM ddp_bill_version_document d
JOIN opencivicdata_bill b ON b.id = d.bill_id
JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
JOIN opencivicdata_jurisdiction j ON ls.jurisdiction_id = j.id
WHERE j.name = 'Utah';
```

**G5. The dry run on RDS** (writes nothing), with the exact executable and environment from G1:
`DATABASE_URL=<RDS, from the master secret as before; never paste it into a note or log> <that executable> recompute-diff-order ut --dry-run`
It must print **`ut: [DRY RUN] 1021 bills checked | unchanged=5137 corrected=1627 nulled=2607`**. The live replica, the legacy database and a full-size copy all printed exactly that. If RDS prints anything else, even slightly, **do not commit: report the line and wait.**

## 3. The run (only if G1 to G5 all passed)
1. Same command and environment with `--commit`:
   `DATABASE_URL=<RDS> <that executable> recompute-diff-order ut --commit`
   It must print the **same three numbers** as G5 (`[COMMITTED]`). Expect about half a minute locally; over the network a little more. **Name `ut`; never `all`.**
2. Immediately run it again with `--dry-run`. It must print **`unchanged=9371 corrected=0 nulled=0`**.
3. Re-run G4's query. Expect **9,371 / 762 / 4,158 / 0 / 0** (the diff-carrying count drops by exactly 2,607; no comparison or excerpt document carries a diff).
4. Do nothing else: no other jurisdiction, no flag, no trigger, no LegBot run, no restart.

**If the commit's three numbers differ from G5, the command errors, or it stops partway: stop and report.** Documents are saved one at a time with no transaction, so some may already be written. Do not retry and do not roll back without authorization; paste the output. A re-run is expected to converge (each new diff is computed from the stored text, not from the stored diff), but that is for Ramon and me to decide, not an automatic retry.

## 4. Reply on this branch
Reply with: G1 (the executable used, how the code was provided, the printed `OK` line and `openstates.__file__`, and the commit), G2 (the time window), G3 (the backup timestamp), G4 and the final query's rows, G5's and each command's exact output line, and the times you ran them. If any gate stopped you, say which and what you saw. **On my side** (read-only, on the Mac) I will then check the replica: Utah documents with a diff = 4,158, comparison and excerpt documents with a diff = 0, a Utah bill's stamped `Amended` versions through the Mac api-v3, and the changelog-transition count (2,042).

## 5. Not authorized
Pulling or changing any existing install, anything about the host's RDS loader, any other jurisdiction, `recompute-diff-order all`, any flag or schedule (including `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED`), any Utah scrape, archive or LegBot run. The **ddp-sync** pull of SYNC-110 on this host (your item 5 earlier) is separate and not part of this. Nothing here is urgent beyond the Sunday and Monday windows.
