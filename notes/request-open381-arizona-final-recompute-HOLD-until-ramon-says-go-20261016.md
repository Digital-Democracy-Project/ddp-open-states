# REQUEST: OPEN-381, the final Arizona `recompute-diff-order`. **Part 1 (read-only, including a dry run) now; Parts 2 and 3 HOLD until Ramon says GO.** (Mac side, 2026-10-16 EDT)

**STATUS:** Ramon asked (Mac session, 2026-10-16) for this request. **Do only Part 1 now.** It is read-only: nothing is deployed, committed or restarted. Part 2 (deploy api-v3) and Part 3 (the real recompute) start only when a note from Ramon on this branch says GO for that part. A failed gate is not permission to improvise: stop and report. If a HOLD note from Ramon appears, follow it instead.

Jira: **OPEN-381**; the merged code is OPEN-368 (#68, api-v3 #30), OPEN-379 (#69) and OPEN-382 (#70, api-v3 #31). Its follow-up is OPEN-383 (regenerate Arizona's summaries), not part of this.

## 0. What changed since the last Arizona recompute

The OPEN-352 Arizona recompute (`reply-open352-golive-part3-...`, 02:24 UTC) applied the blank-page nulls and the missing-cleaning backlog. Three code changes merged after it:
* **OPEN-368:** Arizona's committee and floor-action versions tie on stage; they are now ordered by the number in `GetDocumentPdf/<id>` (a 30-bill check against azleg.gov's dates found 0 contradictions).
* **OPEN-379:** failed floor amendments (16 versions in the archive, 11 distinct notes) take no diff and are not a baseline.
* **OPEN-382:** House and Senate Engrossed Versions are placed among the action documents by the bill's origin chamber (the bill identifier: HB/HCR... House, SB/SCR... Senate). A Mac-side check over all 2,190 Arizona bills found 1,484 predecessor changes in 538 bills.

Code: openstates-core `main` **`53feef5b`**; api-v3 `main` **`ba0b6468`**.

## 1. Part 1: read-only (do now)

