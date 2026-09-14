# Correction to my last note: wrong host -- the Mac should not be triggering cloud_archiver at all, disregard the "set it on the Mac" ask

Ramon caught this directly: the Mac should not be triggering `cloud_archiver` in the first
place -- post-OPEN-192 cutover, that's EC2's job. I found real `RDS_CREDENTIALS_SECRET_ARN`
errors in the Mac's own log and generalized from there without first checking whether the Mac
was even supposed to still be running that scheduler. It isn't, and it currently isn't:

- `OPENSTATES_ARCHIVE_ENABLED=false` in the Mac's `ddp-sync/.env` right now.
- The Mac's own log shows `openstates_archive: disabled — skipping` on every scheduler
  (re)registration going back to **2026-09-13 03:50 EDT** -- over a day before I looked at this.
- The three `fargate launch refused (RDS_CREDENTIALS_SECRET_ARN not set)` errors I cited (ma
  9/11, al 9/12, us 9/13, all at 01:00 EDT) all predate or land right at that disable boundary --
  they're the tail end of a since-corrected misconfiguration on the Mac, not an ongoing problem
  there.

**So my previous ask ("get RDS_CREDENTIALS_SECRET_ARN set on the Mac") was solving the wrong
host's problem.** Retracting it. The real question is unchanged from your own original note:
does **EC2's** ddp-sync have both `OPENSTATES_ARCHIVE_ENABLED=true` and a working
`RDS_CREDENTIALS_SECRET_ARN` (or equivalent Secrets-Manager-resolved RDS access), since that's
the host that should own Fargate archive triggering now. I have no way to check EC2's own
config or ECS/CloudWatch task history from here -- this is squarely the "flagging for whoever
has the access" gap your own original note already named. Sorry for the detour.

What's still real and unchanged from my prior note: NC has zero rows in
`ddp_bill_version_document` and zero bills in the Mac's local Postgres (data lives only in
RDS) -- that part doesn't depend on which host is doing the triggering, just on whether
EC2's archive runs for NC have actually succeeded end-to-end.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
