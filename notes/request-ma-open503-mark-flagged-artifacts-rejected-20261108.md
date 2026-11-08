# Request: mark the artifacts of the 2,445 flagged Massachusetts bills REJECTED in the production broker (OPEN-503). **Part 1 (read-only count) now. Part 2 (the change) HOLDS until a note from Ramon on this branch says GO.** 2026-11-08 (Mac side)

Reply to your `8d78cd8` (thank you: the identifier and OpenStates-id traps are noted). **Ramon's decision (2026-11-08):** take them down the way the broker normally does, by marking them **rejected**, not by deleting: "we normally just mark them as rejected in the broker." So nothing is deleted.

**The mechanism (read from ddp-broker-py, not run).** The admin action `BillArtifactAdmin.mark_rejected` (`common/admin.py`) sets `review_status = BillArtifact.ReviewStatus.REJECTED` and `reviewed_by = <a staff user>` and calls `obj.save()` per row. `legbot_requests.redo` does the same two fields. Use `save()`, not `queryset.update()`: the `post_save` receivers (the `bill_topics` sync, the search rule) must run, and a rejected `bill_topics` source is what hides topics. The public endpoints serve only `complete` + `approved`, so rejecting the approved ones removes them from the site; rows stay and can be re-approved from the admin.

## Part 1: read-only (do now)
For the 2,445 bills in `notes/ma-open503-flagged-bills-in-dev-broker-20261107.csv` (remove the space from each identifier, as you found), with the `bill__in=<Bill rows>` relation:
1. Count artifacts by `(review_status, status)`; expected from your last note: 6,814 complete+approved, 12,746 failed+approved. Say if anything changed since (new artifacts, edits, rejections).
2. Which staff user the change should be recorded under (`reviewed_by`), and whether setting a person-rejected row blocks ddp-sync from writing a replacement later (BROKER-272: a write lands `pending_review` when it would displace a row a person rejected). We expect that is what we want; confirm, and say what ddp-sync will do for these bills if a Massachusetts sync runs (it should skip them: "No archived bill text").
3. Anything that reads the artifacts and would behave oddly when 1,808 bills lose them all at once (alerts, search index, Webflow sync, the website cache). Say what you can read; say what you cannot.
4. Reply `reply-ma-open503-mark-rejected-preflight-20261108.md`. Then wait.

## Part 2: the change (only after a GO note)
Rejecting **only** the `complete`+`approved` artifacts (6,814) or all 19,560? Part 1 should recommend; default **all approved-status artifacts of these bills** (the failed ones are not public anyway, but marking them keeps a later approve-all from publishing them). Take a restore point first, run in the quiet window, print counts before and after, and then repeat Part 1's count: no `complete`+`approved` artifact may remain for these bills, `bill_topics` rows from them must no longer show, and the five bills you checked (S2719, H5665, HD4395, SD3207, SD3069) must now return `found: false` or empty from `/api/bill-artifacts/current/`.
