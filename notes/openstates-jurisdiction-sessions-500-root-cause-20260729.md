# OPEN-12's back_populates diagnosis was wrong — real cause is a missing table (2026-07-29)

## The ticket's claim

OPEN-12 reported `GET /jurisdictions/{iso2}?include=legislative_sessions` returning HTTP 500 for
every tracked jurisdiction, and attributed it to `api-v3/api/db/models/jurisdiction.py`:
`Jurisdiction.legislative_sessions` and `LegislativeSession.downloads` declare `back_populates`
that their partners (`LegislativeSession.jurisdiction`, `DataExport.session`) don't reciprocate,
and the claim was that SQLAlchemy raises a mapper-configuration error the first time such a
mismatched pair is fully configured — which `JurisdictionPagination.include_map_overrides`
(`api/pagination.py`) forces by mapping `legislative_sessions` to
`selectinload("legislative_sessions")` *and* `selectinload("legislative_sessions.downloads")`.

Plausible-sounding, and wrong. This is the second corrected root-cause diagnosis in this repo
recently (see `b5c8acd` for the UT bill-version/document one) — worth independently verifying
tickets' root-cause sections against the actual system before planning a fix, not just against
the code.

## What's actually true

Two independent checks show the back_populates mismatch causes no error at all in this
codebase's pinned SQLAlchemy (1.4.44):

1. Installed sqlalchemy==1.4.44 in isolation, imported api-v3's real, unmodified
   `api/db/models` package (no transcription), and called `sqlalchemy.orm.configure_mappers()`
   directly — succeeds cleanly across the entire model graph, zero errors, zero warnings.
2. Upstream `openstates/api-v3`'s own CI is green on `main`, and its existing
   `test_jurisdiction_include_sessions` test already exercises the list endpoint with
   `include=legislative_sessions` (sessions *and* downloads inline) and passes. If the mismatch
   were a real mapper-config error, this test would already be red upstream.

The real cause, from the actual traceback (reproduced live against `ddp-openstates-api-1` +
`ddp-openstates-postgres-1`, `GET /jurisdictions/fl?include=legislative_sessions`):

```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "bulk_dataexport" does not exist
```

`bulk_dataexport` (the table backing `DataExport` / `LegislativeSession.downloads`) does not
exist in DDP's Postgres schema. Checked every `__tablename__` referenced anywhere in api-v3's
models against `\dt` on the DDP database — `bulk_dataexport` is the *only* one missing; all other
37 tables exist. It's absent because DDP's schema is provisioned by `openstates-core`'s
`os-initdb`, which builds the OCD/pupa scraping schema — `bulk_dataexport` belongs to
openstates.org's own bulk-CSV-export Django app, a feature DDP's replica never runs and was never
part of that schema to begin with.

This also explains the two details the original diagnosis got right for the wrong reason:

- **"Not jurisdiction-specific, reproduces identically for all four tested"** — true, because
  `include_map_overrides` selectinloads `legislative_sessions.downloads` unconditionally
  whenever `legislative_sessions` is requested, so *any* jurisdiction with legislative sessions
  (i.e. all of them) hits the missing table, independent of jurisdiction data.
- **Why upstream's test suite doesn't catch it** — `api/tests/conftest.py`'s
  `create_test_database()` calls `Base.metadata.create_all(bind=engine)`, which creates
  `bulk_dataexport` along with everything else. Upstream's test environment is never missing
  this table, so there was nothing for their existing test to catch. The gap is specific to how
  DDP hand-provisions its replica, not a bug in api-v3's code.

## Why the fix isn't a code change to `api-v3`

Even setting the above aside: `api-v3/` is a deliberately pristine, unpatched checkout of
upstream `openstates/api-v3` (`PRIMITIVES.md`) with no mechanism to preserve a local edit across
a future `git pull` — the same reasoning `PLAN-open-states.md`'s votebot session-identifier
decision already established when it ruled out patching api-v3's route for a different bug. The
`back_populates` one-sidedness is a real, harmless code smell worth fixing upstream at some point
(good hygiene, zero functional impact today, confirmed by the `configure_mappers()` check above),
but it does not belong in this repo and does not fix this incident.

The actual fix: create `bulk_dataexport` idempotently as part of bringing the api-v3 stack up
(`start-os-api.sh`), using api-v3's own `DataExport` SQLAlchemy model as schema source of truth
rather than hand-transcribed DDL. See that script for the implementation and the accompanying
boot-time smoke test that now guards against this exact failure mode recurring silently.
