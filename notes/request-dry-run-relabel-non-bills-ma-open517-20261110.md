# Request (READ-ONLY): dry run of `relabel-non-bills ma` on RDS (OPEN-517). 2026-11-10, about 06:10 UTC (Mac side)

**Ramon, 2026-11-10:** "yes, post the dry-run request".

**This is a dry run only.** Nothing is written. The `--commit` step needs a separate GO note after Ramon has seen the count.

## Why
Massachusetts files agency reports, communications, orders and study orders under bill numbers, and OpenStates stores them as bills. Ramon decided on 2026-11-09 (OPEN-513, OPEN-517) to **relabel** them, never delete them:
* each item gets a label for what it is: `report`, `communication`, `order` or `study request`;
* the old label is kept in `extras` so `--undo` can put it back.

The website will later stop listing them as bills (NEXT-182, BROKER-460, OPEN-519).

The new Massachusetts scraper (OPEN-518, in the next scrapers image v53, **not built or registered yet**) labels these papers itself. **So this relabel must run before v53 goes live**, or the saved old labels would never be written. The next Massachusetts scrape is Sunday 11-15 02:00 UTC.

## Code
openstates-core `main` at **`1459c22e9c54b3f2360e11569d9dbf14b2af18a3`**:
* #90, the command (merge `dab94675`);
* #91, the import keeps the saved label.

Same method as the OPEN-352 and OPEN-495 recomputes:
* a throwaway `git worktree` of `/opt/ddp-open-states/openstates-core` at exactly that commit, first on `PYTHONPATH`;
* the existing venv's Python and `os-text-extract`;
* `DATABASE_URL` from the environment only (never printed).

Remove the worktree afterwards, and leave the host's own core checkout untouched.

## Gates (before running)
* **G1, code:** `python -c "import openstates, openstates.utils.version_ordering as v; print(openstates.__file__, hasattr(v, 'non_bill_kind'), v.ORIGINAL_CLASSIFICATION_KEY)"` prints the worktree path, `True` and `ddp_open517_original_classification`.
* **G2, quiet:** no Massachusetts scrape, archive or text-extract running, and not inside 02:00 to 04:30 UTC. The dry run only reads, but it walks every Massachusetts bill and its actions.

## Baseline (read-only SQL on RDS)
```sql
SELECT b.classification, count(*)
FROM opencivicdata_bill b
JOIN opencivicdata_legislativesession s ON s.id = b.legislative_session_id
WHERE s.jurisdiction_id = 'ocd-jurisdiction/country:us/state:ma/government'
GROUP BY 1 ORDER BY 2 DESC;

SELECT count(*) FROM opencivicdata_bill b
JOIN opencivicdata_legislativesession s ON s.id = b.legislative_session_id
WHERE s.jurisdiction_id = 'ocd-jurisdiction/country:us/state:ma/government'
  AND b.extras ? 'ddp_open517_original_classification';
```
**Expected:**
* `{bill}` and `{"proposed bill"}` only;
* about 11,911 Massachusetts bills in total;
* **0** rows that already carry the saved-label key.

## The dry run
```
os-text-extract relabel-non-bills ma --session 194th --dry-run --list /home/bitnami/ops/open517-20261110/relabel-ma-dry-run.csv
```
**Expected** (the same command on the Mac replica, 2026-11-10, before Sunday's skipped run; production may differ by a handful):
```
ma: [DRY RUN] relabelled=3132 already_labelled=0 skipped_amendment_paper=157 skipped_has_recorded_votes=8
  proposed bill -> report: 1516
  proposed bill -> communication: 982
  bill -> study request: 332
  bill -> order: 205
  proposed bill -> order: 59
  bill -> report: 22
  bill -> communication: 16
```

## Please report
1. **G1 and G2:** the lines, plus the commit the worktree is at.
2. **The baseline SQL results.**
3. **The dry-run output, exactly** (every line).
4. **The CSV:**
   * its row count (not counting the header);
   * please **commit it to this branch** as `notes/open517-relabel-ma-dry-run-rds-20261110.csv`.

   It holds bill ids, numbers, the old and new label and the public title, and no secrets. I'll diff it with the Mac's list before asking Ramon for the go.
5. **The baseline SQL again after the dry run.** It must be identical, which proves nothing was written.

## Not authorized
* `--commit`, `--undo`, or any write.
* Any other state, or a run without `--session 194th`.
* `recompute-diff-order`, a scrape, an archive, a text extract, a refresh, or a LegBot run.
* Pulling the ddp-open-states tip, or any change to the host's core checkout or its installs.
* Building, registering or deregistering a scrapers image or task definition, including v53.
* Any change to ddp-sync, the broker or api-v3.

## What I check on the Mac side
* I diff your CSV against the Mac replica's dry-run list (3,132 rows) and explain any difference.
* I bring Ramon the count for his go on `--commit --expect <count>`. That will be a separate GO note, run outside the Massachusetts scrape window and before v53 is registered.
* After the commit, I check the new labels on the Mac api-v3.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
