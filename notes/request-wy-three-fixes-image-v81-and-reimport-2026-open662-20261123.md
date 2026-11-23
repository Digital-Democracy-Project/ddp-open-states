# REQUEST (not a GO): Wyoming's three scraper fixes. (1) They ride the next image after v80 (v81, notes `21d55d4`/`86a8109`): build at scrapers main **`d8e1bf5d`** or later. (2) Then ONE full re-import of Wyoming 2026. 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Ramon builds the image (`deploy-scrapers-image.sh`). The re-import (part 2) is the prod agent's, after a GO note from Ramon. This is an UPDATE to the v81 request `21d55d4` / `86a8109` (State Specific Handling); everything in those stands.

## Why
Wyoming's first scrape (`wy-d64df4852faf`, rev 81, ddp-sync notes `6ea7c43`) loaded 335 bills and 1,254 roll calls. The read-only check on the Mac replica (OPEN-662) found three scraper defects:

| Merge on scrapers main | Ticket | What it fixes | Measured offline over all of 2026 |
|---|---|---|---|
| #230 `d7d9b1b5` | OPEN-780 | **actions stored newest first** on all 335 bills | backward date steps 2,214 → **0**; roll calls unchanged |
| #231 `b0dcab9a` | OPEN-778 | two Senate "Recalled from Committee Pursuant to Senate Rule 5-5" roll calls (SF 50, SF 56) stored as House votes, so 62 votes match no one | exactly **2** roll calls change chamber; all 31 senators on them resolve |
| #232 `d8e1bf5d` | OPEN-782 | "Larson, JT" split into two voters, so **J.T. Larson counted twice on 498 roll calls** | roll calls with a double count 498 → **0**; every roll call's voters equal its tally |

* All three are reviewed and merged by the PM session.
* Each edits a different function of `scrapers/wy/bills.py`. A trial merge of all three passed the full suite (3,667) and kept every effect.
* **No migration, no new setting, no core change** (core stays `42b48982`). So there is no api-v3 or ddp-sync step.

## Part 1: the image (Ramon)
* Build v81 at scrapers main **`d8e1bf5d74…` or later**. That is `414311c6` (Utah, OPEN-775) plus the three Wyoming merges; nothing else is on main between them.
* **Mac side** checks the image's scrapers tree contains `d8e1bf5d` and that `DDP_CORE_COMMIT` is `42b48982`.
* **Prod side:** please report the image tag and task-definition revision. I'll call it **rev R** below.
* **If OPEN-781** (Idaho acting senators, being built) merges before the build, it can ride too. Its own request follows.

## Part 2: the Wyoming 2026 re-import (prod agent, on a GO note)
Wyoming's weekly runs are incremental: unchanged bills would keep their old actions and voters. So this needs SYNC-181's full re-import, as for Washington (`f179ccc`).

### Gates (stop and report if one fails)
1. **New tasks run rev R or later** (the image holding `d8e1bf5d`).
2. **Nothing Wyoming is running:** no `wy` collection, load, archive or text-extract task, and `ddp:pipeline_lock:wy` empty.
3. **Not on Sunday from 02:00 UTC** (WY's weekly start).

### The run
```
POST /ddp-sync/v1/trigger/openstates-scrape/wy?full=true&sessions=2026
```
* The answer must be **202**, with `"full": true` and the session echoed. A 409: wait; don't force.
* **Report:**
    * the run id and revision;
    * the collection's `"mode": "full"`;
    * the load's final status with bill and vote counts (expect 335 bills, about 1,254 roll calls);
    * the archive result.
* A load stopped by "already imported as ..." means stop and report the full message.

### Go/no-go after (read-only, on RDS)
```sql
-- 1. backward action steps (expect 0; before: 2,214)
WITH a AS (SELECT a.bill_id, left(a.date,10) d, lag(left(a.date,10)) OVER (PARTITION BY a.bill_id ORDER BY a."order") pd
  FROM opencivicdata_billaction a JOIN opencivicdata_bill b ON b.id=a.bill_id
  JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
  WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:wy/government' AND s.identifier='2026')
SELECT count(*) FILTER (WHERE pd > d) FROM a;
-- 2. unmatched person votes (expect 0; before: 62)
SELECT count(*) FILTER (WHERE pv.voter_id IS NULL), count(*) FROM opencivicdata_personvote pv
  JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
  WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:wy/government' AND s.identifier='2026';
-- 3. roll calls where one person has two votes (expect 0; before: 498)
SELECT count(*) FROM (SELECT pv.vote_event_id, pv.voter_id FROM opencivicdata_personvote pv
  JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
  WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:wy/government' AND pv.voter_id IS NOT NULL
  GROUP BY 1,2 HAVING count(*) > 1) x;
```
* Report each number, plus the chamber of SF 50's and SF 56's 2026-02-19 roll calls (expect `upper`).
* **I check the same on the Mac replica** once it catches up. Then I post `reply-verified-wy-reimport-<date>.md` and record it on OPEN-662.

## Things to know
* **Scorecards:** Wyoming isn't live; its routing and LegBot are off. The double count and the missing senators don't reach any scorecard today, and the re-import corrects them before go-live.
* **LegBot hand-off:** WY's `legbot_replica` is false. The Mac refuses the hand-off (`legbot_replica_off`, as on 11-23), and EC2 skips it once SYNC-186 is live there.

## Not authorized
* The re-import before its GO note.
* Any other state or session.
* A recompute or relabel.
* The OPEN-541 `reverse-action-order` pass: the full re-import replaces it for Wyoming.
* Any manifest, schedule, routing or LegBot change.
* A second re-import.

Tickets: OPEN-662 (OPEN-146); fixes OPEN-778, OPEN-780, OPEN-782.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
