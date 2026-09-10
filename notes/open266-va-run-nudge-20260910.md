# Nudge: OPEN-266's last open data point -- please run `va` against revision 23 when convenient

*Follow-up to `notes/rev23-us-clean-all-four-confirmed-20260910.md`.* Thanks for closing out the
four-jurisdiction validation cleanly -- `us`/`az`/`mi`/`ma` all confirmed. One loose end left
specifically for OPEN-266, not blocking anything else: **VA's 4 rows were never part of that ask**
(only `us`/`az`/`mi`/`ma` were requested, since VA is a separate, unrelated population from
OPEN-263's own incident), so they're still sitting unverified.

## What's needed

A real archive run against `va` using task-definition revision 23 (same one already proven clean
on the other four). VA's own regularly-scheduled weekly run would eventually pick these up too, if
it's simpler to just let that happen naturally instead of triggering one now -- no strong
preference here, whichever is less friction on your end.

## What to expect, and why this is a low-stakes check

The 4 rows are `SB 759` (Finance and Appropriations Substitute, Chaptered, Enrolled versions) and
`HB 1320` (Appropriations Substitute), all `is_error=False` with `archive_location` still null --
the working hypothesis (`notes/open266-data-pulled-20260910.md`) is that OPEN-33's 2026-08-06
in-place text backfill fixed extraction for these without ever touching `archive_location`, so a
document whose *original* upload also failed independently looks exactly like this. Given MA's
identically-shaped 100-row population just recovered 149/149 clean under the same OPEN-263 fix, a
live bug specific to VA would be the surprising outcome here, not the expected one -- this is
mostly a formality to close out OPEN-266's last acceptance criterion with real data rather than
an assumption.

## What to report back

Just the same summary-line shape already used elsewhere: `fetched`/`archived`/`s3_verified`/
`s3_unverified`/`persist_errors` for `va`. If all 4 targets resolve (`archive_location` populated,
`persist_errors=0`), that's the confirmation OPEN-266 needs to fully close.
