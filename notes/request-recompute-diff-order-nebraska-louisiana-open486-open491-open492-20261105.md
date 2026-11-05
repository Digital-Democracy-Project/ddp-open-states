# Request: `recompute-diff-order` for Nebraska, then Louisiana, on RDS (OPEN-486, OPEN-491, OPEN-492). **Part 1 (read-only, including dry runs) now. Part 2 (the commit) HOLDS until a note from Ramon on this branch says GO for that state.** 2026-11-05 (Mac side, evening of 11-04 EST)

**What this does.** It applies three merged changes to the already-saved Nebraska and Louisiana documents: (1) amendment papers are left out of the what-changed comparisons (Nebraska AM, FA, ER: OPEN-486; Louisiana committee, floor and bureau amendment papers and Senate floor bureau notes: OPEN-491); (2) Nebraska's text clean-up (header lines out, one sentence per line: OPEN-486); (3) the new `is_bill_version` flag is stored on every saved document (OPEN-492). Nothing else changes: no scrape, no archive, no flag, no schedule, no other state.

**Code.** openstates-core fork `main` **`978fa96c49adc3fb6304fccda8237b24caea0cd5`** (PRs #75 to #80). Image **`ddp-scrapers:v43`, task-definition revision 46**, registered by Ramon this evening (v43 is built from that `main`). Your host's openstates-core is older (it was `5c79b47d`), so use the same method as OPEN-351 / OPEN-399: an environment that runs exactly `978fa96c` (a throwaway worktree first on `PYTHONPATH`, or the v43 image), with a proof that the code is the one named. Your choice; say which you used. The column `ddp_bill_version_document.is_bill_version` is on RDS (your `a5e35ac`) and on the Mac replica.

## Expected lines (measured by me, read-only, on the Mac's copy of production, with that exact code, 2026-11-05 00:4x UTC; the replica is 224,112 documents like RDS)
```
ne: [DRY RUN] 1847 bills checked | unchanged=1955 corrected=637 nulled=790
ne: [DRY RUN] is_bill_version: set=3382 changed=0 not_a_version=790
la: [DRY RUN] 2599 bills checked | unchanged=6318 corrected=919 nulled=3231
la: [DRY RUN] is_bill_version: set=10468 changed=0 not_a_version=3328
```
The dry runs wrote nothing (0 of 224,112 flags set afterwards). Nebraska took 14 s and Louisiana 22 s there. **If RDS prints anything different, even slightly, do not commit: report the line and wait.** (Nebraska 3,382 and Louisiana 10,468 documents are exactly what your archive reports `2df6b64` and `530ea0a` saved, so the counts should match unless something was archived since.)

## 1. Part 1: read-only (do now)
1. **G1 (code).** Show the environment runs `978fa96c` (the file path of `openstates/__init__.py` and `git rev-parse HEAD`, or the image id and tag).
2. **G2 (rollback point and quiet).** Record the RDS latest restorable time. Nothing in flight (no ECS task, scrape, archive, load, LegBot relay, backfill), no ddp-sync job in the last 10 minutes, and propose a window clear of **02:00, 02:30 and 03:00 UTC, Sunday 02:00 UTC, and the Wednesday archive window**. The commit is short (the dry runs take seconds) but it updates thousands of rows that stream to the Mac replica.
3. **G3 (baselines on RDS, read-only).** Report:
```sql
SELECT j.name, count(*) AS docs,
       count(*) FILTER (WHERE d.is_bill_version IS NULL) AS flag_null,
       count(*) FILTER (WHERE d.is_bill_version IS FALSE) AS flag_false,
       count(*) FILTER (WHERE d.diff_from_previous_version IS NOT NULL) AS with_diff
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name IN ('Nebraska','Louisiana') GROUP BY j.name;
```
Expected: Nebraska 3,382 docs, all flag_null, 0 false; Louisiana 10,468, all flag_null, 0 false.
4. **Dry runs (write nothing).** In the G1 environment: `recompute-diff-order ne --dry-run` then `recompute-diff-order la --dry-run`. Report the exact four lines.
5. **Reply** `reply-recompute-diff-order-nebraska-louisiana-preflight-20261105.md` with G1, G2 (the proposed window), G3, the four lines. Then wait for GO.

## 2. Part 2: the commit (needs GO for the state; Nebraska first, Louisiana only after Nebraska is verified)
In the G1 environment, with the dry run first printing **exactly the Part 1 lines** (if new data was archived and it differs, report and wait): `recompute-diff-order <st> --commit` printing the same numbers, then `--dry-run` again: it must print **`corrected=0 nulled=0`**. Then the G3 query again: Nebraska **flag_false = 790, flag_null = 0**; Louisiana **flag_false = 3,328, flag_null = 0**; `with_diff` falls by the `nulled` count (Nebraska by 790, Louisiana by 3,231 compared with the Part 1 baseline, plus whatever the baseline already had null). Report the lines, the query rows, the start and end times (UTC) and that nothing else changed.
Rollback if wanted (not expected): the recompute only rewrites `diff_from_previous_version` and `is_bill_version`; the RDS restore point from G2 is the guarantee. Do not try to undo it by hand without telling me.

## 3. Not authorized
Any state but Nebraska and Louisiana; `recompute-diff-order all`; `recompute-diff-order ma --commit` (OPEN-396); anything in Part 2 before a GO note for that state; a search refresh (`refresh --full`), any scrape, archive, flag, schedule, restart, LegBot run, or change to ddp-sync or the broker. The Nebraska re-archive that saves AM2748 (OPEN-487) is a separate request after this.

## 4. What I check on the Mac side (not yours)
After each commit I will check the Mac replica applied the updates (worker running, lag, no errors, the same four counts) and report.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
