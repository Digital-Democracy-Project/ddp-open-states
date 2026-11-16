# Status: manual scrapes of al and la LAUNCHED on revision 63 (one each), after step 8. 2026-11-16 07:35 UTC (prod agent)

Answers `1f19165e`. **User's words in session (pop-up, earlier):** "Start nc and ne now; al and la wait for step 8"; step 8 is now done and checked (`checkpoint-step8-api-v3-306b4f5-live-20261116.md`), so al and la go next. Alabama's section B was separately approved by the user "each only if its gate passes".

## Launches (each exactly once; no retry)
- **al:** the same ddp-sync trigger call as for nc and ne, 07:34:55 UTC, **`202 {"status":"started","target":"al"}`**, run **`al-2086d764108a`**, task `9175a3b3a5564709a86dd0fbe7ca83b4`.
- **la:** 07:35:01 UTC, **`202 {"status":"started","target":"la"}`**, run **`la-ebf3078695cc`**, task `7c9e359f5578442eaceb4cd9c571f47a`.
- **Task definition read from ECS: `ddp-scrapers:63` for both.**

## Gates, re-checked immediately before (all met)
Step 8 done and checked; scorecard chain over; outside the nightlies; **0 running tasks**; the S3 locks `prod/al/_lock`, `_import_lock`, `prod/la/_lock`, `_import_lock` all **released**; 0 ddp-sync lines for either state in the last 10 minutes; 0 pipelines in flight (two at once, your limit; nc and ne had finished).

## Before-counts (RDS)
**al: 2,550 vote events, 1,507 bills. la: 3,172 vote events, 2,616 bills.**

## Next
I report each run (revision, times, scrape line, archive line, LegBot line, errors, after-counts). **Alabama's section B** (B.1 check, B.2 `recompute-diff-order al`, B.3 `remove-stale-documents al` with a full export first, B.4 final dry run) starts after Alabama's import **and** archive have finished, each step committing only if its dry run passes your gate. Alabama's search rebuild (OPEN-577) holds for its own go. Expected: al about 2.5 h, la about 4 h.
