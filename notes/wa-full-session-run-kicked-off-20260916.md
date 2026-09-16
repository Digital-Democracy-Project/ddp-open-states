# FYI: WA full-session LegBot run kicked off

Follow-up to `wa-bounded-pass-complete-clean-20260916.md`. The bounded 100-bill pass came back
clean (~152 bills/hr, matching MI's steady-state rate, no new failure categories) and Ramon
decided to proceed to the full session.

**Launched** against production via the Mac's ddp-sync, same settings as the bounded pass just
with the limit raised: `jurisdiction_iso2=WA`, `session_code=2025-2026`, all 9 `bill_*` artifact
types + `include_concept_statements=true`, `include_org_research=false`, `limit=5000`,
`retry_failed=false`.

**On `retry_failed`**: discussed explicitly with Ramon before launching. WA's existing 63 failed
rows are all `insufficient_information` -- genuine content-based model declines, not a bug/outage
this pipeline has since fixed (unlike MI's situation, where a real extraction bug got fixed in
between runs, making retries meaningful). Recommended `false` since retrying these would very
likely just re-confirm the same decline for real inference cost -- Ramon agreed.

Baseline before launch: 814 total `BillArtifact` rows for WA (751 complete, 63 failed). At the
confirmed ~152 bills/hr rate and ~3,311 bills remaining (WA's session has ~3,411 total, 100
already covered by the bounded pass), expect roughly 21-22 hours to complete. Will follow up with
real progress and the final result the same way the MI run was tracked.
