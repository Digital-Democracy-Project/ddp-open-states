# REQUEST (not a GO): **the next scrapers image (carrying the Iowa signed-paper reader and the Wyoming struck-text reader), an api-v3 rebuild at that core, then text refreshes for Iowa and Wyoming, dry run first.** 2026-11-27 (Mac side, State Specific Handling)

**Not a GO, nothing to start now.** v99 is built and its parts are in your hands; these two fixes merged **after** it (core merges 2026-11-27 19:04 to 19:05 UTC) and are **not in v99**. Ramon gives the go in your session naming the final note. Start only after v99's parts are finished, so the chains do not overlap. If Oregon's abstract fix (scrapers #310) or anything else rides the same image, the PM or Onboard New States will say so in an `update-` note; this note covers only the two below.

## What the next image carries (for these two states)
| Change | Repo and merge | What it does |
|---|---|---|
| OPEN-913 | openstates-core #183 (merge `c5a44e72`, core `main`) | Iowa's governor-signed enrolled papers (a letter plus an unnumbered scan with a text layer) are read as plain text. They read as about 27 characters before; 259 of them were empty. Every other Iowa PDF reads exactly as before. |
| OPEN-927 | openstates-core #185 (merge `e3371ea7`, core `main`) | Wyoming's PDF reader drops struck-out words (the same reader Idaho, North Dakota and others use). HB 144's levy read "three (3) ten (10) mills"; it will read "ten (10) mills". |
| OPEN-911 | openstates-core #182 (merge `e8c26870`) | A read-only measurement script. Nothing imports it; nothing to run. |

Core `main` is now `e3371ea7`; v99 was built at `1e138376`. The image takes core's `main` at build: **read the recorded core commit and report it; stop if it is older than `e3371ea7`.**

## What I need from you (after the go)
1. **Part 1: the image.** Ramon builds it (your role cannot launch the build). Report the new task-definition revisions and the recorded scrapers and core commits.
2. **Part 2: api-v3 at the new core on both hosts**, and EC2's ddp-sync rebuilt for the new image (as in the v99 checkpoint).
3. **Part 3: `os-text-extract refresh-extraction ia`, dry run first.** Expected (my measurement on the Mac's archive copy of all 6,594 Iowa PDFs; the replica may have moved): **about 393 changed** (344 signed enrolled, 49 marked-up), **6,201 unchanged**, none shrinks, about +5.8 million characters. 34 image-only scans have no text layer and stay empty; they may show as errors or unchanged, so report exactly what the lines say. Report the exact lines; **do not commit**.
4. **Part 4: `os-text-extract refresh-extraction wy`, dry run first.** Expected: **230 changed, 1,065 unchanged, 0 errors** (Introduced 149, Enrolled 47, Amendment 33, one chaptered law). Report the exact lines; **do not commit**.
5. **Part 5: `recompute-diff-order ia` and `recompute-diff-order wy`, each `--dry-run`**, with the new core (the stored comparisons change where text changes). Report the exact lines; **do not commit**.
6. Commits hold until a go note from Ramon, per state.
7. After each part, tell me; I check on the Mac replica: Iowa: HF 2754 and the other signed papers carry their bill text, SJR 9 and SJR 11 are reported separately (their "Enrolled" papers are a different paper that still reads 60 characters; own ticket), no unrelated Iowa text changes, Stage 3 gates. Wyoming: HB 144 reads "ten (10) mills", HB 166 reads "marijuana" without the struck "marihuana", only struck words disappear, Stage 3 gates. Then the Wyoming LegBot re-read (my step) and the Iowa checks.

## Not authorized
Any other state's refresh or recompute; a scrape or re-import; a manifest change; any change to Iowa's or Wyoming's LegBot or scorecard switches; a ddp-sync restart beyond the rebuild; any commit before a go note.

Tickets: OPEN-913, OPEN-927, OPEN-911; Iowa go-live OPEN-673; Wyoming go-live OPEN-662; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
