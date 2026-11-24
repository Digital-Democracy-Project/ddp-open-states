# REPLY-VERIFIED to `de582d8`: **Maryland 5b passes. Verified on the Mac replica.** Continue with 5d ME. 2026-11-24 ~12:00 UTC (Mac side, Onboard New States)

## Verified (Mac replica, core `59dbdaa2`, read only)
* `quality_check.py --structural md` **passes every gate:**
    * versions with no stage **0 / 5,059 (0.0%)**, was 74.8%;
    * votes **0 / 267,947 unresolved**, was 2,733;
    * sponsors 265 / 12,657 (2.1%);
    * unique keys pass; 442 people (the Harlan merge took one).
* **"Speaker" → Joseline Peña-Melnyk 1,483; "Mr. President" → Bill Ferguson 1,246.**
    * **"Speaker" → Luke Clippinger 2** on roll calls 1483–1484, where he presided and she is printed absent. That's Ramon's "credit the chair" rule, working.
* **"Harlan" → Alex Harlan 23, 0 blank.** The 2 post-session votes link too, because your 04:57 ddp-sync rebuild runs core `59dbdaa2` (OPEN-817). That's why you counted 0 where my note said 2. Better than the line.
* **Version names:** Introduced (First Reader) 2,677, Engrossed (Third Reader) 1,258, Enrolled 238, Chapter N. No Impact Note versions.

## Next for Maryland (in this order)
1. **The archive** for 5b. If it hasn't started by itself once the md lock clears, trigger it by hand, as for PA. Report its end line.
2. **On Ramon's go:** `os-text-extract remove-stale-documents md`, dry run first. It removes the archive rows saved under the old "First - <title>" names. Report `stale` / `removed` / `kept_last_copy`.
    * **No deletion of the old Impact Note rows beyond what this tool removes as stale** (Ramon: leave them). If the dry run lists Impact Note rows as stale, report their count before committing.
3. **Then** `recompute-diff-order md` as a dry run; I post the range after measuring.

## Continue on v86
* 5d ME, then NM (`a1c833f`), then OK 2025+2026, then IA 2026 and 2025.

Tickets: OPEN-674, OPEN-813, OPEN-814, OPEN-815, OPEN-816, OPEN-817 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
