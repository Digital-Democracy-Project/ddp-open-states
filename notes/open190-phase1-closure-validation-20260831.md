# OPEN-190 (Phase 1): status on the remaining two acceptance criteria

OPEN-190's rollout itself (every actively-tracked jurisdiction — FL, VA, WA, AZ, MA, USA both
chambers, MI — collected via real Fargate tasks and loaded into the real `ddp-openstates` RDS
instance with zero duplication) was already done; see `infra/rds/README.md`. This documents the
two acceptance criteria that specifically needed a dedicated check.

**Status: one of the two is fully closed (rollback). The other (local-vs-cloud comparison) is
partially closed — its own wording explicitly names three things to compare, and only two of
the three have evidence yet.** Not claiming this ticket is ready to close outright; see below.

## 1. Local-vs-cloud comparison — PARTIAL

**Ticket's exact wording**: *"One jurisdiction collected in the cloud and loaded, matching a
local run of the same jurisdiction on row counts, document references and api-v3 responses."*
Three named things to compare. Two have evidence; the third is outstanding.

Picked a real, already-collected bill rather than launching a new scrape: Florida HB 1325
("Linking Industry to Nursing Education Fund"), 2026 session — present in both the Mac's local
production Postgres and the RDS instance (RDS was seeded from a dump of that same production
database, then had a real Fargate-collected FL run loaded on top; this bill's own data predates
that overlay, so it's a clean apples-to-apples check of data already common to both).

Picked a real, already-collected bill rather than launching a new scrape: Florida HB 1325
("Linking Industry to Nursing Education Fund"), 2026 session — present in both the Mac's local
production Postgres and the RDS instance (RDS was seeded from a dump of that same production
database, then had a real Fargate-collected FL run loaded on top; this bill's own data predates
that overlay, so it's a clean apples-to-apples check of data already common to both).

**Row counts — CLOSED, identical on both:**

| | Local Postgres | RDS |
|---|---|---|
| title | Linking Industry to Nursing Education Fund | (same) |
| updated_at | 2026-08-15 17:52:32.911374+00 | (same) |
| actions | 28 | 28 |
| versions | 3 | 3 |
| sponsors | 5 | 5 |

**Document references — CLOSED, identical set, both sides:**

```
H 1325 Filed  -> https://flsenate.gov/Session/Bill/2026/1325/BillText/Filed/PDF
H 1325 c1     -> https://flsenate.gov/Session/Bill/2026/1325/BillText/c1/PDF
H 1325 c2     -> https://flsenate.gov/Session/Bill/2026/1325/BillText/c2/PDF
```

(Row order differed between the two queries — a sort-key tie on `bv.date`, not a data
difference; the same three URLs/media types are present on both sides.)

**api-v3 responses — OUTSTANDING.** One side captured, not both — this is *not* a closed
comparison yet, only a captured baseline to compare against once the second response arrives.
Queried against the Mac's own existing instance (`GET
/bills/ocd-bill/03418e03-cd16-4614-829f-215e5afa5fec`):

```json
{
  "id": "ocd-bill/03418e03-cd16-4614-829f-215e5afa5fec",
  "session": "2026",
  "jurisdiction": {"id": "ocd-jurisdiction/country:us/state:fl/government", "name": "Florida", "classification": "state"},
  "from_organization": {"id": "ocd-organization/8b0147dc-8942-4fd5-91c4-a72a92a8e1fe", "name": "House", "classification": "lower"},
  "identifier": "HB 1325",
  "title": "Linking Industry to Nursing Education Fund",
  "classification": ["bill"],
  "subject": ["subject index"],
  "extras": {},
  "created_at": "2026-06-19T00:27:59.942288+00:00",
  "updated_at": "2026-08-15T17:52:32.911374+00:00",
  "openstates_url": "https://openstates.org/fl/bills/2026/HB1325/",
  "first_action_date": "2026-01-09",
  "latest_action_date": "2026-03-10",
  "latest_action_description": "Laid on Table; Companion bill(s) passed, see CS/SB 1246 (Ch. 2026-101)",
  "latest_passage_date": ""
}
```

The same query against the second, independent api-v3 instance stood up for INFRA-1 (on the
production `ddp-broker` EC2 host, pointed at the real RDS instance) was requested via that
repo's `notes/ops-handoff` channel; as of this writing, no response yet. **This criterion should
not be marked satisfied until that response arrives and actually matches** (or any real
difference found is understood and judged acceptable) — the row-count and document-link
comparisons above are real, closed evidence, but they are two of the three named things, not a
substitute for the third.

## 2. Rollback demonstrated, including watermark resuming from the store — CLOSED

**Ticket's exact wording**: *"Per-jurisdiction rollback demonstrated, not assumed, including the
watermark resuming from the store."* The "not assumed" is the operative word — the plan doc's
own claim (*"a reverted jurisdiction resumes correctly because `run-scrape.sh` hydrates its
local markers from the external store at startup"*) was a design intent, not yet independently
verified. Tested that exact mechanism directly against the real production S3 memory store:

```
$ echo "2099-01-01T00:00:00" > $TMPDIR/va.ts        # deliberately impossible local value
$ SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX=prod \
  SCRAPER_MEMORY_S3_CMD=ddp-prod-s3-openstates-scrapers \
  scraper_memory_hydrate_markers "va" "va" "$TMPDIR"
$ cat $TMPDIR/va.ts
2026-08-30T02:30:32
```

That value is an exact match for what's actually stored at `prod/va/va/va.ts` in the real
memory store (confirmed via a separate, direct `get`). The local marker was genuinely
overwritten by the external store's value, not left alone or merged.

**Scope of this claim, precisely**: this satisfies the "including the watermark resuming from
the store" clause directly — the specific mechanism the plan's own text names — but does not
itself exercise a full operational rollback (stopping the cloud path, re-enabling the Mac's
scheduled scrape, a real subsequent run completing end to end). Scoped deliberately to just this
mechanism rather than a full `run-scrape.sh` invocation: a live rollback run would also exercise
the cross-machine import-lock machinery (already covered by OPEN-187/OPEN-203's own test suites)
and would cost a real request against VA's site for no additional evidence about the specific
claim this criterion names.

## A real bug found along the way, not part of this ticket's scope

While attempting the comparison test with a fresh incremental VA collection (before switching to
the already-collected-bill approach above), found and filed **OPEN-220**: `VaBillScraper` hits
the same `ScrapeError: no objects returned` crash `OPEN-216` already documents for
`USBillScraper`, on a genuinely empty incremental window. Not fixed here — tracked separately,
now confirmed as a pattern across (at least) two scrapers rather than a one-off.
