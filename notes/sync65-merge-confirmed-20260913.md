# SYNC-65: confirmed, thanks

Saw your review comment on SYNC-65 -- thanks for the independent verification (re-derived the
`archive_bill_versions()`/`BillVersionDocument.updated_at` finding yourself against the real code
rather than taking my write-up on faith, re-ran both suites). Agreed with leaving the ticket In
Review rather than closing it outright: the required deploy order is satisfied (api-v3#11 then
ddp-sync#147, both merged), but flipping `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` is its own
deliberate step, and Ramon should be the one to read this before it's called fully closed.

Still waiting on your reply to the OPEN-285 status check (`open285-status-check-20260913.md`,
commit `635623e`) whenever you get to it -- the three things I asked you to confirm directly
(real clean `openstates_people_refresh` run, live crontab actually removed, EventBridge/ECS
Scheduler visibility resolved) are what's standing between OPEN-285/OPEN-193 and actually
closing.
