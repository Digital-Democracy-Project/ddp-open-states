# Request: Alabama `recompute-diff-order` on RDS (OPEN-525). **Part 1 (read-only, including dry runs) now. Part 2 (the commit) HOLDS until a GO note from Ramon on this branch.** 2026-11-10 about 17:10 UTC (Mac side)

## What I need from you
1. **Part 1 now** (read-only): gates G1 to G3 below, then the two dry runs, then reply.
2. **Part 2 only after a `go-…` note.**

## What this does, and why
Alabama is resuming toward going live (OPEN-523; Ramon ran `/onboard-state Alabama` and said "Resume scraping Alabama"). Its version-stage check failed: 453 of 2,922 Alabama versions are the amendment or substitute papers behind floor motions ("Orr motion to Table - Adopted Voice Vote", "Motion to Adopt - Adopted Roll Call 407"). The scraper stores them as versions named after the action.

OPEN-525 (openstates-core #92, merged `a7a2a861`) marks them as **not bill versions**. The recompute sets that mark (`is_bill_version` false) on the 453 saved documents. They stay archived with their text; nothing is deleted. According to the Mac replica, **no stored comparison changes**, because none of the 453 has one. Nothing else changes: no scrape, no archive, no schedule, no other state.

**Code.** Image **`ddp-scrapers:v54`, task-definition revision 57**, registered by Ramon today (from the `deploy-scrapers-image.sh` run, about 17:00 UTC). I checked inside v54 that it carries `_AL_FLOOR_MOTION_PAPER` (core #92). Use v54, or openstates-core fork `main` at or after `a7a2a861` on `PYTHONPATH`, as for the 11-06 runs, and say which, with the proof.

## Part 1: read-only (now)
1. **G1 (code):** the environment runs v54 / rev 57 (image id and tag), or core `a7a2a861` or later (`git rev-parse HEAD`).
2. **G2 (rollback point and quiet):**
   * Record the RDS latest restorable time.
   * Nothing in flight: no ECS task, scrape, archive, load, LegBot relay or backfill, and no ddp-sync job in the last 10 minutes.
   * Propose a window clear of 02:00, 02:30, 03:00 and 04:00 UTC. Pennsylvania's nightly starts at 04:00 and runs about 7 hours.
3. **G3 (baseline on RDS, read-only):**
```sql
SELECT j.name, count(*) AS docs,
       count(*) FILTER (WHERE d.is_bill_version IS NULL) AS flag_null,
       count(*) FILTER (WHERE d.is_bill_version IS FALSE) AS flag_false,
       count(*) FILTER (WHERE d.diff_from_previous_version IS NOT NULL) AS with_diff
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name = 'Alabama' GROUP BY j.name;
```
   **Expected (Mac replica, 17:05 UTC):** `Alabama | 2923 | 0 | 45 | 918`.
4. **Two dry runs (write nothing), and report the exact lines and each run's start and end time:**
   * `os-text-extract recompute-diff-order al --dry-run`, the full run. This confirms that no comparison would change.
   * `os-text-extract recompute-diff-order al --dry-run --flags-only`.

   **Expected:** 453 documents change their mark, `not_a_version=498`, and no comparison corrected or nulled. If the full run says any comparison would change, **stop and report**.
5. **Reply** `reply-recompute-diff-order-alabama-preflight-20261110.md`, with G1, G2 (window), G3 and the lines. Then wait.

## Part 2: the commit (only after a GO note)
1. Run the dry run again; it must print what Part 1 printed. If anything changed, report and wait.
2. `os-text-extract recompute-diff-order al --commit --flags-only`.
3. `--dry-run --flags-only` again, which must print 0 to change.
4. G3 again. **Expected:** `flag_false` 498, `flag_null` 0, `with_diff` still 918.
5. Report the lines, the query rows, start and end times (UTC), and that nothing else changed. Rollback is the G2 restore point; do not undo by hand without telling me.

## Not authorized
* Any state other than Alabama; `recompute-diff-order all`.
* Part 2 before its GO note.
* A run without `--flags-only` at commit.
* A search refresh, any scrape, archive, schedule change, restart or LegBot run.
* Any change to ddp-sync, the broker, the manifest or a task definition.

## What I check on the Mac side (not yours)
After the commit:
* the Mac replica applied it (worker running, recent messages);
* Alabama: 498 not a version, 0 unmarked, 918 comparisons;
* other states' counts unchanged;
* `quality_check.py --structural al`: version stage coverage passes (0 of 2,922 versions with no stage, against 453 before).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
