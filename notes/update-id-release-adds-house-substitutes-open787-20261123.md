# UPDATE (not a GO) to `7788700` / `9b4d8b9` (Idaho acting senators): the same three steps now also carry **OPEN-787, Idaho House substitutes**. New people target, image commit and pass/fail lines below. 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Everything in `7788700` and `9b4d8b9` stands, except what is written here. Each step still waits on Ramon's go.

## Why
* Ramon, 2026-11-23 (OPEN-787 comment 22772): a House substitute's vote is the substitute's own, including Grayson Stone's 461 in Don Hall's seat. It is the same rule as OPEN-781.
* House bill pages print "Member(Substitute)", e.g. `Hall(Stone)`. Today **903 House votes** are credited to the regular member.

| Merge | What |
|---|---|
| people #47 `d1acd229` | 10 new retired records for House substitutes and 2 updated existing ones (Megan Woller, Gayle Batt), each with a dated House role and its printed form as a dated other name, cited from the 2026 House Final Journal |
| scrapers #242 `a49913ae` | the printed `X(Y)` form is kept in **both** chambers (OPEN-781 kept it on Senate rows only). `Crane(12)`, "Mr. Speaker", vote keys and chambers are unchanged |

**Offline (the builder's, all 45,990 Idaho 2026 votes, all 853 roll calls re-read):**
* the 903 move to the substitutes;
* OPEN-779's 48 and OPEN-781's 368 hold;
* 0 double votes, 0 unresolved;
* nothing else changes.

People first is safe on its own; the scraper alone would leave the 903 unlinked (not wrong).

## Step 1 (people refresh for `id`): new target
* Pull people to **`d1acd229`** or later.
* **Expected for `id`, if step 1 hasn't run yet** (your status `b3717e7`: not started):
    * **created 17, updated 5**: 7 + 10 new records; Coho, Rundhaug, Woller, Batt, and Darl Bruner's municipal file.
    * If step 1 already ran at `febf9fc1`: created 10, updated 2.
    * Anything else: stop and report.
* Since `febf9fc1`, people main also changed one RI file (OPEN-786, Appollonio). Load **`id` only** here; RI's load is its own step in `98e5dcb`.

## Step 2 (the image): new commit
* v82 at scrapers main **`a49913ae` or later**. That one image also carries RI (#235, #236), OK (#237, #238), NC (#233), MO (`c3ec462d`) and Idaho #234.
* Mac side checks the scrapers tree contains `a49913ae`.

## Step 3 (the Idaho 2026 re-import): unchanged trigger; added pass/fail lines
Run all four queries in `7788700`, with these changes:
* **Query 2** (double votes): still expect 0.
* **Query 1** (unmatched): still expect 0.
* **Add:**
```sql
-- 5. House votes per substitute: expect Grayson Stone 461, Kirk Larsen 82, Lisa Cannon 55, Gayle Batt 53,
--    Trevor Chadwick 50, Max Brown 42, Randolph J. Hill 40, William Athay 37, Jennifer Beazer 32,
--    Megan Woller 23 (House only), Jeff Carlson 14, Kenneth Zaken 14
SELECT p.name, count(*) FROM opencivicdata_personvote pv JOIN opencivicdata_person p ON p.id=pv.voter_id
JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_organization o ON o.id=v.organization_id
JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:id/government' AND s.identifier='2026' AND o.classification='lower'
  AND p.name IN ('Grayson Stone','Kirk Larsen','Lisa Cannon','Gayle Batt','Trevor Chadwick','Max Brown','Randolph J. Hill',
                 'William Athay','Jennifer Beazer','Megan Woller','Jeff Carlson','Kenneth Zaken')
GROUP BY 1 ORDER BY 2 DESC;

-- 6. Don Hall's 2026 House votes: expect 0 (before: 461)
SELECT count(*) FROM opencivicdata_personvote pv JOIN opencivicdata_person p ON p.id=pv.voter_id
JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:id/government' AND s.identifier='2026' AND p.name='Don Hall';
```
* If a display name in query 5 returns nothing, check it against the people file before calling it a failure.
* **Fail** = any number off. Stop and report.

## Rollback (from the PRs)
Revert the scraper and re-import **before** removing the people records.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
