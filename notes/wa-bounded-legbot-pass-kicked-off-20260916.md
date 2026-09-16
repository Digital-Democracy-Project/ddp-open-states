# FYI: kicked off a bounded WA LegBot pass (limit=100)

Ramon's call: rather than manually re-test SYNC-66 on `us` (he expects the 119th Congress to
trigger a real automated dispatch on its own soon now that the fix is live -- Congress is active
enough that a real archive with real content should come through cleanly, or now visibly retry/
error instead of silently swallowing), we're doing productive real work on Washington instead.

Real numbers before starting: WA's `2025-2026` session has 3,411 total bills in OpenStates RDS;
only 152 `BillArtifact` rows existed in production before this (140 complete, 12 failed),
covering 39 bills -- almost the whole session is untouched. Full-session scale would be
comparable to the MI marathon (~3,400 vs MI's ~3,973), so we're starting bounded rather than
committing to another multi-hour run back-to-back with MI's.

**Request just launched** against production via the Mac's ddp-sync (`X-DDP-Environment: prod`):
`jurisdiction_iso2=WA`, `session_code=2025-2026`, all 9 `bill_*` artifact types +
`include_concept_statements=true`, `include_org_research=false`, `limit=100`,
`retry_failed=false` (the existing 12 failed rows are deliberately left alone for this pass, not
retried).

No results yet -- just flagging that it's running. Will follow up with the real outcome once it
finishes.
