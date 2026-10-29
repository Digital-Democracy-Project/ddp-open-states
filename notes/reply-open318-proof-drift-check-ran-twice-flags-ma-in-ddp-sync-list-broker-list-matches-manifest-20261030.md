# Reply (read-only) for OPEN-318 / OPEN-330: the drift check ran on 10-28 and 10-29 and flags one thing: MA is in ddp-sync's list but not in the manifest's replica_routing. The broker's list matches the manifest

Prod agent, Fri 2026-10-30 00:00 UTC. The operator said "Option A, run all four". Read-only: log reads, file and variable reads (by exact name; lists and counts only), the checker script on this host, nothing pulled, restarted, edited or posted. The drift script (417 lines) was read first: it only reads files and prints to stdout (no network, no Slack, no write). Output in `/home/bitnami/ops/open318-proof-20261029T2356Z/readonly.txt`.

## 1. The drift check's runs since the 10-28 00:43 restart (ddp-sync)
* **10-28 06:20:00 UTC: ran.** `jurisdiction_manifest_agrees manifest_mtime=2026-10-28T00:13:35.470006+00:00 mode=shadow`, then **`jurisdiction_drift_check: done alerted=True drift=1 env_lists_not_set_on_this_host=['LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST'] status=drift unverifiable=[]`**. So it **did post an alert** that day (I did not look at the Slack message). The saved log has no scheduler duration line for this run.
* **10-29 06:20:00 UTC: ran** (container restarted 10-29 01:03 for SYNC-132; `registered sync_time=06:20` logged at 01:03:34). The scheduler logged `Running job ...` at 06:20:00,000 and `executed successfully` at 06:20:00,003 (**about 3 ms**), and the app logged **`done alerted=False drift=1 env_lists_not_set_on_this_host=['LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST'] status=drift unverifiable=[]`**: the same drift, **no alert this time** (I did not find why; a repeat-suppression would fit but I did not check).
* No missed or skipped run and no error in either log. **The log does not print which list drifts**; item 3 and the script show it.

## 2. The manifest on this host
`GET /ddp/enrollment` 200, `manifest_mtime` **2026-10-28T00:13:35.470006+00:00**; the host file's mtime is the same instant (stat shows 00:13:35.470005935; same as on 10-28). Host checkout `/opt/ddp-open-states` **3b78732760**, clean (no pull since); api-v3 checkout `f9dde91`, api container started 10-28 02:04:53.

## 3. The lists next to the manifest
Manifest `replica_routing` (from `check-jurisdiction-drift.py --matrix`): **us, fl, wa, va, mi, ut, az, nc** (8; **MA, AL not**).
* **Broker `DDP_OPENSTATES_JURISDICTIONS`:** `.env` = **`MI,UT,US,VA,AZ,WA,FL,NC`**; the running **web, celery and celery-beat** containers print the same. **It equals the manifest's `replica_routing` exactly (8 of 8).** `DDP_ENROLLMENT_SOURCE`: **not set** in the container; the effective setting is **`'env'`** (the manifest only compared). **Broker build `fbae62ec`** (not `489c6578`); it **contains the manifest-reading code** (`a7e996b5` is an ancestor of HEAD; `ddpbroker/enrollment.py` present).
* **ddp-sync's effective `ddp_openstates_jurisdictions`** (the app's loaded settings): **`FL,WA,US,VA,MI,MA,UT,AZ,NC`** (9): the broker's eight **plus MA**. The script's own result for it: **`DRIFT enrollment.replica_routing: DDP_OPENSTATES_JURISDICTIONS on prod-ddp-sync ... in DDP_OPENSTATES_JURISDICTIONS on prod-ddp-sync but not in the manifest: ma`**, with nothing the other way. That is **one disagreement, matching `drift=1`; I believe it is the one the check flags** (the log itself does not name it).
* **What the manifest says for MA** (matrix row): live, secondary tier, archive yes, scheduled yes, people_refresh yes, search_refresh no, embedding no, cloud_path yes, api_smoke_test yes, qa_sweep yes, **replica_routing no**, **legbot_replica yes**. (The raw yaml uses lower-case keys; I did not dump its other fields.)
* `LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST` is **not set** in ddp-sync's environment nor in the broker's web container: that is the `env_lists_not_set_on_this_host` item (a list the check wanted to read and could not). I did not check any other host.

## 4. The exact line from OPEN-330's acceptance
```
/opt/ddp-open-states/.venv/bin/python check-jurisdiction-drift.py --live prod-broker:DDP_OPENSTATES_JURISDICTIONS=MI,UT,US,VA,AZ,WA,FL,NC
NOTE: ddp-sync was not checked (no --ddp-sync-root / DDP_SYNC_ROOT); only this repo's lists were.
OK: every list compared agrees with jurisdictions.yaml (10 jurisdictions, this repo only).
exit code: 0
```
It ran read-only (`git status` of the checkout stayed clean). **Extra, same script:** adding `--ddp-sync-root /opt/ddp-sync` and a second live value for ddp-sync gave exit **1** with exactly the single MA drift above; the ddp-sync yaml lists produced no other DRIFT line.

## So, for blocker 1 of pilot #2
Proof from production: the check runs and reports; the **broker's list agrees** with the manifest; the **one disagreement is MA in ddp-sync's effective list** (the manifest says MA is not in `replica_routing`). Whether MA belongs there, or should come out of ddp-sync's list, is a decision I have not been asked to make and did not touch.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
