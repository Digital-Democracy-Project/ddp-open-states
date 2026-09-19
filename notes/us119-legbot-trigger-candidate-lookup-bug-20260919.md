# US/119 LegBot trigger: found a real candidate-lookup bug on EC2-broker, worked around via Mac Studio (2026-09-19)

Session on the EC2-broker host (`/opt/ddp-open-states`, `ip-172-31-78-173`). Two threads: closing
out the open question from last night's `notes/ddp-sync-sync66-deployed-20260919.md`, and a
manual full-session LegBot trigger for the 119th Congress that surfaced a new bug.

## SYNC-66: EC2-broker already had it, no separate deploy needed

Last night's note asked whether SYNC-66 (`a2c4437`) needed deploying to the EC2-broker instance
separately from the Mac Studio deploy it covered. Checked directly: this host's `/opt/ddp-sync`
git HEAD is already `a2c4437`, container up ~2 days, confirmed originally deployed here on
2026-09-16 (predates last night's Mac Studio deploy entirely, unrelated to it). Verified live
during the routine 05:00 UTC `al` archive cron: `resolve_touched_sessions()` succeeded cleanly
(single `200 OK`, no retry, no `Local api-v3 unreachable` warning) and reported a genuine
no-op — the fix's distinguishing behavior (`None`/ERROR vs. real `[]`) wasn't exercised because
there was no failure to distinguish, but the code path is confirmed live. **No action needed —
that open question is resolved, both instances have had SYNC-66 since before last night.**

## New bug found: `/trigger/bill-artifact-generation` can't find candidates from EC2-broker

Asked to trigger a full 119th Congress LegBot run (all 9 `BillArtifact` types +
`include_concept_statements=true`, no `include_org_research`, no bill-count limit) via this
host's own `ddp-sync` (`POST localhost:8001/ddp-sync/v1/trigger/bill-artifact-generation`,
`jurisdiction_iso2=US`, `session_code=119`). Call returned `200 OK` in 0.17s with
`bills_considered=0, bills_processed=0` — looked like an empty scope, wasn't.

**Root cause, confirmed from container logs (`run_id=f3a85e6357fc4a30bcea28eef0a88b36`):**
```
Local api-v3 unreachable -- skipping jurisdiction for this batch run
    error='All connection attempts failed' jurisdiction_iso2=US
```
`list_current_session_bill_candidates()` (`services/local_openstates_client.py`) is hardcoded to
read `settings.local_openstates_api_base`, which defaults to `http://localhost:8002` when
`LOCAL_OPENSTATES_API_BASE` isn't set — and it isn't set on this EC2-broker host. Inside the
`ddp-sync` container's own network namespace, `localhost:8002` has nothing listening; this host's
real api-v3 is `RDS_OPENSTATES_API_BASE=http://10.0.0.11:8002` instead, a completely different
address. Confirmed the data itself is fine — querying `10.0.0.11:8002` directly for
`jurisdiction=US&session=119` returns real bills (e.g. `S 3736`, `S 195`).

This is the same `local_openstates_api_base` vs. per-host-correct-base confusion class as
SYNC-66/SYNC-59, but a different function with **no fix at all yet**:
`resolve_touched_sessions()` already got an `api_base`/`api_key` override added for OPEN-193's
cloud-owned scrape path; `list_current_session_bill_candidates()` has no such override in its
signature — it can never be pointed at RDS, so **`/trigger/bill-artifact-generation` (and by
extension `/trigger/legbot-analyze-bill-full`'s batch sibling) cannot work when called against
this EC2-broker instance's own `ddp-sync`, full stop**, regardless of request parameters.

**Not fixed this session** — this needs a real code change (give
`list_current_session_bill_candidates` the same `api_base`/`api_key` override
`resolve_touched_sessions` has, then wire the trigger route to pass the right base per host)
before this endpoint is usable directly from EC2-broker. Filing as a fresh bug for someone to
scope/ticket — no ticket number assigned yet.

## Workaround used tonight: called the Mac Studio `ddp-sync` instead

Redirected the same request to `MAC_DDP_SYNC_BASE_URL` (`http://10.0.0.8:8001`, `MAC_DDP_SYNC_API_KEY`
from this host's own `.env`) — that instance's `local_openstates_api_base` presumably points at a
real local Postgres-backed api-v3 the way it's meant to. Request:

```
POST http://10.0.0.8:8001/ddp-sync/v1/trigger/bill-artifact-generation
jurisdiction_iso2=US, session_code=119
artifact_types=[bill_summary, bill_pros_cons, bill_vote_yes_frame, bill_vote_no_frame,
                bill_supporting_orgs, bill_opposing_orgs, bill_impact_analysis, bill_topics,
                bill_changelog]
include_org_research=false, include_concept_statements=true
limit=100000 (no real cap intended), retry_failed=false, dry_run=false
```

Connected cleanly (no immediate error, unlike the EC2-broker attempt) and was **still running,
synchronously, as of session close** (started ~05:43 UTC, no response yet after ~15+ minutes) —
consistent with a full-session run across 9 artifact types + concept statements for the whole
119th Congress; comparable full-session LegBot runs (see `wa-legbot-backlog-run-complete-
20260918.md`) have taken 30-50+ hours. No result to report yet either way.

**Minor ops note, not urgent:** passing the bearer token via `-H "Authorization: Bearer $KEY"` on
an interactive shell put the literal key in this host's `ps aux` output, visible to anyone else
with shell access. Worth switching manual/scripted trigger calls to a header file (`-H
@headerfile`) instead of inline `-H` going forward.

## Ask for whoever picks this up next

1. **Check the US/119 run's outcome** — was kicked off against Mac Studio's `ddp-sync`
   (`10.0.0.8:8001`) at ~05:43 UTC 2026-09-19, no `run_id` captured from a response yet since the
   call hadn't returned at session close. Check that instance's `ddp-sync` logs for
   `session_pipeline_run_start`/`session_pipeline_run_end` around that timestamp for
   `jurisdiction_iso2=US session_code=119`, and check broker `BillArtifact` rows for the same
   jurisdiction/session for progress or a final count once it lands.
2. **Fix `list_current_session_bill_candidates`'s missing `api_base`/`api_key` override** so
   `/trigger/bill-artifact-generation` works directly from EC2-broker instead of requiring a
   manual Mac Studio redirect every time. Scope + ticket it.
