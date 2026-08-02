# Bill.openstates_id "drift" in ddp-broker-py — mechanism confirmed, scale was a measurement artifact (2026-08-02)

## The ticket's claim (Jira OPEN-20)

`ddp-broker-py`'s `Bill.openstates_id` was found stale for 3 of 4 FL `2026F` bills during a
LegBot pipeline test (`run_session_pipeline` against real FL data), causing every downstream
write (`write_bill_artifact`, `write_bill_organization_position`) to fail with
`"No Bill with openstates_id='...' exists yet"`. A follow-up scan comparing all 817 bills broker
tracks against their current id in our internal OpenStates fork found 723/807 (~90%) mismatched
— which looked, at first glance, like a severe, widespread problem.

## The real mechanism (confirmed, still valid)

`openstates.importers.bills.BillsImporter.get_object()` (`openstates-core/openstates/importers/bills.py:108-118`)
matches an existing `Bill` row by `(legislative_session_id, identifier)`. If that match ever
fails, the importer falls back to inserting a brand-new row with a fresh `uuid4` PK — silently,
no error (a known, accepted-rare edge case per `ddp-infra/PLAN-bill-document-provenance.md:35`).

In `ddp-broker-py`, `OpenStatesService.update_bill()` sets `Bill.openstates_id` once and never
updates it again:

```python
# apps/ddp-broker/fetch/interfaces/OpenStates/openstates_service.py:1542
bill_record.openstates_id = bill_record.openstates_id or strip_ocd_prefix(bill_data.id)
```

`get_or_create_bill()` has the same effect via Django's `defaults={}`. So if the upstream id ever
legitimately changes after first sync, broker has no way to notice. This part of the original
report is correct and still stands as a real, if currently latent, bug.

## Why the 90% figure was misleading

Production `ddp-broker` only routes **Utah and Michigan** through our internal fork
(`OpenStatesService._get_client_for_jurisdiction()`, gated by `DDP_OPENSTATES_JURISDICTIONS`,
prod default `UT,MI` — confirmed live via `ddp-open-states-dev/PLAN-open-states.md`'s 2026-07-23
check: prod does **not** match the local checkout's wider `.env` list). Every other jurisdiction,
including FL and US Congress, syncs against the real public `v3.openstates.org` — a completely
separate OpenStates instance that mints its own independent UUIDs.

The dev broker DB used for the comparison isn't live-synced at all — it's restored wholesale from
a production `pg_dump` (`ddp-broker-py/infra/scripts/restore-broker-db.sh`), and `common_bill` is
not among the tables excluded from that restore. So the original OPEN-20 test compared our fork's
*live* FL ids against broker's *dumped-from-prod, public-API-sourced* ids: two unrelated ID
spaces. A mismatch there proves nothing about same-source drift.

The tell: **Utah and Michigan — the only two jurisdictions actually routed through our fork in
production — showed zero mismatches** in the full 817-bill scan. Every other jurisdiction, all
routed through the public API in prod, was almost entirely mismatched. That split is the
explanation, not a coincidence.

(An earlier read of 11 US-Congress bills as "clean proof" of same-source drift, because broker's
row was created *after* our fork's row already existed, was wrong and has been retracted — US
isn't in prod's `DDP_OPENSTATES_JURISDICTIONS` either, so those ids also came from the public API.)

## Have we ever observed a bill's UUID change within our own fork's database?

No. Checked directly against `ddp-openstates-postgres-1`: all four FL 2026F bills exist as
exactly one row each, created in a single batch at one timestamp — no orphaned second row, no
trace of a prior id. What we did find is that several sessions' bills were each bulk-created
within a single hour (e.g. ~1,900 FL 2026 bills in one hour on 2026-06-19, ~2,190 AZ bills in one
hour on 2026-06-16) — consistent with whole-database reloads of our fork at various points, not
with individual bills quietly getting reassigned during normal re-scrapes. Neither database has
a history/audit table, and scrape-run logs (`pupa_runplan`/`pupa_scrapereport`) only record
aggregate insert/update counts, not per-bill old-id→new-id transitions — so live per-bill drift
can't be fully ruled in or out, only judged on the evidence available, which currently points
away from it.

## Outcome

- Filed [ddp-broker-py#261](https://github.com/Digital-Democracy-Project/ddp-broker-py/issues/261)
  and Jira BROKER-15: replace the write-once guard with a real reconcile-on-sync. Per the broker
  admin's request, retain the superseded id rather than just overwriting it, so a future
  jurisdiction switchover (public API → internal fork) leaves a record of both UUIDs.
- Evaluated `Bill.attributes` (`common/models/Bill.py`, a `GenericRelation` to the shared
  `KeyValueAttribute` table used today only for Webflow slug/URL bookkeeping) as a place to store
  the legacy id, and rejected it — it has no cross-bill uniqueness on the identifier value and no
  identifier semantics, just freeform per-bill key/value pairs.
- Found the actual precedent already exists for legislators: `RepresentativeExternalId`
  (`common/models/RepresentativeExternalId.py`) is a dedicated FK table with `scheme` +
  `identifier` and a global `unique_together(scheme, identifier)` constraint, and its own
  docstring already lists a `'legacy_openstates'` scheme for exactly this scenario. Recommended
  fix: add an analogous `BillExternalId` table and write the old id there (atomically, alongside
  updating any `BillVersion` rows FK'd via `to_field="openstates_id"`) before overwriting
  `Bill.openstates_id` with the new canonical value.
- This surfaced a second, pre-existing issue: BROKER-14 /
  [ddp-broker-py#161](https://github.com/Digital-Democracy-Project/ddp-broker-py/issues/161) had
  proposed the opposite direction for representatives — fully migrating
  `Representative.openstates_id` into `RepresentativeExternalId` and dropping the column. That
  plan has a gap: `RepresentativeExternalId` has no way to mark one `scheme='openstates'` row as
  canonical vs. an alias, and the codebase already produces multiple such rows per representative
  in practice (cross-jurisdiction alias backfill). Revised both BROKER-14 and #161 to match the
  BROKER-15 pattern instead: keep `Representative.openstates_id` as the live canonical column,
  keep `RepresentativeExternalId` for aliases/history only, no column drop.

## References

- Jira [OPEN-20](https://digitaldemocracyproject.atlassian.net/browse/OPEN-20) — full
  investigation log and data-lineage comparison
- Jira BROKER-14, BROKER-15
- GitHub `ddp-broker-py` issues #161, #261
