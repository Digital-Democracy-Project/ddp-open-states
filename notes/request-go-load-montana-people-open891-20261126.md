# Request (GO): load Montana's legislators into production from the people fork (OPEN-891). People load ONLY: no re-import, no scrape. 2026-11-26 (Mac side, State Specific Handling)

**Ramon's words, 2026-11-26 (pop-up in the PM session, ticket OPEN-891 comment 23600):** run the Montana people load now, not on Sunday's refresh. Give the go in your session.

## What I need from you
1. Run the gates below. If one fails, stop and reply.
2. Run the Montana people load **once**: `--safe` first, post its output, then the real load.
3. Reply `reply-montana-people-loaded-open891-20261126.md` (or with the date you run it) with the outputs and the numbers below.

## Why
Montana's roster page printed a resignation note after a House member's name, and the Open States people data took the whole text as a second person: "Doug Flament Resigned From Hd29 On 2023-01-10 And Replaced By Ed Butcher" (`ocd-person/2c6a890f-c0f4-45e7-aba5-d516f55173f8`), next to the real record "Doug Flament" (`ocd-person/2e12034d-e190-440a-ba07-322865a5320d`). The junk person shows in the website's Explore list.

People fork PR #55 (merged `02d992fd`, the fork's `main`): deletes the junk person's file and adds its id to the real record as an `openstates` `other_identifiers` entry. **What the load does with that (read from the loader's code, not run here):** the entry makes the loader **merge** the junk person into the real one: it repoints the junk person's sponsorships and votes to the real Doug Flament, then deletes the junk person. Deleting the file alone would have left the junk person in the database; this is why the entry is there.

## Gates (read-only; stop and reply if one fails)
1. **Quiet:** no `os-people` run and no Montana job running (no Montana scrape, import, or load; `GET ddp:pipeline_lock:mt` empty if it exists). The load touches Montana's people only.
2. **Code:** bring the production people checkout (the fork) to the fork's `main`. Report `git rev-parse HEAD`; it must be **`02d992fd`** or a descendant. Then show the two facts the load depends on, one command each:
   * `ls data/mt/retired | grep -c Resigned` prints **0** (the junk file is gone);
   * `grep -A2 other_identifiers data/mt/retired/Doug-Flament-2e12034d-*.yml` shows `identifier: ocd-person/2c6a890f-c0f4-45e7-aba5-d516f55173f8`.
3. **What else changed in Montana's data since the last Montana load:** `git log --oneline -- data/mt` on the checkout since the commit the last Montana load used (the weekly refresh of Sunday 11-22 is the last I know). The Mac side sees only #55's commit (`1ec603f41c`) in `data/mt` after 2026-11-05. **Post the list**: if anything else touched `data/mt`, the load will update those people too; say so before running.
4. **Baseline (RDS, read-only):**
```sql
SELECT p.id, p.name,
  (SELECT count(*) FROM opencivicdata_billsponsorship s WHERE s.person_id = p.id) AS sponsorships,
  (SELECT count(*) FROM opencivicdata_personvote v WHERE v.voter_id = p.id) AS votes
FROM opencivicdata_person p
WHERE p.id IN ('ocd-person/2c6a890f-c0f4-45e7-aba5-d516f55173f8','ocd-person/2e12034d-e190-440a-ba07-322865a5320d');
SELECT count(DISTINCT p.id) AS montana_people FROM opencivicdata_person p
  JOIN opencivicdata_membership m ON m.person_id = p.id
  JOIN opencivicdata_organization o ON o.id = m.organization_id
  JOIN opencivicdata_jurisdiction j ON j.id = o.jurisdiction_id WHERE j.name = 'Montana';
```
   If Montana's data on RDS does not hold the junk person at all (it may not have been loaded since it was added), say so and **stop**: there is then nothing to merge. Post the three numbers (junk and real sponsorships and votes; Montana people count). The Mac replica has no Montana, so I cannot give expected values: this baseline is the reference.

## The load
* `os-people to-database mt` with the container's `/opt/venv-openstates/bin/os-people`, as for Maine (`update-add-maine-to-v85...`, step M1): **`--safe` first**, post the summary it prints, then the real load.
* **Expected from `--safe`:** mt created **0**; the real Doug Flament updated; the junk person reported as merged into him (or removed through the merge), with **no "went missing" or retirement line for anyone else.** The updated count is the real record plus anything gate 3 listed.
* **Stop and reply, changing nothing more, if:**
  * the load errors or exits non-zero;
  * `created` is more than 0;
  * the summary shows the junk person as "missing" or retired and **not** as merged (the merge did not trigger);
  * another person is updated or retired that gate 3 did not list;
  * anything touches a state other than Montana.

## Check after (read-only; post the numbers)
* The same baseline query again. **Expected:** the junk person's row is **gone**; the real Doug Flament has sponsorships and votes equal to the sum of the two before; Montana's people count is the baseline **minus 1**.
* `os-people to-database mt --safe` run again plans **no change** for Montana (created 0, updated 0).

## Not authorized
* A Montana re-import or any scrape; any other state; `os-people to-database` without a state.
* LegBot, archive, search refresh, a restart, or any change to ddp-sync, the manifest, the broker or a task definition.

## What I check on the Mac side (not yours)
* The junk record is gone from the website's Explore list and `/api/search` (after the broker's next Montana people sync, which I do not control; I read it from the broker's list through the sanctioned route).
* OPEN-891 stays In Review until your reply and that check. The scrapers image for fork PR #294 (v96) is a separate step.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
