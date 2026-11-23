# REQUEST (not a GO): Idaho acting senators (OPEN-779, OPEN-781). (1) people refresh for `id`, (2) the next scrapers image holding scrapers `02ba6f4e`, (3) ONE full re-import of Idaho 2026, in that order. 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Each step waits on Ramon's go. Step 2 is Ramon's build (`deploy-scrapers-image.sh`). Steps 1 and 3 are the prod agent's, each after a GO note.

## Why
Ramon decided (OPEN-781, comment 22684) that **an acting (substitute) senator's vote is the acting senator's own.** Idaho's first scrape (`id-2a1021ebee6f`, ddp-sync notes `6ea7c43`) stores:
* **48 Senate votes that match no one.** Four acting senators had no record: Zach Brooks, Joan Hawkins, Brian Merrell, and Darl Bruner (who goes on his Nampa mayor record, per Ramon).
* **368 Senate votes credited to a senator who didn't cast them,** 15 of them as a second vote on the same roll call:
    * Lesli Bjerke 351, on Carl Bjerke;
    * Steve Keyser 11, on Josh Keyser;
    * Garrett Bjerke 4, on Carl Bjerke;
    * Elisha Toews 2, on Ben Toews.

| Merge | Ticket | What |
|---|---|---|
| people #44 `133e2fb0` | OPEN-779 | the first four acting senators, with dated Senate roles cited from the 2026 Senate Final Journal (Idaho Code 67-412 letters) |
| people #45 `febf9fc1` | OPEN-781 | the other four, plus every 2026 acting senator's printed form (e.g. "Bjerke(Bjerke)") as a dated other name |
| scrapers #234 `02ba6f4e` | OPEN-781 | on Senate roll calls, the scraper keeps the bill page's printed "Acting(Senator)" form instead of the bare surname, so only the acting senator matches |

All three are reviewed and merged by the PM session. No migration, no core change (core stays `42b48982`), no manifest change.

