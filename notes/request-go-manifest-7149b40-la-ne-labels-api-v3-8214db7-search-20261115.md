# Request (GO): roll out the state list `7149b40` (Louisiana and Nebraska labelled newest first, OPEN-562) and move api-v3 to `8214db7` (search uses the bill page's document, OPEN-533) on EC2, tonight before 02:00 UTC. The search rebuild in part 3 HOLDS for its own go.

**Ramon's go, 2026-11-15 (/ask-me):**
- **OPEN-562: "Fix the labels now".** The option he picked said "one state-list release now". PR #370 is merged.
- **OPEN-533: "Switch all states".** PR api-v3 #60 is merged.
- **Later, 22:10 UTC: "i want us to clear up all the data quality items for each of these states so we can be confident they are ready at launch".**
- The **search rebuild** (part 3) was described to him as "on your go" and has **no go yet**.

**Why:**
- **Labels:** Louisiana and Nebraska store each bill's history newest first, but the list labels them oldest first, so the broker reads their stages backwards. Mac replica, 11-15: LA 2,590 of 2,616 bills newest first and NE 1,845 of 1,847, with 0 oldest first. The new file labels `newest_first: true` for **la, nc, ne, us** (was nc, us). Nothing else in the file changes.
- **api-v3:** search now indexes the same document the bill page shows (XML, then OpenDocument, then PDF). Today Pennsylvania's search matches struck-out words in the PDF (HB 2625 for "precondition"). Deploying changes nothing in search until a bill is re-indexed (part 3, or each state's routine refresh after its scrape).

## What I need from you

### 0. Gates (stop and report if any fails)
- **G0, time:** start after your ddp-sync release `8a65f1e` (done) and finish by **02:00 UTC Monday 11-16**. The nightlies are wa 02:30, usa 03:00 and pa 04:00. If you can't, **hold** and post a note.
- **G1, code:** `/opt/ddp-open-states` at **`991c64f`** (your `a49a34e`) with `git status` clean; api-v3's checkout at **`94c0994`**, clean.
- **G2, quiet:** no scrape, import, archive, LegBot or search-refresh line in the last 10 minutes, and 0 running `ddp-scrapers` tasks.
- **G3, rollback points:** record both revisions. Tag api-v3's running image `ddp-openstates-api:pre-8214db7`. Record the md5 of `jurisdictions.yaml` in the checkout, in api-v3's copy and in the container (expected `b20f14c4430903f33f7eba549d533fd2`, from 11-14).

### 1. State list: the script, as on 11-14
1. `git -C /opt/ddp-open-states merge --ff-only origin/main`, expected **`7149b40`**. It brings 7 files: the list, its validator test, `deploy/rollout-manifest.sh` (OPEN-532: the dry run now uses the incoming checkers), its test, PRIMITIVES, RUNBOOK and a CI workflow.
2. `deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --state la`. Expect exit 0, drift `OK ... (13 jurisdictions)`, and api-v3's copy synced. **Expected md5 of the new file: `3502890e65d50db0172be9b880dca5f1`**, equal in the checkout, the copy and the container.
3. **Please confirm read-only:** the only data change in the file is `actions.newest_first: false → true` for `ne` and `la`, plus two comments.

### 2. api-v3 to `8214db7`
`git merge --ff-only 8214db7` changes 4 files: `api/document_choice.py` (new), `api/bills.py`, `api/search_projection.py` and their test. No new columns, so no `ensure`. Build, then `up -d --no-deps api` (**the `api` service only**), as on 11-14.

### 2b. Checks (report each)
- `/ddp/enrollment`: 200, 13 states, `actions.newest_first` **true for exactly us, nc, la and ne**, 0 `voatz` keys, `replica_routing` unchanged.
- `/bills?jurisdiction=pa&per_page=1`: 200. One bill page, any PA bill with versions: 200.
- One search call, any state: 200.
- The ddp-sync log since the rollout: no `jurisdiction_manifest_unusable` and no `jurisdiction_manifest_disagrees`.

### 3. HOLDS for a go note: search rebuild
Do **not** run this until a `go-` note from Ramon is on this branch:
`docker exec ddp-openstates-api-1 python -m api.search_projection refresh --full --jurisdiction <x>` for us, pa, ut, va, az and mi.

**Rollback:**
- state list: `git checkout --detach 991c64f` in `/opt/ddp-open-states`, then the script;
- api-v3: the tag `pre-8214db7`.

## Not authorized
- The search rebuild (part 3) without its go.
- Any restart or pull of ddp-sync; the broker; a cache delete; Secrets Manager.
- Any scrape, archive, people load, recompute, `reverse-action-order` or task-definition change.
- Any other state's entry.
- The Mac. Its checkout and its api-v3 are mine.

## What I check on the Mac side afterwards
- I roll the same list out on the Mac and move the Mac's api-v3 to `8214db7`, with the same checks.
- Then `validate_bill_stages --jurisdictions ne,la` on the replica. Nebraska's "failed, then moved on" should fall from 988 to a handful.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
