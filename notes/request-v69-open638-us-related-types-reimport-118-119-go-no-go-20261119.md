# REQUEST (each part on Ramon's go): scrapers image v69 with OPEN-638, then a full re-import of the 118th and 119th Congresses, then the read-only go/no-go of PLAN-companion-lineage §4.2. 2026-11-19 (Mac side, State Specific Handling)

**Not a GO.** Ramon approved phase 1 of PLAN-companion-lineage v0.2 on 2026-11-19 ("Yes, phase 1 as planned"; OPEN-634 comment 21545). This is its step 1. Step 2, the broker (BROKER-548), waits until Part C passes.

## Why
* **Today:** the federal scraper stores every bill congress.gov lists as related as a `companion`. That includes House rules resolutions ("Procedurally related"), bills from other Congresses, and laws that absorbed a bill's text.
* **What it changes:** openstates-scrapers #134 (OPEN-638, merged `65815f3d`) reads congress.gov's own type. A link is `companion` **only when congress.gov calls it "Identical bill"**; every other link is stored as `related`.
* **New scrapes only:** stored links change only when a bill is re-imported, hence Part B.

## Part A: image v69 (Ramon builds it with `deploy-scrapers-image.sh`; then it is registered)
| Repo | v69 | Since v68 (rev 71: scrapers `dca8e7a6`, core `5c1455e1`) |
|---|---|---|
| openstates-scrapers | `65815f3df68a1e1d635e0cc8072b9d2319909847` | #134 only (OPEN-638): `scrapers/usa/bills.py` `scrape_related_bills` and its tests |
| openstates-core | `5c1455e1679bbdac8f00fe050d57c0152e17c648` | unchanged |

* **What doesn't change:**
  * No core change, so no migration, no api-v3 rebuild, and no ddp-sync rebuild for this step.
  * `related` is an existing OpenStates relation type.
* **Register only when no scrape task is running** (ECS check), as for v68.
* **If main has moved** by the build, the `update-` note names v69's scrapers and core commits.

## Part B: re-import the 118th and 119th Congresses (after A, on its own GO)
* **What:** one full walk of US **sessions 118 and 119**, both chambers, through the normal cloud path: Fargate collection on v69, then `cloud_loader.py` into RDS.
  * No `start=` cutoff, so every bill is scraped again and its links rewritten.
  * No other state.
  * **How to start it is your call**, as in `request-open397` (the NC re-run): ddp-sync's manual trigger if it accepts `us` with sessions and no cutoff, or `aws ecs run-task` plus the loader. If you need a code change to start it, report that instead of making it.
  * Expect hours: the Mac replica holds 19,315 bills for the 118th Congress and 20,004 for the 119th.
* **Gates:**
  * No `us` scrape, archive or text-extract is running, and none is scheduled to start during the run.
  * The Fargate task reports the v69 revision.
* **Report:** the run ids, the image revision, the loader's final status (no `DuplicateItemError`), and the bill and vote counts the loader reports.
* **Downstream, expected and harmless:**
  * The touched bills' `updated_at` moves, so the broker's next US sync re-reads them.
  * The broker **never deletes** a companion link it already holds, and since this step it adds only "Identical bill" links. So **no scorecard changes from Parts A and B.**
  * The 25 broker US links that predate this are reconciled in step 2 (BROKER-548), through the scorecard gate.
  * Report anything else the load starts (LegBot, artifacts, archive, embedding). Don't start or stop any.

## Part C: the go/no-go (read only, RDS and EC2 api-v3; report in a `reply-` note)
**Reference lists (this branch), built on the Mac on 2026-11-18** from congress.gov's own BILLSTATUS files for the polled US bills of the dev copy of the broker (268 polled bills with links, 1,110 links):
* `notes/open638-expected-companions-polled-us-20261118.csv`: the **99 links congress.gov calls "Identical bill"**. md5 `0468b2403216f8bb72e0f4c9b5f48a87`.
* `notes/open638-procedural-links-polled-us-20261118.csv`: the **114 "Procedurally related" links** without "Identical bill". md5 `5bcc251fd8043d26d2d2d740c1ab42ac`.

**C1. The broker's federal links are all within the re-imported Congresses** (production broker, read only):
```sql
SELECT s.code, count(*) FROM common_billrelation r
JOIN common_bill b ON b.id IN (r.from_bill_id, r.to_bill_id)
JOIN common_legislativesession s ON s.id = b.session_id
JOIN common_jurisdiction j ON j.id = s.jurisdiction_id
WHERE j.iso2 = 'US' GROUP BY 1;
```
* Expect only `118` and `119` (the dev copy shows only those).
* Any other Congress: report it; that Congress needs a re-import too, before step 2.

**C2. Federal link counts by Congress and type, before Part B and after** (RDS):
```sql
SELECT s.identifier, rb.relation_type, count(*) FROM opencivicdata_relatedbill rb
JOIN opencivicdata_bill b ON b.id = rb.bill_id
JOIN opencivicdata_legislativesession s ON s.id = b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id = s.jurisdiction_id
WHERE j.name = 'United States' GROUP BY 1, 2 ORDER BY 1, 2;
```
* **Before:** every federal link is `companion` (about 29,800 on the Mac replica).
* **After:** for 118 and 119, `companion` and `related` only, with `companion` a small share.
* Report the exact numbers.

**C3. Companion links on the polled bills equal the "Identical bill" list, exactly.**
* **The polled set:** the production broker's polled US bills (`voatz_id` set, `build_scorecard`).
* **The list:** each one's `companion` links on RDS (identifier and session of the related bill).
* **Compare with `open638-expected-companions-...csv`, row for row.** Expect the same 99.
* A bill polled on production but not in the Mac's list is reported on its own, with its links. It is not a failure.

**C4. No procedural companion is left.**
* For every row of `open638-procedural-links-...csv`, the stored link's `relation_type` is `related`.
* Expect 0 `companion`.

**C5. api-v3 serves the new types**, EC2 api-v3, `include=related_bills`:
* **118 HJRES 109:** SJRES 59 is `companion`; HRES 1194 (the rule) is `related`.
* **118 HR 8371:** S 141 is `related`. congress.gov calls it "Related bill". The broker's existing link stays until step 2.
* **119 HR 1:** all of its related bills are `related`.

**Stop rules:**
* Any C3 or C4 difference: stop and report the rows. BROKER-548 does not start.
* A failed load: report the log tail. No retry, no rollback without a GO.

## Rollback (only if Ramon asks)
* Deregister v69's task-definition revision; the next run uses v68.
* Stored links go back only by re-importing on v68.

## Not authorized
* Any other state.
* Any broker change or broker data change (BROKER-548 is separate).
* Extra scrapes beyond Part B.
* `--allow_duplicates`.
* Any S3 marker or working-tier edit.
* Starting or stopping LegBot, archive or embedding runs.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
