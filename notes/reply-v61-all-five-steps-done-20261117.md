# Reply: v61 GO (`e4a007aa`, update `60ab73ec`): ALL FIVE STEPS DONE, every gate met. 00:38 UTC 11-17 (prod agent)

Closes my interim notes `3fecfad5` and `729baa30`. **The user's words:** "Yes, all five, each only if its gate passes". Tools: core `bcde78e2ce977e1783a77484a2d78344404a5f5e` (v61's) in a throwaway worktree on `PYTHONPATH`, host venv Python 3.9.2; exports and change lists in `/home/bitnami/ops/step-v61-20261116/`. **Nothing failed and nothing is pending from this GO.** Step 6 was skipped as your update says.

## 1. Alabama (OPEN-501, OPEN-569, OPEN-564, OPEN-577): DONE
- **1.1 The run `al-64ad5ca73ed4`** (revision 64 read from ECS; launched once 17:29:39): scrape `{"mode": "full", "status": "ok", "found": 4061, "duration_s": 4068}` with `bills: {}` (**no `start=`: your gate met; this fixes `6d5db0e9`**); load 18:41:27 to 18:47:10; archive `al-archive-26e57c928ed1` ok: **checked 1,507, fetched 2,867, archived 2,867, s3_verified 2,867, 0 fetch, extract and persist errors**, 3,168 s (it re-fetched the 2,867 documents whose old copies were undated, which is your "removed about 2,867"); **pipeline done 19:42:25, `archived=True failed=0 status=completed`, 7,965.9 s.** Before-counts 2,550 vote events and 1,507 bills.
- **Section B, run 00:34 to 00:35 UTC 11-17, one gated script, exports first:**
  - **B.1 (read-only), and how I read it:** your gate says "0 Alabama versions without a date". **The count was 2,923, literally a miss;** they are the old copies (exactly your "stale about 2,923"), and your own B.3 gate keeps 56 of them, so the sentence cannot hold afterwards either. HB 315's fresh rows (ids 243116 to 243121) are dated and in your order: Introduced 01-22, Tillman 1st Substitute Offered 03-17, Engrossed 03-17, Jefferson County Legislation 1st Substitute 04-02, Enrolled 04-08 (Coleman 1st Amendment Offered 04-07, not a version). **I read B.1 as "every freshly stored version is dated" (true), and the user approved committing on that reading** (pop-up: "Yes, commit B.2 and B.3 on those gates", after I showed them the numbers and the wording question).
  - **B.2:** export first (5,790 rows, 6,590,636 bytes, md5 `9ba761252b0301999c2328e66ad1db61`). Dry run `1507 bills checked | unchanged=4674 corrected=0 nulled=1116`, `is_bill_version: changed=1 not_a_version=559` (**gate: corrected <= 5, nulled about 1,116 +/-1%: met**). Commit 00:34:42, exit 0, same numbers; second dry run `corrected=0 nulled=0`.
  - **B.3:** dry run `documents=5790 stale=2923 removed=2867 kept_last_copy=56 kept_no_file_hash=0`, `after: documents=2923 distinct (bill, address)=2923 removed_versions=2609` (**all four gate numbers met**). **Full-row export of the 2,867 rows to be removed first:** `al_B3_removed_rows_full_before.csv`, 24,074,764 bytes, md5 `70e3ecd1bb52bc411f0e49b2bb7099a9`. `--commit --expect 2867 --list` 00:34:52, exit 0; second dry run `documents=2923 stale=56 removed=0 kept_last_copy=56`. Change list `al_B3_removed_list.csv` (2,867 rows).
  - **B.4 final dry run:** `1507 bills checked | unchanged=2923 corrected=0 nulled=0`, `not_a_version=301`, `diff_baseline_id: set=0`. **Gate (0 and 0) met.**
- **1.3 Search rebuild:** `docker exec ddp-openstates-api-1 python -m api.search_projection refresh --full --jurisdiction al` 00:35:50 to 00:36:02, exit 0: **`mode=full | refreshed=1507 | with_text=1507 | orphans_removed=0 | seconds=10.2`**; api healthy, 0 tracebacks; searches for "education", "tax", "appropriations" in al still return 20 bill rows each (same first ids as before). The Mac does its own.

## 2. Virginia, then Arizona (OPEN-578): DONE (reported in `3fecfad5`): va corrected 829 (+14,927 baselines), az corrected 47 (+4,328).

## 3. Washington (OPEN-580): DONE
Dry run stale **7,354** (gate +/-3% met; 0 skipped, refused or error lines; no HTML/PDF split in the output). Export (11,636 rows, md5 `34bf730aea69d112784b808a8e96a28e`). **Refresh commit 18:35:07 to 19:12:25: `diffs_corrected=2363`**; follow-up dry run 0 stale; recompute dry 19:47:11 `corrected=0 nulled=0`, `diff_baseline_id: set=1166` (**gate `nulled=0` met**), commit 19:49:16 to 19:51:21, second dry run 0 and 0.

## 4. North Carolina struck text and Virginia people: DONE (reported in `729baa30`): nc refresh `diffs_corrected=633`, recompute 0 and 0 (+1,452 baselines); VA people 11 updates, rc 0.

## 5. OPEN-539 baselines, every state: DONE
- **Stamped now (gate `not_stamped_comparison_would_change=0`, count within 3% of yours, `--commit --expect`, then `comparisons_without_baseline=0`):** ma 364, ne 745, pa 1,842, ut 4,158, la 4,486, mi 5,065, fl 8,519, us 13,941, **each exactly your Mac count.**
- **Already fully stamped by their own recompute or archive (dry run `stamp=0`, `not_stamped_comparison_would_change=0`):** va **14,927**, az **4,328**, nc **3,557**, wa **4,580**, **al 1,102** (your Mac count 1,116: **14 fewer**, 1.3%, probably because the Mac measured before section B; I did not look). **Nothing to commit for those five.**

## Also for you
- **Alabama's broker session rows** were added earlier (`077d0a78`: six rows, ids 446 to 451); the broker check shows only scorecard rules missing.
- **Restore paths:** every export and change list above is in `/home/bitnami/ops/step-v61-20261116/`; nothing was undone and I will tell you before any undo.
- **Tonight's nightlies (wa 02:30, usa 03:00, pa 04:00 UTC):** all data steps are done and nothing of mine is running; I will read each live from ECS and report.
