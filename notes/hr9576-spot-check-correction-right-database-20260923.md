# Correction: earlier spot-check queried the wrong database on this Postgres server -- redone against the real replica, now an exact match

**Re:** `hr9576-spot-check-sample-20260923.md` (this branch, earlier). Ramon caught this --
`ddp-openstates-postgres-1` (:5433) hosts multiple databases on the same server, and every query
this whole thread ran against it (including the original "this replica looked stale" finding)
used the `openstates` database -- a separate, stale local database, not the actual RDS logical
replica. The real one is `openstates_rds_repl_20260911` (same container, same port, different
`-d` argument), set up per the earlier-cited OPEN-271/272/273 work, complete with its own
`ddp_local_readonly` grant. `\l` inside the container shows it plainly; nobody had run that.

## Confirms HR9576 was there all along

```sql
SELECT b.identifier, ve.motion_text, ve.start_date FROM opencivicdata_voteevent ve
JOIN opencivicdata_bill b ON ve.bill_id = b.id WHERE b.identifier = 'HR 9576';
-- HR 9576 | On Passage | 2026-09-16T22:37:00+00:00
```

## Re-ran the dry-run against the correct database -- exact match to production

```
Loaded 837 distinct person identifiers.
Found 75,887 unresolved vote records with a usable note/identifier.
Dry run complete. Would resolve 72,550 records (3,337 still unresolvable).
```

Identical to the real RDS trigger's own numbers, digit for digit. This *is* a live, current
mirror of production -- the earlier "3.3x gap, replica lags behind" explanation in the first
spot-check note was wrong; it was purely an artifact of querying the wrong database, not real
staleness.

## Redid the spot-check for real this time

Same Bean (FL) -> B001314 -> Aaron Bean pattern confirmed across 6 different bills, correct
every time. Unresolvable set re-characterized against the real data: **3,337 total, 16 distinct
identifier values (not 14 -- the earlier count was itself from the wrong database), zero
ambiguous cases** -- every one is still "no matching identifier at all," the same missing-`lis`-
id-for-some-senators shape as before, just measured correctly this time.

## Net

Same conclusion as the (now-superseded) earlier note, but on a verified-correct dataset instead
of a coincidentally-similar-looking stale one: clean, safe to `--commit`. Nothing about the
recommendation changes, just the confidence behind it.
