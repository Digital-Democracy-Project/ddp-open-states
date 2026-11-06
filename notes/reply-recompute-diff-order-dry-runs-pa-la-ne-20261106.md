# Reply (read-only): `recompute-diff-order` dry runs for pa, la, ne (OPEN-495, 496, 497). 2026-11-06, 21:28-21:29 UTC

Reply to d178c3c3, Part 1 only. **Nothing was written** (`--dry-run` only; the database session also ran in read-only mode for the baselines). No commit, no other state.

**The user's words (this session):** "Yes, run the three dry runs now, write nothing (Recommended)".

## G1 the code
openstates-core **`47e9b768316231d56b2cbbfe786ccafd25829592`** in a throwaway worktree on `PYTHONPATH` (same method as the five earlier states). `openstates.__file__` = `<worktree>/openstates/__init__.py`; the file `openstates/cli/text_extract.py` there names the three cleaners (9 mentions of `clean_pa_text`, `clean_louisiana_text`, `clean_ne_text`). Not the image: I did not use v45.

## G2
RDS latest restorable time **2026-11-06T21:22:45Z**. At 21:27 UTC: no ECS task, no scrape/archive/recompute/backfill process, no ddp-sync job in the last 10 minutes.

## G3 baselines (read-only, same query as before)
| state | documents | `is_bill_version` null | false (not a version) | comparisons with a non-null diff |
|---|---|---|---|---|
| Louisiana | 10,468 | 0 | 3,328 | 4,541 |
| Nebraska | 3,383 | 0 | 791 | 745 |
| Pennsylvania | 6,188 | **6,188** | 0 | 921 |
Table total 224,167; flags set in the whole table 66,932. All match your expected numbers.

## Dry runs, exact lines (one state at a time)
```
[21:28:18 -> 21:28:40] pa
     pa: [DRY RUN] 5267 bills checked | unchanged=5270 corrected=918 nulled=0
     pa: [DRY RUN] is_bill_version: set=6188 changed=0 not_a_version=0
[21:28:40 -> 21:28:51] la
     la: [DRY RUN] 2599 bills checked | unchanged=9613 corrected=855 nulled=0
     la: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=3328
[21:28:51 -> 21:29:04] ne
     ne: [DRY RUN] 1847 bills checked | unchanged=3007 corrected=376 nulled=0
     ne: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=791
```
Times: pa 22 s, la 11 s, ne 13 s.

## Against what you expected (differences first)
- **pa:** `corrected=918`, not all 921 (the other 3 of 921 compared pairs are not in "corrected"; I did not look at why). `unchanged=5270` (5,270 + 918 = 6,188 documents). **The `is_bill_version` line says `set=6188 changed=0 not_a_version=0`, not `changed=6188` as you predicted.** The baseline shows all 6,188 still null, and the dry run wrote nothing; I am pasting the line as printed and will not guess what `changed` counts. Please check it against the design before any commit.
- **la:** `corrected=855`; you expected the 853 footer-line comparisons to go to 0, so 855 is two more than 853 (I did not look at which two). `is_bill_version: set=0 changed=0 not_a_version=3328`: flags already set, 3,328 not-a-version, as expected.
- **ne:** `corrected=376` as you expected (the output does not say how many of those become empty, so I cannot confirm the 158 or the changed-line counts 52,739 to 49,417; the command prints neither). `set=0 changed=0 not_a_version=791` as expected.
- 0 `nulled` in all three.

## Not done / still holding
No `--commit` for any state; each waits for a note from Ramon saying GO for that state. The throwaway worktree is removed. **Item 2 (which image revision tonight's 04:00 UTC Pennsylvania task runs)** is still owed: I read it from the launch and will post it as its own short reply.
