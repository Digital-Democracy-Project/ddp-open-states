# Request (GO): load Alabama's legislators into production from the people fork (OPEN-526). People load ONLY: no re-import, no scrape. 2026-11-12 about 02:10 UTC (Mac side)

**Ramon's words, 2026-11-12 (/ask-me):** "load it now". The question was whether to load the updated Alabama legislator list into production before Sunday's first Alabama scrape (11-15 02:00 UTC), so that the scrape's import attaches the 134 Alabama sponsors who currently have no legislator.

## What I need from you
1. Run the gates below. If any gate fails, stop and reply.
2. Run the load **once**, for Alabama only.
3. Reply `reply-alabama-people-loaded-open526-20261112.md` (or with the date you run it).

## Why
134 of Alabama's 1,507 2026rs person sponsorships have no legislator. They are written in ALISON's "Surname (Initial)" form, which the people data lacked for 12 sitting legislators. People fork PR #19 (merged `c78cad65`, which is still the fork's main) adds those 12 alternate names, data only. Nothing in production has them yet. On the Mac replica, 0 of the 12 exist in `opencivicdata_personname`.

Sunday's scrape does **not** load people first (the weekly people refresh runs after the Sunday scrapes), so the load has to happen now. **No re-import is wanted:** Sunday's scrape imports Alabama with the new names in place.

The 12 names: Coleman (M), Hall (L), Baker (A), Hill (J), McClammy (P), Jones (A), Hammett (M), Robertson (C), Butler (T), Price (R), Smith (I), Whorton (R).

## Gates (read-only; stop and reply if any fails)
1. **Quiet:** no Alabama job and no people refresh running; no ddp-sync job in the last 10 minutes. Not within 15 minutes of 02:00, 02:30, 03:00 or 04:00 UTC (Pennsylvania's nightly starts at 04:00; the load does not touch Pennsylvania, but keep clear of the start). Any time before **Sunday 11-15 01:30 UTC** is fine.
2. **Code:** bring the production people checkout (the fork, switched on 10-14) to the fork's `main`. Report `git rev-parse HEAD`; it must be `c78cad65` or a descendant. Show that `data/al/legislature/` contains `Coleman (M)` and `Whorton (R)` (one `grep` each).
3. **Baseline (RDS, read-only):**
```sql
WITH al AS (SELECT DISTINCT p.id FROM opencivicdata_person p
  JOIN opencivicdata_membership m ON m.person_id=p.id JOIN opencivicdata_organization o ON o.id=m.organization_id
  JOIN opencivicdata_jurisdiction j ON j.id=o.jurisdiction_id WHERE j.name='Alabama')
SELECT (SELECT count(*) FROM al) AS people,
       (SELECT count(*) FROM opencivicdata_personname WHERE person_id IN (SELECT id FROM al)) AS alt_names,
       (SELECT count(*) FROM opencivicdata_personname WHERE name IN ('Coleman (M)','Hall (L)','Baker (A)','Hill (J)','McClammy (P)','Jones (A)','Hammett (M)','Robertson (C)','Butler (T)','Price (R)','Smith (I)','Whorton (R)')) AS new_names;
```
   **Expected (Mac replica, 02:05 UTC):** `285 | 442 | 0`.

## The load
* `os-people to-database al`, the same command and environment as Pennsylvania, Nebraska and Louisiana on 11-03. Record start and end (UTC) and the full summary it prints.
* Then the baseline query again. **Expected:** `people` 285 (unchanged), `alt_names` about 454 (+12), `new_names` 12.

**Stop and reply, changing nothing more:**
* the load errors or exits non-zero;
* `people` changes;
* `new_names` is not 12;
* anything touches a state other than Alabama.

## Not authorized
* An Alabama re-import (`os-update al --import`) or any scrape. Sunday's scheduled run does that.
* Any other state, or `os-people to-database` without a state.
* LegBot, archive, search refresh, a restart, or any change to ddp-sync, the manifest, the broker or a task definition.

## What I check on the Mac side (not yours)
* The replica shows the 12 names.
* After Sunday's scrape, Alabama 2026rs sponsorships with no person are 0 (now 134). OPEN-526 closes on that.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
