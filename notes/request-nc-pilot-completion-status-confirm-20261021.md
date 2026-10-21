# Please confirm where NC's pilot actually stands (OPEN-231, Stage 6 and the open items), read-only

**To:** the prod agent on the EC2-broker host. **From:** the ddp-infra session, at Ramon's request. Ramon believes most of what
`PLAN-push-button-onboarding.md` (on `ddp-infra` main, 2026-10-21) lists as still open for NC is already done. The plan was written
from Jira, merged PRs and the notes on this branch, so it may simply be behind. Please check each item against real evidence and
correct the plan's picture. **Read-only: do not start, retry, restart or change anything.**

## What the plan currently says is left (please confirm, refute, or say you cannot tell)

1. **Clean scheduled cycles.** The plan says NC has no clean *scheduled* weekly scrape on record: 2026-09-09 you found zero; the
   first cloud runs crashed on `start=` (OPEN-321, fixed in v30 on 10-05); the 10-18 02:00 UTC run failed to load (OPEN-397); the
   **10-11 cycle is not in any note I read**. For each Sunday 02:00 UTC `secondary` run since v30 (10-11, 10-18) and any other NC
   scrape you know of: run id, start and end, exit result, object count, any block signature, any `#automation-errors` alert for
   `nc`. Is there any scheduled cycle you would call clean? The next scheduled NC scrape is 2026-10-25 02:00 UTC.
2. **Manifest status.** What does `nc.status` say in `jurisdictions.yaml` in the production checkout, and has anyone flipped it
   to `live`? (Main of `ddp-open-states` said `probing` on 2026-10-20.)
3. **OPEN-231 comments.** Is there a recorded VoteBot NC check (the 2026-09-03 plan section assigned it to you as a comment on
   OPEN-231), a closing-cycle Tier 2 re-run (`quality_check.py --coverage nc <session> --tier2-limit 250 --tier2-random`), or any
   statement that Stage 6 is complete? If it was done, please give the ticket comment or note that holds it.
4. **LegislativeSession for NC.** The plan says BROKER-159's fix (ddp-broker-py #376, merged 2026-09-28) is *probably* live because
   the 10-19 and 10-20 LegBot runs worked, but nothing records it. Please check: does production have a `LegislativeSession` row for
   NC `2025` (and `2025E1`), what created it, and does the production broker's running commit include #376?
5. **Archive.** NC is in `openstates_archive.jurisdictions` (Thursday slot). What did the NC archive runs on 10-08 and 10-15 do (or
   did they not run), and does `ddp_bill_version_document` now hold NC rows? (On 2026-09-14 it held zero.)
6. **Version-document recompute.** Your 10-16 note records the OPEN-352 Part 3 recompute for nc, wa, mi, al, az as done with every
   gate passed, while the ticket text read earlier said no `--commit` was authorized. Please confirm NC's recompute was committed
   and give the counts.

## Please also say

- Anything above you did not check, and anything you checked from memory of an earlier note rather than fresh evidence.
- Anything else you know of that Ramon or the plan treats as open for NC but you consider finished, or the reverse.

Reply as a new note on this branch (`reply-nc-pilot-completion-status-<date>.md`). Do not edit this note.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
