# STATUS, STOPPED: step 4.1 (Alabama stale documents) COMMITTED; step 4.2 (Alabama recompute) FAILED its gate, NOT committed. Nothing after it was run. 2026-11-16 02:36 UTC (prod agent)

Answers `2f57a434`. User's words in session for the later steps: **"Run each step if its dry run passes its gate"**. Rule from `9963ec87`: a failed gate means stop and report, so I stopped.

## Step 4.1: `remove-stale-documents al`: gate passed, COMMITTED
- Run with core `eec94082b` (a throwaway worktree on `PYTHONPATH`) on the **host venv, Python 3.9.2**, not v59 (v59 is 3.13).
- **Dry run** 02:34:36-02:34:37: `al: [DRY RUN] documents=3379 stale=456 removed=456 kept_last_copy=0 kept_no_file_hash=0`, `after: documents=2923 distinct (bill, address)=2923 removed_versions=2`. **Gate met exactly** (`stale=456 removed=456 kept_last_copy=0`, ending `documents=2923`).
- **Before the commit** I exported **all columns of the 456 rows** (a restore path; your list names the rows but is not a full copy): `/home/bitnami/ops/step4-al-20261116/al_removed_rows_full_before.csv`, 3,966,104 bytes, md5 `a5dbe195697bd1dca8105a2fe75b10d4`, mode 600.
- **Commit** `--commit --expect 456 --list /home/bitnami/ops/step4-al-20261116/al_removed_list.csv` 02:35:00-02:35:01, exit 0: `al: [COMMITTED] documents=3379 stale=456 removed=456 ...`, `after: documents=2923`, change list 456 rows. **Second dry run:** `documents=2923 stale=0 removed=0`. The dry-run list is also kept (`al_stale_dryrun_list.csv`).

## Step 4.2: `recompute-diff-order al --dry-run`: GATE FAILED
- 02:35:13-02:35:20, exit 0, output (the only lines it prints):
  `al: [DRY RUN] 1507 bills checked | unchanged=2812 corrected=110 nulled=1`
  `al: [DRY RUN] is_bill_version: set=0 changed=1 not_a_version=301`
- **Your gate:** `nulled` <= 1 and `corrected` <= 5, and HB 248 the changed bill. **`nulled=1` meets it; `corrected=110` does not (limit 5).** I did **not** commit. The command has no option to list which bills it would change, so **I cannot tell you which 110**, and I did not check whether HB 248 is among them.
- **HB 248 as read just before the dry run (2026rs, all `application/pdf`, all `is_bill_version` true):** ids 166304 (no diff), 166307 (diff length 517), 166309 (2,107), 241566 (0), 241567 (164,594). I read it before the dry run only, so I have no "after".
- **What I did not do:** a recompute dry run on Alabama **before** step 4.1, so I do not know whether the 110 existed before the removal or came from it. A plausible reading (a guess, not checked) is that removing 456 earlier copies changes which document is "previous" for many bills, but the `changed=1` and `nulled=1` lines say only that one document would change its flag and one diff would be nulled.

## State now (read-only facts)
- Alabama: **2,923 documents** (stale rows removed, committed); **diffs and flags otherwise as before** (step 4.2 is dry-run only, nothing written by it).
- **Steps 4.3 (people load), 5 (Pennsylvania recompute), 6 (LA/NE flip), 7 (struck words) and 8 (api-v3 #61) were NOT run.** I stopped everything after the failed gate, as your note says; I did not decide that step 5 is independent of Alabama.
- **Timing you may want:** Pennsylvania's nightly starts at **04:00 UTC** on revision 62 and has run 7 to 14 hours; your note says to avoid steps 4-7 while a nightly's import or archive for the same state is in progress, so step 5 is cleanest before 04:00 or after PA's load and archive.

## What I need from you
1. **Alabama 4.2:** is 110 expected after 4.1 (then the gate was wrong), or is something off? Commit anyway only on your word.
2. **Step 5 (PA) and the rest:** go ahead with them before 04:00 UTC, or hold everything until 4.2 is settled?
- **Restore for 4.1 (not wanted so far):** from `al_removed_rows_full_before.csv`; your call with Ramon. No auto-undo.
