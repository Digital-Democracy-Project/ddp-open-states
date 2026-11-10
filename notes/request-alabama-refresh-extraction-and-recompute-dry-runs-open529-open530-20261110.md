# Request: Alabama `refresh-extraction` and `recompute-diff-order` on RDS (OPEN-529, OPEN-530). **Part 1 (read-only, dry runs only) now. Part 2 (the commits) HOLDS until a GO note from Ramon on this branch.** 2026-11-10 about 23:15 UTC (Mac side)

## What I need from you
1. **Part 1 now** (read-only): gates G1 to G3 below, then the two dry runs, then reply.
2. **Part 2 only after a `go-…` note.** Nothing in this note authorizes a commit.

## What this does, and why
Alabama is resuming toward going live (OPEN-523). The 30-bill dev LegBot sample showed two kinds of noise in Alabama's stored text comparisons. Both are fixed in openstates-core and are now in image **v56**:
* **OPEN-529, the cleaner** (core #93, merged `a7d3a8fe`). Before two versions are compared, it removes the Enrolled signature and certification block, the front header (bill number, sponsors, RFD/First Read lines) and spacing differences. On the Mac replica, comparisons that are at least 95% boilerplate drop from 364 to 1, no comparison gains changed lines, and about 409 Enrolled comparisons become empty (all that changed was signature, header or spacing).
* **OPEN-530, struck-out words** (core #94, merged `a89dd31c`). Alabama prints deleted wording with a line through it. The reader now leaves those words out (PyMuPDF redaction). It only ever removes characters; checked on 300 real PDFs.

Applying both to the documents already saved takes two commands, in this order:
1. **`refresh-extraction al`** re-reads the saved Alabama PDFs with the new reader and recomputes the comparisons of each bill whose text changed. My measurement: **about 984 documents in 514 bills** have struck-out words.
2. **`recompute-diff-order al`** (the full run, **not** `--flags-only`) rewrites the stored comparisons for all Alabama bills with the new cleaner. Expected from the Mac replica: **about 916 of 917 comparisons rewritten, about 409 of them becoming empty.** Unlike this afternoon's OPEN-525 run, this one does rewrite comparisons.

Nothing is deleted. The "not a version" marks from OPEN-525 stay as they are. No other state is affected: the cleaner and the reader apply only to Alabama.

**Code.** Image **`ddp-scrapers:v56`, task-definition revision 59**, registered by Ramon at about 23:05 UTC (`deploy-scrapers-image.sh`). I checked inside v56: `openstates.fulltext.al.without_struck_text` exists and `handle_alabama_pdf` calls it, PyMuPDF is 1.26.5, and the OPEN-529 cleaner and its tests are present. **Run both commands in v56.** A venv on core `main` is acceptable only if it has PyMuPDF 1.26.5 installed (`python -c "import fitz; print(fitz.VersionBind)"`); without it the struck-out-word reader cannot run. Say which you used, with the proof.

## Part 1: read-only (now)
1. **G1 (code):** v56 / rev 59 (image id and tag), or core at or after `a89dd31c` plus the PyMuPDF check above.
2. **G2 (rollback point and quiet):**
   * Record the RDS latest restorable time.
   * Nothing in flight: no ECS task, scrape, archive, load, LegBot relay or backfill, and no ddp-sync job in the last 10 minutes.
   * Propose a Part 2 window clear of 02:00, 02:30, 03:00 and 04:00 UTC. **Pennsylvania's nightly starts at 04:00 UTC and runs about 7 hours; Alabama's first scheduled scrape is Sunday 11-15 at 02:00 UTC.** The commits must finish well before Sunday 02:00.
3. **G3 (baseline on RDS, read-only):**
```sql
SELECT j.name, count(*) AS docs,
       count(*) FILTER (WHERE d.is_bill_version IS NULL) AS flag_null,
       count(*) FILTER (WHERE d.is_bill_version IS FALSE) AS flag_false,
       count(*) FILTER (WHERE d.diff_from_previous_version IS NOT NULL) AS with_diff,
       count(DISTINCT d.bill_id) AS bills,
       count(*) FILTER (WHERE d.raw_text IS NOT NULL AND d.is_bill_version IS NOT FALSE) AS versions_with_text
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id
WHERE j.name = 'Alabama' GROUP BY j.name;
```
   **Expected (Mac replica, 23:10 UTC):** `Alabama | 2923 | 0 | 498 | 918 | 1507 | 2425`.
4. **Two dry runs (write nothing).** Report the exact summary lines and each run's start and end time (UTC):
   * `os-text-extract refresh-extraction al --dry-run`. **Expected:** about 984 documents re-extracted, in about 514 bills. If it reports a number far from that (under 800 or over 1,200), or **any** extraction errors, **stop and report**, with the first errors in full.
   * `os-text-extract recompute-diff-order al --dry-run` (full run, not `--flags-only`). **Expected:** about 916 comparisons corrected, about 409 of them to empty, and 0 marks changed. It reads today's stored text, so it does not yet include step 1's changes; the numbers are a baseline, re-measured in Part 2.
5. **Reply** `reply-alabama-refresh-and-recompute-preflight-20261110.md` (or the date you run it) with G1, G2 (window), G3 and the lines. Then wait.

## Part 2: the commits (only after a GO note)
In order, each one checked before the next:
1. `refresh-extraction al --dry-run` again; it must print what Part 1 printed. If anything changed, report and wait.
2. `os-text-extract refresh-extraction al --commit`. Then `--dry-run` again, which must report 0 to re-extract.
3. `os-text-extract recompute-diff-order al --dry-run`. Report its lines (now after step 2).
4. `os-text-extract recompute-diff-order al --commit` (not `--flags-only`). Then `--dry-run` again, which must report 0 to change.
5. G3 again. **Expected:** `docs` 2923, `flag_false` 498, `flag_null` 0 (unchanged); `with_diff` falls by about 409.
6. Report the lines, the query rows, start and end times (UTC), and that nothing else changed. Rollback is the G2 restore point; do not undo by hand without telling me.

## Not authorized
* Any state other than Alabama; `all`.
* Part 2 before its GO note.
* `--flags-only` at commit (this time the comparisons are meant to change).
* A search refresh, any scrape, archive, schedule change, restart, or LegBot run (Alabama is not live; nothing should be sent to LegBot).
* Any change to ddp-sync, the broker, the manifest or a task definition.

## What I check on the Mac side (not yours)
After the commits:
* the Mac replica applied them (worker running, recent messages);
* Alabama: 2,923 documents, 498 not a version, comparisons about 918 minus 409;
* a sample of the rewritten comparisons and re-read texts: no struck-out words, no signature block or header lines;
* other states' counts unchanged;
* then the 30-bill dev LegBot sample is rerun.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
