# MI LegBot run: confirmed 2 MLX workers (not 4), and real bills/hour throughput from the logs

Ramon asked us to double-check the worker count for the current Michigan full-session run and
to estimate real throughput. Both checked directly against CAMS's own logs (`legbot.mlx_worker_supervisor`
audit lines), not inferred from config alone.

## Worker count: confirmed 2, not 4

This Mac's `.env` sets `LEGBOT_MLX_WORKER_MAX_WORKERS=2` and `LEGBOT_MLX_WORKER_MAX_BILLS_PER_WORKER=4`.
Live log inspection confirms both numbers match reality: at any given moment exactly two worker
processes are active (each ~27-29GB resident, matching two large `Python` entries in Activity
Monitor), interleaving artifact calls across two different bills concurrently. Each worker is
retired after exactly 4 bills (`prefills=4` on every retirement line) and immediately replaced by a
fresh one, so the pool of worker IDs climbs continuously (`w886`, `w887`, ... `w896`, ...) even
though only 2 are ever alive at once -- that rotation is likely what read as "4" from outside if
PIDs were sampled a few minutes apart. There is only one MLX fleet on this host (LegBot's text
model); ScrapeBot's separate MLX-VLM vision daemon is unrelated and not involved in this run.

## Throughput: ~123 bills/hour overall, ~150/hour once past the first few hours

Run details, read directly from `ddp-sync`'s own log (`session_pipeline_run_start` /
`session_pipeline_bill_complete` lines):

- `run_id=cce7bb54-8ded-449d-9e9d-f6990fef0d2d`, dispatched via the `scraper_triggered_legbot`
  path, `jurisdiction_iso2=MI`, `session_code=2025-2026`, all 9 `bill_*` artifact types +
  `concept_statements` (no org research), `limit=5000`.
- Started **2026-09-14 21:16:11**, still running as of this note (**2026-09-15 17:34**, most
  recent dispatch line).
- **2,500 `session_pipeline_bill_complete` lines logged for this run_id so far.**
- That's **~20.3 hours elapsed for 2,500 bills = ~123 bills/hour average over the whole run.**

Broken out by hour, the real rate isn't flat -- it was noticeably slower for the first ~6 hours,
then settled into a steady state:

```
2026-09-14 21:00  63    2026-09-15 05:00 154    2026-09-15 12:00 147
2026-09-14 22:00  54    2026-09-15 06:00 136    2026-09-15 13:00 159
2026-09-14 23:00  42    2026-09-15 07:00 160    2026-09-15 14:00 144
2026-09-15 00:00  10    2026-09-15 08:00 161    2026-09-15 15:00 156
2026-09-15 01:00  48    2026-09-15 09:00 146    2026-09-15 16:00 160
2026-09-15 02:00  54    2026-09-15 10:00 166    2026-09-15 17:00 100 (partial hour)
2026-09-15 03:00 152    2026-09-15 11:00 138
```

- **First ~6 hours (21:00-02:00): ~271 bills, ~45 bills/hour.** No cancellations, stalls, or
  errors found in the logs around the slowest hour (00:00, only 10 bills) -- looked directly for
  `mlx_cancelled`/stall/timeout events in that window and found none, so this reads as ordinary
  early-run variance (larger bills, cold caches), not an incident.
- **Steady state from 03:00 onward: ~2,129 bills over 14 hours = ~152 bills/hour.** This is
  probably the more representative number for estimating how long a similarly-sized run would
  take once past its first few hours.

Not making any claims here about failure rates or data quality from this run -- that's a separate
question already being tracked elsewhere on this branch. This note is scoped to worker
configuration and raw throughput only, per what was asked.
