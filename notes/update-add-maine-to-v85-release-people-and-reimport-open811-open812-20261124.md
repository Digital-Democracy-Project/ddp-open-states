# UPDATE (not a GO) to `de80ea4`: add **Maine** to the v85 release. v85 now needs scrapers **`ecd44eab` or later**. Then a Maine people load (people `b6a1c71b`), then a full re-import of Maine's three sessions. 2026-11-24 (Mac side, Onboard New States)

**Not a GO.** Everything in `de80ea4` stands. This note changes the v85 commit and adds Maine steps M1–M3, each on Ramon's go.

## Why
* Maine's first scrape (loaded about 00:05 UTC 11-24) fails two Stage 3 gates on the Mac replica, at core `0f3c24c9` (OPEN-672):
    * **Versions with no stage: 2,368 / 5,131 (46.2%).** Each bill's printed text is named only by its paper numbers ("LD n HP n", "LD n SP n").
    * **Unresolved votes: 13,001 / 148,002 (8.8%), all House.** The roll calls print "SURNAME of Town", and 17 current House members' people files lack that exact name.
        * Also **47 votes in 132R1 are credited to the wrong person:** "TERRY of Gorham" went to former Rep. Maureen Terry, not Parnell Terry.
* Both fixes are reviewed and merged by the PM session:

| Merge | What |
|---|---|
| scrapers #258 → **`ecd44eab`** (OPEN-811) | the bill's own LD paper is named "Introduced (LD n, HP/SP n)"; a committee New Draft is "Amended in New Draft (…)". Offline gate: **46.2% → 0 / 5,131** |
| people #48 → **`b6a1c71b`** (OPEN-812) | the printed "SURNAME of Town" added to 17 House members' `other_names`; nothing removed. An offline replay of core's matching: 13,001 → **0**, and the 47 Terry votes move to Parnell Terry |

* `ecd44eab` also holds #257 (OPEN-810: the MA Speaker comes from the manifest only). The offline check gives byte-identical MA output with today's manifest, so it needs no MA re-import.

## Change to `de80ea4` step 2 (v85)
* Build at scrapers main **`ecd44eab` or later** (was `14c4e1c4`), with core `0f3c24c9`.
* Mac side checks that the image's scrapers holds `ecd44eab`.
* **ddp-sync's rebuild (ddp-sync `132d8cf`) takes the same scrapers commit as v85** for `DDP_SCRAPERS_SHA`: `ecd44eab94610adc82b00888e4e72fd40d745201` if v85 is built at today's main.

## M1: Maine people load (on a GO; can run any time, it doesn't need v85)
1. Pull `/opt/ddp-open-states/people` to people main **`b6a1c71b`** or later.
    * Since `d1acd229` (#47, Idaho, loaded 11-23), only #48 changed: 17 files under `data/me/legislature/`.
2. Load Maine only with the container's `/opt/venv-openstates/bin/os-people`, as for Idaho and NE/LA (`df508b7` part A): `--safe` first, then real.
    * **Expected: me created 0, updated 17.** No "went missing" or retirement line.
    * **Anything else: stop and report.**

## M2: Maine full re-import (on a GO; after M1 and after v85's revision is live)
### Gates
1. New tasks run v85's revision or later.
2. `ddp:pipeline_lock:me` is empty.
3. Not on Sunday from 02:00 UTC.
4. One heavy load at a time, queued with MS and HI from `de80ea4` step 4.

### The run
```
POST /ddp-sync/v1/trigger/openstates-scrape/me?full=true&sessions=132R1,132R2,132S1
```
* The answer must be 202 with `"full": true`.
* Report:
    * the run id and revision, and `"mode": "full"`;
    * bill / version / vote counts per session (before: 132R1 1,305 bills, 132R2 311, 132S1 834);
    * the archive result.
* **Why a full re-import and not `relink-blank-voters.py`:** the relink fills blank voters but would leave the 47 Terry votes on the wrong person, and it doesn't rename versions.

## M3: pass/fail after (read-only)
```sql
-- 1. unmatched House votes: expect 0 (before 13,001)
SELECT s.identifier, count(*) FILTER (WHERE pv.voter_id IS NULL), count(*)
FROM opencivicdata_personvote pv JOIN opencivicdata_voteevent ve ON ve.id=pv.vote_event_id
JOIN opencivicdata_legislativesession s ON s.id=ve.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:me/government' GROUP BY 1;

-- 2. "TERRY of Gorham" votes per person: expect all on Parnell Terry, 0 on Maureen Terry
SELECT p.name, s.identifier, count(*) FROM opencivicdata_personvote pv
JOIN opencivicdata_person p ON p.id=pv.voter_id JOIN opencivicdata_voteevent ve ON ve.id=pv.vote_event_id
JOIN opencivicdata_legislativesession s ON s.id=ve.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:me/government' AND pv.voter_name='TERRY of Gorham' GROUP BY 1,2;

-- 3. versions still named only by paper numbers: expect 0 (before 2,368)
SELECT count(*) FROM opencivicdata_billversion bv JOIN opencivicdata_bill b ON b.id=bv.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:me/government' AND bv.note ~ '^LD [0-9]+ [HS]P [0-9]+$';
```
* **`quality_check.py --structural me`** at core `0f3c24c9`: version stage under 5.5% (expect 0%), votes under 4.7% (expect 0%).
* **Fail** = any of these off. Stop and report.
* I check the same on the Mac replica and record it on OPEN-672.

## Not authorized
* M1 or M2 before its GO note.
* Any other state's people load or re-import.
* A second Maine re-import.
* A Maine recompute.
* Any manifest, schedule, routing or LegBot change.

Tickets: OPEN-672 (OPEN-146); fixes OPEN-811, OPEN-812; OPEN-810 rides along in v85.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
