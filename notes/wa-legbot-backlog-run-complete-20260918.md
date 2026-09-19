# WA LegBot backlog run finished (2026-09-18)

Follow-on to `notes/wa-legbot-bill-changelog-mlx-hang-diagnosis-20260918.md` (last night) and
`notes/wa-legbot-no-bill-error-diagnosis-and-open297-20260918.md` (today, 16:56 -- OPEN-297
filed while the run was still at 96.3%). This answers that note's ask #1. No code changes made
this session; read-only check against `ddp-sync/logs/ddp-sync.log`.

## Run finished

`session_pipeline_run_end` fired 2026-09-18 18:38:40 for `run_id=938895ee-bd3f-4995-89c7-b58a5f5c76ea`
-- `duration_seconds=190521.021` (~53h from the 09-16 13:43:22 start), `bills_considered=3411
bills_processed=3411`, `truncated=False`. Full backlog cleared, nothing dropped.

## Final `artifacts_failed` tally (all 3,411 bills)

- **1,320 (38.7%) fully clean.**
- **1,573 (46.1%) failed ONLY `bill_opposing_orgs`** -- now confirmed the dominant failure mode
  by a wide margin, higher than the mid-run snapshot (855/1,884, 45%) suggested. Still no root
  cause found by anyone across either of the last two check-ins. This is now the single largest
  open item on this pipeline -- bigger in bill-count terms than OPEN-295/282/296/297 combined.
- **269 (7.9%) failed every artifact** -- count matches OPEN-297's diagnosed gating mismatch
  exactly (`ensure_bill_exists()` skipped when text isn't archived yet, but the artifact-write
  path still attempts a `failed` BillArtifact write that needs a Bill row that was never
  created). Confirms OPEN-297's root cause, not the earlier (already-corrected-in-ticket)
  resolution/memorial-gov_id hypothesis.
- **Only 5 bills** ended in a terminal `bill_changelog` failure -- the OPEN-295/282/296 MLX-stall
  problem cost wall-clock time (the ~53h runtime, well above what the early ~116/hr rate would
  predict) but auto-retry recovered almost all of the actual data. Not the main data-quality
  problem here.
- Remaining bills split across small mixed-failure combinations (`bill_pros_cons` +
  `bill_opposing_orgs`, `bill_impact_analysis` alone, etc.).

## Ask for whoever picks this up next

1. `bill_opposing_orgs` at 46.1% failure needs its own investigation -- it's now the clear
   priority over the already-diagnosed tickets, which are all comparatively low-impact by final
   bill count (OPEN-297: 269 bills / 7.9%; OPEN-295/282/296: 5 bills / 0.1%).
2. OPEN-297 is scoped with an agreed fix direction (gate the artifact-write path on the same
   archived-text check `ensure_bill_exists()` uses, log-and-skip instead of writing a `failed`
   record) but not implemented -- straightforward pickup.
3. OPEN-295/282/296 (MLX-stall root causes) still all "To Do" -- lower priority now that the
   run's actual final failure count from that path is confirmed small (5 bills).
