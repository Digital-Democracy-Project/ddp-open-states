# Request: `recompute-diff-order` for Virginia, Utah, Alabama, Arizona and North Carolina on RDS (OPEN-492, OPEN-422). **Part 1 (read-only, including dry runs) now. Part 2 (the commit) HOLDS, per state, until a note from Ramon on this branch says GO for that state.** 2026-11-06 (Mac side)

**What this does.** Nebraska and Louisiana already have every saved bill document marked as a real bill version or a procedural paper (`is_bill_version`), with the what-changed comparisons rebuilt (your `61f5693` and `54c2b04`, both matched). Ramon asked on 2026-11-06 (/ask-me, all five states chosen) to do the same for the five older states, whose saved documents still have no mark (`is_bill_version` NULL). The commit sets the mark on every saved document and rebuilds the stored comparisons so a procedural paper is never compared as a version. Nothing else changes: no scrape, no archive, no schedule, no other state.

**Code.** openstates-core fork `main` **`978fa96c49adc3fb6304fccda8237b24caea0cd5`** (PRs #75 to #80), image **`ddp-scrapers:v43`, task-definition revision 46** (confirmed live by your `0efc7e7`). Use the same environment as the Nebraska and Louisiana runs (`978fa96c` on `PYTHONPATH`, or the v43 image) and say which, with the proof of the code. The column is on RDS and the Mac replica.

**No pre-measured expected lines this time.** For Nebraska and Louisiana I measured the dry runs on the Mac first and gave you the exact lines. I could not do that here (the Mac has no GDAL library, so the exact-code command will not start on it). So the dry-run lines are the first reading, not a check against mine: **report them, do not commit, and I will read them against the Mac replica's own counts before Ramon decides.**

## 1. Part 1: read-only (do now), one state at a time in this order: va, ut, al, az, nc
1. **G1 (code).** The environment runs `978fa96c` (`openstates/__init__.py` path and `git rev-parse HEAD`, or image id and tag).
2. **G2 (rollback point and quiet).** Record the RDS latest restorable time. Nothing in flight (no ECS task, scrape, archive, load, LegBot relay, backfill), no ddp-sync job in the last 10 minutes, and propose a window clear of 02:00, 02:30 and 03:00 UTC, Sunday 02:00 UTC and the archive windows. Virginia, Utah, Alabama, Arizona and North Carolina are bigger than Nebraska and Louisiana: **report each dry run's time**, because the commit updates thousands of rows that stream to the Mac replica.
3. **G3 (baselines on RDS, read-only), per state:**
```sql
SELECT j.name, count(*) AS docs,
       count(*) FILTER (WHERE d.is_bill_version IS NULL) AS flag_null,
       count(*) FILTER (WHERE d.is_bill_version IS FALSE) AS flag_false,
       count(*) FILTER (WHERE d.diff_from_previous_version IS NOT NULL) AS with_diff
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name IN ('Virginia','Utah','Alabama','Arizona','North Carolina') GROUP BY j.name;
```
(Expected shape: every document `flag_null`, `flag_false` 0, except any document archived on v43 since 11-05 03:14 UTC, which already has its mark.)
4. **Dry runs (write nothing).** `recompute-diff-order <st> --dry-run` for each state; report the exact lines, and each run's start and end time.
5. **Reply** `reply-recompute-diff-order-va-ut-al-az-nc-preflight-20261106.md` with G1, G2 (window), G3 and the lines. Then wait.

## 2. Part 2: the commit (per state, only after a GO note for that state)
Same shape as Nebraska and Louisiana: the dry run first printing exactly what Part 1 printed (if anything changed, report and wait), then `recompute-diff-order <st> --commit` printing the same numbers, then `--dry-run` again, which must print **`corrected=0 nulled=0`**, then the G3 query again: **`flag_null` = 0** for that state and `flag_false` = the `not_a_version` count from the commit line. Report the lines, query rows, start and end times (UTC) and that nothing else changed. Rollback is the G2 restore point; do not try to undo by hand without telling me.

## 3. Not authorized
Any state other than these five; `recompute-diff-order all`; `recompute-diff-order ma --commit` (OPEN-396); Part 2 for any state before its GO note; rejecting or changing any approved bill summary (Arizona has 17 on procedural papers; that is a separate step, not asked); a search refresh, any scrape, archive, schedule, restart, LegBot run, or change to ddp-sync or the broker.

## 4. What I check on the Mac side (not yours)
After each commit: the Mac replica applied it (worker running, lag, no errors), the same counts, no row left unmarked in that state, and the 104-bill Virginia re-scan from OPEN-422.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
