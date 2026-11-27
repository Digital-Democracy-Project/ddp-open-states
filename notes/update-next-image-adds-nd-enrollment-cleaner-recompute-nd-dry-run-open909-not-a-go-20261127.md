# UPDATE (adds to the next-image request; still NOT a GO): **core #188 (North Dakota Enrollment changelog cleaner) rides the same image; a `recompute-diff-order nd` dry run is added; the image must carry core 77e3e398 or newer.** 2026-11-27 (Mac side, Onboard New States)

Adds to `request-next-image-iowa-signed-papers-wyoming-struck-text-refresh-extraction-ia-wy-dry-run-open913-open927-not-a-go-20261127.md` and to `update-next-image-adds-iowa-sjr-and-oklahoma-reader-ok-refresh-dry-run-open930-open914-not-a-go-20261127.md`. Read both first; they stand except as below. **Not a GO.** Ramon gives the go in your session naming the final note. Start only after v99's parts are finished.

## What I need from you (changes)
1. **Image:** it must carry core **`77e3e398`** or newer (the merge of #188; it replaces `6c520c59` in the earlier update). Read the recorded core commit and report it; stop if older. The image then contains core #183, #185, #186, #187 and #188.
2. **Manifest first:** ddp-open-states PR #511 (nd `quality.diff_cleaner` none to `clean_nd_text`) is what keeps the drift check green once core main dispatches nd to `clean_nd_text`. Roll it out with the manifest at the next rollout (pull first, then the script, dry run first); the PM merges it. Drift check against core main must say OK.
3. **New Part 5c: `recompute-diff-order nd --dry-run`** with the new core. Expect **about 648 North Dakota Enrollment changelogs to change, no others** (my measurement on the Mac replica: all 648 Enrollments; 0 of 2,042 other ND documents change; changed lines in the Enrollment changelogs 169,943 to 132,563; header, signature and filing lines in the changelogs 12,810 to 11). Report the exact lines; **do not commit**; the commit holds until a go note.
4. After it: tell me; I check on the Mac replica: HB 1540's changelog no longer carries the veto certificate pages (565 to 456 changed lines), no unrelated North Dakota change, Stage 3 gates.

## Not authorized
Any other state's recompute or refresh beyond those already named in the next-image notes; a scrape or re-import; any LegBot or scorecard switch; a ddp-sync restart beyond the rebuild; any commit before a go note.

Tickets: OPEN-909; North Dakota go-live OPEN-663; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
