# WA LegBot backlog run + bill_changelog MLX-hang diagnosis (2026-09-18)

Ramon asked for a status check on the Washington LegBot artifact-generation backlog run, then
asked why its throughput had dropped -- this note is the handoff summary of that investigation.
No code changes were made this session; this is diagnosis + ticket-filing only.

## How WA's LegBot pipeline actually gets triggered (easy to get wrong)

`ddp-sync`'s weekly LegBot batch cron (`session_pipeline_batch`, SYNC-9) is hardcoded to
`jurisdiction_iso2: "FL"` only -- it does not cover WA. WA's dispatch comes from the separate,
independently-gated SYNC-48/50 "scraper-completion trigger"
(`ddp-sync/src/ddp_sync/pipelines/scraper_triggered_legbot.py`): every time a WA scrape/archive
completes on the cloud/Fargate path, it fires LegBot dispatch automatically. If asked about any
other jurisdiction's LegBot status later, check `GET /ddp-sync/v1/schedule` for what's actually
registered (only 2 jobs show up there day-to-day) rather than assuming the weekly cron covers it.

## Run status

A full-backlog run (`run_id=938895ee-bd3f-4995-89c7-b58a5f5c76ea`, limit=5000,
session_code=2025-2026) started 2026-09-16 13:43 and is still in progress. As of the last check
(2026-09-18 ~01:15 local / 05:15 UTC): **1,897 of 3,411 total WA bills for this session (55.6%)**.

Throughput is highly non-stationary: ~116 bills/hr for the first ~11 hours, then a sustained
drop to ~20-40 bills/hr, with individual hours as low as ~6/hr during active stalls. A live check
at 2026-09-18 05:18 UTC found the pipeline in a healthy stretch (a worker had just completed a
normal 49s/29GB cycle) -- but this is a point-in-time read, not a resolved-problem signal, since
none of the root causes below have been fixed yet. Rough ETA for the remaining ~1,514 bills:
1-3 days, dominated entirely by how often the stalls below recur, not by steady per-bill cost.

## Root cause of the slowdown: CAMS's MLX worker pool wedging on oversized bill_changelog calls

Confirmed directly from `ddp-agents/logs/cams-server.log`'s `legbot.mlx_worker_supervisor` AUDIT
lines. Normal worker cycle: ~30-50s, ~28-30GB peak memory, serves 4 bills then recycles. Since
2026-09-17 ~03:00 UTC, at least 7 workers have instead gotten stuck mid-`generate()` call for
**46 minutes to 2+ hours**, peaking at **43.8-47.2GB**, before an internal watchdog
(`mlx_worker_stall_threshold_s=7200`, i.e. 2h) force-cancels them. The pool caps concurrency at
2 workers, so each multi-hour stall halves the pipeline's effective throughput for its duration --
this is the whole slowdown, not a separate issue.

Every one of these hangs is a `bill_changelog` call with an oversized prompt (90K-207K tokens vs
a normal median ~4,420). Traced this to two genuinely independent, now-separately-tracked causes:

### Cause 1 -- OPEN-295 (filed, Michigan-only, real bug, precisely scoped)

`openstates-core`'s `openstates/utils/version_ordering.py`, `extract_ordinal()`:
```python
paren = re.search(r"\([sh]-(\d+)\)", lowered)
```
`[sh]` is a non-capturing character class -- `"Substitute (H-1)"` and `"Substitute (S-1)"` both
resolve to ordinal `1.0`, colliding into the same `version_sort_key`. Michigan's House and
Senate substitute lineages are independent, parallel numbering tracks, not one shared sequence,
so `archive_bill_versions()` can pick two unrelated per-chamber documents as "adjacent" and diff
them against each other. Confirmed directly against MI `HB 5630`: `Substitute (H-1)` (788,452
chars, amends ~130 sections) vs `Substitute (S-1)` (20,425 chars, amends only 3 sections) --
both tagged ordinal 1.0. The stored diff for that pairing is 813,181 chars, essentially
`old_len + new_len` -- the signature of two documents sharing almost no matching lines.

Scoped precisely against the live DB: 634 MI bills use this `(H-N)`/`(S-N)` notation (MI-only,
no other jurisdiction), 41 have substitutes from both chambers (where the bug can manifest), 16
have an exact ordinal collision (guaranteed arbitrary pairing, not just plausibly wrong).

### Cause 2 -- OPEN-282 (existing ticket, WA added via comment; "measure first", not MI-specific)

WA's own large diffs (`SB 6003`, `SB 6005`, both real WA capital-budget bills) are **not** the
same bug -- confirmed by reading the actual stored diff content: real amendments, WA's own
cleaner (`_clean_wa_text`, OPEN-7) visibly running, correct version ordering. This is instead the
same general line-diffing fragility OPEN-282 already scoped for US/VA: `difflib`'s exact-line-
match comparison treats a reflowed remainder as fully unmatched once one edit shifts a
print-width wrap point, so a bill amending 100+ line items can cascade into a diff far larger
than the actual edit. Math check: `SB 6003`'s diff (380,753 chars, 136.8% of the longer document)
is 84.5% of the theoretical "nothing matched" ceiling (`old_len + new_len` = 450,427) --
consistent with reflow cascade, not corruption. Added a comment to OPEN-282 requesting WA be
included in its planned jurisdiction-agnostic measurement pass, with these two bills as concrete
spot-check candidates.

### Separately -- OPEN-296 (filed, a design inconsistency, not a bug, cross-jurisdiction)

The *other* half of the `bill_changelog` prompt -- `old_bill_source`, the full prior-version
text -- is sent uncapped in the common/direct MLX path
(`ddp-agents/src/legbot/handlers.py::handle_analyze`), while the existing chunked (>700K-token,
Claude-only) path already caps the equivalent input at a 4,000-char "identity excerpt"
(`changelog_identity_excerpt_chars` in `legbot/config.py`), specifically to avoid repeating full
bill text. Measured across the whole archive (51,223 real diff transitions, using
openstates-core's real `version_sort_key()` imported directly, not reimplemented):
`old_bill_source` and `diff_source` are roughly balanced at the median (54.4%/45.6% split), but
`old_bill_source` has no ceiling while `diff_source` does -- applying the chunked path's own
4,000-char cap to the direct path would cut p95 total prompt size ~51%, mean ~44%. Not yet
reconciled against CAMS's own observed `prompt_tokens` for real dispatched calls -- flagged as an
open question on the ticket, not a committed number.

## What's NOT yet done

None of OPEN-295 / OPEN-282 / OPEN-296 have been implemented. All three are "To Do". OPEN-295 is
the most contained, precisely-scoped fix (16-41 MI bills, a one-line regex capture-group fix plus
a sort-key change); OPEN-282 and OPEN-296 are explicitly "measure first, then decide" tickets
following this repo's own established pattern for changes to shared diff-generation logic that
feeds every jurisdiction, not just WA.

## Ask for whoever picks this up next

1. Monitor the WA run via `ddp-sync/logs/ddp-sync.log`'s `session_pipeline_bill_complete` count
   for `run_id=938895ee-bd3f-4995-89c7-b58a5f5c76ea` -- no dedicated dashboard exists for this.
2. Decide whether OPEN-295 is worth fixing now (contained, scoped, real bug) independent of
   OPEN-282/296's larger measurement work.
3. `bill_opposing_orgs` fails alone on a large fraction of otherwise-clean WA bills in this same
   run (separate from everything above) -- cause not yet found, noted but not investigated this
   session.