**Offline check (the builder's, over all 45,990 stored Idaho 2026 votes, core `42b48982`):**
* the 48 resolve;
* the 368 move to the acting senators who cast them;
* double votes go from 15 to 0;
* **no other vote changes.**

**The order matters.** With the new scraper but **without** the people refresh, 486 acting-senator votes would load unmatched. They wouldn't be wrong, but they'd be unlinked. With the people refresh and the old scraper, only OPEN-779's 48 change, so step 1 is safe on its own.

## Step 1: people refresh for `id` (prod agent, on a GO note)
* Pull `/opt/ddp-open-states/people` to people main **`febf9fc1`** or later.
    * If the NE/LA request (`df508b7`, part A, target `efc86188`) hasn't run yet, this pull covers it too. Then load **only `id`** here; `la` and `ne` stay with their own go.
* Since `efc86188`, only Idaho files changed:
    * 7 added in `data/id/retired/` (the 7 new acting senators);
    * 3 modified in `retired/` (Coho, Rundhaug, Woller: dated other names);
    * 1 modified in `municipalities/` (Darl Bruner: the Senate role).
* `os-people` from the container's venv, as on 11-21: `--safe` first, then real, **`id` only**.
    * **Expected: created 7, updated 4**, no "went missing" or retirement line. Anything else: stop and report.

## Step 2: the image (Ramon)
* Any scrapers image built at scrapers main **`02ba6f4e` or later** carries #234.
    * If v81 (requested in `21d55d4` / `86a8109` / `795a93b`) is built from main now, it also holds North Carolina's OPEN-783 (#233) and Idaho's #234; no separate v82 is needed.
    * If v81 was built before `02ba6f4e`, the next image (v82) carries it.
* Mac side checks the image's scrapers tree contains `02ba6f4e`, and `DDP_CORE_COMMIT` is `42b48982`.
* **Best after step 1:** Idaho's weekly Sunday run would otherwise load any changed Senate roll call on the new scraper without the people. Idaho's 2026 session ended 04-02, so few or none would change.

## Step 3: the Idaho 2026 re-import (prod agent, on a GO note, after steps 1 and 2)
### Gates (stop and report if one fails)
1. Step 1 is done and reported (created 7, updated 4).
2. New tasks run the image holding `02ba6f4e`. Report the revision.
3. **Nothing Idaho is running:** no `id` collection, load, archive or text-extract task; `ddp:pipeline_lock:id` empty.
4. Not on Sunday from 02:00 UTC.

### The run
```
POST /ddp-sync/v1/trigger/openstates-scrape/id?full=true&sessions=2026
```
* The answer must be 202 with `"full": true`. A 409: wait; don't force.
* **Report:**
    * the run id and revision;
    * `"mode": "full"`;
    * the load's status with bill and vote counts (expect 817 bills, 853 vote events, as on 11-23);
    * the archive result.
* A load stopped by "already imported as ...": stop and report the full message.

### Pass/fail after (read-only, on RDS)
```sql
-- 1. unmatched Idaho 2026 person votes: expect 0 (before: 48)
SELECT count(*) FILTER (WHERE pv.voter_id IS NULL), count(*)
FROM opencivicdata_personvote pv JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id
JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:id/government' AND s.identifier='2026';

-- 2. roll calls where one person has two votes: expect 0 (before: 15)
SELECT count(*) FROM (SELECT pv.vote_event_id, pv.voter_id FROM opencivicdata_personvote pv
  JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
  WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:id/government' AND s.identifier='2026' AND pv.voter_id IS NOT NULL
  GROUP BY 1,2 HAVING count(*) > 1) x;

-- 3. Senate votes per acting senator
--    expect Lesli Bjerke 351, Darl Bruner 28, Steve Keyser 11, Joan Hawkins 10,
--    Zach Brooks 6, Garrett Bjerke 4, Brian Merrell 4, Elisha Toews 2
SELECT p.name, count(*) FROM opencivicdata_personvote pv
JOIN opencivicdata_person p ON p.id=pv.voter_id
JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id
JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:id/government' AND s.identifier='2026'
  AND p.name IN ('Lesli Bjerke','Darl Bruner','Steve Keyser','Joan Hawkins','Zach Brooks','Garrett Bjerke','Brian Merrell','Elisha Toews')
GROUP BY 1 ORDER BY 2 DESC;

-- 4. Carl Bjerke's Senate votes from 2026-03-02 to 04-02: expect 0 (before: 351)
SELECT count(*) FROM opencivicdata_personvote pv JOIN opencivicdata_person p ON p.id=pv.voter_id
JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:id/government' AND s.identifier='2026'
  AND p.name='Carl Bjerke' AND v.start_date::date BETWEEN '2026-03-02' AND '2026-04-02';
```
* **Fail** = any number off. Stop and report; no second run. Each person's display name should be checked against the people files if a name query returns nothing.
* **I check the same on the Mac replica** once it catches up. Then I post `reply-verified-id-acting-senators-<date>.md` and record it on OPEN-664.

## Possibly riding along: OPEN-787 (Idaho House substitutes)
* 903 House votes are credited to a regular representative who didn't cast them (12 substitutes; ticket comment 22722).
* It waits on Ramon's confirmation of the Don Hall / Grayson Stone case (461 votes). It is **not built**.
* If it's merged before the step 2 image, I'll post an UPDATE here: one more people refresh line, and changed numbers for the same re-import. If not, it gets its own people refresh and re-import later.

## Scorecards
Idaho isn't live (routing and LegBot off), so no scorecard shows these votes today. The re-import corrects them before go-live.

## Not authorized
* Any step before its GO note.
* Any other state or session, including la and ne in step 1.
* A second re-import.
* A recompute or relabel.
* Any manifest, schedule, routing or LegBot change.

Tickets: OPEN-664 (OPEN-146); fixes OPEN-779, OPEN-781; OPEN-787 pending.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
