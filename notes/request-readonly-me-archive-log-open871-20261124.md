# REQUEST (read-only, answer in a `reply-` note): **Maine's archive saved nothing.** Please read its archive task's log and report the counts. And: Maine's re-import is verified. 2026-11-24 ~18:50 UTC (Mac side, Onboard New States)

## What I need from you
1. **Read-only:** for Maine's archive tasks (the one after `me-9c24de62c00b`, 132S1, task of 121 s, and, if you can, the earlier ones at 00:11 UTC and for 132R1 and 132R2), report from the archive task's own log (CloudWatch):
    * the counts it prints (`archived`, `failed`, `skipped`, `not_a_version`, errors);
    * any line saying why it skipped or ended early;
    * the HTTP status or error for a sample of 3 Maine PDF links, if it fetched any.
   No archive run, no retry.
2. **Don't start another Maine archive** until I post `OPEN-871`'s finding. If Ramon wants it re-run in the meantime, tell me first.

## Why
* **Maine's re-import is verified.** `quality_check.py --structural me` passes every gate (versions 0 / 5,131; votes 0 / 148,002; "TERRY of Gorham" all on Parnell Terry; sponsors 1.0%). Three sessions: 132R1 1,305 bills, 132R2 311, 132S1 834.
* **But the Mac replica holds 0 Maine archive documents for those 5,131 versions,** although the archive "succeeded" in 121 s. Maryland's (5,128 versions) took 5,144 s and left 5,128 documents. Maine's manifest has `archive.enabled: true`. This also held after the first scrape's archive at 00:11 UTC.
* Filed as **OPEN-871** (blocks the Maine go-live). Nothing else for Maine waits on it except the text checks.

## Not authorized
A Maine archive or re-import, or any change; this is a read-only question.

Tickets: OPEN-672, OPEN-871 (OPEN-146).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
