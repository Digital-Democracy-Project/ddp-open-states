# Request (GO): roll out the state list without the Voatz section (ddp-open-states `991c64f`) and move api-v3 to `94c0994` on EC2 (BROKER-494)

**Ramon, 2026-11-14 ~22:45 UTC: "request 3 too".** That is the go for this rollout on EC2.

**Why:** BROKER-494 takes the Voatz test labels out of the OpenStates state list and out of api-v3 (Ramon, 11-13: "api-v3 should only be serving up the ddp-open-states data"). The broker that reads the labels from its own records instead (36cdbda8, migration 0092) went **live at 21:56 UTC** per your checkpoint `c362d49a`. That release was the condition for this rollout. The two other halves were merged 11-13:
- ddp-open-states #365 (`a712730`): the `voatz` block leaves all 13 entries, and the validator rejects one;
- api-v3 #59 (`94c0994`): `/ddp/enrollment` stops serving `voatz`.

## What I need from you

### 0. Gates (stop and report if any fails)
- **G0, time:** start before **01:15 UTC Sunday 11-15** and finish before 01:30. The weekly batch starts 02:00. If you cannot start by 01:15, **hold** and post a note. Do not run it during Sunday's batch.
- **G1, code:** `/opt/ddp-open-states` at **`90e0db44`** (your 11-13 checkpoint) with `git status` clean; api-v3's checkout at **`5c123ef`**, clean.
- **G2, quiet:** no import, people, archive, scrape or LegBot line in the last 15 minutes, and 0 running scraper tasks.
- **G3, rollback points:** record both revisions; tag api-v3's running image `ddp-openstates-api:pre-94c0994`; record the md5 of the current `jurisdictions.yaml` in the checkout, in api-v3's copy and in the container.

### 1. State list: pull first, then the script
**Pull first. The script's dry run will fail on the old checker, by design.** I tested it on the Mac:
- `90e0db4`'s `validate_jurisdictions.py` against the incoming file says `13 problem(s)`, all `<state>.voatz: missing required field`. This is OPEN-532, the same limitation as 11-10 and 11-13 ("pull first, then validate").
- The incoming checker (`991c64f`) says `OK: 13 jurisdiction(s) valid`.

Steps:
1. `git -C /opt/ddp-open-states pull --ff-only origin main` → expect **`991c64f`**. The pull brings 8 files: the manifest, the validator and its tests, `new-jurisdiction`, the drift check, PRIMITIVES.
2. `validate_jurisdictions.py` → expect `OK: 13 jurisdiction(s) valid`.
3. `rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --state us`, as on 11-13 → expect exit 0, drift `OK ... (13 jurisdictions)`, and api-v3's copy synced. **Expected md5 of the new file: `b20f14c4430903f33f7eba549d533fd2`** (the checkout, the copy and inside the container all equal).

**The only change to the file:** the 13 `voatz:` blocks are removed (`test_precinct`: `FEDERAL-TEST` for US, `FLORIDA-TEST` for FL, null for the other 11), and the header comment is reworded. No `status`, `replica_routing`, `legbot_replica`, `cloud_path`, `archive.enabled` or timing changes. Please confirm that read-only, as you did on 11-13.

### 2. api-v3 to `94c0994`
`git merge --ff-only 94c0994`. It changes 2 files: `api/ddp_enrollment.py` and its test. Then build and `up -d --no-deps api` (**the `api` service only**), as you did for `5c123ef` on 11-13.

### 3. Checks (report each value)
- `/ddp/enrollment` 200, 13 states, **0 entries carry a `voatz` key**, `replica_routing` unchanged from before, `actions.newest_first` unchanged (true for US and NC only).
- `/bills?jurisdiction=pa&per_page=1` 200.
- ddp-sync log since the rollout: no `jurisdiction_manifest_unusable` and no `jurisdiction_manifest_disagrees`.
- The broker read in my ddp-broker-py note (`request-read-first-legbot-write-after-36cdbda8-20261115.md`, ask 4): test labels still US and FL.

**Rollback:** `git checkout --detach 90e0db44` in `/opt/ddp-open-states` then the script, and the api-v3 tag `pre-94c0994`. The live broker 36cdbda8 does not read the `voatz` block, so either state list is safe for it.

## Not authorized
- Any restart or pull of ddp-sync.
- The broker, a cache delete, Secrets Manager.
- Any scrape, archive, people load, recompute or task-definition change.
- Any other state's entry.
- The Mac. Its checkout and its api-v3 are mine; I do them after your reply.

## What I check on the Mac side afterwards
I pull the Mac's production checkout to `991c64f`, roll the state list out there, and move the Mac's api-v3 to `94c0994`, with the same checks. Then I close BROKER-494 if your broker read (the ddp-broker-py note) shows the test labels intact.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
