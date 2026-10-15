# REQUEST: OPEN-352, go live with the fixes and recompute stored diffs for NC, WA, MI, AL. **HOLD until Ramon says GO.** (Mac side, 2026-10-15 EDT)

**STATUS: NOT AUTHORIZED YET.** Ramon asked (2026-10-15, Mac session) for this request to be written. **Do only Part 1 (read-only) now.** Part 2 (deploy) and each state in Part 3 (real runs) start only when a note from Ramon on this branch says GO for that part. A failed gate is not permission to improvise: stop and report. If a HOLD or change note from Ramon appears, follow it instead.

Jira: OPEN-352 (audit, closed) and its fix tickets OPEN-365, 366, 367, 369, 371, 372, 373 (all closed, code merged, nothing deployed). Dry-run evidence: `reply-open352-recompute-dry-runs-nc-wa-az-mi-al-20261015.md` and `reply-open352-isolation-dry-runs-az-al-before-the-fixes-20261015.md`.

**Out of scope, on hold by Ramon's decision:** Arizona's recompute (it carries a backlog of 3,697 stored diffs unrelated to these fixes; OPEN-368 decides its ordering first), Massachusetts (OPEN-370, a separate hide), Utah (done, OPEN-351), Florida, Virginia, the US.

## 0. What is merged (and what each part changes)

openstates-core `main` at **`cbf13925`**: Alabama amendment-excerpt exclusion and cleaner (#61, #66); North Carolina stage rules, stamp-page exclusion and cleaner (#62, #65); blank-page handling (#63); Washington introduced-resolution stage (#67).
api-v3 `main` at **`5a0ee983`**: North Carolina stage rules (#26), blank-page picker (#27), last-document-by-URL picker (#28), Washington stage rule (#29).

Effect on stored data once the recompute runs (dry-run lines at `cbf13925`):
`nc: 2338 bills | unchanged=2588 corrected=3550 nulled=54`, `wa: 3411 bills | unchanged=11596 corrected=40 nulled=0`, `mi: 4134 bills | unchanged=14336 corrected=32 nulled=2`, `al: 1507 bills | unchanged=1960 corrected=918 nulled=45`.

## 1. Part 1: read-only preflight (do now, no GO needed)

1. **G1 (core code).** Same method as before: the runtime will be a build of `cbf13925`; for the recompute commands use a separate `git worktree` at `cbf13925` first on `PYTHONPATH` with the existing venv, existing installs untouched. The snippet from `request-open352-recompute-dry-runs-...` must print `OK`.
2. **G2 (rollback points).** Record the latest automatic RDS backup / point-in-time window timestamp, and the current Fargate task definition revision and the current RDS-backed api-v3 image/commit (what you would roll back to).
3. **G3 (baseline on RDS, read-only).** Run the four counting queries below and record the rows; they are the "before" for Part 3's checks:
```sql
-- run once; the result has one row per check
SELECT 'nc stamp pages with a diff' AS check_name, count(*) AS n
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name='North Carolina' AND d.is_error=false AND d.diff_from_previous_version IS NOT NULL
  AND d.version_note ~* '^a([1-9][0-9]*)?: amendment$'
UNION ALL
SELECT 'nc Edition/Ratified/SL with a diff', count(*)
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name='North Carolina' AND d.is_error=false AND d.diff_from_previous_version IS NOT NULL
  AND (d.version_note ~* '^edition [1-9][0-9]*$' OR d.version_note ~* '^ratified$' OR d.version_note ~* '^sl [0-9]{4}-[0-9]+$')
UNION ALL
SELECT 'al amendment-family documents with a diff', count(*)
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name='Alabama' AND d.is_error=false AND d.diff_from_previous_version IS NOT NULL
  AND d.version_note ~* '^.+[[:space:]]amendment( offered)?$'
UNION ALL
SELECT 'mi blank documents with a diff', count(*)
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name='Michigan' AND d.is_error=false AND d.diff_from_previous_version IS NOT NULL
  AND d.raw_text <> '' AND d.raw_text ~ '^[[:space:]]*$';
```
Expected before: about 54, 0, 45, 2.
4. **G4 (quiet window).** No scrape, archive or load in flight for these states; stay at least an hour clear of the weekly scrape (Sunday 02:00 UTC; next 2026-10-18) and Monday 05:00 UTC. Report the window you propose.
5. **Heads-up to check, not to act on:** after the api-v3 deploy about **316 versions** will present a different document (`archived_document_id`: US 173, VA 50, WA 117+, AZ 16, AL 1, NC 1; counts from the replica), so the knowledge-base ledger comparison will see them as changed and may re-embed them. Say which process does the embedding on your side, whether its orphan-removal circuit breaker would trip on about 316, and what you expect.
6. **Report Part 1** in a `reply-open352-golive-preflight-...` note. Then wait for GO.

## 2. Part 2: deploy (needs GO for Part 2)

Order matters: **api-v3 on both instances before any recompute**, so the version array and the picker agree with the archiver's rules.

1. **api-v3 `5a0ee983`:** the RDS-backed instance (yours) and the Mac's instance (Ramon, Mac side; he will confirm in a note). **Both must run the same commit before Part 3.** After deploy, confirm with a read through each instance's API: a North Carolina bill with an `Edition 1` version reports `version_stage: amendment` (before: `unknown`), and a Washington `Joint Memorial` reports `introduced`.
2. **openstates-core `cbf13925`** into the runtime that archives new data (the same way OPEN-351 did it: a new task-definition revision; the old revision is the rollback). Existing host installs stay untouched.
3. Record exact commits, revision numbers and times. Do nothing else (no flag, schedule, scrape, archive or LegBot run).

## 3. Part 3: stored-data recompute, one state at a time (needs GO for that state)

For each of **`nc`, `wa`, `mi`, `al`** (in that order; one state per command; **never `all`**), with the Part 1 environment:

1. `recompute-diff-order <state> --dry-run` must print **exactly the same three numbers as above**. If the data changed since (new archive) and they differ, report the line and wait.
2. `recompute-diff-order <state> --commit` must print the same numbers (`[COMMITTED]`).
3. Immediately `recompute-diff-order <state> --dry-run` again: must print `corrected=0 nulled=0` (nothing left to change).
4. Re-run the Part 1 G3 query: NC stamp pages with a diff = **0**, NC Edition/Ratified/SL with a diff about **3,550**; AL amendment-family with a diff = **0**; MI blank with a diff = **0**.
5. If the commit's numbers differ from the dry run, the command errors, or it stops partway: stop and report; documents are saved one at a time with no transaction, so some may already be written; do not retry and do not roll back without authorization.

## 4. Expected consequences (accepted by Ramon, 2026-10-15)

* **Existing changelogs are not regenerated** by any of this.
* **North Carolina will start generating changelogs on its own.** NC has none today. After its recompute, ddp-sync's coverage check will see about 3,550 new transitions, so the next changelog run may write up to about 3,550 NC changelogs, which go live automatically (`BILL_ARTIFACT_REQUIRE_REVIEW=false`). Ramon chose not to hold this. **Do not start any run; the existing schedule and trigger decide.** Report if you see one start.
* Alabama's scrape is off, so its recompute has no live effect yet.

## 5. Reply

A `reply-open352-golive-...` note after each part: gates, commits and revisions, exact command output lines, G3 before and after, times. If a gate stopped you, say which and what you saw.

## 6. Not authorized

Anything in Part 2 or 3 before a GO note from Ramon for that part; `recompute-diff-order all`; Arizona, Massachusetts, Utah or any state not named; any flag, schedule, scrape, archive, embedding or LegBot run; changes to existing installs; rolling back without authorization.
