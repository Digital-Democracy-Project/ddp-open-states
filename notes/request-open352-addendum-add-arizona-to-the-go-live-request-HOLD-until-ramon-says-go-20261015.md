# ADDENDUM: OPEN-352, add Arizona to the go-live and recompute request. **Still HOLD until Ramon says GO.** (Mac side, 2026-10-15 EDT)

Amends `request-open352-go-live-and-recompute-nc-wa-mi-al-HOLD-until-ramon-says-go-20261015.md` (`5ec936e`). Everything in that request stands (the gates, the order of parts, the "not authorized" list, the HOLD). This note only changes the scope: **Arizona is now in.** Ramon decided this on 2026-10-15 after the research below.

## Why Arizona was held, and why it is now in

The dry runs showed Arizona with `corrected=3697 nulled=131`. Your isolation run at `14cc6a5` (`corrected=3828 nulled=0`) showed the 3,697 are not caused by the OPEN-352 fixes. Mac-side research since (read-only, through the replica's api-v3, recomputing every Arizona PDF diff from stored text with core's own `unified_diff` and `_reflow_paragraphs`; full write-up on OPEN-368):

* **Not an ordering problem.** 0 stored diffs were taken against a different version than the predecessor.
* **Missing cleaning.** 1,722 of the 1,849 changed PDF diffs (93%) are the diff **without** Arizona's line-wrap tidy-up; the recompute applies it. On those, changed lines fall from 322,043 to 112,352 (65% fewer), larger in only 3.
* Not explained: 125 diffs (5%); the HTML twins are not visible through api-v3.

So an Arizona recompute applies (a) the 131 blank-page nulls and (b) a backlog of mostly missing cleaning. The recompute is repeatable, so it does not lock in the unresolved ordering question in OPEN-368 (whether the `HOUSE - ` / `SENATE - ` documents are in chronological order); if that order changes later, another recompute fixes it.

## What changes in the original request

1. **Scope:** `nc`, `wa`, `mi`, `al` **and `az`** (Arizona last).
2. **Part 1, G3 baseline:** add a fifth row, read-only:
```sql
SELECT 'az blank documents with a diff', count(*)
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name='Arizona' AND d.is_error=false AND d.diff_from_previous_version IS NOT NULL
  AND d.raw_text <> '' AND d.raw_text ~ '^[[:space:]]*$';
```
Expected before: about **131**; after the Arizona commit: **0**.
3. **Part 3, Arizona step** (own GO needed, as for each state): `recompute-diff-order az --dry-run` must print **`az: [DRY RUN] 2190 bills checked | unchanged=5105 corrected=3697 nulled=131`** (if the data changed and the numbers differ, report and wait); `--commit` prints the same; the second dry run must print `corrected=0 nulled=0`; the G3 Arizona row must be 0.
4. **Expected consequences for Arizona:** existing Arizona changelogs (1,907 live) are **not** regenerated; a recompute only rewrites the stored diff column. Ramon knows that about two thirds of them were probably written from untidied diffs; regenerating them is a separate decision. Do not start any run.
5. Arizona's ordering fix (OPEN-368) is **not** part of this and PR #64 stays unmerged.

## Reply

Same as the original request: a `reply-open352-golive-...` note after each part. Nothing here authorizes any step beyond Part 1.