1. **G1 (code).** Same method as before: a throwaway `git worktree` at exactly `53feef5bdde1f277195719a9144f88f6c38fe4dc`, first on `PYTHONPATH`, the existing venv's Python, existing installs untouched. In that environment this must print `OK` (note `origin_chamber` and `document_number`, new in this build):
```python
import inspect, openstates
from openstates.utils.version_ordering import (
    is_procedural_document as p, version_sort_key as k, note_stage, STAGE_INTRODUCED,
    origin_chamber, document_number)
from openstates.cli.text_extract import (
    _has_text, _clean_nc_text, _clean_al_text, recomputed_diffs_for_documents)
assert "bill_identifier" in inspect.signature(recomputed_diffs_for_documents).parameters
assert p("North Carolina", "A1: Amendment") and not p("North Carolina", "A1: ABR-9-V-1")
assert k("Filed", "") < k("Edition 1", "") < k("Edition 2", "") < k("Ratified", "") < k("SL 2025-14", "")
assert p("Alabama", "Judiciary 1st Amendment") and not p("Alabama", "Judiciary 1st Substitute")
assert note_stage("Joint Memorial")[0] == STAGE_INTRODUCED
assert not _has_text("\n \n") and _has_text("A")
assert p("Utah", "Comparison to Sub #1") and not p("Utah", "Amended 2/12/2026 10:02:409")
assert p("Arizona", "SENATE - Ortiz flr amend (ref Bill) failed")
assert not p("Arizona", "SENATE - Finchem flr amend (ref FED) adopted")
az = lambda i: [f"https://apps.azleg.gov/BillStatus/GetDocumentPdf/{i}"]
assert k("HOUSE - Education", "", az(100)) < k("HOUSE - Appropriations", "", az(200))
assert document_number(az(536047)) == 536047 and document_number([]) == 0
assert origin_chamber("HB 2014") == "house" and origin_chamber("SCR 1049") == "senate"
h = lambda n, u=(): k(n, "", u, "house")
assert h("HOUSE - Judiciary", az(5)) < h("House Engrossed Version") < h("SENATE - Natural Resources", az(1)) < h("Senate Engrossed Version")
s_ = lambda n, u=(): k(n, "", u, "senate")
assert s_("SENATE - Judiciary", az(5)) < s_("Senate Engrossed Version") < s_("HOUSE - Education", az(1)) < s_("House Engrossed Version")
print("OK", openstates.__file__)
```
2. **G2 (rollback points).** Record the RDS latest restorable time and your current api-v3 image tag (the one to roll back to, `pre-open381` or similar).
3. **G3 (baselines on RDS, read-only).** Report these rows (they are the "before"):
```sql
-- Arizona only
SELECT 'az documents with a failed-amendment note' AS check_name, count(*) AS n,
       count(*) FILTER (WHERE d.diff_from_previous_version IS NOT NULL) AS with_diff
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name='Arizona' AND d.is_error=false AND d.version_note ~* '^(house|senate) - .+[[:space:]]failed$'
UNION ALL
SELECT 'az documents total', count(*), count(*) FILTER (WHERE d.diff_from_previous_version IS NOT NULL)
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name='Arizona' AND d.is_error=false;
```
Expected: the failed-amendment row about 16 versions' documents, all with a diff today; the total row matches the last run (Arizona's 5,105 + 3,697 + 131 = 8,933 documents, minus what the OPEN-352 run nulled, so check against its `summary.json`).
4. **Dry run (read-only, writes nothing).** In the G1 environment: `recompute-diff-order az --dry-run`. **Report the exact line.** There is no expected line to match: this is the first Arizona run on this code, so its numbers become the gate for Part 3. Rough scale for comparison only: Mac-side measurement found 1,484 lineage versions (in 538 bills) getting a different predecessor, plus the 16 failed-amendment versions losing their diff, counted by document (PDF and HTML twins), so `corrected` in the low thousands is plausible; `nulled` should be about the failed-amendment documents (16 or more). If the line looks very different from that, say so; it is information, not a reason to do anything.
5. **Quiet window and proposal.** Check no scrape/archive/text-extract is running; propose a window (the weekly scrape is Sunday 02:00 UTC; finish at least an hour before).
6. **Report Part 1** in a `reply-open381-preflight-...` note. Then wait for GO.

## 2. Part 2: deploy api-v3 `ba0b6468` (needs GO for Part 2)

Same as OPEN-352's Part 2: tag the current image as the rollback, `git pull --ff-only` in `/opt/ddp-open-states/api-v3` to `ba0b6468`, build and swap only the `api` container, check. After: an Arizona bill with an Engrossed version (for example `HB 2014`, 2026 2nd regular) returns `House Engrossed Version` **after** `HOUSE - Natural Resources, Energy & Water` and `HOUSE - Appropriations` and **before** `SENATE - Natural Resources` (before, the Engrossed versions came first). The **Mac's** api-v3 is Ramon's side; **Part 3 must not start until a note on this branch confirms the Mac's api-v3 is on `ba0b6468`.**

## 3. Part 3: the real recompute (needs GO for Part 3)

After Part 2 and Ramon's Mac confirmation: `recompute-diff-order az --dry-run` must print **exactly the line you reported in Part 1** (if new data was archived and it differs, report and wait), then `--commit` printing the same three numbers, then a second dry run with `corrected=0 nulled=0`, then the G3 rows again: failed-amendment documents with a diff **0**. Record the restorable time just before the commit. One state, never `all`. If a commit differs from the dry run, errors, or stops partway: stop and report; no retry, no rollback without authorization.

## 4. Accepted consequences

Existing Arizona summaries (about 1,907) are **not** regenerated (OPEN-383 is that, later). A stored recompute only rewrites the diff column.

## 5. Not authorized

Anything in Part 2 or 3 before a GO note for it; `recompute-diff-order all` or any state but Arizona; any flag, schedule, scrape, archive, embedding or LegBot run; changes to existing installs, the Fargate task definition (a separate request), or `delete_orphans`; rolling back without authorization; the Arizona summary regeneration.
