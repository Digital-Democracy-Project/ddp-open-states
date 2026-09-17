# Overnight (2026-09-16/17): SYNC-66 confirmed working live, NC's first real automated dispatch failed completely, MI's failed differently

Checked the full night's `scrape_triggered_archive_result`/`archiver_triggered_legbot_*` activity
across `us`/`wa`/`mi`/`nc` while checking on the ongoing WA full-session run. Three separate real
findings, full detail below so nothing needs re-deriving.

## 1. SYNC-66 (PR #159) confirmed working live -- good news

`us`'s archive-completion check hit the same api-v3 connectivity issue seen two nights ago, but
this time the new code handled it correctly:

```
2026-09-17 03:24:39 [warning] Local api-v3 unreachable -- retrying touched-sessions read attempt=1 error= jurisdiction_iso2=US max_attempts=3
2026-09-17 03:24:51 [warning] Local api-v3 unreachable -- retrying touched-sessions read attempt=2 error= jurisdiction_iso2=US max_attempts=3
2026-09-17 03:25:03 [warning] Local api-v3 unreachable -- cannot resolve touched sessions attempts=3 error= jurisdiction_iso2=US
2026-09-17 03:25:03 [error]   archiver_triggered_legbot_session_resolution_failed jurisdiction=us since=2026-09-17T03:09:24.071135+00:00
```

Real 3-attempt retry, correctly logged as ERROR (not the old silent "no sessions touched" INFO
path) when all three failed. The archive itself succeeded fine (905.1s, `success=true`) -- only
the session-resolution step for the LegBot trigger couldn't complete. This is the fix working
exactly as designed; the underlying connectivity blip itself is still real and unresolved (worth
its own look at some point -- two occurrences now, both against this same api-v3 endpoint), but
it no longer masquerades as a false negative.

Also note (separate, expected-working behavior, not a bug): USA's upper chamber's own
archive-completion attempt for `us` a few minutes later was correctly debounced
(`result={'success': True, 'jurisdiction': 'us', 'skipped': 'debounced'}`), and WA's own routine
archive-completion check ran clean with a real `200 OK` (no connectivity issue that time),
genuinely finding nothing touched.

## 2. NC: first-ever real automated dispatch fired, failed completely -- real gap, not a fluke

NC's archive found real content and correctly triggered a genuine WireGuard dispatch to the Mac
(`archiver_triggered_legbot_wireguard_result`, `run_id=57bf4ea2029244469491c6d5a77ea4f2`,
`bills_considered=2338, bills_processed=2338, truncated=False, duration_seconds=818.1,
success=true` at the top level). **But every single one of the 2,338 bills failed identically**:

```
error: "ensure_failed: ddp-broker-py rejected the ensure-bill-exists request (400):
{\"detail\":\"No LegislativeSession found for jurisdiction='NC' session_code='2025'\"}"
```

Confirmed directly against production (not inferred from the log alone): **NC has zero
`LegislativeSession` rows and zero `BillArtifact` rows in `ddp-broker-py` at all** --
`Jurisdiction.objects.filter(iso2='NC')` resolves fine (id=33), but it has never had a session
created underneath it. `ensure_bill_exists`'s `resolve_legislative_session` call fails before
any Bill row can be created, so nothing downstream (artifact generation, concept statements) even
gets a chance to run -- the `success: true` at the top level is genuinely misleading here; it
means the HTTP round-trip and orchestration completed without crashing, not that any real content
was produced. Zero real work happened.

This lines up with the standing `nc_stage6_soak_findings` caution (zero confirmed clean cycles,
recommended against promoting NC to live) -- this is now very concrete, additional evidence for
exactly why. Real questions for you: is NC's total absence from ddp-broker-py's own session data
expected/known, or is this itself a gap (should NC have a LegislativeSession by now, same as
MI/WA/US do)? And separately: should NC's inclusion in `openstates_archive.jurisdictions` (and
therefore its ability to trigger this chain automatically) be reconsidered until this is
resolved, given every future NC archive with new content will hit the identical wall?

## 3. MI: automated dispatch also failed, differently, with an unlogged root cause

```
2026-09-17 06:04:35 [error] archiver_triggered_legbot_wireguard_trigger_failed error= jurisdiction=MI session_code=2025-2026
```

The `error=` field is empty in the actual log line -- whatever exception was caught didn't
produce a usable message (or something's swallowing it before it reaches the log call). Can't
tell you the root cause from EC2 logs alone; this is a real gap in the error-logging itself, not
just an unknown failure. Worth checking `_trigger_legbot_session_via_mac_wireguard`'s own
exception handling for what could produce an empty `str(e)`, and whether Mac-side logs from
around 06:04:35 UTC have more detail than what reached here.

## Context: WA's manual full-session run (still in progress) slowed down overnight

Not necessarily connected to the above, flagging as background: the ongoing WA full-session
LegBot run (see [[wa_full_session_legbot_run]]) dropped from its earlier ~150+/hr steady state to
roughly ~29/hr over the stretch spanning last night's activity, though NC's failed run was short
(13.6 min, ended by 07:00) and unlikely to be the main driver of a many-hours-long slowdown by
itself. No new failure category appeared in WA's own results despite this -- still 100%
legitimate `insufficient_information`. Not chasing the exact cause further right now; flagging in
case it's a useful data point alongside the above.
