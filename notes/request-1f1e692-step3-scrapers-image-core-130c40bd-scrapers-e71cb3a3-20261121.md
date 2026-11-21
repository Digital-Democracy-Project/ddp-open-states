# REQUEST (not a GO): step 3 of `1f1e692`: the next scrapers image, at core `130c40bd` and scrapers `e71cb3a3`. One decision for Ramon first (Florida). 2026-11-21 17:10 UTC (Mac side, State Specific Handling)

Answers `debec5b` (RDS is at `data.0052`; the image hold is lifted). **There is no release skill for scrapers images.** This note is written by hand, as every image request so far has been. The build is Ramon's, on the Mac: `bash ~/Developer/repos/ddp-open-states/deploy-scrapers-image.sh` (RUNBOOK "Deploying a Fargate image change"). Registering the revision is the cutover.

## Step 2 check 3d (the Mac replica after RDS got the column): streaming, but the structure check cannot run
* **The subscription is fine:**
  * the worker is running, with 0 apply errors and 0 sync errors;
  * the position moved from `17F/34000000` (16:41 UTC) to `17F/3C000688` (16:55 UTC), after RDS added the column at 16:50, so rows are still applied;
  * both sides have `ddp_relation_label`, all 47,585 rows NULL.
* **`sync-structure.sh --dry-run` did not run its comparison.** It stops with "root certificate file /root/.postgresql/root.crt does not exist" (exit 1, 0 changes).
  * **Cause:** the replica container was recreated at 14:35 UTC 11-21, when Colima was restarted (the Mac side asked; the user approved). The certificate the subscription uses was put back at `/tmp/rds-global-bundle.pem`, but the structure check uses the default path, which is still missing.
  * **Effect:** the 5-minute structure check has failed on every run since then (replica-check.log: 09:37 local, 14:37 UTC). Replication is not affected.
  * **Fix options (Ramon's call; nothing done):**
    * (a) on the Mac, copy the bundle inside the container to `/root/.postgresql/root.crt` (lost again on the next recreate);
    * (b) a small ddp-open-states PR so `sync-structure.sh` passes `sslrootcert=/tmp/rds-global-bundle.pem`, as the subscription does.
  * I did not connect to RDS myself to compare the columns by hand.

## What the image will contain (the build clones `main` of all three; these are today's heads)
| Repo | Head now | Since v74 (scrapers `ad33d76b`, core `83584c48`) |
|---|---|---|
| openstates-core | `130c40bdf313f68f13bb65703879249be1a8b31c` | **#135 (OPEN-640):** migration `data.0052`, the `ddp_relation_label` column, now on RDS and the Mac replica; `add_related_bill(label=)`. **#136 (OPEN-720):** `note_stage()` places a few more exact document names (US "Agreed to Senate", "Received in Senate", "Considered and Passed …", "Private Law"; Michigan "Adopted Resolution"). No migration. Stored stages change only through their own recompute, not here |
| openstates-scrapers | `e71cb3a3a43c70c1caf5e764fb148da71505fd33` | **#187 (OPEN-642): Florida writes its own related-bill links** (see the decision below). **Onboarding fixes for probing states (no scheduled scrapes):** ND #170 #171, ID #172, RI #173 #175, OK #176, KY #177, HI #178, MS #179 #180 #182 #183 #184, MT #181, MO #185 #186. Tests only: #174 (OPEN-725) |
| ddp-open-states | `8a24c169b48e134ae2b4bd24a55ccb68015cdda6` | manifest entries for 12 more states (#441, OPEN-146) and their chamber names (#442 #444 #445 #448); MS/MO Speaker fixes (#446 #449); docs (#436 #443 #447 #450); OPEN-712's tool (#438); AGENTS-250/251 (#439 #440). v74's own ddp-open-states commit is not recorded on this branch, so this list covers merges since 11-20 12:00 UTC |

**If any of the three heads has moved when Ramon builds,** the build log's first lines show the commits it cloned. Anything newer than this table needs its own look before registering.

## Decision for Ramon before building: Florida's links (OPEN-642)
* OPEN-642's acceptance says Florida's link changes reach scorecards only after Ramon approves the list (the scorecard gate), measured after a re-import.
* With #187 in this image, every Florida bill the scheduled runs re-scrape gets its links at once.
* **Measured on the dev broker copy:** Florida 2026, a session the scheduled runs still visit, holds **82 polled bills**, and 2026E/F hold 6 more. Older sessions (2023 to 2025, 201 polled bills) change only on a re-import.
* **Not measured:** how many of those bills the next runs re-scrape, and whether the broker would turn their new links into counted stand-ins before BROKER-540 and BROKER-548. That is the gate's own dry run.
* **Options:**
  1. **Build now, with Florida's scheduled scrape paused** until the dry run and Ramon's approval of the list. Recommended: it is the gate as written.
  2. Build now, Florida runs as scheduled, and the list is reviewed afterwards. New links may reach polled 2026 bills before approval.
  3. Revert #187 on scrapers main first, then build. It comes back after the gate.

## After registering (Ramon's Mac, or the PM session)
1. Post the tag, digest and task-definition revision here, as for v69.
2. **The drift check shows api-v3 and ddp-sync behind the image's core until step 4.** Expected; step 4's request is `request-1f1e692-step4-api-v3-ddp-sync-core-130c40bd-20261121.md`.
3. **Waiting on this image, each on its own GO:**
   * OPEN-659's release reports (`6c007d772`);
   * SYNC-181's US 118th/119th re-import (`ddf23c9`), after ddp-sync's rebuild in step 4;
   * OPEN-642's Florida re-import and gate.

## Not authorized
Registering while a scrape task runs; any recompute (OPEN-720's stored stages, OPEN-637); any re-import; anything on RDS.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
