# Request: pull ddp-open-states `0551550` (archive.enabled and people_refresh for PA, NE, LA) on the EC2 host and recreate api-v3, 2026-11-03

**Ramon's go (this session): "pull and recreate api-v3 here, then ask the prod agent to do the same."** He merged ddp-open-states **#325** at 19:56 UTC (merge commit **`0551550`**). **The Mac is done** (pulled, api-v3 `api` recreated at 19:58 UTC, healthy, the container's `jurisdictions.yaml` shows the new values, `/ddp/enrollment` serves 13 jurisdictions, bill counts unchanged).

## What the pull brings (small)
**One file, `jurisdictions.yaml`, 6 lines:** for `pa`, `ne` and `la`, `archive.enabled` false to **true** and `enrollment.people_refresh` false to **true**. `archive.scheduled` stays **false** (so nothing is on a recurring archive schedule), and `embedding`, `legbot_replica`, `replica_routing`, `search_refresh` and `qa_sweep` stay **false**. Your host is at `2b71a9d`/`7853dbb` for this repo (reply `b0763ab`, then `1a3ca36`); this is two merges later (`#324` is documentation only). `git diff` between your revision and `0551550` should show exactly `jurisdictions.yaml` and nothing else; if it shows more, stop and tell me.

## What it changes in behaviour (checked in the code)
- **`run-archive.sh <st>` will now accept `pa`, `ne`, `la`** when run by hand (it reads `archive.enabled`). **Nothing runs by itself:** ddp-sync's recurring and after-scrape archive list comes from `archive.scheduled` (OPEN-418), which is still false. **Do not run any archive for these states from this note; the timed trial is a separate request.**
- **The weekly people refresh (Sundays, after the secondary scrapes) will now include `pa`, `ne`, `la`.** Their people are already loaded (your reply `db2e88b`); the refresh keeps them current.

## What I need
1. **Gates:** nothing in flight (no ECS task, no real `run-scrape` process, no ddp-sync job in the last 10 minutes), away from 02:00, 02:30 and 03:00 UTC. Record the host's current revision of this repo first.
2. **Pull** `/opt/ddp-open-states` to `0551550` (fast-forward) and read the diff as above.
3. **Recreate only the api-v3 `api` service** (`up -d --no-deps --no-build --force-recreate api`; the manifest is a single-file mount, so a pull is invisible until the container is recreated). No image rebuild is needed; do not touch ddp-sync, the broker or the database.
4. **Read-only checks, each with its value:**
   - the container is healthy; the host's and the container's `jurisdictions.yaml` md5 are equal;
   - inside the container, for `pa`, `ne`, `la`: `archive.enabled` **true**, `archive.scheduled` **false**, `enrollment.people_refresh` **true**, `status: scraping`, `cloud_path: true`;
   - `/ddp/enrollment` still shows **13** jurisdictions with a new `manifest_mtime`;
   - the combined drift check (`check-jurisdiction-drift.py --ddp-sync-root /opt/ddp-sync`) is **OK for 13 jurisdictions**, exit 0;
   - with the host's key: `/bills?jurisdiction=` Pennsylvania **5,270**, Nebraska **1,847**, Louisiana **2,616**, Massachusetts **11,872** (unchanged);
   - the broker's routed list is unchanged (`AZ FL MI NC US UT VA WA`); no traceback in the api log since the restart.
5. **Reply** with the revision now live, the time (UTC), the values read, and the rollback you hold (the previous revision and image).

## Not asked
- **No ddp-sync restart:** it reads the manifest by modification time and its own lists are unchanged by this merge. If the drift check says otherwise, report first.
- No archive trial, no scrape, no people load, no LegBot, embedding or routing change.
- **A second small ddp-open-states change (#326: a validator rule and a new `advance-jurisdiction` command, no runtime effect) is not merged yet.** You may be asked for one more pull of this repo later; this note does not wait for it.

**Next, when you have replied:** a separate request for the timed archive trial for `ne`, then `la`, then `pa`, one at a time (Ramon's go to follow).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
