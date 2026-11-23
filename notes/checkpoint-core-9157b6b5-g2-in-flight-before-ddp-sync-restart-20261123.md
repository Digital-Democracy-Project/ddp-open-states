# Checkpoint (2026-11-23 23:02 UTC): core rebuild at 9157b6b5: api-v3 DONE; in-flight list BEFORE the ddp-sync restart

Ramon (pop-ups in my session, 11-23): approved the rebuild **now, repairs included**, and, when I asked, chose **`9157b6b5` now, as approved** for ddp-sync (not your newer `fd486fa4`; `c639029d`/`3e6c766`/`a16f424e` read: the certificate-checks core (OPEN-800), the Missouri versions (OPEN-806) and v85 are separate steps for his go, and ddp-sync will need **one more restart** for them). I rebuilt api-v3 at `9157b6b5` **before reading your `fd486fa4` update** (my mistake: the new notes were in the same command output as the build; I should have read them first). No harm: api-v3 was down about 8 s.

## api-v3 (EC2) at core `9157b6b5563b9fbca71a081ada4c00c18878d9edb`... (exact: DDP_CORE_SHA=9157b6b563b9fbca71a081ada4c00c18878d9edb)
Rollback tag `ddp-openstates-api:pre-core9157b6b5` = 7c06a09bb0a4; build and recreate 18 s, **down about 8 s**, `/healthz` 200. (Done outside the 05:00-07:00 UTC chain window.)

## G2: in flight now (23:02 UTC)
- **Collecting on Fargate (resume after restart):** ok **2026** (second session of `2025,2026`; 2025 loaded 20:52), ia **2026** (`2026,2026s1`: 2026s1 would not start), fl **2025** (2026 would not start), ma, me.
- **Archive tasks in flight (cut by a restart, re-trigger):** **hi** (manual archive since 20:29), **ms** (manual archive since 19:49; 3 h 13 min, unusually long).
- **Done, no action:** la (archive ok 20:51), ut (archive ok 19:51), mo (pipeline done 21:49), ne (pipeline done 21:59, results to follow), mt, az, mi.
- **Held pipeline locks:** hi, ia, ms, ok.

## After the restart I will re-trigger only (Ramon's earlier approvals): archives for hi and ms, and for ok, ia, fl, ma, me when each loads; ia `?sessions=2026s1` after its 2026 loads; Florida `full=true&sessions=2026` after its 2025 loads. Locks still held with no task: key and TTL reported, nothing deleted.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
