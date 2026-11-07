# Reply: `recompute-diff-order ma --commit --flags-only` done and checked (OPEN-498). 2026-11-07, 05:40-05:44 UTC

Reply to the GO `dac2ce19`, Part 2. **Stopped after this: I wait for your "verified".** I never ran `ma` without `--flags-only`; OPEN-396 is untouched and nothing here triggered a Massachusetts generation.

**The user's go (this session, verbatim):** "Yes, commit now, then stop for verified (Recommended)". I took Ramon's relayed go as information and asked first. I also told the user that the 20 flipping marks had not been listed to anyone; they chose to commit.

## Gates (right before)
- **G1:** openstates-core `138fa3df92d303e17c490a6251c31bb615bbbf63` in a throwaway worktree (not the v48 image); `--flags-only` is in `recompute-diff-order --help`.
- **G2:** RDS latest restorable time **2026-11-07T05:37:51Z** (the rollback point). At 05:40:42 UTC: no ECS task, no scrape/recompute/backfill process, 0 ddp-sync jobs in the last 10 minutes; the Saturday 05:00 archive had finished at 05:01; Pennsylvania's 04:00 run is over. Window chosen by me: now.
- **G3 before:** `docs 12,157 | flag_null 12,113 | flag_true 44 | flag_false 0 | bills 11,799 | with_diff 291` and `diff_fingerprint 7476ed1f0aa33cfabe38de09528f4741`: **identical to Part 1's baseline.**

## The runs, exact lines
```
[05:40:48 -> 05:41:26] ma --dry-run --flags-only (before)
ma: [DRY RUN] 11799 bills checked | diffs untouched (--flags-only)
ma: [DRY RUN] is_bill_version: set=12113 changed=20 not_a_version=3200
[05:41:42 -> 05:42:49] ma --commit --flags-only   (exit 0, 67 s)
ma: [COMMITTED] 11799 bills checked | diffs untouched (--flags-only)
ma: [COMMITTED] is_bill_version: set=12113 changed=20 not_a_version=3200
[05:42:51 -> 05:43:29] ma --dry-run --flags-only (after)   (exit 0)
ma: [DRY RUN] 11799 bills checked | diffs untouched (--flags-only)
ma: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=3200
```
The before dry run matched Part 1 exactly (no `nulled=` or `corrected=` anywhere), so I committed. The after dry run prints `set=0 changed=0` and the same `not_a_version=3200`.

## G3 after
`docs 12,157 | flag_null **0** | flag_true **8,957** (= 12,157 - 3,200) | flag_false **3,200** | bills 11,799 | with_diff **291**` and **`diff_fingerprint 7476ed1f0aa33cfabe38de09528f4741`: identical to Part 1's.** No diff was touched. The Massachusetts row of the whole-table snapshot also shows the same total diff length (7,998,573 characters) and diff checksum (`ad96947c5e`) as before.

## Whole table, and one thing that moved that is not mine
Compared with my snapshot after Pennsylvania's commit (21:45 UTC 11-06):
- The Massachusetts row changed in its flags only, as expected: null 12,113 to 0, false 0 to 3,200.
- **The group with no `/state:` in its jurisdiction id (the federal/USA documents) also moved: 92,778 to 92,800 documents (+22), 13,828 to 13,846 diffs (+18), diff length +81,639.** The whole table is therefore 224,189 documents (not 224,167) and flags set 85,255 rather than the 85,233 I would get from 73,120 + 12,113 alone (the difference is those 22 new documents, already marked). I did not run anything for that group; I read it as the scheduled USA scrape and archive adding documents since last night (USA ran at 03:00 and its archive finished 04:19), but I did not trace the 22 rows.
- **Every other state is identical** (documents, flag counts, diff counts, diff length and checksum).

## Not done
No run without `--flags-only`, no other state, no search refresh, no cleanup of the HD/SD bills already published, no restart or schedule change. The throwaway worktree is removed.

## Waiting
Your Mac-side checks and "verified" line (replica applied, SD 4329 end to end, H 3188 and SD 3237 still readable as real bills). The 20 documents whose marks flipped were not listed to anyone before the commit: if you or Ramon want the list, I can read it from the replica or RDS, but their previous marks are now overwritten on RDS (the rollback point is the 05:37:51 UTC restore time, or revert the rule and rerun with the switch).
