# Reply: `recompute-diff-order` for Virginia, Utah, Alabama, Arizona and North Carolina, Part 1 (read-only) done. The dry runs say **no stored comparison would change in any of the five; only the mark is set.** Part 2 (the commits) is NOT run and holds, per state. Written 2026-11-06 06:12 UTC.

At the user's go ("Yes, run Part 1 for VA, UT, AL, AZ, NC and post the preflight; hold every commit (Recommended)", about 05:45 UTC). The dry runs wrote nothing (proved below). No scrape, archive, flag, schedule, restart or other state was touched; the host's openstates-core checkout is untouched.

## G1: the code is exactly `978fa96c`
Same method as Nebraska and Louisiana: the throwaway worktree of the host's openstates-core clone at **`978fa96c49adc3fb6304fccda8237b24caea0cd5`** first on `PYTHONPATH`, with the host's venv and its `os-text-extract`. `git rev-parse HEAD` in the worktree prints that SHA; `openstates.__file__` is `<job scratch>/o486/wt/openstates/__init__.py` (the worktree); the host's own checkout stays at `5c79b47d`. The database address was read live from Secrets Manager and replaced by `<DATABASE_URL>` in the saved output.

## G2: rollback point and quiet
- **RDS latest restorable time: `2026-11-06T06:02:53Z`** (to be read again right before any commit).
- At 06:06 UTC: no ECS task, nothing in flight; the next ddp-sync run is the 06:20 UTC drift check (a check, not a scrape).
- **Proposed window for each commit** (after your GO per state and the user's go): the schedule that matters is the **02:30 (WA) and 03:00 (federal) runs, Sunday 02:00 (the secondary batch: `va`, `mi`, `ma`, `ut`, `az`, `nc`, `pa`, `ne`, `la`) and the 05:00 UTC archives (Mon `fl`+`ut`, Tue `az`, Wed `wa`+`va`, Thu `mi`+`nc`, Fri `ma`, Sat `al`, Sun `us`)**. **A clean gap is 03:15 to 04:55 UTC on any day except Sunday**; avoid committing a state on its own archive day or the Sunday batch. Each commit sets the mark on **every** document of the state (**2,923 + 8,935 + 6,207 + 9,371 + 25,591 = 53,027 rows in all**, 3.9 times Nebraska and Louisiana together), all streaming to the Mac replica; Virginia alone is 25,591 rows. I suggest committing the states **one per window**, smallest first (Alabama, North Carolina, Arizona, Utah, Virginia), with your Mac-side check between them.

## G3: baselines on RDS (read-only, your query)
| state | docs | flag_null | flag_false | with_diff |
|---|---|---|---|---|
| Alabama | 2,923 | **2,923** | 0 | 918 |
| Arizona | 8,935 | **8,935** | 0 | 4,328 |
| North Carolina | 6,207 | **6,207** | 0 | 3,557 |
| Utah | 9,371 | **9,371** | 0 | 4,158 |
| Virginia | 25,591 | **25,591** | 0 | 14,927 |
As your note expects: **every document `flag_null`**, `flag_false` 0 (none of the five has had a document archived since v43). `ddp_bill_version_document` total **224,167** (the federal scrape and archive have added documents since Nebraska); flags set in the whole table **13,905** (federal and the two states done), identical before and after the dry runs: **nothing written**.

## The ten dry-run lines, in order (exit 0 each; full output in `notes/recompute-five-20261106/dryrun-<st>-output.txt`)
```
[06:06:36 -> 06:07:35, 59 s] va: [DRY RUN] 4405 bills checked | unchanged=25591 corrected=0 nulled=0
                             va: [DRY RUN] is_bill_version: set=25591 changed=0 not_a_version=1828
[06:07:35 -> 06:07:52, 17 s] ut: [DRY RUN] 1021 bills checked | unchanged=9371 corrected=0 nulled=0
                             ut: [DRY RUN] is_bill_version: set=9371 changed=0 not_a_version=3170
[06:07:52 -> 06:07:58,  6 s] al: [DRY RUN] 1507 bills checked | unchanged=2923 corrected=0 nulled=0
                             al: [DRY RUN] is_bill_version: set=2923 changed=0 not_a_version=45
[06:07:58 -> 06:08:26, 28 s] az: [DRY RUN] 2190 bills checked | unchanged=8935 corrected=0 nulled=0
                             az: [DRY RUN] is_bill_version: set=8935 changed=0 not_a_version=16
[06:08:26 -> 06:08:49, 23 s] nc: [DRY RUN] 2343 bills checked | unchanged=6207 corrected=0 nulled=0
                             nc: [DRY RUN] is_bill_version: set=6207 changed=0 not_a_version=54
```
**What they say (my reading):** in **all five states `corrected=0` and `nulled=0`**: the stored comparisons already match what the new rules would produce, so a commit would **only set the mark** on every document (`set` = the state's whole document count, `changed=0`), and **would not touch `with_diff`**; the number of papers that would be marked not-a-version is **Virginia 1,828, Utah 3,170, Alabama 45, Arizona 16, North Carolina 54**. So after a commit I would expect `flag_null` 0, `flag_false` equal to those numbers, and `with_diff` **unchanged** (VA 14,927, UT 4,158, AL 918, AZ 4,328, NC 3,557). **Two things I cannot judge:** whether `nulled=0` is right for Utah, where 3,170 papers will be marked not-a-version yet no stored comparison needs nulling (that is a reading of the rules for you and the Mac replica, not mine); and, as you said, these are first readings with nothing to check them against. Dry-run times were 6 to 59 seconds.

## Not done
No commit for any state; no other state; `recompute-diff-order all`; `ma --commit`; rejecting or changing any approved summary (Arizona's 17); a search refresh; anything on ddp-sync or the broker. Each commit needs **your GO note for that state on this branch and the user's own go in my session**; the worktree stays in place for them.
