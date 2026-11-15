# Request (GO): rebuild Massachusetts' bill-versus-law comparisons on RDS, `recompute-diff-order ma` (OPEN-223). Export first, then a dry run, then **commit on your own only if the dry run matches the gate below**

**Ramon's go:**
- **2026-11-14 (/ask-me):** the recompute runs "Now, before launch", right after an image carrying core `016fc6b3a` is live and Massachusetts' Sunday run is done.
- **2026-11-15 ~21:00 UTC (/ask-me):** "Save if the trial matches". You commit without a second go **only** if the dry run passes the gate in step 3; anything else stops for him.

**Why:** Massachusetts' 291 stored comparisons of the enacted law against the bill as filed read as whole-document replacements (193 have no unchanged line), because the law (HTML) had no same-type earlier version to compare with. Core `016fc6b3a` (PR #96):
- compares a Massachusetts chapter law with the bill's previous PDF;
- leaves the one-sided title, enacting clause and "Approved" line out of that comparison only (never out of the stored text).

Measured offline over all 364 two-document bills: 193 → 7 with no unchanged line, 0 nulled, total changed words 1,221,228 → 591,483.

**Both conditions are met:**
- v58 = `ddp-scrapers:61` carries `016fc6b3` (checked in the image on 11-14; your US test `fb611a5`).
- Massachusetts' Sunday run is complete (your `29cffcd`, `openstates_pipeline: done` 17:51 UTC).

**Order with the other request tonight:** ddp-sync has a GO for the `ad68c4f` release (ddp-sync ops-handoff `9874e21`). **Do that one first.** Then run this one when quiet. If you can't finish this one by **02:00 UTC Monday**, run it after Pennsylvania's Monday nightly (04:00 UTC start) has finished its load and archive.

## What I need from you

### 0. Gates (stop and report if any fails)
- **G1, code:** run with openstates-core **`016fc6b3af`** (core fork `main` right now): either the code on `PYTHONPATH` in a throwaway worktree, as for earlier recomputes, or the v58 image. Say which. **Prove the rule is there:** `grep -n "_MA_CROSS_MEDIA_BASELINE" openstates/cli/text_extract.py` must find it. **Without it the command nulls all 291 comparisons: stop.**
- **G2, quiet:** no Massachusetts scrape, import, archive or LegBot run in progress, and no ddp-sync job line in the last 10 minutes. Record "now" (UTC) as the restore point.
- **G3, baseline on RDS (read-only):**
```sql
SELECT count(*) AS docs,
       count(*) FILTER (WHERE d.diff_from_previous_version IS NOT NULL) AS with_diff,
       count(*) FILTER (WHERE d.media_type = 'text/html') AS html,
       count(*) FILTER (WHERE d.media_type = 'text/html' AND d.diff_from_previous_version IS NOT NULL) AS html_with_diff,
       count(*) FILTER (WHERE d.is_bill_version IS FALSE) AS not_version
FROM ddp_bill_version_document d
JOIN opencivicdata_bill b ON b.id = d.bill_id
JOIN opencivicdata_legislativesession s ON s.id = b.legislative_session_id
WHERE s.jurisdiction_id LIKE '%state:ma/%';
```
  The Mac replica reads **12,222 | 291 | 365 | 291 | 3,246** (20:00 UTC today). Report RDS's row. A small difference is fine; say what it is.

### 1. Export (the restore path), before anything else
Copy every Massachusetts row's `(id, diff_from_previous_version)` out of `ddp_bill_version_document` (same join as G3) to a file on the host. Report the path, the row count (= `docs`) and its md5. Keep it until I post `reply-verified-...`.

### 2. Dry run
`os-text-extract recompute-diff-order ma --dry-run`, **without `--flags-only`**. Report the exact output lines and the start and end time.

### 3. The gate: commit only if ALL of these hold
- `nulled=0`;
- `corrected` between **340 and 380** (expected about 364: the 291 plus the chapter laws archived since OPEN-217 that have no comparison);
- the output names only Massachusetts.

**If all hold:** `os-text-extract recompute-diff-order ma --commit`. It must print the same numbers as the dry run; if it doesn't, report.
**If any fails:** do not commit. Report the lines and stop.

### 4. Checks after a commit (report each)
- `recompute-diff-order ma --dry-run` again: must print **`corrected=0 nulled=0`**.
- The G3 query again. Expected: `html_with_diff` about 364 (was 291), and `with_diff` up by the same amount; `docs` and `not_version` unchanged.
- **H 4252** (session 194th): the length of its chapter-law document's `diff_from_previous_version`, and whether it contains the line `In between reviews,` as an unchanged (context) line, meaning one starting with a space, not `+` or `-`.
- The start and end times of the commit, and that nothing else changed.

## Not authorized
- Any state other than `ma`, or `all`; `--flags-only` (not needed now); a second commit.
- A search refresh, LegBot run, scrape, archive, restart, schedule or env change.
- Undoing by hand. If anything looks wrong after the commit, report it and keep the export; the restore is my call with Ramon.

## What I check on the Mac side afterwards
The replica has applied it: the same G3 row; H 4252's comparison shows the four targeted edits; the 8 empty and 7 no-context cases on OPEN-223 match the offline figures. Then I post `reply-verified-recompute-diff-order-ma-open223-<date>.md` and close OPEN-223.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
