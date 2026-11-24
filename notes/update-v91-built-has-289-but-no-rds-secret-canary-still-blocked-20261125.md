# UPDATE (not a GO) to `9ad05ee`, `85ce7f0` and `d8df145`: **v91 is built and is the image Rhode Island was waiting for. It is NOT the database-login release: `ddp-scrapers-db:20` has no stored RDS secret, so the Arizona canary stays blocked.** 2026-11-25 ~00:05 UTC (Mac side, Onboard New States)

**Not a GO.** Please confirm each with Ramon in your session. Revisions come from him via the PM session (`ddp-scrapers:93`, `ddp-scrapers-db:20`); his build output said "RDS secret in ddp-scrapers: no" and "RDS secret in ddp-scrapers-db: no", because the `TASK_RDS_*` values were not set for this run.

## What I read on the Mac (the local copy of the image)
* **v91** = `ddp-scrapers@sha256:b1defacffb71…`. `DDP_CORE_COMMIT` = **`70146facdb8493d990415ee9deff19200c4e4777`** (unchanged). Scrapers main `261cae78`: Rhode Island's header-shape rule (#289) is in it, and so are #284 to #288 (checked by content).
* **`ddp-scrapers-db:20` carries both plain API keys forward** (the script copies entries, as predicted). Nothing new to do about that here (OPEN-880).

## What changes in the plan
1. **Rhode Island's full 2026 re-import can run now, once, on v91** (Ramon's go; `ebd7c94` held it for exactly this image):
   * `POST /ddp-sync/v1/trigger/openstates-scrape/ri?full=true&sessions=2026`, must answer 202 with `"full": true`; the task must run **revision 93 or later**.
   * **Pass (I read it on the replica):** Senate roll calls on HB 7127 **0 → 14** (12 amendments, 1 consideration 31-7, 1 passage 32-6); the three header-shape roll calls (S 2067 twice, the Senate vote on H 7165) labelled `passage` ("In Concurrence" for H 7165); passage events about **1,323** (Senate about 739), which is a **prediction from the offline model**, not read from the replica, so I judge a few either way, not an exact number; the other roll calls keep their key, bill, chamber and counts; unmatched person votes about as before.
   * Then (each its own dry run first): `recompute-diff-order ri` (expect none) and `relabel ri` (0 after the 11-24 commit; the re-import should keep it at 0).
2. **Oklahoma 2025+2026:** new launches now use the latest revision (**93**), so it runs on v91 after its current archive ends; report the revision (must be 92 or later, as before). It carries everything v90 had.
3. **WY, NE, UT** started on v90 (rev 92) and stay as they are.
4. **The Arizona canary: still blocked.** **Step 2 is still owed**, and it is **another build run**: main's `deploy-scrapers-image.sh` has no register-only mode, so the secret release is a **v92** build (same code) run with `TASK_RDS_SECRET_ARN`, `TASK_RDS_HOST`, `TASK_RDS_PORT=5432`, `TASK_RDS_DBNAME` set. Steps 3 (ddp-sync pull and restart, staged) and 4 (`#488`) wait for it and for the read-back of the new `ddp-scrapers-db` revision (names only). The OPEN-880 secrets cleanup (#490) rides **after** that release, as Ramon decided.
5. **Until the secret release, `ddp-scrapers-db:20` is safe to launch from:** it has no secret entries, so archive and load launches behave as before.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
