# OPEN-290 ready for your review: consolidate the two LegBot trigger endpoints

PR: https://github.com/Digital-Democracy-Project/ddp-sync/pull/152
Ticket: OPEN-290 (In Review, under the OPEN-180 epic)

Directly motivated by the FL/2026E double-dispatch investigation in this same
thread: `/trigger/bill-artifact-generation` (manual) and `/trigger/scraper-session-
legbot` (automated, SYNC-59) both dispatch `run_legbot_pipeline` for a jurisdiction+
session, but only the automated one held SYNC-48's Redis overlap lock -- a manual
call and an automated one for the same jurisdiction/session could run fully
concurrently, neither visible to the other. Whatever the second FL/2026E run's exact
source turns out to be (see the correction note posted alongside this one), this
architectural gap is real and independently confirmed by code reading, not just by
that one incident.

**What changed**:
- `bill-artifact-generation` now dispatches through `trigger_scraper_session_pipeline`
  (the existing lock wrapper) instead of calling `run_legbot_pipeline` directly --
  gains the lock without becoming subject to the automated-only
  `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` pause flag.
- `scraper-session-legbot` is deleted. Its one caller (the archive-completion hook's
  EC2-to-Mac WireGuard hop) now posts to `bill-artifact-generation` instead.

**Sent through /pm-review once**, briefed to guard scope to just these two endpoints.
It caught two real gaps, both fixed:
1. Lock-key case sensitivity -- the archive hook always locks with `jurisdiction.
   upper()` ("FL"), a manual caller can type any case ("fl"). Fixed by uppercasing
   both components of the lock key.
2. Defaulting the lock wrapper's enable-flag bypass for every caller would have
   silently dropped the Mac operator's independent kill switch for automated
   dispatch. Fixed with a new `X-DDP-Automated-Trigger` header the WireGuard caller
   sends to identify itself, so the Mac's own enable flag still gates that specific
   path; a plain manual call is unaffected.

**One thing I need you specifically to verify** (I don't have EC2 access): the
WireGuard-relayed path's dispatch-shape settings (`artifact_types`/`limit`/
`include_concept_statements`) now resolve from **EC2's own** config instead of the
Mac's -- previously only the boolean enable flag needed to agree across hosts, since
the Mac fully resolved the dispatch shape itself on receipt. Please confirm EC2's
`LEGBOT_SCRAPE_COMPLETION_TRIGGER_ARTIFACT_TYPES` / `_LIMIT` /
`_INCLUDE_CONCEPT_STATEMENTS` are actually set and match the Mac's values before this
deploys -- if `artifact_types` is unset on EC2 it defaults to an empty list, which
would make every automated dispatch fail with a 400 that the hook's log-and-continue
contract swallows silently.

Full test suite: 1247 passed. Please give this a final review -- merge + close the
ticket if it looks good, or comment on OPEN-290 if anything needs adjustment.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
