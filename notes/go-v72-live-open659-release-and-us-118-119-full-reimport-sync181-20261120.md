# GO (Ramon, 2026-11-20): image v72 is live; GO for OPEN-659's release (`8f665b0` / `6c007d7`) and for the US 118/119 full re-import (`ddf23c9`)

Written 04:40 UTC 11-20 (Mac side, State Specific Handling).

**Ramon, 2026-11-20 (relayed by the PM session):** "please ask the relevant agent to relay this to prod along with my GO for the US re-import". This note is that relay.

## 1. Scrapers image v72 is live (Ramon built and registered it)
**Read on the Mac at 04:38 UTC** (`describe-task-definition`, `describe-images`):

| Definition | Image | Execution role | Task role | Secret | Registered |
|---|---|---|---|---|---|
| `ddp-scrapers:75` | `ddp-scrapers:v72` | `ddp-scraper-ecs-execution-role` | `ddp-scraper-task-role` | none | 04:25:48 UTC |
| `ddp-scrapers-db:2` | `ddp-scrapers:v72` | `ddp-scraper-db-execution-role` | `ddp-scraper-task-role` | none | 04:38:46 UTC |

- `ddp-scrapers-db:2` is `ddp-scrapers-db:1` with only the image changed: the same roles and no secret.
- v72 digest is `sha256:41834d64…`.

**Built from (Ramon):**
- ddp-open-states `8977ced`, which contains SYNC-181's `8977cedf` (checked here);
- scrapers fork `8e0ab3dc3`;
- core `10f32ce0`, unchanged.

**`v73` was pushed but is not used. Do not register it.**

The scrapers fork `8e0ab3dc3` contains both OPEN-659 merges: `23968383` (#135) and `8e0ab3dc` (#136), checked with `merge-base --is-ancestor`. That is the gate of `8f665b0` step 1, met here.

**One consequence for your IAM proof:** the archive retries now launch from `ddp-scrapers-db:2`, the family's newest revision, not `:1`. Ramon's IAM grant covers `ddp-scrapers-db:*`, so the same proof applies: the task reaches RUNNING and exits 0.

## 2. GO: OPEN-659's release (`8f665b0`, updated by `6c007d7`)
- The release is v72, already registered by Ramon. There is nothing to register on your side.
- **Your part, as listed there:**
  - the gate: confirm the image's scrapers commit contains both merges, if you can read it from a task's environment or log;
  - then the **Nevada report** after its next scheduled run: the sessions scraped (expect `84` and `2025Special36`), the count of `84` bills (about 190, not 0), and that the load and archive finished;
  - the **Florida report**: the 2027 row's dates, expected `2027-03-02` to `2027-04-30`. If they did not update, report it and do not edit the row by hand.
- "Not authorized" there stands: no manual Nevada run, no other state, no data edit.

## 3. GO: the US 118/119 full re-import (`ddf23c9`), in its order
1. **Step 1 (the image) is done:** v72 is built from ddp-open-states `8977ced`, which contains `8977cedf`. **I confirm the image.** You wrote that the user pre-approved the ddp-sync rebuild "when the dev confirms the image". This is that confirmation.
2. **Step 2: ddp-sync on EC2 at `becbceb8` or later.**
   - Use the same core `DDP_CORE_SHA=10f32ce08088e544e88d54ec64aa325aea80756f`.
   - Tag the running image `ddp-sync:pre-sync181` first.
   - `up -d --no-deps ddp-sync`.
   - **Checks:** as listed in `ddf23c9` step 2, including the 400 for `sessions=118%3Bx` with the `us` lock unchanged.
   - **Only when nothing is running in ddp-sync. That includes the archive retries waiting inside it** (section 4): restarting ddp-sync drops a pipeline that is waiting for its next archive attempt.
3. **Step 3: the re-import.** Start it at the first idle gap after step 2, with the trigger, gates, expected alerts, report, stop rule and Part C exactly as in `ddf23c9`.
   - **The gate `GET ddp:pipeline_lock:us` is empty** also covers the `us` archive retry below. Do not start while it holds the lock.

## 4. Still open: the archive IAM proof (your `cbc37b3`)
- **Not read yet:**
  - **wa** attempt 3, about 05:05 UTC;
  - **us** attempt 3, about 05:39 UTC.
- **Do not start the ddp-sync rebuild (3.2) or the re-import (3.3) while either pipeline is still waiting for or running its archive.**
- Please report the two results as you planned: definition and revision, RUNNING, exit code. If the third attempt fails again, report the new error and do not go ahead with section 3. Section 2 does not depend on it.

## Not in this GO
- Registering `v73`.
- api-v3 #72 (OPEN-557): your `a2b4903` read-back is noted; I confirm it on the Mac replica separately before Ramon merges it.
- BROKER-560 (waits for #780).
- Any `.env`, `sync_schedule.yaml` or IAM change.
- Any other state.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
