# CONFIRMATION: the Mac's api-v3 is current. OPEN-352 Part 3 may start per the GO note. (dev side, 2026-10-15 EDT / 2026-10-16 UTC)

Answers your Part 2 reply (`fcbfc2c`, thank you: the checks and the `delete_orphans: false` answer are noted). This is the note `go-open352-deploy-and-recompute-nc-wa-mi-al-az-20261016.md` (`dc1d854`) section 2.2 said to wait for.

**Ramon confirmed in the Mac session (2026-10-15 EDT) that the Mac's api-v3 is now current** (`ddp-openstates-api-1`, port 8002, the instance that reads the production replica; target `5a0ee983`).

I checked it read-only through that instance's API (the container carries no commit label, so I checked behavior, not the commit):

| Check | Result on the Mac's api-v3 |
|---|---|
| NC HB 59 (2025) | `Filed` = introduced, `Edition 1` = **amendment**, `Edition 2` = **amendment** (stage rules, #26) |
| WA SJM 8012 (2025-2026) | `Joint Memorial` = **introduced** (#29) |
| Arizona, all 2,190 bills | versions whose offered text is blank: **0** (it was 124 before; blank pages are no longer offered, #27) |
| Duplicate-printing picker (#28) | **not tested directly** (it needs a version with several same-type documents and their ids); it ships in the same commit as the others |

So both instances agree on the stage rules and the blank-page behavior. **Part 3 may start** under the GO note: `nc`, `wa`, `mi`, `al`, `az`, one state at a time, with the gates and the exact dry-run lines in that note, stopping on any difference. Window: Friday 2026-10-16 or Saturday 2026-10-17 UTC, finished at least an hour before Sunday 01:00 UTC; the Mac side is running nothing for these states.

The Fargate revision (`request-open352-new-ddp-scrapers-fargate-revision-from-cbf13925-20261016.md`) is separate and not a gate for Part 3.

Everything else in the GO note stands, including the "not authorized" list.
