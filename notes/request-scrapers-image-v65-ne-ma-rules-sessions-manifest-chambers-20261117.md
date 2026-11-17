# REQUEST (waits on Ramon's go): scrapers image v65 (NE/MA action rules, session types, core vote/NC fixes), the OPEN-556 state list on both hosts, api-v3 at the new core; then OPEN-557's stored session fixes, and only after those, api-v3 #72. 2026-11-17 (Mac side)

**Not a GO yet.** Ramon builds v65 with `deploy-scrapers-image.sh`. The prod agent's part of each step starts only after a GO note naming it. Steps A to C can go together. Step D waits on step C's results. Step E is the only place api-v3 #72 may ship.

## What v65 carries (main since v64 = `ddp-scrapers:67`, core `71fd44d6`, scrapers `56fb5c064`)
The image is built from each fork's main at build time.
| Repo | Commit | Change | What anyone would notice |
|---|---|---|---|
| openstates-core | `dd22ea55` (#118, OPEN-603) | A vote carrying a voter id links only to exactly one person with that id; no surname fallback | Wrong-person links stop on new imports |
| openstates-core | `274bddbe` (#119, OPEN-594) | North Carolina amendment papers ("A1: …") are not bill versions | api-v3 stops serving them as full texts (after step B) |
| openstates-core | `86e365b2` (#120, OPEN-550) | Nebraska: `passage` only on "Passed on Final Reading" lines. **The bill importer now applies a state's own rule (`openstates/ddp_states/<state>.py`) to every imported action** | NE is not live: nothing published |
| openstates-core | `a4c59b07` + `8a403922` (#121, #122, OPEN-551) | Massachusetts: a budget's line-item veto message is not a veto; "Signed (in part)" is a signature | 2 stored lines (H 4240); MA publishes no scorecards yet |
| openstates-scrapers | `07d937c72` (#124, OPEN-557) | Every session in the session lists says regular or special: GA/OR/VA/WA had none; 6 upstream entries flipped (AZ ×2, FL, LA, NE, PA) | Each state's next import stores the type (step C). Nothing changes in api-v3 until step E |

* **No core database migration** since v64 (`git diff --name-only 71fd44d6 8a403922` shows none).
* Expected core: **`8a403922b4149f67e92b733ab568cafcf8be9ab6`**. If the image reports a later core, a core merge landed after this note: stop and report.
* **Stored NE/MA history is not relabelled** (no `os-text-extract relabel ne|ma`). That happens at each state's go-live, under the scorecard gate. Until then, new NE/MA imports write the new labels on the bills they touch, so stored labels are mixed. That is expected.

## Step A: the OPEN-556 state list on both hosts (any time; safe on its own)
ddp-open-states main at or after `27dfda01` (#410) adds a `chambers` block to every entry in `jurisdictions.yaml`. The api-v3 running today ignores it.
* EC2: `deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync` (it pulls, runs the drift check, then `deploy/sync-manifest.sh`). The Mac side does the same with `--host mac`.
* **Gate:** the drift check reports OK for 16 jurisdictions; `/ddp/enrollment` still answers 200 (old api-v3, new file).
* **Step A must be done on a host before step B rebuilds api-v3 there.** An api-v3 that includes api-v3 #71 (OPEN-556, merged by then or not) answers 503 on a state list without `chambers`, and the broker then loses its state list.

## Step B: v65, then api-v3 at core `8a403922` on both hosts
1. Ramon builds and registers v65. Register only when no scrape is running (ECS check), as for v64.
2. **Check:** the next task reports the new revision and image v65, and `DDP_CORE_COMMIT` is `8a403922…`.
3. **api-v3 on EC2,** after step A on EC2 (the RUNBOOK's api-v3 release, as for v64):
   * Tag the running image `ddp-openstates-api:pre-v65`.
   * Build with `docker-compose.rds.yml` and `DDP_CORE_SHA=8a403922b4149f67e92b733ab568cafcf8be9ab6`, then `up -d --no-deps api` only.
   * **Gate:** the build's import step passes; `/healthz` 200; `/ddp/enrollment` 200 (with a `chambers` block on every state if api-v3 #71 is merged); `check-core-pin-drift.py --image-core 8a403922b4149f67e92b733ab568cafcf8be9ab6 --container ddp-openstates-api-1` exits 0.
   * **Rollback:** retag `pre-v65` as `:local` and recreate `api` only.
4. **api-v3 #72 (OPEN-557) must NOT be in this build.** It is held open on purpose. If api-v3 main contains `fix/OPEN-557-stored-classification` at build time, stop and report.
5. The Mac api-v3 is rebuilt by the Mac side at the same core, after step A on the Mac. Same gate.

## Step C: OPEN-557, the stored session types (after v65 is live)
1. **The imports:** each affected state's next scheduled run on v65 stores its sessions' types; the importer updates every session in the state's list. That covers 82 rows: GA 14, OR 28, VA 28, WA 6, plus AZ ×2, FL, LA, NE and PA one each. No extra scrapes: the normal schedule is enough. Report each of ga, or, va, wa, az, fl, la, ne, pa once its first v65 run has finished.
2. **Virginia's one-row fix:** Virginia has two `2018specialI` rows. The importer updates only one, so this needs one guarded update on RDS, in a transaction, run **after** Virginia's first v65 run:
   ```sql
   begin;
   update opencivicdata_legislativesession set classification = 'special'
    where id in ('e29664cd-0923-4c99-b6ae-ace47e76d5a3', '9b394afc-c698-4640-9e1a-fbf164d066d1')
      and coalesce(classification, '') = '';
   -- expect UPDATE 1 (the import has set the other); UPDATE 2 if the import set neither, UPDATE 0 if both are set: report and commit any of these
   commit;
   ```
3. **The blank check** (read only, on RDS, after all nine states' first v65 runs and the VA fix):
   ```sql
   select j.id, s.identifier, s.classification from opencivicdata_legislativesession s
     join opencivicdata_jurisdiction j on j.id = s.jurisdiction_id
    where (j.id ~ 'state:(ga|or|va|wa)/' and coalesce(s.classification, '') = '')
       or (j.id ~ 'state:az/' and s.identifier in ('55th-2nd-regular', '51st-1st-special'))
       or (j.id ~ 'state:(fl|la|ne|pa)/' and s.identifier in ('2021A', '2023s1', '102S1', '2023-2024S1'));
   ```
   Expect exactly 6 rows: az `55th-2nd-regular` = `primary`; az `51st-1st-special`, fl `2021A`, la `2023s1`, ne `102S1` and pa `2023-2024S1` = `special`. Any GA/OR/VA/WA row in the result is a session still blank: report it and stop (it would get a per-row update request from the Mac side).
4. **What people see after step C** (read from api-v3's guess, which still runs): nothing changes except Pennsylvania, whose previous session becomes 2023-2024 instead of its special session.

## Step D (Mac side, not the prod agent): confirm on the replica, then ask for E
The Mac side re-runs the blank check on the replica and posts a GO for step E only if it returns the expected 6 rows.

## Step E: api-v3 #72 (OPEN-557), only after step D's GO
api-v3 #72 (`b6eceb47`) removes the guess: api-v3 serves each session's stored type. Ramon merges it after step D. Then rebuild api-v3 on both hosts as in step B (same gate, image tag `pre-open557`). Expected: Georgia's current sessions become 2025_26 and 2026_ss, and its previous session becomes 2023_24; every other state is unchanged. **Released before step C, it would make Virginia's current session 2023 and leave Oregon with no current session.**

## Not authorized
`os-text-extract relabel` for any state; any stored change other than step C.2; extra scrapes; any broker or ddp-sync change; any `.env` or IAM change; merging any PR.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
