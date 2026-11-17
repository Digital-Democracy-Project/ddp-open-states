# Status: US Congress flip COMMITTED (step 2 done): 39,263 bills reversed; the four bills check out; ready for #398. 02:11 UTC 11-17 (prod agent)

Answers `1fc0d674`. **The user's words in session (pop-up, after I showed them the dry run and the "do nothing" risk): "Yes, commit the US flip now".** I told them the label rollout would follow once you merge #398; **step 3 (the label) is NOT done: please merge #398 and I will roll it out.**

## Step 1, before (read-only, 02:03 UTC)
- Core: **`44c3b8dc82a0f296b68c3bf2a2e6e2454e5b29b9`** (revision 65's recorded core, in a throwaway worktree on `PYTHONPATH`, host venv Python 3.9.2): **no migration beyond `0051`** in it.
- **0 running `ddp-scrapers` tasks; 0 ddp-sync pipeline lines; the US pipeline lock `ddp:pipeline_lock:usa` is free** (key absent in ddp-sync's Redis; no pipeline lock exists at all).
- **The broker's bill-event task: none** (beat table: the same 9 tasks as on 11-16, none is a bill-event check; `sync webflow organizations` is disabled), **so step 4 is a no-op.**
- **Not verifiable from this host: "revision 65 is the latest active `ddp-scrapers` and its image is v62"** (`ecs:ListTaskDefinitions` and `DescribeTaskDefinition` are denied). I will read the revision from the running 03:00 US task instead and report it.
- The manifest still has us `newest_first: true` (the command read it and ran; I did not roll out #398).

## Step 2: the reversal
- **Dry run 02:03:58 to 02:04:47 UTC, exit 0:** **`us: [DRY RUN] reversed=39263 actions=130008 skipped_single_action=14`**, `stored dates: mixed=39 newest_first=10605 same_day=28619`; change list 39,263 rows, **by session: 119: 19,957 and 118: 19,306 (no older sessions)**. **Gate met** (0 errors; 39,263 inside 37,000-42,000, exactly your figure).
- **The caution I put to the user:** 28,619 of those bills have all their actions on one day, so for them the reversal cannot be checked by date (your own blind spot, far larger here than for LA or NE).
- **Commit** `--commit --expect 39263 --list /home/bitnami/ops/step-us-flip-20261117/us-commit.csv` **02:05:31 to 02:10:34 UTC, exit 0:** **`reversed=39263 actions=130008 skipped_single_action=14`**; **`latest action fields recomputed and changed: 31441`**; commit list 39,263 rows. **I committed once only.** Gates re-checked just before: 0 tasks, lock free, no US lines, 54 minutes to 03:00.
- **Second dry run (read-only, 02:10): `reversed=0 actions=0 skipped_already_reversed=39263 skipped_single_action=14`**, so it cannot double-apply.
- **Your four bills (read from RDS, by action order):**
  | bill | stored latest action | last by order | first by order |
  |---|---|---|---|
  | HR 1 (119) | "Became Public Law No: 119-21." (2025-07-04) | order 52, 2025-07-04, "Became Public Law No: 119-21." | order 0, 2025-05-20, "The House Committee on the Budget reported an original measure..." |
  | S 5 | "Became Public Law No: 119-1." (2025-01-29) | order 35, same | order 0, "Introduced in Senate" |
  | HR 4 | "Became Public Law No: 119-28." (2025-07-24) | order 38, same | order 0, "Introduced in House" |
  | HR 1968 | "Became Public Law No: 119-4." (2025-03-15) | order 30, same | order 0, "Introduced in House" |
- **How many of the 17,182 bills now have a different latest action:** the command's own count of **latest action fields changed is 31,441 across all 39,263 bills of both sessions**; **I did not count the 17,182 subset separately**, so I cannot give you that number.
- **Rollback (not done):** `--undo --commit` with `us-commit.csv`, inside the window; tell me before any undo.

## What is next
- **Step 3:** merge ddp-open-states #398, then I roll it out (`rollout-manifest.sh`, enrollment must show no state with `newest_first: true`), and I will report when the broker has re-read it (about an hour).
- **Step 5:** the 03:00 US run is not held; I will read its revision from ECS when it launches and report `status=completed failed=0` and the four bills afterwards.
- **Step 6 (Virginia OPEN-593, after 03:00):** not started and **not yet approved by the user**; I will ask them for it separately.
