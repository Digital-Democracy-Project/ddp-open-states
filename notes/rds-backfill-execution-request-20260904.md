# Ready to run the real RDS backfill -- dev rehearsal done, here's exactly what to run

*Follow-up to `notes/open193-ac6-rds-baseline-reply-20260904.md`.* Thanks for that comparison
work -- it paid off directly: VA's and UT's "count decrease" anomalies both turned out to be
**exact, digit-for-digit matches** to the not-yet-applied backfill (see below), not new bugs.
Ramon's asked to run the real backfill now. Plan: `PLAN-rds-data-quality-backfill.md`
(`ddp-infra`, merged, PR #130) -- read it in full before running anything if you haven't
already; this note is the execution summary, not a replacement for it.

## Dev rehearsal: done, clean

Ran every command against `ddp-open-states-dev`'s own isolated Postgres tonight, `--dry-run`
then `--commit`, then a repeat `--dry-run` to confirm idempotency:

- `refresh-extraction ut/wa/us --dry-run` -- 0 stale docs found in dev's small dataset (expected,
  per the plan's own note -- dev may just lack a document shaped like the bug). No errors.
- `recompute-diff-order fl/us/va/mi/wa/ut --dry-run` then `--commit` -- real corrections found
  and applied cleanly (fl: 5 corrected; us: 47 corrected + 33 nulled; mi: 4 nulled; wa: 4
  corrected + 2 nulled; ut: 6 corrected + 5 nulled; va: 0 bills in dev's small dataset, a
  coverage gap in dev, not a failure).
- **Repeat dry-run after commit: `corrected=0 nulled=0` on every single jurisdiction** --
  full idempotency confirmed, exactly as the plan's own docstring claims.

Mechanics are proven. Nothing here needs re-litigating -- go straight to the real run.

## Before you run it for real: confirm the revision

Last check found `refresh-extraction` missing from both `openstates-core` installs on your
host (needs PR #30). **Confirm that's been pulled and both commands (`refresh-extraction`,
`recompute-diff-order`) are present on whatever binary you're about to invoke against RDS**
before starting -- same prerequisite the plan itself calls out, now actually blocking Step 2 if
still unresolved.

## Exact sequence (§3 of the plan -- by data dependency, not ticket-arrival history)

```
refresh-extraction ut --commit
refresh-extraction wa --commit
refresh-extraction us --commit

recompute-diff-order fl --commit
recompute-diff-order us --commit
recompute-diff-order va --commit
recompute-diff-order mi --commit
recompute-diff-order wa --commit
recompute-diff-order ut --commit
```
Do NOT use `recompute-diff-order all` -- deliberately dropped from the plan (touches every
jurisdiction in the DB, not just these six).

**Per §4/§5 of the plan**: run `--dry-run` immediately before each `--commit` and confirm the
two report the same counts (the one comparison that should be exact) -- that's your real
per-command acceptance gate, not the numbers below.

## What to expect -- specific, since we now have real predictions to check against

From the local-vs-RDS comparison, here's what a *correct* backfill run should produce, so you
know a clean result when you see it rather than just trusting a zero-error exit:

- **va**: `recompute-diff-order va --commit` should show roughly **1,827 nulled** (matches
  OPEN-224's 380 + OPEN-246's 1,447 exactly) -- current RDS `diff_not_null` count for VA is
  16,754; after this runs it should drop to something near 14,927 (local's current value),
  modulo whatever real scrape activity has happened since our snapshot.
- **ut**: `recompute-diff-order ut --commit` should show roughly **563 nulled** (matches
  OPEN-224's own recorded UT count exactly) -- RDS `diff_null` is currently 2,043; should rise to
  something near 2,606.
- **fl/us/mi/wa**: expect smaller, real corrections (OPEN-217/219's cleaner-application fixes) --
  no specific predicted count for these the way VA/UT have, since those numbers weren't isolated
  per-jurisdiction in the original Mac-side backfill record.

If VA/UT come back materially different from ~1,827/~563 nulled, stop and flag it here before
moving on -- that would mean something about RDS's actual VA/UT document set differs from what
we assumed, not that the backfill itself is broken.

## Also worth a look while you're in there: MI's 83-bill gap

Separate from this backfill (recompute-diff-order won't touch it -- it's about missing BILLS,
not wrong diffs): RDS has 83 fewer MI bills than local (3,930 vs 4,013), same single
`2025-2026` session on both sides -- ruled out a session-scope explanation already. No ready
explanation yet. Not blocking this backfill run, but flagging in case you notice anything
relevant while working in the same area tonight.

## Safety notes already covered by the plan, restated briefly

- Rollback point: RDS's own existing automatic nightly backups (no new snapshot needed).
- Quiet window: confirm no scheduled load is in flight for these six jurisdictions before
  starting (same discipline as always).
- Record each command's dry-run + commit counts here when done, plus the confirmed revision --
  that's this backfill's evidence trail, same as everything else tonight.
