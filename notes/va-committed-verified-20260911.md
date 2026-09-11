# va committed and verified — backfill progress: mi, ut, fl, va done; wa/us remain

`recompute-diff-order va --commit` run via the Fargate trigger, fresh dry-run immediately
before (matched exactly: `4380/9161/14553/1827`).

`va: [COMMITTED] 4380 bills checked | unchanged=9161 corrected=14553 nulled=1827` — matches
the dry-run exactly.

**Verified the actual post-commit DB state directly** (not just the summary line), against
2 of the 7 samples confirmed clean earlier: `id=23753` (SJ 60/2026) ->
`diff_from_previous_version=None` as expected; `id=70535` (HR 2002/2026S1) -> 897-char diff,
matching the spot-check exactly.

`va` is closed out. Only `wa` and `us` remain in this backfill.

`us refresh-extraction --dry-run` is still running (well over 1.5 hours now) — checked
CloudWatch directly rather than assume: confirmed genuinely active, most recent log line
only ~1 minute old at last check (poppler warnings from real PDF processing), not stalled.
Will report once it lands.
