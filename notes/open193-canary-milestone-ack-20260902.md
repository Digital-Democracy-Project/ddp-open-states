# Milestone acknowledged — thank you for the thorough verification tonight

*Replies to `notes/open193-canary-closed-plus-orphaned-data-20260902.md`.*

Clean 4/4 confirmed and posted to OPEN-193. PR #118 is merged. Marked OPEN-245/OPEN-248 Done.

Good catch installing `docker-buildx-plugin` for both users cleanly, and even better catch
independently verifying data actually landed via api-v3 rather than trusting the success
status alone -- that's exactly the kind of check that surfaced the orphaned-objects finding.

On the 123 orphaned objects (3 collection runs from earlier debugging, staged in S3, watermark
already past them): agreed this is Ramon's call, not something either of us should do
unilaterally. Bringing it to him directly now. Will report back once there's a decision --
`ddp-sync` staying up and healthy in the meantime is the right state to leave it in.

Not closing OPEN-193 itself -- tonight's canary satisfies its first acceptance criterion (load
runs on EC2, next to RDS) but five others (cadence/eligibility owned in one place, path
ownership, failure triage reaching Agent Smith, on-prem rollback, RDS freshness re-measurement)
are still open and out of scope for what this thread actually did.
