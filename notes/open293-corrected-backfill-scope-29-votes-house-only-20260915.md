# OPEN-293: corrected backfill scope -- 29 votes, House-side only. My "11 Senate-side" number was a bug in my own scoping, not real.

Correction to the two notes above. Ramon asked me to check whether the Senate case bug also
hits SRES/SCONRES (not just SJRES), since real production scrape output (checked directly in
S3) showed wrong-case identifiers across every Senate resolution type. Scoped all 1,100
SRES/SCONRES/SJRES session-119 bills against congress.gov and found 13 with apparently-missing
votes.

Before trusting that, I re-verified every previously-flagged "missing" vote (this batch and the
original 40) against the local DB using the vote's own roll-call number instead of date --
`VoteEvent.extras['senate-rollcall-num']`/`['house-rollcall-num']`, unambiguous, no timezone
involved.

**21 of the previously-flagged votes are false positives, all on the Senate side.** My original
scoping script compared dates truncated to `YYYY-MM-DD` strings between congress.gov and the
local DB. A vote recorded late at night Eastern lands on the next UTC calendar day, so a real,
correctly-linked vote can differ by one calendar day from congress.gov's reported date and get
spuriously flagged as missing. Checked concretely: `SJRES 55`'s 4 supposedly-missing rolls
(266/273/274/275) are all present in the DB right now, correctly linked, with the right
`senate-rollcall-num` extras. Same story for `HJRES 105`, `HJRES 25`, `SJRES 34/41/83/185/196`,
and the new `SCONRES 7` find -- none of them were ever actually missing.

**Practical upshot: the Senate case bug doesn't appear to have dropped any real votes.** Senate
bill-matching is evidently case-insensitive in practice -- `SRes 377` (wrong case, straight from
a real scrape) matched bill `SRES 377` with zero issue across all 6 of its votes, checked
directly. The case-bug fix (PR #48, folded into #49) is still correct and worth keeping, but
there's no Senate-side backfill needed.

**Real, confirmed backfill scope: 29 votes, all House-side, all HJRES/SJRES** (the spacing bug --
mangles the string itself, not just case, so these genuinely have zero matching VoteEvent row,
re-confirmed by roll number):

`HJRES 1, 104, 105, 106, 117, 130, 131, 139, 140, 142, 20, 24, 25, 35, 42, 60, 61, 72, 75, 78,
87, 88, 89`, `SJRES 11, 13, 18, 28, 31, 80`.

Down from "35 bills / 40 votes" -- that count was inflated by the date-comparison bug above.
Sorry for the churn across these notes -- should have matched by roll number from the start.

Nothing about PR #49's status changes: still the fix that matters, still needs review/merge/
deploy before these 29 House-side votes are re-scrapeable.