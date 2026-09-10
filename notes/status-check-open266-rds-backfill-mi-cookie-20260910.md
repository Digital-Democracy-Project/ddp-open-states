# Status check requested: OPEN-266, RDS data-quality backfill, MI cookie publish

Now that OPEN-192's Fargate archive validation is closed out end to end (all four jurisdictions
clean on rev23, GLACIER_IR confirmed directly -- `notes/rev23-us-clean-all-four-confirmed-
20260910.md`), Ramon asked for a status check on three threads that were left open, not
blocking that close-out:

## OPEN-266 -- the 35 is_error=True rows (ma: 30, mi: 4, wa: 1)

Last status (`notes/open266-investigation-status-20260910.md`, since merged as part of PR #231):
confirmed these are a permanent dead end under OPEN-263's fix (which only retries `is_error=False`
rows) and not covered by any existing mechanism (OPEN-33 was VA-specific and one-off, OPEN-229 --
the generalized `reextract` command -- is still To Do). Disposition (bespoke one-off script vs.
building OPEN-229 first) wasn't decided as of that write-up. Any movement since?

## RDS data-quality backfill (OPEN-193/`PLAN-rds-data-quality-backfill.md`)

Step 3 (dry-run) came back clean for UT/WA/US days ago
(`notes/rds-backfill-real-baseline-all-three-20260909.md`) -- `docs_refused=0` across the board
after the poppler-utils fix. Still waiting on an explicit go-ahead for the actual `--commit` step
per the plan's §4. Is that approved yet, or still pending?

## MI cookie publish (`MI_COOKIE_PUBLISH_ENABLED`)

Root-caused as a deliberate flag left over from the original OPEN-193 canary setup, not a bug
(`notes/mi-cookie-publish-root-cause-deliberately-disabled-20260909.md`). You said you'd take the
flip-it-or-not decision to Ramon directly rather than deciding it on this branch. Any answer yet?

No urgency on any of these relative to the archive-validation work that just closed -- just
checking in on where each stands.
