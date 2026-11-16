# Status: v61 GO (`e4a007aa`, update `60ab73ec`): Alabama launched on revision 64 (fix confirmed), Virginia and Arizona committed, Virginia people loaded; Washington and NC refresh dry runs running. 17:47 UTC (prod agent)

**The user's words in session (pop-up):** **"Yes, all five, each only if its gate passes"**, and for the ddp-sync release, **"we actually have 2 more ddp-sync fixes, so i need you to pull from main and reload ddp-sync"** (`844a932`, ddp-sync `ce459b4` live). Step 6 (api-v3 pin) is skipped as your update says. Tools: **core `bcde78e2ce977e1783a77484a2d78344404a5f5e`** (v61's) in a throwaway worktree on `PYTHONPATH`, **host venv Python 3.9.2**; exports and change lists in `/home/bitnami/ops/step-v61-20261116/`.

## 1. Alabama: the run is live and the `start` bug is fixed
- **Launched once, no retry: 17:29:39 UTC, `202 {"status":"started","target":"al"}`, run `al-64ad5ca73ed4`, task `1e25b708453a4d98af2461a2f94d7f1c`, task definition `ddp-scrapers:64` read from ECS (your gate).** Before-counts: **2,550 vote events, 1,507 bills.** Gates: 0 running tasks; Alabama's three S3 locks released; no pipeline starting. **One departure from a literal reading of your window rule: my check saw one ddp-sync line for al in the last 10 minutes; it was the start-up registration line from the ddp-sync restart two minutes earlier (`registered day=sunday ... start_utc=02:00`), not activity, so I launched.**
- **The scrape log (CloudWatch, 17:30:20):** `al (scrape)`, **`bills: {}`** (no `start`), then the normal `Scraping B offset 0 limit 50`, `save vote_event ...`: it is past the exact point where `al-2086d764108a` died, and walking in full. I have not yet seen its end: **the "mode: full", `status=completed failed=0` and the archive are still to come**, and **section B and the search rebuild wait for them.**

## 2. Virginia, then Arizona (OPEN-578): both COMMITTED
- **va:** export first (25,607 rows, 154,864,337 bytes, md5 `5bb5c74f74ba8d3b5c971e1c28b98653`). Dry run 17:31:03-17:35:19: **`4413 bills checked | unchanged=24778 corrected=829 nulled=0`**, `is_bill_version: set=0 changed=0 not_a_version=1828`, `diff_baseline_id: set=14927 changed=0 cleared=0`, change list 14,927 documents. **Gate met** (0 errors; `nulled=0`; `corrected` inside 800-860; the Mac's 829). Commit `--commit --list` 17:35:34-17:40:13, exit 0, same numbers. **Second dry run: `corrected=0 nulled=0`, baseline `set=0`.**
- **az:** export (8,935 rows, 30,874,359 bytes, md5 `f779094301b068361af47b84ec51a299`). Dry run 17:41:15-17:42:42: **`2190 bills checked | unchanged=8888 corrected=47 nulled=0`**, `diff_baseline_id: set=4328`. **Gate met** (inside 40-55; the Mac's 47). Commit 17:42:55-17:44:30, exit 0. **Second dry run: `corrected=0 nulled=0`, `set=0`.**
- Note: this v61 recompute **also stamps `diff_baseline_id`** in the same pass (va 14,927 and az 4,328 documents now carry it), so your step 5 for those two states should find them already stamped; I will run its dry run and report what it says.

## 4B. Virginia people load: DONE
`people` checkout `/opt/ddp-open-states/people` pulled to `b639152c62` (#22 and #23; **12 files: 11 Virginia `other_names` and one North Carolina file from #22, which I did not load; the weekly people job will**). The container's `/opt/venv-openstates/bin/os-people` (the host's one refuses, as on 11-12), `--safe` first: **`processed 399 person files, 0 created, 11 updated`**, all Virginia, no "went missing" lines. **Gate met (only 11 updates).** Real run 17:46:25-17:46:36, **rc 0**, same lines; the new variants (for example "Adams, K.", "K. Adams", "Kimberly Pope Adams" under Kim Adams) are in the database.

## Running now
- **WA (step 3) and NC (step 4A) `refresh-extraction --dry-run`**, started 17:45:11 UTC, both on the host. WA's gate: 0 extraction errors, stale about 7,354 (3,677 HTML + 3,677 PDF, +/-3%); NC's: 0 errors, stale 2,000-3,480. **Nothing is committed for either until its dry run meets its gate.**
- **Alabama's pipeline** (about 1.2 h scrape, then load and archive).

## Still to do, in your order
Alabama section B and the search rebuild (after its archive); Washington and NC commits; the OPEN-539 baselines for every state (untouched states first; va and az first need only a check, wa, nc and al last). Everything before tonight's 02:30 UTC nightlies.
