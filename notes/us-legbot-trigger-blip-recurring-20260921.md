# US legbot-trigger "resolution_failed" is recurring nightly, not a one-off blip

Follow-up to `us119-status-check-20260920.md`, which flagged one occurrence of
`archiver_triggered_legbot_session_resolution_failed` for `jurisdiction=us` as "a transient blip
... not reproducing right now." Checked again from `/opt/ddp-open-states` on EC2
(`ip-172-31-78-173`) at 2026-09-21 ~15:00 UTC. **Correction: it has now fired 4 times over 3
consecutive nights, and every single logged outcome for `jurisdiction=us` in that window is a
failure — no successful `archiver_triggered_legbot_for_sessions` or `..._no_sessions_touched` at
all since 2026-09-19.**

```
2026-09-19 03:24:03  since=2026-09-19T03:06:52
2026-09-20 03:44:07  since=2026-09-20T03:28:57
2026-09-20 05:14:40  since=2026-09-20T05:00:00
2026-09-21 03:49:32  since=2026-09-21T03:35:22
```

**New diagnostic detail the earlier note didn't have**: pulled the full log window around the
09-21 03:49 occurrence. It fires immediately (within ~10-25s) after `openstates_archive: fargate
task done jurisdiction=us` completes, as part of the same `_maybe_trigger_legbot_for_archive`
call this session has seen before ([[sync66_legbot_trigger_false_negative]] / SYNC-66's own PR
#159 retry logic -- 3 attempts, ~12s apart, then a real ERROR log, which IS the fixed behavior
working correctly here, not a regression of SYNC-66 itself). What's new: checked
`ddp-openstates-api-1`'s own request logs for that exact same window (`03:48:30`-`03:50:00`) --
**no request from this call ever shows up there at all**, only unrelated `/healthz` 200s. The
container itself has 0 restarts since 2026-09-13 and was serving healthz fine throughout. That
rules out "api-v3 app is slow/overloaded" as the cause -- this looks like a connection-level
failure between the `ddp-sync` container and `10.0.0.11:8002` (Docker network/DNS hiccup, or
host-level contention) that never even reaches the app, specifically in the few seconds right
after the nightly `us` archive's Fargate task finishes.

**Not filing a ticket number for this yet** (matching the previous note's judgment call) since
root cause isn't pinned down, but downgrading the "one-off, not reproducing" assessment --
4-for-4 over 3 nights, always in the same post-archive window, is a real pattern. Worth someone
with time checking: (1) does anything else on this host contend for network/CPU/IO right in that
same post-archive window (log shipping, backups, the next `usa` cloud_scrape kicking off -- log
shows `cloud_scrape: triggering Fargate collection jurisdiction=usa` firing in the very same
second as the failed resolution), (2) whether Docker's embedded DNS resolution for
`ddp-openstates-api-1` is flaky under that specific load pattern.

**Practical impact so far**: same as before -- each failure means that night's `us` archive
content didn't auto-trigger LegBot dispatch. Not catastrophic (the manual US/119 backlog run
covers 119th-Congress bills regardless), but any bill whose *only* new content lands in one of
these windows on a night with no manual backfill running would be silently missed until someone
re-triggers it by hand.

## US/119 backlog run: no run-status API still, but broker-side proxy shows real growth

Couldn't get an authoritative bills_processed/bills_considered number from Mac Studio's
`ddp-sync` (still no run-status-by-id endpoint, no filesystem/log access from EC2 -- same
limitation as yesterday's note). As a proxy, read `ddp-broker-py`'s production Postgres
(read-only, `Bill`/`BillArtifact` tables only):

- **US `Bill` rows: 5,271** (up from the 3,304 a session recorded several days ago -- ~1,967 new
  bills have cleared the `ensure_bill_exists()` gate, i.e. gotten real archived text, since then).
- **US `BillArtifact` rows: 40,894** (36,428 complete / 4,466 failed, ~89% success rate).
- **4,985 distinct US bills have at least one artifact.**

Caveat: this isn't the same denominator as the run's own `18,494` bills_considered figure (that
count is presumably every 119th-Congress bill OpenStates knows about, not just ones that have
cleared the archived-text gate), and a bill that landed as `status="not_applicable"` under
[[open297_bill_gating_mismatch]]'s OPEN-301 fix wouldn't show up here at all despite being
"processed" by the run. Treat this as directional evidence of real, substantial progress, not a
literal substitute for the run's own progress counter.
