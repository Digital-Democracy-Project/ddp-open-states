# Request (read-only dry runs now; commits HOLD for Ramon's go per state): `recompute-diff-order` for Pennsylvania, Louisiana and Nebraska (OPEN-495, OPEN-496, OPEN-497, OPEN-478/479/480). 2026-11-06 about 20:50 UTC (Mac side)

## What I need from you
1. **Part 1, now (read-only):** the dry runs and baselines below, for `pa`, `la`, `ne`, one state at a time, with the replies in one file. **Write nothing.**
2. **Confirm which image revision tonight's 04:00 UTC Pennsylvania task runs (reporting).** Ramon released **`ddp-scrapers:v45`, task-definition revision 47** at about 20:43 UTC (his deploy script printed "tag v45, revision 47"; the previous image was v43 / rev 46; v44 was built and pushed but never registered). You cannot read task definitions, so read it from the launch: the image or revision in tonight's task log or launch line.
3. **Part 2 (the commits): do NOT run.** Each state holds until a note from Ramon on this branch says GO for that state, then you run it, then you stop for my "verified", as with the five earlier states.

## What changes and why
Three text cleaners, all merged to openstates-core `main` **`47e9b768`** and carried by image v45: **Pennsylvania** (OPEN-495: drops the `PRINTER'S NO.` line and the `<--` change bar, collapses spaces, lower-cases each line), **Louisiana** (OPEN-496: drops `Page N of M` footer lines), **Nebraska** (OPEN-497: removes the stray space after a wrapped hyphen, slash or bracket). `recompute-diff-order <st>` re-diffs each stored pair through the real cleaner and, with `--commit`, saves `diff_from_previous_version` (it rewrites that derived column only; stored text is untouched). Your before picture (`015e50c`) matches mine: pa 909 of 921 with `<--`; la 853 of 4,541 with a footer line; ne 0.

## Code to use
openstates-core `main` **`47e9b768`** (the same throwaway-worktree method as the five earlier states, with that SHA on `PYTHONPATH`, or image v45). Say which, with proof (`openstates/__init__.py` path and `git rev-parse HEAD`, or image id and tag).

## Part 1 gates and steps (read-only)
G1 the code is what you say. G2 record the RDS latest restorable time; nothing in flight; no ddp-sync job in the last 10 minutes (it is read-only, but keep the same quiet window habit). G3 baselines per state (read-only): documents, `is_bill_version` null / false counts, and comparisons with a non-null diff (use the same query as before). Then `recompute-diff-order <st> --dry-run`, **report the exact lines** and start and end times, for `pa`, then `la`, then `ne`.

## What I expect (measured on the Mac replica by the three builds; tell me if yours differ)
- **ne:** about **376 stored comparisons rewritten, 158 of them to empty** (the pure re-wrapping ones); 745 pairs in total; 0 pairs worse; changed lines 52,739 to 49,417. Flags: `is_bill_version` already set (3,383 documents; 791 not-a-version).
- **la:** comparisons with a footer line 853 to 0; changed lines drop slightly (a 937-pair sample: 47,878 to 47,410, none worse). Flags already set (10,468 documents; 3,328 not-a-version).
- **pa:** all **921** comparisons are touched by the lower-casing and the change bar (909 had `<--`); changed lines 201,965 to 148,828 over the 921 pairs; none worse (110 equal, 811 better). **One thing to report carefully: Pennsylvania's documents are not marked yet (`is_bill_version` is null on all 6,188), so the dry run may also print `is_bill_version: set=6188 changed=6188 not_a_version=0`.** That is the mark "this is a real bill version" being written for the first time, not a text change; paste the line as printed and I will check it against the design before any commit.

## Not authorized
Any commit (`--commit`), `recompute-diff-order all`, any other state, `ma`, any refresh, scrape, archive, schedule, restart, LegBot run, pull of the ddp-open-states tip (a separate later request), or a change to ddp-sync or the broker.

## Reply
`reply-recompute-diff-order-dry-runs-pa-la-ne-<date>.md` (Part 1 for all three, item 2 as its own short reply when tonight's run launches).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
