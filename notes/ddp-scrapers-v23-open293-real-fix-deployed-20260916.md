# ddp-scrapers v23 (task-def revision 27): the real OPEN-293 fix is now live -- runs next, not dormant

PR #49 (`openstates-scrapers`, merged) is the fix that actually matters for OPEN-293: it applies
the HJRES/SJRES bill-id normalization to `usa/bills.py`'s `scrape_house_votes()`/
`scrape_senate_votes()` -- the code path that actually runs in production. (v22 had fixed the
same bug in `usa/votes.py`, which is never invoked -- see
`open293-v22-fixed-wrong-file-pr49-is-the-real-fix-20260915.md` above for the full story.)

Built, verified (`python --version` -> 3.10.21, `pdftotext -v` -> 22.12.0, both matching v22;
also directly imported `normalize_clerk_bill_id`/`normalize_senate_bill_id` from `usa.bills`
inside the built image and confirmed correct output before pushing), pushed to ECR as
`ddp-scrapers:v23`, and registered as task-definition revision 27.

**Same as v22: this is not dormant, it runs next.** `ddp-sync` references the task-definition
family by bare name (`"ddp-scrapers"`, no pinned revision), so ECS's own latest-revision default
means the next real scheduled/triggered US scrape (or archive) job picks up v23 automatically.
Nobody needs to flip anything.

## What to watch on the next real US run

- HJRES/SJRES votes should now link correctly on both House and Senate sides, going forward.
- Real, confirmed impact (see `open293-corrected-backfill-scope-29-votes-house-only-20260915.md`
  above): 29 already-missing House-side votes (all HJRES/SJRES bills) are now re-scrapeable, but
  re-scraping them is a separate, not-yet-started backfill step -- this deploy alone doesn't
  recover them retroactively.
- Rollback: revision 26 (v22) is untouched and still registered if anything looks wrong --
  register the old image tag again, or pass `taskDefinition: ddp-scrapers:26` for one run to
  bypass the "latest" default.