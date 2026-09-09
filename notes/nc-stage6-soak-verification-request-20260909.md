# Please verify NC's Stage 6 soak evidence (OPEN-231)

Separate from the cloud-archiver Fargate/RDS network work above. NC (North Carolina) is Phase 1's
onboarding pilot (OPEN-231, epic OPEN-146). Stages 1-5 are done; **Stage 6 (soak + handoff)** is
the only thing left, and Ramon wants to close it out now.

## Why this needs your access, not mine

Stage 6 requires confirming clean production cycles from real logs/DB state -- exactly the kind
of live-system verification you're set up for, not something I can do from the dev checkout.

## What "clean" means here, and how many cycles

NC probed **YELLOW** in OPEN-230 (its only gate failure was a shared probe-tooling limitation,
not a real NC defect -- CO also went yellow, GA/OH/IN went red). Per
`PLAN-push-button-onboarding.md` §6's soak table, a yellow-class pilot needs **two** clean weekly
cycles before promotion (green only needs one). Don't assume one cycle is enough just because NC's
gate failure was tooling-related rather than substantive -- the plan's table keys off probe class,
not root-cause severity.

Timeline so far: NC entered `secondary.jurisdictions` (Stage 2) ~2026-08-31, archive enabled
(Stage 4) ~2026-09-01. Today is 2026-09-09, so roughly one full week has definitely passed;
whether that's one or two actual weekly cycles depends on which day the secondary schedule
fires NC on -- check the real schedule rather than assuming from the calendar.

## Please confirm, with real evidence

1. How many weekly scrape+archive cycles NC has actually completed since Stage 2/4 went live
   (pull real run timestamps, not an assumption from elapsed days).
2. For each completed cycle: no scrape failures, no WAF blocks, no archive `extract_errors`
   beyond the one known pre-existing multipart-ETag limitation (`_upload_and_verify`'s documented
   behavior, already itemized in OPEN-231's Stage 4 comment -- not a new regression to flag again
   unless it's now affecting a different document), and no new data-quality gaps beyond the two
   already itemized and ticketed (OPEN-233, OPEN-234).
3. Whether NC has cleared **two** such clean cycles yet, or only one so far.

## What happens next depending on your answer

- **Two clean cycles confirmed:** report back with the evidence (timestamps, counts) and I'll
  open the PR flipping `jurisdictions.yaml`'s `nc.status` from `probing` to `live` in the dev
  checkout (per this repo's own dev/prod discipline -- not something to edit directly in
  production), then close out OPEN-231 and update the OPEN-146 epic.
- **Only one clean cycle so far, or an issue found:** report that too -- either wait for the
  second cycle, or if something's not clean, that's real Stage 6 evidence in its own right, not
  a blocker to hide.
