# MI HB 6244-6322 gap: EC2-side logs for 2026-09-03 don't exist -- and that's itself informative

Checked CloudWatch directly for the `ddp-scrapers` Fargate task log group around
2026-09-03 01:05 UTC. **No logs exist for that date at all** -- the oldest retained log stream
in this log group goes back only to 2026-09-10 05:40 UTC. Not a retention-rotation question
(this host's own IAM role can't check the group's retention setting directly to confirm that
precisely), but the practical result is the same either way: nothing recoverable from here.

**More useful than a dead end**: this strongly suggests the 9/3 01:05 UTC run **never went
through this Fargate/cloud path at all** -- real cloud-orchestrated scraping/archiving for this
task family didn't start logging to this group until 9/9-9/10, right when the OPEN-192 cutover
went live. If MI's scrape had run via Fargate on 9/3, it would be in this same log group
(subject to whatever retention applies) -- the complete absence of ANY stream before 9/10
points to this specific run having gone through the old pre-cutover path instead (Mac-local or
some other retired mechanism), not cloud/EC2-orchestrated as your note wondered.

**Net: this specific incident isn't traceable further from either side** -- the evidence is
gone, not just hard to find. Worth watching for the same pattern (a contiguous number-range
hole with a couple of scattered survivors, clean before and after) on a *current* cloud-path
run if it ever recurs -- that would actually be investigable, unlike this one.
