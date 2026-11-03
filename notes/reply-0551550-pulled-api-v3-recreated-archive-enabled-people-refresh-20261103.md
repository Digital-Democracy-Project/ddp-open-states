# Reply (`7a94599`): ddp-open-states `0551550` pulled on the EC2 host and api-v3 recreated, 2026-11-03 20:56 UTC

**The operator approved it ("Yes, do it as written").** **Revision recorded before: `7853dbb2a978cbba60555eb8d475a8a7b5c2ad50`** (for recovery). **Revision now live: `055155052928cfe97430289ad83b93f1ecfd4b0b`.**

- **Gates (20:56 UTC):** 0 ECS tasks, 0 real `run-scrape` processes, no ddp-sync job in 10 minutes; far from 02:00, 02:30 and 03:00; the checkout was clean.
- **Main moved after your note: `main` is now `5ae528d`** (**#326** / OPEN-447, the validator rule and `advance-jurisdiction`, merged after your request). **I pulled exactly `0551550` as asked, not the newer commit**, so this host is **one merge behind `main`**; I will take #326 only if you ask.
- **The diff `7853dbb..0551550`:** exactly **two files: `jurisdictions.yaml` (6 lines) and `PRIMITIVES.md` (4 lines, the documentation-only #324 you mentioned)**. **Your note says "exactly `jurisdictions.yaml` and nothing else"; the extra file is the documentation change you described, so I went on and am telling you.** The 6 yaml lines: for `pa`, `ne` and `la`, `archive.enabled` false to true and `enrollment.people_refresh` false to true.
- **Release:** api log saved (`log-archive/api-v3-pre-archive-flags-20261103T2056Z.gz`); `git merge --ff-only` to `0551550`; **`up -d --no-deps --no-build --force-recreate api` at 20:56:31 UTC; healthy at 20:56:48 (about 17 s);** image unchanged (`5659b12c601a`, no rebuild). **ddp-sync, the broker and the database were not touched.**
- **Checks, each with its value:**
  - healthy; **host and container `jurisdictions.yaml` md5 equal (`ade8e7847d03…`)** (the container's was `351dd7e41e5d…` before).
  - **Inside the container, for `pa`, `ne` and `la` each:** `archive.enabled` **true**, `archive.scheduled` **false**, `enrollment.people_refresh` **true**, `status: scraping`, `cloud_path` **true**; `embedding`, `legbot_replica`, `replica_routing`, `search_refresh` and `qa_sweep` all **false**.
  - **`/ddp/enrollment`: 13 jurisdictions, new `manifest_mtime 2026-11-03T20:56:31.398421+00:00`.**
  - **Combined drift check (`check-jurisdiction-drift.py --ddp-sync-root /opt/ddp-sync`): `OK: every list compared agrees with jurisdictions.yaml (13 jurisdictions).`, exit 0.**
  - **Bills with the host's key: Pennsylvania 5,270, Nebraska 1,847, Louisiana 2,616, Massachusetts 11,872** (unchanged).
  - **The broker's routed list unchanged:** AZ FL MI NC US UT VA WA (fresh fetch, 13 jurisdictions in the manifest). **No traceback** in the api log; ddp-sync up 23 h, healthy.
- **Not done, as you said:** no ddp-sync restart (it reads the manifest by its modification time; the drift check agrees, so nothing to report), no archive trial, no scrape, no people load, no LegBot, embedding or routing change. **From Sunday the weekly people refresh will include `pa`, `ne` and `la`** (their people are already loaded: `db2e88b`).

**Rollback I hold:** `git -C /opt/ddp-open-states checkout --detach 7853dbb2a978cbba60555eb8d475a8a7b5c2ad50` then `up -d --no-deps --no-build --force-recreate api` (about 17 s); the image is unchanged, so nothing to re-tag.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
