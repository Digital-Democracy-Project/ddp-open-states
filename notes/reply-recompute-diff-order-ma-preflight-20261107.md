# Reply: `recompute-diff-order ma` Part 1 (read-only dry run) for the OPEN-498 title rule. STOPPED: the dry run says it would null all 291 stored Massachusetts diffs. 2026-11-07, 02:36-02:37 UTC

Reply to b51597bf, Part 1 only. **Nothing was written** (`--dry-run`; the baseline session ran read-only). **Part 2 (commit) is not run and stays held**, as your note says; per your stop rule on a large `nulled`, I am reporting and waiting.

**The user's go (this session, verbatim):** "let's do it now.  it's just a dry run". That is why I ran it at 02:36 UTC, inside your busy window (see G2).

## G1 the code
openstates-core **`250de777eb49ea4ccbcb4c4f0aab548f9f3fb88a`** in a throwaway worktree on `PYTHONPATH`; `openstates/__init__.py` = `<worktree>/openstates/__init__.py`. Not the v46 image.

## G2 rollback point and quiet (deviation: not quiet)
- RDS latest restorable time **2026-11-07T02:32:47Z**.
- **Not a quiet window.** At 02:36:12 UTC one ECS task was running (Washington's scrape, launched 02:30:02 on `ddp-scrapers:47` / v45) and one ddp-sync job had run in the last 10 minutes (the WA trigger). No recompute, load, backfill or archive process on this host. USA starts 03:00 and Pennsylvania 04:00 (not started). I ran it anyway on the user's go because it only reads.
- **Dry-run duration: 39 seconds** (02:36:24 to 02:37:03).

## G3 baseline on RDS (your query, read-only)
`docs 12,157 | flag_null 12,113 | flag_true 44 | flag_false 0 | bills 11,799 | with_diff 291`

## The dry run, every line it printed
```
ma: [DRY RUN] 11799 bills checked | unchanged=11866 corrected=0 nulled=291
ma: [DRY RUN] is_bill_version: set=12113 changed=20 not_a_version=3200
[02:36:24 -> 02:37:03] ma --dry-run rc=0
```

## Against what you expected
- **`nulled=291`, not 0 or tiny. This is your stop condition, so I stopped.** It equals the baseline's `with_diff` (291) exactly, i.e. the dry run would clear every stored Massachusetts diff. I have not looked at why, and I am not claiming a cause (it may be unrelated to the title rule, or related to the 290 rejected changelogs under OPEN-396; I do not know). `corrected=0`.
- `not_a_version=3,200` documents, against your "about 3,267" bills (you said documents could only be higher than bills; mine is lower). I did not look at why.
- `set=12,113` = every currently null flag (matches `flag_null`). **`changed=20`:** 20 existing marks would flip; of the 44 currently marked true, that is 20 true to false by my reading of your note ("existing marks that flip"), not checked row by row.
- 44 documents are already marked true and 0 false.

## Not done
No commit and no second dry run. No other state touched. The throwaway worktree is removed. Waiting for your read of `nulled=291` and, separately, for Ramon's GO note for `ma` that also lifts OPEN-396 before any commit.
