# REQUEST (not a GO): the next scrapers image carries the 2027 session changes (OPEN-659); Nevada's first run scrapes its pre-filed 84th bills. 2026-11-20 (Mac side, Onboard New States)

**Ramon, 2026-11-20 (relayed by the PM session):** "start setting all of our jurisdictions to their 2027 sessions ... most of them are already pre-filing bills for 2027 that we need to start scraping".

**This waits for two things:** both PRs below merged, and Ramon's go. It needs no image of its own: it can ride the next scrapers image (for example the one in `ddf23c9`, SYNC-181).

## What changes (openstates-scrapers fork)
* **#135** Nevada's 84th (2027) session is **active now**. Nevada lists about 190 pre-filed bills. The 2025 special session (`2025Special36`) stays active beside it until 84 starts on 2027-02-01.
* **#136** Florida 2027 dates become 2027-03-02 to 2027-04-30 (they were placeholders, 13 Jan to 13 Mar). Utah 2027 dates become 2027-01-19 to 2027-03-05. No active flag changes.

**No ddp-sync change in this request.** Nevada and Florida have no `sessions:` list, so they scrape every active session.

## What I need from you, after the go
1. **Gate:** the image you build or register contains both merge commits. Check with `git -C <build checkout>/openstates-scrapers merge-base --is-ancestor <merge> HEAD` for each one. If either is missing, stop and report.
2. **The release itself:** done the usual way (RUNBOOK, scrapers image). Nothing else rides on this request.
3. **Nevada's next scheduled run** (Saturday 12:00 UTC, or a manual trigger if Ramon says so). Report:
   * the sessions the run scraped. Expected: `84` and `2025Special36`.
   * the count of Nevada bills in session `84` afterwards. Expected: about 190, and not 0.
   * that the load and archive finished.
   * Read-only SQL:
     ```sql
     select s.identifier, count(b.id) from opencivicdata_legislativesession s
       join opencivicdata_jurisdiction j on j.id = s.jurisdiction_id
       left join opencivicdata_bill b on b.legislative_session_id = s.id
      where j.name = 'Nevada' group by 1 order by 1;
     ```
4. **Florida's next run:** the stored 2027 session row should read `start_date 2027-03-02`, `end_date 2027-04-30`. It holds the placeholders today. Report what it reads; if it did not update, say so, and do not edit the row by hand.

**Rollback:** if Nevada's run fails on 84, revert #135 (one line) in the next image. Nothing stored needs undoing.

## What I check on the Mac afterwards
* On the replica: Nevada `84` bills, and Florida 2027's dates.
* api-v3 should **not** show Nevada 84 as current before 2027-02-01. That is by design: pre-filed bills are stored but not shown until the session starts, which is a separate decision for Ramon.

## Not authorized
Any other state; a session added or removed beyond these PRs; any ddp-sync change (`usa` keeps `119`; the 120th Congress is a later request before 2027-01-03); any data edit; a manual run unless Ramon says so.

Tickets: OPEN-659 (OPEN-606, OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
