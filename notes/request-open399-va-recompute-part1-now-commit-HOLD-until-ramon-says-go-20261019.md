# REQUEST: OPEN-399, recompute Virginia's stored diffs without the page-footer tail lines, then regenerate the affected changelogs. **Part 1 (read-only, including a dry run) now; Parts 2 and 3 HOLD until Ramon says GO for each.** (Mac side, 2026-10-19 EDT)

**STATUS:** Ramon asked (Mac session, 2026-10-19) for this request. **Do only Part 1 now.** It is read-only: nothing is deployed, committed, rejected or regenerated. Part 2 (the real recompute) and Part 3 (changelog regeneration) start only when a note from Ramon on this branch says GO for that part. A failed gate is not permission to improvise: stop and report. A HOLD note from Ramon overrides this one.

Jira: **OPEN-399** (the fix, merged), **OPEN-393** (Virginia changelog triage). Code: openstates-core fork `main` **`4f023bec60c0d9425472ead0927b7f82234cc936`** (PRs #71 Virginia and #72 Massachusetts). Image: **`ddp-scrapers:v37`, task-definition revision 40**, registered by Ramon on 2026-10-19 (digest `sha256:7ad6d1851c0d04ad8315bf26a855dc2e4148d54ea378bba1895494eae16a4b5a`; the Mac side confirmed the fix is inside the image; your role cannot describe ECS, so you cannot re-check that, and nothing here needs it).

## 0. What this fixes, and how many changelogs it touches

Virginia's PDF text leaves the tail of a printed page footer ("Page 3 of 12" becomes a bare line `of 12`), often mid-paragraph. A different page count then shows it as a removed or added line in `diff_from_previous_version`, so a page-count change reads as a text change. On HB 979 it made the changelog report a donor-screening fee as removed; that claim was false. The fix drops those lines in the Virginia pre-diff cleaning; stored `raw_text` is never touched. New archives already use it (the v37 image). **This request fixes the diffs already stored.**

**Stored diffs (Mac replica of production, read-only):** the real dry run is `va: [DRY RUN] 4380 bills checked | unchanged=22749 corrected=2792 nulled=0`. Before the fix (core `53feef5b`, the old code) the same dry run reads `unchanged=25541 corrected=0 nulled=0`, so **every one of the 2,792 is this fix**. All 2,792 are PDF documents. For every one the net change in text lines is identical apart from the marker lines (checked over all 4,380 bills); 13,445 marker lines go. Of the 2,792, 2,738 contain a marker line in the diff text and 54 change only in their `@@` line numbers (an earlier footer line is gone, so every later offset moves).

**Changelogs (my estimate, you will compute the exact number in Part 1):** a changelog is affected if its version's diff (api-v3 serves the PDF's, since Virginia has no XML) is one of those 2,792. Against the 213 Virginia changelogs in the 2026-10-17 snapshot: **77 (36%) are affected**, on 54 bills; in **73 of them the marker is a changed line** (the HB 979 kind, the only kind that can have misled the model), in 2 only an unchanged context line, in 1 the diff is nothing but marker lines (HB 49, Commerce Agriculture & Natural Resources Subcommittee Substitute, whose summary still lists a change). HB 979 is among them (Finance Substitute and Subcommittee #3 Subcommittee Substitute). You reported 511 Virginia changelogs in production now (298 more than the snapshot), so if the share holds the total is about **185** (range 77 to 185); most will be unchanged in substance, since the diff's real edits are the same, and the point of regenerating is the few where the model was misled. Your exact count settles it.

## 1. Part 1: read-only (do now)

1. **G1 (code).** A throwaway `git worktree` at exactly `4f023bec60c0d9425472ead0927b7f82234cc936`, first on `PYTHONPATH`, the existing venv's Python, existing installs untouched (the OPEN-381 method). In that environment `notes/open399-va-recompute-20261019/g1_code_proof.py` must print `OK <path inside the worktree>`. (On the old code `53feef5b` it fails with an ImportError, which is what makes it a proof.)
2. **G2 (rollback point and quiet).** Record the RDS latest restorable time. Check no scrape, archive, load, text-extract, LegBot relay or backfill is in flight on this host, and propose a window clear (at least an hour) of the **Sunday 02:00 UTC** weekly job, **Virginia's archive Wednesday 05:00 UTC** and the other archive starts. A Virginia archive running on v37 while you recompute is harmless (it only adds new versions without markers) but leave it out of the window so the numbers are clean.
3. **G3 (baselines on RDS, read-only).** Report these rows:
```sql
-- stored Virginia diffs that still contain the footer tail as ANY kind of line (before)
SELECT count(*) AS docs_with_marker_line
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name='Virginia' AND d.diff_from_previous_version ~ E'(^|\n)[ +-][[:space:]]*[Oo][Ff][[:space:]]+[0-9]{1,3}[[:space:]]*(\n|$)';
-- Virginia bill_changelog rows by status (the broker side; you reported 511, all complete + approved)
```
Expected on the Mac replica: **2,738**. Production may be a little higher (anything archived since the replica copy).
4. **Dry run (read-only, writes nothing).** In the G1 environment: `recompute-diff-order va --dry-run`. Report the exact line. Gate: **`nulled` must be 0 and `corrected` should be about 2,792** (more only by what was archived since). If `nulled` is above 0, or `corrected` is far from 2,792 (say off by more than 10%), say so and stop; it is information, not a reason to do anything.
5. **The exact changelog list.** `notes/open399-va-recompute-20261019/VA_changed_docs.csv` has the 2,792 documents (ocd bill id, version note, media type, `archived_document_id`; the ids match production's, as your earlier id check did for OPEN-387). Join your production Virginia `bill_changelog` rows to it on (bill, new version note) and write the result as `VA_affected_changelogs_production.csv` (artifact id, gov_id, session, new version note, status, review_status), **with the count**. For comparison, `VA_affected_changelogs_snapshot.csv` is the same join over the 2026-10-17 snapshot (77 rows, with a flag for the changed-line kind). Report the production count and whether the snapshot's 77 artifact ids are all still there with the same status.
6. **Report Part 1** in a `reply-open399-va-recompute-preflight-...` note. Then wait for GO.

## 2. Part 2: the real recompute (needs GO for Part 2)

In the G1 environment: the dry run must print **exactly the line you reported in Part 1** (if new data was archived and it differs, report and wait), then `recompute-diff-order va --commit` printing the same three numbers, then a second dry run with `corrected=0 nulled=0`, then the G3 query again: **0** documents with a marker line. Record the restorable time just before the commit. Then read the HB 979 Finance Substitute diff from api-v3 and confirm it has no `of 12`/`of N` line. One state, never `all`. If the commit differs from the dry run, errors or stops partway: stop and report; no retry, no rollback without authorization. (Rollback if ever needed: check out the previous core commit and recompute again; `raw_text` is untouched.)

## 3. Part 3: regenerate the affected changelogs (needs a separate GO for Part 3)

Only after Part 2 verified. Use the procedure and safety rules in `notes/request-open387-live-bill-changelog-triage-and-per-state-rewrite-directions-20261018.md` on **ddp-sync's `notes/ops-handoff`** ("Rules for every state" and the trigger), applied to the list from Part 1 step 5: **the wording freeze** (nothing starts until Ramon confirms the changelog prompt is final), one state, one batch at a time (batches of 50 to 100 bills), back up the batch's review fields to a CSV first, a one-row test, reject only the batch you are about to run and run it at once (production auto-approves, `BILL_ARTIFACT_REQUIRE_REVIEW=false`), `X-DDP-Environment: prod` on every call, `dry_run: true` first, Ramon or you checking `cams status` is idle. Verify each batch: every rejected row `complete` and `approved` again; HB 979's new summary must not say the donor-screening fee was removed; read about 10 regenerated summaries against their diffs. Stop on any raw `{'...'}` object, empty output, row-count mismatch or still-failed row.

## 4. Not yours

Reverting ddp-agents PR #371 (the LegBot-side filter) is the Mac side's, only after Part 3 is verified; do not touch ddp-agents.

## 5. Not authorized

Anything in Part 2 or 3 before a GO note for it; `recompute-diff-order all` or any state but Virginia; **`recompute-diff-order ma --commit`** (it would null Massachusetts's 291 legacy cross-media diffs, a separate decision, OPEN-396); the Fargate task definition or image; any flag, schedule, scrape, archive, embedding or LegBot run you start outside Part 3; changing existing installs; rolling back without authorization.
