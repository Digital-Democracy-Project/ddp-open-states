# Verified: bill actions ARE persisted in the DDP OpenStates replica — "can't be recomputed from the database alone, the actions feed isn't persisted anywhere" is incorrect

## Context

Another agent, working on a task whose details aren't reproduced here, asserted:

> This can't be recomputed from the database alone — the actions feed isn't persisted anywhere.

Asked to check this claim against the actual schema, data, and the public v3.openstates.org API.
It does not hold: the actions feed is persisted in full, in the same replica every other DDP tool
already reads from.

## Method

Checked three things directly:
1. The `openstates-core` Django schema in this checkout, for a bill-actions model.
2. The production OpenStates Postgres DB (`postgresql://openstates:openstates_dev@localhost:5433/openstates`
   — the actual replica; **not** the `cams` DB the `postgres` MCP tool defaults to, and not this
   checkout's separate `openstates_dev` DB) for real row counts and sample data.
3. The public `v3.openstates.org` API (via `OPENSTATES_API_KEY` from this checkout's `.env`,
   already used the same way by `quality_check.py`) for the same bill, to confirm the local rows
   match what OpenStates itself calls the "actions" feed.

## Result

**The table exists and is fully populated.**

`opencivicdata_billaction` (prod DB): **482,212 rows**, columns
`id (uuid), description (text), date (varchar), classification (array), order (int), bill_id, organization_id`.

A companion table, `opencivicdata_billactionrelatedentity` (**31,562 rows**), stores each action's
related people/organizations (e.g. "SENATE CO-SPONSOR(S) NAMED: ..." actions link to the named
legislator).

**Local rows match the public API's `actions[]` exactly**, spot-checked on MI SB 1136
(`ocd-bill/423ac389-bd5c-4145-8f4e-317bd273be42` locally):

| Source | order 0 | order 1 | order 2 |
|---|---|---|---|
| Local DB (`opencivicdata_billaction`) | "INTRODUCED BY SENATOR KEVIN HERTEL" (`introduction`), 2026-07-29 | "REFERRED TO COMMITTEE ON GOVERNMENT OPERATIONS" (`referral-committee`), 2026-07-29 | "SENATE CO-SPONSOR(S) NAMED: MALLORY MCMORROW" (`[]`), 2026-08-12 |
| Public v3 API (`GET /bills?...&include=actions`) | identical description, classification, date | identical | identical |

Date, description, classification, and order all matched, field-for-field, across both sources.

## Conclusion

The DDP OpenStates replica persists the full actions feed — it's queryable directly from Postgres
without any dependency on the live v3 API. If the other agent's underlying concern was about some
other derived or aggregated view (not the raw actions feed itself), that should be named
specifically; as stated, the claim that "the actions feed isn't persisted anywhere" is false for
this database.

## References

- `openstates-core/openstates/data/models/bill.py` — `BillAction` model definition
- Production DB: `opencivicdata_billaction`, `opencivicdata_billactionrelatedentity`
  (`postgresql://openstates:openstates_dev@localhost:5433/openstates`)
- Public API cross-check: `https://v3.openstates.org/bills?jurisdiction=Michigan&identifier=SB+1136&include=actions`
- `quality_check.py` — existing precedent in this repo for hitting `v3.openstates.org` with
  `OPENSTATES_API_KEY` from `.env`
