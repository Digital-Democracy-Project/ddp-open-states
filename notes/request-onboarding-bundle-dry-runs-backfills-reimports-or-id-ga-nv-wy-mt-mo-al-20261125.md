# REQUEST (not a GO): **ONE bundle for the states still waiting on production steps: the dry runs, the Georgia and Alabama backfills, and the Alabama and Nevada re-imports.** Ramon can give it as **three goes** (Part 1, Part 3, Part 4), with Part 2's commits each on a second go after he has seen the numbers. 2026-11-25 ~22:00 UTC (Mac side, Onboard New States)

**Not a GO.** Please confirm each go with Ramon in your session. Everything here was already requested in earlier notes (`e30bb8e`, `a0e5d64`, `request-oregon-…`) and **has not run** (I found no prod-agent note with these results); this note only puts them in one place, on today's code: scrapers image v95 (core `a7035d68`), ddp-sync running core `a7035d68`. **The Arizona full load is running (started 21:37 UTC): do not restart ddp-sync until its load task is down.** The narrow restart rule applies to anything that touches ddp-sync; none of the steps below needs a restart.

## Part 1: dry runs only, ONE go for all (read-only; report the exact summary lines and each list's md5; commit nothing)
The commands are `os-text-extract recompute-diff-order <st> --dry-run --list <file>` and `os-text-extract relabel <st> --dry-run --list <file>` in the ddp-sync container. **My expected numbers come from earlier measurements on older cores; I could not re-measure today (my scratch tools were lost in the Mac reboot), so a different number is a report, not a stop.**
| State | Dry run | Expect (ticket) |
|---|---|---|
| **OR** | `relabel or`, then `recompute-diff-order or` | relabel **337** changed; recompute **433 / 432 / 201** (OPEN-841, 846; `request-oregon-…`) |
| **ID** | `recompute-diff-order id` | `not_a_version` **56**, `corrected` **50**, `nulled` **56** (OPEN-834) |
| **GA** | `recompute-diff-order ga` | `corrected` **3**, 0 nulled, no flag or baseline change (OPEN-842) |
| **WY** | `recompute-diff-order wy` | `not_a_version` **845** (840 amendment papers and 5 veto messages); each Enrolled's baseline = Introduced (OPEN-835) |
| **MT** | `relabel mt`, then `recompute-diff-order mt` | relabel about **62** gain `introduction`; recompute **60** comparisons change (38 become empty, 22 shrink, none grow) (OPEN-826, 827, 862) |
| **MO** | `recompute-diff-order mo` | `not_a_version` **700 to 800**, `corrected` **420 to 510** (earlier range, unchanged) |
* **Also read-only, MT's draft cleanup (ddp-sync #310, SYNC-191, OPEN-861):** the **dry run** for `mt` only; do **not** apply it. Report the count.
* **Not in Part 1:** HI and MD (I owe you ranges; I will post them), Nevada's recompute (it needs the Nevada re-import first, Part 4), KY and MS (already committed), ND, ME and RI (done).

## Part 2: the commits (each its own go, after Ramon has seen that state's dry-run numbers; `--commit --expect <n> --list <file>`, a second dry run must then read 0)
Only for the states whose numbers match. Same rule as every earlier commit: stop on any difference.

## Part 3: the two backfills, ONE go for both (dry run, compare, then apply; `a0e5d64` Step 2)
* **GA:** `backfill-vote-rollcall-num.py --jurisdiction ga --dry-run --list <file>`; expect **280** votes (245 House, 35 Senate), md5 **`ea69e3715f5f7aff2058844b0b198e5f`**; then `--apply-list <file> --expect 280 --list <committed>.csv`.
* **AL:** `--jurisdiction al`; expect **2,550** votes (1,359 House, 1,191 Senate, none numbered yet), md5 **`ad12bf8301a199efd315c92ddf999275`**; then `--apply-list <file> --expect 2550`.
* Deterministic, so **no file is needed from me**; a different md5 or count: stop and report. (Nevada's backfill is already applied and verified.)

## Part 4: the Alabama and Nevada re-imports, ONE go, started together (own run, own pass/fail; image v95 or later; not Sunday from 02:00 UTC)
| State | Request | Pass (I read it on the replica) |
|---|---|---|
| **AL** | `al?full=true&sessions=2026rs` | Stage 3 unchanged (285 people, versions 0/2,867, votes 0/183,715, sponsors 0/1,507); `house-rollcall-num` / `senate-rollcall-num` on **every** vote (the same numbers the GA/AL backfill sets); HB 605 Senate and SB 146 Senate labelled `amendment`; HB 201 still passage (OPEN-863) |
| **NV** | `nv?full=true&sessions=2025Special36,84` | sponsors 0 unmatched of 27; versions 237; versions named `^Amendment` 0; documents named `^Amendment` 26; `2025Special36` 431 actions; AB 4, AB 5, SB 10 read as fail (the same result the backfill set); `passed_both_without_passed_one` 0 (OPEN-849, 865) |
After Nevada's re-import: its recompute dry run (**corrected 32, nulled 26, flags 26, baselines 22/10/26**), then its commit on a second go.

## Also, one read-only question
**Iowa's `2026s1`:** what did the 11-24 run report for session `2026s1` (bills loaded, or "no such session")? The replica has no `2026s1` rows. And the Iowa 2025 archive's end line (started 17:33 UTC).

## Not authorized
Any commit before its second go; the draft cleanup's apply; a ddp-sync restart; any state beyond those named; HI, MD, MS and ME second passes (they need Ramon's separate decision, not a go here); Oklahoma (OPEN-887 and OPEN-892 carry it).

Tickets: OPEN-146; OPEN-841, 846, 834, 842, 835, 826, 827, 862, 861, 863, 864, 865, 849.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
