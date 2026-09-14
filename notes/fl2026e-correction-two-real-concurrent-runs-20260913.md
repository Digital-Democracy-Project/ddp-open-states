# Correction to "FL 2026E: full regeneration complete" (014be0a): this was two real, concurrent runs, not one

Re-checked `~/Developer/repos/ddp-sync/logs/ddp-sync.log` directly on the Mac against the
`014be0a` note's claim ("did NOT fire a second overlapping request... confirmed via direct DB
polling that the original request was the one doing the work, not a phantom"). The DB-polling
check was reasonable but the log evidence says this conclusion is wrong: **two independent
pipeline runs genuinely executed concurrently** for FL/2026E on 2026-09-13, ~980s apart in
duration, 20s apart in start time:

- `run_id=7a8d340d-37df-4629-b453-b9cd426da3be`, `session_pipeline_run_start` at 23:02:13,
  `session_pipeline_run_end` at 23:18:34 (980.714s), `bills_considered=22 bills_processed=22`
- `run_id=5b3ad68f-a262-401a-b1dd-3819168a990a`, `session_pipeline_run_start` at 23:02:33,
  `session_pipeline_run_end` at 23:18:35 (962.043s), `bills_considered=22 bills_processed=22`

Confirmed independently real (not one run's log line duplicated) via matching
`session_pipeline_bill_complete` entries for the same gov_ids (e.g. `HB 5501E`, `SB 2512E`,
`SB 2514E`) appearing under **both** run_ids, each with its own distinct MLX generation duration.

**How this happened, reconstructed from the access log right before both runs started**
(same log, lines ~4351337-4338), the only two inbound requests in that window, both from
`10.0.0.1` (EC2/WireGuard side):

```
10.0.0.1:52062 - POST /ddp-sync/v1/trigger/scraper-session-legbot HTTP/1.1" 200 OK
10.0.0.1:59238 - POST /trigger/bill-artifact-generation HTTP/1.1" 404 Not Found
```

The 404 is the bare-path mistake already described in `014be0a` -- it never reached a handler
and dispatched nothing. The `scraper-session-legbot` 200 OK is real and is one of the two runs
(it's the locked, fire-and-forget endpoint, so its access-log line returns fast, right before
the run_start it kicks off). For the second run, there's no access-log completion line anywhere
near its real finish time (~23:18) -- consistent with `014be0a`'s own account of a client-side
curl timeout against the full, correct `/ddp-sync/v1/trigger/bill-artifact-generation` path: the
client gave up waiting, but the server kept running the whole synchronous pipeline to completion
in the background with nothing left to log once the socket was gone.

So the DB-polling check in `014be0a` was watching one real run land -- it just wasn't the only
one. **A second, separate dispatch went out through `scraper-session-legbot` around the same
20-second window**, most plausibly the automated archive-completion hook (SYNC-65) firing
independently for the same FL/2026E session while the manual `retry_failed` regeneration was
still in flight -- not necessarily anything done wrong on the manual-trigger side.

**Why this matters**: the two endpoints do not share an overlap lock. `bill-artifact-generation`
has none at all; `scraper-session-legbot`'s lock only ever sees calls that go through it. A call
to one while the other is mid-flight for the same jurisdiction+session is invisible to both. This
is a live, concrete instance of exactly the gap **OPEN-290** (filed today, under OPEN-180) was
opened to close -- not a hypothetical risk.

**Practical consequence for the "162/176 succeeded, 14 failed" tally**: both runs were dispatched
against the same 176 target rows (all marked `status=failed` + `retry_failed=True` going in), and
ran concurrently for their full ~16 minutes. That tally may reflect whichever writer's result
happened to persist last on each row, not one clean, isolated pass -- worth treating the specific
counts (which 14 failed, why) as needing re-verification rather than final, if anyone downstream
is relying on the precise list. It also may be a second, independent contributor to the already-
flagged `ConceptStatementSet` duplication (44 rows instead of 22) from earlier in this same
thread, if the same concurrent-dispatch pattern happened during that run too.

No action taken on this beyond the log correction -- flagging for awareness and for OPEN-290's
eventual fix, which will close this specific gap by giving both endpoints the same lock.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
