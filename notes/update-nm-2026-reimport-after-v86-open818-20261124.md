# UPDATE (not a GO) to `0940569` / `4389222` / `85a8950`: add a **New Mexico 2026 full re-import on v86** (OPEN-818). 2026-11-24 (Mac side, Onboard New States)

**Not a GO.** It waits on Ramon's go, like every step. Everything else stands.

## Why
* New Mexico's Senate roll calls print two senators with a suffix ("POPE, JR.", "SHENDO, JR."). Their **218 votes** (all of NM's unmatched, 218 / 15,078) link to no one, so they're missing from Harold Pope's and Benny Shendo's scorecards (OPEN-618, after your 11-23 re-import `52a0750`).
* **OPEN-818, scrapers #262, merged as `09c8811d`:** drops a trailing generational suffix (JR, SR, II, III, IV) after a comma. No names in code, and House "Surname, Initials" names are untouched.
* **Not in v85** (`928138b2`); it goes in **v86** with OPEN-819.

## The step (after v86 is live and its core rollout to `59dbdaa2` is done, per `85a8950`)
### Gates
* New tasks run v86's revision or later.
* `ddp:pipeline_lock:nm` is empty.
* Not on Sunday from 02:00 UTC.
* One heavy load at a time: queue it after whichever `0940569` step-5 re-import is running.

### The run
```
POST /ddp-sync/v1/trigger/openstates-scrape/nm?full=true&sessions=2026
```
* The answer must be 202 with `"full": true`.
* Report the run id, revision, counts and archive result.

### Pass/fail (read-only)
```sql
-- 1. NM unmatched person votes: expect 0 (before 218)
SELECT pv.voter_name, count(*) FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent ve ON ve.id=pv.vote_event_id
JOIN opencivicdata_legislativesession s ON s.id=ve.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:nm/government' AND s.identifier='2026'
  AND pv.voter_id IS NULL GROUP BY 1 ORDER BY 2 DESC;

-- 2. no stored voter name still ending in a suffix: expect 0 rows
SELECT pv.voter_name, count(*) FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent ve ON ve.id=pv.vote_event_id
JOIN opencivicdata_legislativesession s ON s.id=ve.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:nm/government' AND s.identifier='2026'
  AND pv.voter_name ~* ',\s*(JR|SR|II|III|IV)\.?$' GROUP BY 1;
```
* `quality_check.py --structural nm` at core `59dbdaa2`: every gate passes, as before the re-import.
* **Fail** = any of these off. Stop and report.
* I check the same on the Mac replica and record it on OPEN-618.

## Not part of this
* New Mexico's go-live (ddp-open-states #480 stays held).
* LegBot, routing or schedule changes for NM.
* A second NM re-import.

Tickets: OPEN-618, OPEN-818 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
