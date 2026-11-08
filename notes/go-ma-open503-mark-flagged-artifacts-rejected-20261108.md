# GO: mark all artifacts of the 2,445 flagged Massachusetts bills REJECTED in the production broker (OPEN-503). Ramon's go, 2026-11-08 (Mac side). Follows `39694f4`.

**Ramon (2026-11-08):** "you can test that against the dev broker and then ask the prod agent to do the real rejection". The dev test is done; this is the ask. Nothing is deleted; the rows stay and can be re-approved in the admin.

## Dev test (Mac's dev broker, `ddpbroker-web-1`, mirrors production exactly: 2,445 bills, 19,560 artifacts, 6,814 complete+approved and 12,746 failed+approved)
- Recorded each artifact's prior (`review_status`, `reviewed_by`), then for every artifact set `review_status = BillArtifact.ReviewStatus.REJECTED`, `reviewed_by = <superuser>` and `save()` (what the admin's `mark_rejected` does). **19,560 rows in 9 seconds.**
- After: 19,560 rejected (6,814 complete, 12,746 failed), none approved.
- `/api/bill-artifacts/current/` for H5665, S2719, HD4395: before `found: true` with 7, 7 and 2 artifacts; **after `found: true` with 0 artifacts each** (so expect an empty set, not `found: false`).
- `public_bill_topics()` rows on the flagged bills: 3,361 before, **0 after** (the `BillTopic` rows stay, hidden by the rejected-source rule); all Massachusetts bills still show 19,785 public topic rows.
- Not tested on dev: ddp-sync's behaviour toward a rejected row, and the website.

## What to do (one run, same gates as before: quiet window, restore point first)
1. Re-run Part 1's counts (`39694f4` items 1-3). **Proceed only if they still read 6,814 complete+approved and 12,746 failed+approved, no staff edits, no polls, no real-person review. If anything differs, stop and report.**
2. Reject **all 19,560** (approved-status artifacts of these bills, both complete and failed), per row with `save()` (not `queryset.update()`), `reviewed_by` = the staff user you choose (say which). Print counts before and after.
3. Verify: no `complete`+`approved` artifact remains for these bills; `public_bill_topics()` shows 0 rows for them; the five bills you read last time (S2719, H5665, HD4395, SD3207, SD3069) return an empty artifact set from `/api/bill-artifacts/current/`; nothing else changed (total Massachusetts bills still 11,044; a count of approved artifacts for all other bills unchanged).
4. Rollback, for the record: set those rows back to `approved`, `reviewed_by` empty. I have the dev backup format (id, status, reviewer) if you want the same list.
5. Reply `reply-ma-open503-mark-rejected-done-20261108.md`; if you hit a stop, say so. Do not touch Webflow, the website, search indexes or the other states.
