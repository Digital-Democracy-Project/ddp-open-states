# GO update: SYNC-175's production steps are WITHDRAWN; OPEN-390 (NC first-time changelogs) runs NOW. Answers `93bf7de`. 2026-11-17 (Mac side)

**Ramon, 2026-11-17** (via the PM session; recorded on SYNC-175 comment 21225 and OPEN-390 comment 21226):
* SYNC-175: "we can do a legbot sample run for LA and NE to test the latest changes. just understand that those results will get wiped, so i wouldn't do more than about 100 bills".
* OPEN-390: "Go now".

## 1. SYNC-175: nothing runs on production (answers your `93bf7de`)
You're right. A summary or changelog row exists only after a LegBot run, and this broker has 0 LA, 0 NE and 0 AL bills, so there's nothing to rewrite. The LA/NE results the request counted on were written on the Mac side (dev sample runs), not on production, and they get wiped at the next broker release.
* **`go-sync175-legbot-rewrite-la-ne-20261117.md` (`78b3ca4`) is withdrawn in full.** Don't reject, back up, generate or trigger anything for LA or NE on this host.
* What replaces it is a **Mac-only sample run of about 100 LA/NE bills**, run by the Mac side. It needs nothing from you.

## 2. OPEN-390: run now
**Run `go-open390-nc-first-time-changelogs-20261117.md` (`78b3ca4`) as written, starting now.** It no longer waits for SYNC-175. Unchanged:
1. **Count first (read only):** NC `bill_changelog` rows on this broker, by session and status. Expected about 0 for `2025` (the broker has 2,343 NC bills). If any exist, list them and say whether any was written from a stamp page or an amendment paper.
2. **The ten-bill test,** all ten read against their comparisons, before going on.
3. **Batches of at most 100 bills:** `bill_changelog` only, `include_org_research: false`, `include_concept_statements: false`, `retry_failed: false`, `background: true`, `dry_run: true` first.

Timing rules, real reasons only:
* no other LegBot run in flight (the trigger lock; wait, don't force);
* not during the Mac's organization-logo catch-up (shared CAMS);
* no Mac ddp-sync restart or CAMS reload while a batch is in flight.

Stop conditions and the "Not authorized" list are as in that note.

## Not authorized
Anything for LA, NE or WA on this host; any other state; any artifact type other than `bill_changelog` for NC; organization research.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
