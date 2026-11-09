# Request: confirm the first Massachusetts scrape on image v51 (OPEN-508). READ-ONLY. 2026-11-09 (Mac side)

Ramon asked for this on 2026-11-09 ("ask the prod agent to confirm the Massachusetts run"). **Nothing to change anywhere. Do not start a scrape, do not run any recompute, do not delete or edit any row.**

**What is live.** Image `ddp-scrapers:v51` (built and pushed from the Mac), ECS task-definition **revision 53** (registered by Ramon; the previous revision ran v48). It carries openstates-scrapers `main` **`c939b63`**: the Massachusetts scraper now skips a Documents-list row when the bill's PAGE title (not the list title) says it is not a measure (`is_not_a_measure(bill_title)` in `scrape_bill`; PRs #83 and #84). Each skip writes a log line that contains `OPEN-508`.

**Why we ask.** OPEN-508, OPEN-509 and OPEN-513 wait on proof that a real Massachusetts run skips reports, orders and amendment papers and skips no real bill. Nobody on the Mac side has read such a run.

## What to report
1. **Did a Massachusetts scrape start after revision 53 was registered?** If yes: the ECS task id, the task-definition revision and image tag it actually ran on (`describe-tasks`, not the schedule's wording), start and end time (UTC), exit status. If no: say so, and when the next one is due. **Do not launch one.** Also give the registration time of revision 53 from ECS.
2. **If it ran, the skips:**
   - the number of log lines containing `OPEN-508`;
   - every distinct skipped title, or if there are more than 60, the count plus the first 60 and any whose title begins "An Act", "Resolve", "Resolves", "Resolution", "Joint Resolution" or "Proposal" (those would be real measures wrongly skipped; there should be none);
   - how many of the skipped bill numbers already exist as bills in RDS (read-only count), and how many of those have a vote or an action (read-only).
3. **The rest of the run:** bills scraped, bills created or updated, errors or tracebacks (count and the first one), duration, and the same figures for the previous Massachusetts run so the Mac side can compare.
4. **Anything odd:** a spike or a drop in the bill count, a new error, an `SSLError`, a run that hit the 12 or 24 hour limit.

## Not authorized
Any write to RDS; `recompute-diff-order` in any form; starting, stopping or re-registering a task; any change to a task definition; cleanup of the existing Massachusetts non-bill rows (that is OPEN-513, held for Ramon's go).

## Reply
`reply-ma-scrape-v51-open508-20261109.md`, with the real numbers and what you could not read marked "not checked". Then wait.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
