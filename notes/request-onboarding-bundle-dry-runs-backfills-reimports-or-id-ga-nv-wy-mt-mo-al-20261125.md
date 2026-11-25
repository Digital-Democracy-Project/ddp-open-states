# REQUEST (not a GO): **ONE bundle for the states still waiting on production steps: the dry runs, the Georgia and Alabama backfills, and the Alabama and Nevada re-imports.** Ramon can give it as **four goes** (Part 1, Part 3, Part 4, Part 4b), with Part 2's commits each on a second go after he has seen the numbers. 2026-11-25 ~22:00 UTC (Mac side, Onboard New States)

**Not a GO.** Please confirm each go with Ramon in your session. Everything here was already requested in earlier notes (`e30bb8e`, `a0e5d64`, `request-oregon-…`) and **has not run** (I found no prod-agent note with these results); this note only puts them in one place, on today's code: scrapers image v95 (core `a7035d68`), ddp-sync running core `a7035d68`. **Ramon's decisions (11-25, via the PM; the goes themselves he gives in your session): Part 1 YES, Part 3 YES, Part 4 YES, and Part 4 starts NOW, in parallel with the Arizona full load (scrapers run in parallel on Fargate): nothing here waits for Arizona.** None of the steps below touches ddp-sync or needs a restart.

## Part 1: dry runs only, ONE go for all (read-only; report the exact summary lines and each list's md5; commit nothing)
The commands are `os-text-extract recompute-diff-order <st> --dry-run --list <file>` and `os-text-extract relabel <st> --dry-run --list <file>` in the ddp-sync container. **The numbers below are measured today (11-25 ~23:00 UTC): I ran the same dry runs read-only against the Mac replica inside the v95 image (core `a7035d68`). They agree with the earlier measurements. A different number on the host is still a report, not a commit.**
| State | Dry run | Expect (ticket) |
|---|---|---|
| **OR** | `relabel or`, then `recompute-diff-order or` | relabel **337** changed (306 lose `passage`, 29 gain it, 2 failure labels); recompute `is_bill_version` changed **433**, `nulled` **432**, `corrected` **201**; 633 documents (OPEN-841, 846) |
| **ID** | `recompute-diff-order id` | `not_a_version` **56**, `corrected` **50**, `nulled` **56**; 106 documents (OPEN-834) |
| **GA** | `recompute-diff-order ga` | `corrected` **3**, 0 nulled, no flag or baseline change (`not_a_version` 102 is the stored count); 3 documents (OPEN-842) |
| **WY** | `recompute-diff-order wy` | `is_bill_version` changed **845** (840 amendment papers and 5 veto messages), `corrected` **88**, `nulled` **841**, baselines changed 88 / cleared 841; 929 documents (OPEN-835) |
| **MT** | `relabel mt`, then `recompute-diff-order mt` | relabel **62** gain `introduction`; recompute **60** corrected, 0 nulled, no flag or baseline change (OPEN-826, 827, 862) |
| **MO** | `recompute-diff-order mo` | `is_bill_version` changed **746** (`not_a_version` 756), `corrected` **461**, `nulled` **598**, baselines set 372 / changed 119 / cleared 598; 1,089 documents (inside the earlier ranges 700-800 and 420-510) |
| **HI, MD** | `recompute-diff-order hi`, `recompute-diff-order md`, `relabel hi` | **all 0** (nothing to commit: HI unchanged 21,472, relabel 68,030 unchanged; MD unchanged 5,128). Please still run them once so the host's own read is on record |
| **RI, ND** | `relabel ri`, `relabel nd` | **0 changed** (the commits already landed) |
* **Also read-only, MT's draft cleanup (ddp-sync #310, SYNC-191, OPEN-861):** the **dry run** for `mt` only; do **not** apply it. Report the count.
* **Not in Part 1:** Nevada's recompute (it needs the Nevada re-import first, Part 4), KY and MS (already committed), ND, ME and RI (done).

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

## Part 4b: the Maine, Maryland and Mississippi second passes, ONE go (Ramon: YES to all three, 11-25), started together with Part 4, each its own run (own pass/fail; image v95 or later; the sessions are the ones their first runs used)
| State | Request | Pass (I read it on the replica) |
|---|---|---|
| **ME** | `me?full=true&sessions=132R1,132R2,132S1` (the first run took over 6 hours of collection; one run only) | **actions in the legislature's own order**: bills with a backward date step **1,473 → 0** (today's count; OPEN-839, scrapers #267); 2,450 bills; unmatched **0 of 148,002**; then its archive (a fresh launch archives itself) |
| **MD** | `md?full=true&sessions=2026,2026s1` (about 2 hours) | **HB 1372 and HB 139 final-passage votes labelled `passage`** (OPEN-832, #271); 2,677 bills; unmatched **0 of 267,947**; its recompute dry run stays 0 |
| **MS** | `ms?full=true&sessions=2026,20261E` (about 1.7 hours) | **SN 10, SN 50 and SN 101 sponsored by the organization "Office of the Governor"**; SN 1 (Lt. Governor) and SN 110 (Attorney General) unchanged; 4,124 bills; unmatched about **4 of 149,303** (4 today) (OPEN-828, #270) |
* A failure stops that state only; two states with the same error stop further starts. A state has one run at a time (so none of these starts while that state's own scheduled run is going).

## Also, one read-only question
**Iowa's `2026s1`:** what did the 11-24 run report for session `2026s1` (bills loaded, or "no such session")? The replica has no `2026s1` rows. And the Iowa 2025 archive's end line (started 17:33 UTC).

## Not authorized
Any commit before its second go; the draft cleanup's apply; a ddp-sync restart; any state beyond those named; Oklahoma (OPEN-887 and OPEN-892 carry it).

Tickets: OPEN-146; OPEN-841, 846, 834, 842, 835, 826, 827, 862, 861, 863, 864, 865, 849.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
