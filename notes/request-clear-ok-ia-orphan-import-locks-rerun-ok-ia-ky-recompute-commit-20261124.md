# REQUEST (not a GO): (A) mark Oklahoma's and Iowa's orphan import locks expired, the way `SourceLock.release()` does, **only if** each is still held by the run your restart killed; (B) re-run Oklahoma 2025+2026 and Iowa 2026; (C) the Kentucky recompute **commit**. 2026-11-24 ~05:30 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon answered these in the PM session's /ask-me (about 05:15 UTC, relayed to me):
* (2) "CLEAR NOW" for the OK and IA locks, then re-run OK 2025+2026 and IA 2026;
* (12) "APPLY" the Kentucky recompute commit, his second go after the numbers in `73344ed`.

Please confirm each with him in your session before acting, as for every relayed answer.

## (A) The two locks (SYNC-189 context)
Your `98fbc47` and ddp-sync `907462c`: each load was killed by a ddp-sync restart while running. The OPEN-203 import lock (an S3 object, 24 h TTL) was never released, so a reload is refused (`cloud_loader.py exited 90 ... another import of <st>_2026 already holds the lock`). SYNC-189 (in ddp-sync `60791f5`, live since 04:57) makes a resumed run release its own lock; these two predate it.

**What `release()` does** (`cloud_collector.py` `SourceLock`): it never deletes. It rewrites the object with `{"holder": <same holder>, "acquired_at": now, "expires_at": now - 1}`, conditional `IfMatch=<the etag it read>`. The next `acquire()` then sees an expired lock and reclaims it.

**For each lock:**
* key `<work prefix>/ok_2026/_import_lock` (expected holder `ok-b13efe4b9c89`);
* key `<work prefix>/ia_2026/_import_lock` (expected holder `ia-826c2805ac5e`);
* `<work prefix>` = the loader's own `prefix` (the same bucket/prefix `cloud_loader.py` builds its `SourceLock(..., suffix="_import_lock")` from).

1. **Read** the object (read-only) and report `holder`, `acquired_at`, `expires_at` and the ETag.
2. **Only if** `holder` is exactly the killed run above **and** `expires_at` is still in the future, write the expired body above with `IfMatch` = that ETag (holder unchanged, `expires_at = now - 1`).
3. **If the holder is anything else, or the PUT fails its precondition: stop and report.** Don't write.
4. **If your host's role can't write S3** (you said read-only in `98fbc47`): stop and say so. Ramon decides who runs it; nobody deletes the object.
5. Read it back and report the new body.

## (B) The re-runs (on v86, rev 88 or later; one heavy load at a time; after A for that state)
* **Oklahoma:** `POST /ddp-sync/v1/trigger/openstates-scrape/ok?full=true&sessions=2025,2026`. **Both sessions**: the 11-23 2025 load left 11 House roll calls unrewritten (HB 1017, 1021, 1022 ×2, HJR 1024, 1032–1035, HR 1002, 1004).
    * **Pass:**
        * 2025 unmatched = 44 (SB 920 only); 2026 unmatched about 0;
        * "Hader" 0 in both years;
        * "Mr. Speaker" linked to Kyle Hilbert, 0 unmatched;
        * 0 double votes;
        * person votes about 331,234;
        * the 11 roll calls' `updated_at` is newer than the run start.
* **Iowa:** `POST /ddp-sync/v1/trigger/openstates-scrape/ia?sessions=2026,2026s1` (as the killed run `ia-826c2805ac5e`).
    * Then **Iowa 2025** as already approved in `fe2bb48` (`ia?sessions=2025`), when the 2026 load is done.
    * **Pass:** as in ddp-sync `aa0bf45` / `12be6e8`. Report counts per session and any timeout.
* Report run ids, revision, counts and archives. I verify each on the Mac replica.

## (C) Kentucky recompute commit (OPEN-773)
* The dry run is yours, `73344ed` at core `9157b6b5`: `corrected=811`, `set=652`, `changed=179`, 0 nulled, 0 cleared; list md5 `d21f9eb840921a26bd7cfd8bf463724e`.
* **Core is now `59dbdaa2`**, so run the dry run again first, in the ddp-sync container (it contains the KY rule since `42b48982`).
    * **The numbers must equal those above** (KY's weekly run may add a few bills: `corrected` 790–830, `set` 640–665, still 0 nulled and 0 cleared). Otherwise stop and report.
* Export KY's stored comparisons as the backup (you noted at `73344ed` that you'd do it at commit time).
* Then `os-text-extract recompute-diff-order ky --commit --list <file>`, and report the commit's summary lines.

## Not authorized
* Deleting any S3 object or Redis key.
* Expiring any lock whose holder isn't the killed run named above.
* Any other state's lock or re-run.
* A second run of any of these.
* Any recompute commit other than Kentucky's.
* Hawaii's re-import: Ramon chose once, on v87 (`3c886e8`).

Tickets: OPEN-666 (OK), OPEN-673 (IA), OPEN-667 / OPEN-773 (KY), SYNC-189 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
