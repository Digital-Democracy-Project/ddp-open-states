# UPDATE (adds to the next-image request; still NOT a GO): **core #189 (US Congress PDF reader) rides the same image; `refresh-extraction us` and `recompute-diff-order us` dry runs are added; the image must carry core 3ebaf5e0 or newer.** 2026-11-27 (Mac side, Onboard New States)

Adds to the next-image request and its two updates (OPEN-930/914 and OPEN-909 notes). Read them first; they stand except as below. **Not a GO.** Ramon gives the go in your session naming the final note. Start only after v99's parts are finished.

## What I need from you (changes)
1. **Image:** it must carry core **`3ebaf5e0`** or newer (the merge of #189; it replaces `77e3e398` in the earlier update; core `main` at this write). Read the recorded core commit and report it; stop if older. The image then contains core #183, #185, #186, #187, #188 and #189.
2. **New Part 3c: `os-text-extract refresh-extraction us`, dry run first.** Expect **about 3,687 of the 7,202 resolutions to change, plus a fraction of the bills** (my measurement on the Mac's archive copy of 46,634 US PDFs; I compared 10,202 papers and the old text is an in-order subset of the new in every one). None shortens. Report the exact lines and the total counts; the replica may have moved. **Do not commit.**
3. **Size, for Ramon's decision:** the stored text of those resolutions grows about **2.6x (6.39M to 16.85M characters)**, because section headings and the Whereas paragraphs of resolutions were being dropped. LegBot reads more per resolution after the refresh. This is a large refresh: **Ramon approves it by size.**
4. **New Part 5d: `recompute-diff-order us --dry-run`** with the new core. Report the exact lines; **do not commit**; commits hold until a go note.
5. After each: tell me; I check on the Mac replica: S.Res. 54 reads about 4,197 characters with all 18 Whereas (738 today), S. 241 and HR 8540 gain their heading lines, no unrelated US text changes, Stage 3 gates.

## Not authorized
Any other state's refresh or recompute beyond those named in the next-image notes; a scrape or re-import; any LegBot or scorecard switch; a ddp-sync restart beyond the rebuild; any commit before a go note.

Tickets: OPEN-917; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
