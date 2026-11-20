# REPLY (done, read-only Part C): US 118/119 full re-import (SYNC-181) finished clean, and the OPEN-638 Part C go/no-go PASSES (C1-C5). 2026-11-20 19:35 UTC (EC2 prod agent)

Replies to `ddf23c92d` (SYNC-181) and `5836c52` (Part C). The re-import was pre-approved by Ramon ("Yes, both, when the dev confirms").

## The re-import (started 05:56:22 UTC, ended 18:45:23 UTC)
Trigger answered **202** with `"full": true` and the four sessions. ddp-sync image `38596a47977a` (core `10f32ce0`), scrapers image v72 (`ddp-scrapers:75`). Collections in turn, each loaded into RDS:

| Session | Run id | Collection done | Load done | Total |
|---|---|---|---|---|
| 118 lower | `usa-d9d5d6800035` | 09:37:09 | 09:56:49 | 14,426 s |
| 118 upper | `usa-e74de0f47ea1` | 11:55:08 | 12:03:56 | 7,625 s |
| 119 lower | `usa-479f58d966f1` | 15:53:56 | 16:14:04 | 15,007 s |
| 119 upper | `usa-bb5291307172` | 18:16:56 | 18:26:43 | 7,958 s |

Pipeline `openstates_pipeline: done archived=True duration_seconds=46140.2 failed=0 sessions=4 status=completed` at 18:45:23. The archive (`ddp-scrapers-db:2`) ran after the loads; then the knowledge-base embedding run (`jurisdiction=us bills=80 chunks=239 complete=True failed_bills=0`). **`DuplicateItemError`: 0** in ddp-sync's log. **No LegBot hand-off line** appeared after the archive (none for US). **Not confirmed by me:** the `"mode": "full"` record of each collection (not in ddp-sync's log; the CloudWatch streams are named by task id and I did not find the four). The 202 echoed `full: true`, and the stored data (below) shows the new relation types, so the walk was full. Per-load bill/vote counts: the loader log does not print them; tell me where they are logged if you need them.
The weekly `warning ... no usable filing figures ... expected_path=.../usa_session_*.imported` lines appeared for the four sessions (same message as GA's today; I have not checked earlier weeks).

## Part C (read only; files in /home/bitnami/ops/open638-partc-rds-20261120.txt)
Reference lists verified by md5: expected `0468b2403216f8bb72e0f4c9b5f48a87` (99 rows), procedural `5bcc251fd8043d26d2d2d740c1ab42ac` (114 rows).
- **C1 (production broker):** federal links by Congress: **118: 34, 119: 28; no other Congress.** PASS.
- **C2 (RDS), after:** 118 `companion` 4,508, `related` 10,634; 119 `companion` 4,393, `related` 10,487; total 30,022. Companion is 8,901 of 30,022 (about 30%), so not "a small share" in the sense of a few percent; the Mac replica's "before" was about 29,800, all companion. I have no "before" count of my own (the re-import began before I measured).
- **C3:** polled US bills on production (`voatz_id` set and `build_scorecard`): **367** (141 in 118, 226 in 119). The 99 expected "Identical bill" rows all sit on bills polled on production; the companion links RDS stores for those bills are **exactly those 99: 0 missing, 0 extra.** (The broker stores bill numbers without a space, `HJRES109`; RDS has `HJRES 109`: I matched after normalizing.) PASS.
- **C4:** the 114 procedural rows: stored `related` **114**, `companion` 0, absent 0. PASS.
- **C5 (EC2 api-v3, `include=related_bills`):** 118 HJRES 109: SJRES 59 `companion`, HRES 1194 `related`; 118 HR 8371: S 141 `related` (14 related in all); 119 HR 1: all 29 `related`. PASS. The same values read straight from RDS.
- Side facts: the production broker holds **33** `companion` relations in all (the dev expected 25 US links): nothing deleted or changed there.

**Go/no-go: all of C1-C5 pass, no C3 or C4 difference, so BROKER-548's stop rule does not trigger.** Nothing changed by me in Part C. BROKER-548 itself needs its own request and Ramon's go.
