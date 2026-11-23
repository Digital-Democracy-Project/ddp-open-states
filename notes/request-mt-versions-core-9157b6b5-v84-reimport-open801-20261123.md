# REQUEST (not a GO): Montana version names (OPEN-801). (1) Core `9157b6b5` on both api-v3 copies and EC2 ddp-sync, (2) image v84 (Ramon builds it after step 1's core is on main, which it already is), (3) ONE full re-import of Montana 2027 and the version-stage gate. 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Each step waits on Ramon's go. Step 2 is Ramon's build. Steps 1 and 3 are the prod agent's, each after a GO note.

## Why
* Montana's first scrape (`mt-9bbf779af061`, rev 84, 2027 pre-filing) fails Stage 3's version-stage gate: **294 / 294 versions (100%)** are named by their file name ("HB0017_1.pdf"), which has no stage (OPEN-670).
* Both fixes below are reviewed and merged by the PM session.

| Merge | What |
|---|---|
| openstates-core #142 → **`9157b6b5`** | one exact-name rank: "Bill Draft" just below "Introduced". A whole-replica check of 26,350 (state, name) pairs changes **0** stages. No migration |
| openstates-scrapers #250 → **`2c29d8a1`** | Montana names versions from the legislature's own file kinds: `LCnnnn` → "Bill Draft", `_1` → "Introduced", `_2…` → "Amended Version N", `_X` → "Enrolled". Re-uploads become links of one version; amendments and veto papers become documents |

* **Offline (the builder's, core `note_stage`):**
    * MT 2027: 294/294 → **0/294** with no stage;
    * all of MT 2025: 0.2%;
    * order matches the legislature's 1, 2, …, X numbering on all 1,167 multi-version 2025 bills.

## Step 1: core `9157b6b5` (on a GO)
* As for `939e4a2c` (`38e02fc`), with `DDP_CORE_SHA=9157b6b5…`:
    * EC2 api-v3: tag a rollback image, build, then `up -d --no-deps api`;
    * Mac api-v3: `refresh-api-v3.sh`, done by me or by Ramon;
    * **EC2 ddp-sync rebuilt at its current commit (`85c8888`)** with the new core. A restart drops in-flight archives and queued runs, as in `692a2ba`. Post the in-flight list first, and pick a quiet moment; never 02:15–04:45 UTC.
    * Then `check-core-pin-drift.py --image-core 9157b6b5…` exits 0 for each.
* **Core since `939e4a2c` is only #142:** `version_ordering.py` and tests. No migration.
* Not 05:00–07:00 UTC for api-v3 (the scorecard chain reads it).

## Step 2: image v84 (Ramon)
* Build at scrapers main **`2c29d8a1` or later**, with core main **`9157b6b5`**.
* It also carries the v84 set already merged:
    * OPEN-797 (#247, Iowa timeouts);
    * OPEN-799 (#248, Maryland);
    * OPEN-798 (#249, Idaho's redesigned session page).
* So **one v84 serves Idaho's re-import, Maryland's first scrape again, Iowa 2025 and Montana**. I'll post one image update when its revision is known.
* Mac side checks the scrapers tree contains `2c29d8a1` and `DDP_CORE_COMMIT` is `9157b6b5`.

## Step 3: the Montana 2027 re-import (on a GO, after steps 1 and 2)
### Gates
1. New tasks run v84's revision or later.
2. Nothing Montana running (`ddp:pipeline_lock:mt` empty).
3. Not on Sunday from 02:00 UTC.

### The run
```
POST /ddp-sync/v1/trigger/openstates-scrape/mt?full=true&sessions=2027
```
* The answer must be 202 with `"full": true`.
* Report the run id, revision, `"mode": "full"`, bill / version / vote counts (expect about 2,096 bills, 0 votes) and the archive result.

### Pass/fail after (read-only)
```sql
-- 1. versions named by a file name: expect 0 (before: 294)
SELECT count(*) FROM opencivicdata_billversion bv JOIN opencivicdata_bill b ON b.id=bv.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:mt/government' AND s.identifier='2027' AND bv.note ILIKE '%.pdf';

-- 2. version names: expect only "Bill Draft", "Introduced", "Amended Version N", "Enrolled"
SELECT bv.note, count(*) FROM opencivicdata_billversion bv JOIN opencivicdata_bill b ON b.id=bv.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:mt/government' AND s.identifier='2027'
GROUP BY 1 ORDER BY 2 DESC;
```
* **3. The gate:** `quality_check.py --structural mt` at core `9157b6b5`: version stage coverage under 5.5% (before: 100%).
* **Fail** = any of these off. Stop and report.
* I check the same on the Mac replica, then record it on OPEN-670.

## Not authorized
* Any step before its GO note.
* Any other state's re-import (Idaho, Maryland and Iowa have their own requests).
* A recompute.
* A second re-import.
* Any manifest, schedule, routing or LegBot change.

Tickets: OPEN-670 (OPEN-146); fix OPEN-801.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
