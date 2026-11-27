# UPDATE (adds to the next-image request; still NOT a GO): **two more core fixes ride the same image, Oklahoma gets a refresh and recompute dry run, and Iowa's count rises by 2.** 2026-11-27 (Mac side, Onboard New States)

This adds to `request-next-image-iowa-signed-papers-wyoming-struck-text-refresh-extraction-ia-wy-dry-run-open913-open927-not-a-go-20261127.md`. Read it first; everything there stands except the items below. **Not a GO.** Ramon gives the go in your session naming the final note. Start only after v99's parts are finished.

## What I need from you (changes to that request)
1. **Image:** it must now carry core `6c520c59` or newer (the merge of #187). Read the recorded core commit and report it; stop if older. It then contains core #183, #185, #186 and #187.
2. **Iowa dry run (Part 3 there):** expect **about 395 changed** (the 393 plus Iowa's SJR 9 and SJR 11 "Enrolled" papers, 60 characters each today, 1,761 and 2,892 after), none shortens. Report the exact lines; do not commit.
3. **New Part 3b: `os-text-extract refresh-extraction ok`, dry run first.** Expect **about 12,863 changed of 17,574 PDFs in the active sessions**, **0 shorter, 0 errors**, text about 2.3% longer (about +4.2 million non-space characters). Report the exact lines; the replica may have moved, so say if the counts differ. **Do not commit.** It is a large refresh: Ramon approves it by size.
4. **New Part 5b: `recompute-diff-order ok --dry-run`** with the new core (stored comparisons change where text changes). Report the exact lines; do not commit.
5. Commits hold until a go note from Ramon, per state.
6. After each part tell me; I check on the Mac replica: Oklahoma: a paper such as SB 439 and HB 3588 carries its unnumbered lines, no old line is missing, no unrelated Oklahoma text changes, Stage 3 gates. Then Oklahoma's dev LegBot re-sample (my step).

| Change | Repo and merge | What it does |
|---|---|---|
| OPEN-930 | openstates-core #186 (merge `debe29ac`) | Iowa's unnumbered text "Enrolled" papers (SJR 9, SJR 11) read in full instead of 60 characters. Every other Iowa PDF reads as before. |
| OPEN-914 | openstates-core #187 (merge `6c520c59`) | Oklahoma's own PDF reader keeps the unnumbered lines inside numbered pages (97 of 251 sampled papers lost 5% or more of their lines; now 0). Only `ok` differs in the reader table. |

## Not authorized
Any other state's refresh or recompute; a scrape or re-import; a manifest change; any LegBot or scorecard switch; a ddp-sync restart beyond the rebuild; any commit before a go note.

Tickets: OPEN-930, OPEN-914, OPEN-913, OPEN-927; Oklahoma go-live OPEN-666; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
