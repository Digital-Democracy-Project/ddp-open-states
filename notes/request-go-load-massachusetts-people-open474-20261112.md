# Request (GO): load Massachusetts' legislators into production from the people fork (OPEN-474, OPEN-68). People load ONLY: no re-import, no scrape. 2026-11-12 about 21:00 UTC (Mac side)

**Ramon's words, 2026-11-12 (/onboard-state Massachusetts):** "Go, load it before Sunday (Recommended)". The question was whether to load the updated Massachusetts legislator list before Massachusetts' next run (Sunday 11-15 02:00 UTC), so that run matches every vote.

## What I need from you
1. Run the gates below; if any fails, stop and reply.
2. Run the load **once**, Massachusetts only, **with the ddp-sync container's `os-people`** (the tool your Alabama load used, `caba67f`), not the host venv's.
3. Reply `reply-massachusetts-people-loaded-open474-20261112.md` (or the date you run it).

## Why
OPEN-474: 24.1% of Massachusetts votes carry a name but no legislator. The scraper fix (openstates-scrapers #89) is in image **v57 / revision 60** (Ramon's `deploy-scrapers-image.sh`, about 20:55 UTC), so Sunday's run rewrites the names. Three House names also need the people data: people fork **#20** (merged `83a8126a`, now the fork's main) adds "Garcia" (Judith García) and "Gómez" (Homar Gomez), and Vanna Howard's House role has been on the fork's main since 10-21 but was never loaded. Without this load about 1% stays unmatched; with it, the author measured 0%. **No re-import is wanted:** Sunday's scrape imports with the names in place.

## Gates (read-only; stop and reply if any fails)
1. **Quiet:** no Massachusetts job and no people refresh running; no ddp-sync job in the last 10 minutes; not within 15 minutes of 02:00, 02:30, 03:00 or 04:00 UTC; done well before Sunday 11-15 01:30 UTC.
2. **Code:** bring the production people checkout to the fork's `main` and report `git rev-parse HEAD`. It must be `83a8126a` or a descendant. Show that `data/ma/legislature/` contains `- name: Garcia` (one `grep`).
3. **Baseline (RDS, read-only):**
```sql
WITH ma AS (SELECT DISTINCT p.id FROM opencivicdata_person p JOIN opencivicdata_membership m ON m.person_id=p.id
  JOIN opencivicdata_organization o ON o.id=m.organization_id JOIN opencivicdata_jurisdiction j ON j.id=o.jurisdiction_id
  WHERE j.name='Massachusetts')
SELECT (SELECT count(*) FROM ma) AS people,
       (SELECT count(*) FROM opencivicdata_personname WHERE person_id IN (SELECT id FROM ma)) AS alt_names,
       (SELECT count(*) FROM opencivicdata_personname pn WHERE pn.name IN ('Garcia','Gómez') AND pn.person_id IN (SELECT id FROM ma)) AS new_names,
       (SELECT count(*) FROM opencivicdata_membership m JOIN opencivicdata_person p ON p.id=m.person_id
          JOIN opencivicdata_organization o ON o.id=m.organization_id WHERE p.name ILIKE '%Vanna Howard%' AND o.classification='lower') AS howard_house;
```
   **Expected (Mac replica, 20:58 UTC):** `415 | 857 | 0 | 0`.

## The load
* `os-people to-database ma`, from the production people checkout, with the **ddp-sync container's `/opt/venv-openstates/bin/os-people`** and the same environment as the weekly refresh (as for Alabama). Record start and end (UTC) and the full summary it prints. A "went missing from source data, left in database unchanged" line is expected and fine.
* Then the baseline query again. **Expected:** `people` about 415 to 416 (Vanna Howard may be a new person or an existing one with a new role; report which); `alt_names` up by 2 or more; `new_names` 2; `howard_house` at least 1.

**Stop and reply, changing nothing more, if:** the load exits non-zero, `people` drops, `new_names` isn't 2, or anything outside Massachusetts changes (report the persons updated in the last 15 minutes by jurisdiction).

## Not authorized
* A Massachusetts re-import (`os-update ma --import`) or any scrape. Sunday's scheduled run does that.
* Any other state, or `os-people to-database` without a state, or `--purge`.
* LegBot, archive, search refresh, a restart, or any change to ddp-sync, the manifest, the broker or a task definition.

## What I check on the Mac side (not yours)
* The replica shows the new names and Vanna Howard's House role.
* After Sunday's run: `quality_check.py --structural ma` below 4.7%, and no stored Massachusetts voter names with "X " or "--" marks.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
