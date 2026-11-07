# Request: `recompute-diff-order ma` on RDS to apply the new Massachusetts title rule (OPEN-498). **Part 1 (read-only, the dry run) now. Part 2 (the commit) HOLDS until a note from Ramon on this branch says GO for `ma`, which also has to say it lifts the OPEN-396 hold.** 2026-11-06 (Mac side)

**What this does.** About 27% of Massachusetts "bills" are not bills: agency reports, study and extension orders, amendment papers, messages and rules filed under HD / SD / H / S numbers, all with the note "Bill Text". LegBot was being asked to analyse them and refused (AGENTS-79). openstates-core now decides "is this a real bill version" for Massachusetts from the bill's **title** (a real measure opens "An Act", "Resolve(s)", "A Resolve", "Resolutions", "Joint Resolution" or "Proposal"); everything else is saved as `is_bill_version = false`, which api-v3 (OPEN-422) already hides and ddp-sync already skips. The commit sets that mark on Massachusetts documents already saved. No new column, no migration, no api-v3 or ddp-sync change.

**Code (done, not yours to build).** openstates-core fork `main` **`250de777`** (PR #84, on top of `47e9b768`). Image **`ddp-scrapers:v46`**, digest `sha256:faa680f802aff3256676b41a23d9f8cfff41bd319ee48aed2ad092a494530395`, pushed 2026-11-06 21:19 ET; **task-definition revision 48 registered 2026-11-06 about 21:30 ET** (previous v45 / revision 47). Ramon ran the register step himself.

## 0. Heads-up (read, no action unless something looks wrong)
Your status note expects tonight's Pennsylvania launch (04:00 UTC) on **v45 / revision 47**. Revision 48 was registered after that note, so **the launch will run v46 / revision 48** (the ECS family resolves to the latest revision). v46 was built from `main` of openstates-core and of ddp-open-states at 2026-11-06 21:1x ET; the only core change I know it adds over v45 is OPEN-498, and the only Massachusetts-specific behaviour is the title rule. **I did not compare v45 and v46 file by file, so please report in the launch reply which revision it ran and watch that run as planned.** If you would rather the Pennsylvania launch stay on v45, say so on this branch and Ramon can deregister revision 48 (`aws ecs deregister-task-definition --task-definition ddp-scrapers:48`); I have not done that.

## 1. Part 1: read-only (do now)
1. **G1 (code).** The environment you run `recompute-diff-order` from carries `250de777` (`openstates/__init__.py` path and `git rev-parse HEAD`, or the v46 image id and tag). Say which.
2. **G2 (rollback point and quiet).** Record the RDS latest restorable time. Nothing in flight (no ECS task, scrape, archive, load, LegBot relay, backfill), no ddp-sync job in the last 10 minutes, and propose a window clear of 02:00, 02:30 and 03:00 UTC, Sunday 02:00 UTC and the archive windows. Report the dry run's duration.
3. **G3 (baseline on RDS, read-only):**
```sql
SELECT count(*) AS docs,
       count(*) FILTER (WHERE d.is_bill_version IS NULL)  AS flag_null,
       count(*) FILTER (WHERE d.is_bill_version IS TRUE)  AS flag_true,
       count(*) FILTER (WHERE d.is_bill_version IS FALSE) AS flag_false,
       count(DISTINCT d.bill_id) AS bills,
       count(*) FILTER (WHERE d.diff_from_previous_version IS NOT NULL) AS with_diff
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name='Massachusetts';
```
4. **Dry run (writes nothing):** `recompute-diff-order ma --dry-run`. Report **every line it prints**, start and end time. What I expect, and how to read it: `is_bill_version: set=N changed=N not_a_version=N` with `not_a_version` **about 3,267** (that is the number of Massachusetts *bills* the rule excludes on the Mac copy of the 194th session, 11,872 bills; the dry run counts *documents*, so if a bill has more than one document the figure is higher, and I will compare yours with the Mac replica's own count). The diff counters (`corrected`, `nulled`) should be **0 or tiny**: the title rule does not change diff lineage, so a large number there means something else is stale and **you stop and report**.
5. **Reply** `reply-recompute-diff-order-ma-preflight-20261106.md` with G1, G2, G3 and the lines. Then wait.

## 2. Part 2: the commit (only after a GO note for `ma`)
Dry run first, printing exactly what Part 1 printed (if anything changed, report and wait); then `recompute-diff-order ma --commit` printing the same numbers; then `--dry-run` again, which must print **`corrected=0 nulled=0`** and `changed=0`; then the G3 query: `flag_null` = 0 and `flag_false` = the `not_a_version` figure. Report lines, rows, times (UTC), that nothing else changed. Rollback is the G2 restore point, or, for the flag only, reverting the rule and rerunning the recompute (tested: it sets a wrongly-false document back to true); do not undo by hand without telling me.

## 3. Not authorized
`recompute-diff-order ma --commit` before the GO note, **which must also say it lifts the OPEN-396 hold** (290 Massachusetts changelogs rejected and hidden; a Massachusetts LegBot trigger would regenerate them live; this request does not touch that, and nothing here triggers Massachusetts); `recompute-diff-order all`; any other state; a search-index refresh (it may be needed after the commit, a separate request); cleaning up the roughly 2,000 HD/SD Bills already in the broker or published artifacts; any scrape, archive, schedule, restart, LegBot run, or change to ddp-sync or the broker.

## 4. What I check on the Mac side (not yours)
Before Ramon's GO I post the list of the documents whose mark would change true to false (titles, not text) for him to read. After the commit: the Mac replica applied it (lag, no errors), the same counts, one known report end to end (SD 4329: flag false, api-v3 shows no `raw_text`, ddp-sync logs "No archived bill text"), and H 3188 and SD 3237 still readable as real bills.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
