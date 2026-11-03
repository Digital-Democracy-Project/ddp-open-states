# Reply (OPEN-482, `2c03655`): api-v3 `72e6d21` (the PA, NE, LA version-stage rules) is LIVE on the EC2 host, 2026-11-03 18:25 UTC

**The operator told me to do the release as written** (report first on any failed check). Production api-v3 was at `b3148ac` (OPEN-481).

- **Gates (18:24 UTC):** 0 ECS tasks, 0 real `run-scrape` processes, no ddp-sync job in 10 minutes; the nested checkout `/opt/ddp-open-states/api-v3` was clean at `b3148acb20`; `72e6d21` present, a fast-forward; the diff is exactly **`api/version_ordering.py` (+23) and `api/tests/test_bill_version_fields.py`**, and `OPEN-482` occurs once in the new file.
- **Before:** api log saved (`log-archive/api-v3-pre-open482-20261103T1824Z.gz`); the running image **`31d95356e4ba`** is tagged **`ddp-openstates-api:pre-open482` (the rollback)**.
- **Release:** `git merge --ff-only` to **`72e6d21f71`** (clean); `docker compose ... build api` finished in 2.4 s to the **new image `5659b12c601a`**; **`up -d --no-deps --no-build --force-recreate api` at 18:24:56 UTC, healthy at 18:25:12 (about 16 s).** Only `api` was recreated; the database, Redis, ddp-sync and the broker were not touched. **No `ensure`, bill-search refresh, `recompute-diff-order` or import was run.**
- **Checks, each with its value:**
  - **Image** `5659b12c601a` (not `31d95356e4ba`); **healthy**; **`grep -c OPEN-482 /app/api/version_ordering.py` in the container: 1**.
  - **`note_stage(n)[0]` inside the container:** `Printer's No. PN1422` **1**, `Slip Law` **4**, `Final Reading` **3**, `von Gillern AM1020` **1**, `HB519 Act 303` **4**, `Introduced` **0**, `Printer's No.` **99**: **all seven as you expected.**
  - **With the host's own key:** `/bills?jurisdiction=` **Pennsylvania 5,270, Nebraska 1,847, Louisiana 2,616, Massachusetts 11,872** (all unchanged).
  - **`/ddp/enrollment`:** **13 jurisdictions**, `manifest_mtime 2026-11-02T22:22:23.118963+00:00` (unchanged); **`pa`, `ne`, `la` each `status: scraping`, `cloud_path: true`.** (My first script printed an empty list for these three because it guessed the wrong key names; the manifest is keyed by code. I re-read it with the right keys.)
  - **The broker's routed list unchanged:** AZ FL MI NC US UT VA WA.
  - **`GET /people/<id>/votes`:** **200 with the key** (Jay Adams), **403 without one** (the key check).
  - **No `Traceback`** in the api log since the restart; 0 nginx 5xx on the broker in 4 minutes; ddp-sync up 20 h, healthy.
- **Not done, as you said:** no recompute, re-import, re-archive or backfill; no ddp-sync restart; no broker release; no change to any allowlist or routing. (The openstates-core change, PR #74, needs a scrapers-image rebuild only when the archive is switched on for these states; not touched.)

**Rollback I hold:** `docker tag ddp-openstates-api:pre-open482 ddp-openstates-api:local` then `up -d --no-deps --no-build --force-recreate api` (about 16 s); source back with `git -C /opt/ddp-open-states/api-v3 checkout --detach b3148acb20`.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
