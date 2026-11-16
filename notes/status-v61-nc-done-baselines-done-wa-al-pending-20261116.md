# Status: v61 passes: NC done, baselines done for 11 states, WA refresh committed (recompute pending), Alabama's archive still running. 19:40 UTC (prod agent)

Follows my `3fecfad5`. **The user's words in session:** "Yes, all five, each only if its gate passes". Same tools as before: core `bcde78e2c` in a throwaway worktree, host venv; files in `/home/bitnami/ops/step-v61-20261116/`. **No gate has failed.**

## 4A. North Carolina (OPEN-584): DONE
Refresh dry run 17:45 to 18:14 (stale 3,044, 0 skipped or refused, 0 error lines; gate 2,000-3,480 met). Export first (6,207 rows, 21,443,387 bytes, md5 `572f4b66dbcea3b201ed80092cef07f0`). **Refresh commit 18:15:02 to 18:42:16: `diffs_corrected=633`, 0 skipped, 0 refused. Follow-up dry run: 0 stale.** Recompute dry run 19:09:28: `2343 bills checked | unchanged=6207 corrected=0 nulled=0`, `not_a_version=54`, `diff_baseline_id: set=1452` (**gate `nulled=0` met; `corrected` is 0, as the refresh had already recomputed**); commit 19:09:55 to 19:10:24, exit 0; second dry run `corrected=0 nulled=0`, `set=0`.

## 5. OPEN-539 baselines (the stamp, `--baseline-only`): the eleven that can be done now are done
Per state: dry run with `--list`, gate **`not_stamped_comparison_would_change=0`** and `stamp` within +/-3% of your Mac count, `--commit --expect N --list`, then `after: comparisons_without_baseline=0` and a second dry run `stamp=0`. **Every one matched your Mac count exactly:**
| state | stamped | your Mac count | | state | stamped | your Mac count |
|---|---|---|---|---|---|---|
| ma | 364 | 364 | | la | 4,486 | 4,486 |
| ne | 745 | 745 | | mi | 5,065 | 5,065 |
| pa | 1,842 | 1,842 | | fl | 8,519 | 8,519 |
| ut | 4,158 | 4,158 | | us | 13,941 | 13,941 |
- **va, az and nc were already fully stamped** by their own recompute commits (the v61 recompute writes the baseline in the same pass): their baseline dry runs read **va `comparisons=14927 stamp=0`, az `comparisons=4328 stamp=0`, nc `comparisons=3557 stamp=0`**, each `not_stamped_comparison_would_change=0`, equal to your Mac counts (14,927, 4,328, 3,557). **Nothing to commit for those three.**
- Still to do: **wa** (after its recompute) and **al** (after section B).

## 3. Washington (OPEN-580): refresh COMMITTED, recompute pending
Refresh dry run (17:45 to 18:21): **stale 7,354** (your "about 7,354"; gate +/-3% met), 0 skipped, 0 refused, 0 error lines; the dry-run output does not give an HTML/PDF split, so I cannot report one. Export (11,636 rows, 64,648,890 bytes, md5 `34bf730aea69d112784b808a8e96a28e`). **Refresh commit 18:35:07 to 19:12:25: `diffs_corrected=2363`, 0 skipped, 0 refused.** Its follow-up dry run (must show 0 stale; about 37 minutes) is running, then the recompute dry run (gate `nulled=0`) and commit.

## 1. Alabama: scrape and load pass; the archive is still running
- **Run `al-64ad5ca73ed4`, revision 64 from ECS:** scrape `{"mode": "full", "status": "ok", "found": 4061, "duration_s": 4068}` (**your gate: "mode: full" with no `start=`**, met; found 4,061 as on Sunday), collection done 18:41:27, **load 18:41:27 to 18:47:10**.
- **Archive task `al-archive-26e57c928ed1`** (revision 64) started 18:47:52 and is **still running at 19:40**, downloading Alabama PDFs one a second; it is much longer than Sunday's (about 10 minutes). Probably because it is re-fetching documents whose rows I removed on 11-16 (the 456 stale rows) and whose file names changed; I have not confirmed that. I am **not** touching it. **Section B and the search rebuild start only when the pipeline has finished its archive.**

## Not yet / not done
Washington's recompute and baseline; Alabama's archive result, section B (B.1 to B.4), search rebuild and baseline. I will post a final note when all five are done.
