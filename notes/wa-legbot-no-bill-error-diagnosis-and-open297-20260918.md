# WA LegBot run status + "No Bill exists" root cause diagnosed, OPEN-297 filed (2026-09-18)

Follow-on to last night's handoff (`notes/wa-legbot-bill-changelog-mlx-hang-diagnosis-20260918.md`).
Ramon asked to check WA run progress and asked about a second failure mode noticed in that
check -- this note covers both. No code changes made this session; diagnosis + ticket-filing
only, same as last night.

## Run status (`run_id=938895ee-bd3f-4995-89c7-b58a5f5c76ea`)

Still in progress, no `session_pipeline_run_end` yet. Progress over today's checks:

| Time (local) | Bills complete | % of 3,411 |
| --- | --- | --- |
| 2026-09-18 ~01:15 (last night's check-out) | 1,897 | 55.6% |
| 2026-09-18 15:30 | 3,210 | 94.1% |
| 2026-09-18 16:54 | 3,285 | 96.3% |

Throughput is uneven: ~92 bills/hr averaged over the first stretch of today's checks, dropping to
~53/hr in the most recent 85-minute window -- consistent with the still-unfixed CAMS MLX stall
pattern from last night's note (OPEN-295/OPEN-282/OPEN-296, none implemented yet). ~126 bills
remain; likely wraps within a few hours but expect more stalls given nothing's been fixed.

## New finding: a second, unrelated failure mode -- diagnosed and filed as OPEN-297

Noticed a chunk of bills failing *every* artifact type near-instantly (~0.2-0.4s, no real
LLM work) with:

```
ddp-broker-py rejected the BillArtifact write (400): No Bill with openstates_id='...'
exists yet -- this endpoint attaches artifacts to an existing Bill, it does not create one.
```

**Initial hypothesis (wrong, corrected same session): a classification gap for WA's
resolution/memorial types (HCR/HJM/SJM).** Production log data disproved this directly -- in
this run, HR (101) and SR (83) hit the identical error, more than double HCR+HJM+SJM combined
(34), and zero HB/SB bills hit it. No classification filter exists anywhere in ddp-sync,
`ddp-broker-py`'s `ensure_bill()`, or the openstates-core archiver.

**Real root cause: a gating mismatch between two independent "is there archived text?" checks**
in `ddp-sync`:

1. `session_pipeline_runner.py:599-648` (SYNC-21) -- `ensure_bill_exists()` is deliberately
   *skipped* when a bill's text isn't archived yet (comment: a bill must never get a stub Bill
   row created for it in that case).
2. `bill_artifact_generation.py:306-334` / `:392-418` -- when there's no archived text, the code
   still tries to write a clean `failed` BillArtifact row (`failure_reason="no_archived_bill_text"`)
   regardless. That write needs a Bill row that step 1 never created for the identical reason, so
   `ddp-broker-py`'s serializer rejects it with the confusing "No Bill exists" message instead of
   the intended, legible failure.

Confirmed against production logs: 253 unique bills hit this in the WA run, 100% also have a
matching "no archived bill text" log line for the same bill. Globally across all jurisdictions in
the log: 978/983 (99.5%) of bills lacking archived text hit this exact rejection -- systemic, not
WA-specific.

**Filed as [OPEN-297](https://digitaldemocracyproject.atlassian.net/browse/OPEN-297)**, under
epic OPEN-180 (Scraper execution migration), labels `legbot`/`open-states`/
`scraper-execution-migration`/`repo:ddp-sync` -- matching OPEN-292's precedent (a similar
pipeline-mechanics bug found during a full-session LegBot sweep).

**Decision recorded on the ticket**: the fix should move the archived-text check earlier so it
gates the *entire* write attempt, and on a miss should **log a warning and skip -- not write a
`failed` record**. Reasoning: `session_pipeline_runner.py:537-549` (SYNC-42) skips any artifact
already marked `failed` on all future runs unless launched with `retry_failed=True`, and the
standing WA runs default to `retry_failed=false`. Recording `failed` for "text not archived yet"
would permanently orphan that bill even after its text does get archived. A log-only skip lets it
naturally retry on the next run once archival catches up.

**Not yet investigated**: the same rejection-message pattern is duplicated for BillVersion
(`serializers.py:615-616`) and OrgPosition (`:1245-1246`) -- unconfirmed whether those write
paths share the same gating mismatch. Flagged on OPEN-297 for whoever picks it up.

## Still open from last night, unchanged

- `bill_opposing_orgs` still fails alone on a chunk of otherwise-clean WA bills in this run
  (visible again in the 16:54 check, e.g. `HB 1868`) -- cause not yet found, not investigated
  further this session.
- OPEN-295/OPEN-282/OPEN-296 (MLX stall root causes) -- still all "To Do," nothing implemented.

## Ask for whoever picks this up next

1. Check whether `run_id=938895ee-...` has finished (`session_pipeline_run_end` in
   `ddp-sync/logs/ddp-sync.log`) and how the final tally looks.
2. OPEN-297 is scoped and has an agreed fix direction but is not implemented -- straightforward
   pickup if someone wants a contained, well-evidenced bug fix.
3. `bill_opposing_orgs`'s standalone failure is still the one thread from last night nobody has
   pulled on yet.
