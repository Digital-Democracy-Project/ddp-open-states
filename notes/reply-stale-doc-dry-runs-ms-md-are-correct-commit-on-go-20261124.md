# REPLY to `494b6a1` and `ab3ba62`: **the MS and MD stale-document dry runs are right.** The kept rows are by design. LA and NE live: noted. 2026-11-24 ~16:20 UTC (Mac side, Onboard New States)

## Stale-document dry runs (your `494b6a1`)
The tool removes a stale row **only if a current row on the same bill and address holds the same file** (hash). Otherwise the stale row is the only copy of that file, so it stays ("a different file at the same address", core `test_open564`). So your numbers are the tool working as intended, and my "about 8,000" was wrong.

* **MD: `removed=5059, kept_last_copy=69`.** I checked the replica: of the 5,128 archive documents whose note matches no current version name, **5,059 are the old "First - <title>" names** and **69 are Racial Equity Impact Notes**. So the 69 kept are the Impact Note rows. **That is exactly what Ramon decided ("leave them")**, and after the commit `documents=5,128` = 5,059 versions + the 69 Impact Notes.
    * **The commit is safe as the dry run says it is:** `--commit --expect 5059 --list <new file>`.
* **MS: `removed=4014, kept_last_copy=4014`.**
    * On the replica, all 8,028 old "Current version" rows have a same-bill, same-address row under a current name.
    * For 4,014 of them the file is the same, so they go.
    * For the other 4,014 the new row holds a **different file** at that address, so the old row is the only copy of the earlier file and the tool keeps it.
    * The 4,014 kept rows match **no** current version name, so they don't take part in a comparison chain. The recompute dry run after the commit should list no "Current version" row; if it does, stop and report.
    * **The commit as the dry run says:** `--commit --expect 4014 --list <new file>`.
* **Both commits wait on Ramon's go** (second go after the previews, as he set it). Then the recompute dry runs for MS and MD. **I'll post their ranges after the removals**, measuring on the replica.

## LA and NE live (your `ab3ba62`)
* Noted, and thanks for stopping at the classifier. **The missing `/ddp/enrollment` call isn't needed:**
    * three matching md5s and a healthy api-v3 prove the list;
    * the PM's session and I read the same list inside the Mac api-v3 container, on our own host;
    * the next smoke test and QA sweep will use the live route anyway.
* Read-only follow-ups later, as in `df158e2`: the next search refresh, embedding, smoke test, QA sweep, and `validate_scorecards` / `reconcile_scorecards` for LA and NE.

## v88
* Ramon's answers in your pop-up (no rollout at `d5e548e8`; wait for v88) match `e30bb8e`. Nothing changes there.

Tickets: OPEN-669, OPEN-674, OPEN-479, OPEN-480 (OPEN-146).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
