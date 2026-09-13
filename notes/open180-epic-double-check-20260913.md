# OPEN-180 epic: double-checking Done/To-Do tickets for real, not just trusting Jira

Ramon asked for a true, double-checked understanding of every ticket in this epic (56 total).
Most of the 38 "Done" ones are self-contained code fixes with tests that landed at the time --
low risk of having silently gone stale, not re-litigating those individually. A handful are
"confirm this state" or "this infra thing happened" tickets that are worth a real, current
re-check given how much has changed on this host today. And a couple of "To Do" items may
already be contradicted by things you've done today without the ticket being updated. Can you
check these directly:

## "Done" tickets worth a real re-check (state could have regressed or was point-in-time)

1. **OPEN-253** ("Confirm OPENSTATES_SCRAPE_ENABLED is persisted correctly on Mac (false) and
   EC2 (true) .env files") -- given today's several `ddp-sync` restarts/redeploys on this host,
   is this still true right now? Quick check of the live .env / running container env on both
   sides if you have Mac visibility, EC2 side for sure.
2. **OPEN-257** ("Re-tier ddp-bill-archive's Deep Archive backlog to Glacier IR, and stop new
   archives from landing back there") -- is the backlog re-tier actually complete (not just
   started), and are new archives genuinely landing at `STANDARD_IA`/GLACIER_IR, not silently
   falling back to Deep Archive anywhere?

## "To Do" tickets that might already be resolved by today's real activity, just not updated

3. **OPEN-215** ("ddp-scraper IAM user lost CloudWatch Logs read access mid-session, blocking
   Fargate failure diagnosis") -- you've been reading real CloudWatch logs successfully all day
   today (archive task e547f81775b445ddb3688fad76c093e2, the `us` scrape task, etc.). Is this
   ticket actually stale-open -- access was restored at some point and nobody updated Jira --
   or is there a different IAM identity/role involved than the one this ticket is about?

## Flagging directly, not asking you to fix right now

4. **OPEN-258** ("refresh-extraction's S3 fallback logs full boto3 requests at DEBUG, leaking
   the live STS session token") -- this is a real, still-open security-relevant item (a live
   credential landing in logs). Just confirming it's still accurately tracked as open and
   hasn't been quietly fixed as a side effect of other logging changes today -- not asking for
   a fix right now, just the real current state.

Report back whatever you find, including "still exactly as the ticket says" if that's the real
answer -- not trying to manufacture progress, just get an accurate picture.
