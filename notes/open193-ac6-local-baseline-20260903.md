# OPEN-193 AC6: local-Postgres baseline captured -- need the RDS-side numbers to diff

Closing out OPEN-193's AC6 ("RDS freshness re-measured per jurisdiction"). I have real read
access to the Mac's local production Postgres from here (confirmed via `activate.sh`'s own
`DATABASE_URL`) but zero path to RDS (confirmed: `ddp-scraper` IAM lacks even
`rds:DescribeDBInstances`, and RDS is documented as reachable only through the WireGuard jump
box). You're the one with real, confirmed RDS access tonight -- need you to run the RDS half.

## Important framing before you run this -- direction of "fresher" has flipped

Per Ramon: **all of today's 9-jurisdiction canary ran in Fargate and loaded straight to RDS**,
while the Mac's own scraper schedule has been off since earlier today (OPEN-253) -- so the
Mac's local Postgres hasn't picked up anything from today's runs at all, and some of these
jurisdictions haven't scraped locally since their last Sunday `secondary.jurisdictions` cycle.

**Expect RDS to now be NEWER than the local-Postgres baseline below for every jurisdiction
touched by today's canary** (fl, wa, va, mi, ut, az, usa, ma) -- that's the correct, expected
result, not a discrepancy to chase. The one exception is **nc**, which had no individual
Fargate trigger today (no `_OPENSTATES_SINGLE_JURISDICTION` entry yet) -- nc's RDS/local
comparison is the one where I'd actually expect them close together.

The actual thing worth flagging as a real gap: anything where RDS is *older* than local for a
canary jurisdiction (would mean today's load didn't actually land), or where either side is
missing a jurisdiction entirely, or where the diff_null/diff_not_null split is wildly different
in a way that doesn't trace to a known unapplied backfill (see `PLAN-rds-data-quality-backfill.md`,
merged but not yet run against RDS -- OPEN-211/217/219/224/246's corrections are NOT expected to
be in RDS yet, so a diff_null count that doesn't match local there is *also* expected, not new).

## Local-Postgres baseline (captured just now, read-only, all 9 tracked jurisdictions)

```json
{
  "fl": {
    "jurisdiction_id": "ocd-jurisdiction/country:us/state:fl/government",
    "bill_count": 7685,
    "max_bill_updated_at": "2026-08-15T17:52:32.911374+00:00",
    "vote_event_count": 10076,
    "version_doc_count": 20038,
    "diff_null": 11519,
    "diff_not_null": 8519,
    "spot_check_bill": {
      "id": "ocd-bill/7a46c120-eadf-448a-82f4-fe3160bb02b7",
      "identifier": "HB 399",
      "updated_at": "2026-08-02T11:37:23.549561+00:00",
      "version_count": 7
    }
  },
  "wa": {
    "jurisdiction_id": "ocd-jurisdiction/country:us/state:wa/government",
    "bill_count": 3411,
    "max_bill_updated_at": "2026-06-15T23:09:25.032880+00:00",
    "vote_event_count": 2302,
    "version_doc_count": 11636,
    "diff_null": 7097,
    "diff_not_null": 4539,
    "spot_check_bill": {
      "id": "ocd-bill/0147f79c-da68-44ad-a310-934fd23491bc",
      "identifier": "HB 1960",
      "updated_at": "2026-06-15T23:09:05.098932+00:00",
      "version_count": 6
    }
  },
  "usa": {
    "jurisdiction_id": "ocd-jurisdiction/country:us/government",
    "bill_count": 37809,
    "max_bill_updated_at": "2026-09-01T23:09:41.661155+00:00",
    "vote_event_count": 1548,
    "version_doc_count": 89091,
    "diff_null": 76166,
    "diff_not_null": 12925,
    "spot_check_bill": {
      "id": "ocd-bill/fab1200c-53c6-48fa-8e8b-cde9e19d1338",
      "identifier": "HR 6644",
      "updated_at": "2026-08-13T23:00:57.935370+00:00",
      "version_count": 9
    }
  },
  "va": {
    "jurisdiction_id": "ocd-jurisdiction/country:us/state:va/government",
    "bill_count": 4380,
    "max_bill_updated_at": "2026-08-25T00:31:20.943513+00:00",
    "vote_event_count": 11553,
    "version_doc_count": 25541,
    "diff_null": 10614,
    "diff_not_null": 14927,
    "spot_check_bill": {
      "id": "ocd-bill/2cc31350-f636-48cb-a38c-ef928af06ed9",
      "identifier": "SB 783",
      "updated_at": "2026-06-29T17:27:31.678938+00:00",
      "version_count": 16
    }
  },
  "mi": {
    "jurisdiction_id": "ocd-jurisdiction/country:us/state:mi/government",
    "bill_count": 4013,
    "max_bill_updated_at": "2026-08-29T22:14:49.991654+00:00",
    "vote_event_count": 1226,
    "version_doc_count": 13825,
    "diff_null": 9061,
    "diff_not_null": 4764,
    "spot_check_bill": {
      "id": "ocd-bill/006abf23-5a5a-4aa3-9e14-a53aa8bb2f19",
      "identifier": "HB 4420",
      "updated_at": "2026-06-14T01:52:56.034029+00:00",
      "version_count": 21
    }
  },
  "ma": {
    "jurisdiction_id": "ocd-jurisdiction/country:us/state:ma/government",
    "bill_count": 11451,
    "max_bill_updated_at": "2026-08-30T07:34:29.218947+00:00",
    "vote_event_count": 474,
    "version_doc_count": 11623,
    "diff_null": 11332,
    "diff_not_null": 291,
    "spot_check_bill": {
      "id": "ocd-bill/db94bbcd-c21b-4a1d-9302-f7bbeb327fea",
      "identifier": "S 3181",
      "updated_at": "2026-08-30T07:25:00.284176+00:00",
      "version_count": 2
    }
  },
  "ut": {
    "jurisdiction_id": "ocd-jurisdiction/country:us/state:ut/government",
    "bill_count": 1021,
    "max_bill_updated_at": "2026-07-28T19:14:43.829674+00:00",
    "vote_event_count": 1917,
    "version_doc_count": 9371,
    "diff_null": 2606,
    "diff_not_null": 6765,
    "spot_check_bill": {
      "id": "ocd-bill/d369d37d-d652-421c-a7a2-e1c3f5cb6b5d",
      "identifier": "HB 44",
      "updated_at": "2026-07-28T19:14:36.652874+00:00",
      "version_count": 25
    }
  },
  "az": {
    "jurisdiction_id": "ocd-jurisdiction/country:us/state:az/government",
    "bill_count": 2190,
    "max_bill_updated_at": "2026-08-25T11:43:44.516612+00:00",
    "vote_event_count": 3443,
    "version_doc_count": 8933,
    "diff_null": 4460,
    "diff_not_null": 4473,
    "spot_check_bill": {
      "id": "ocd-bill/684dd592-426c-44b6-b635-b851b8aa91f4",
      "identifier": "HB 2999",
      "updated_at": "2026-06-16T22:04:19.528671+00:00",
      "version_count": 10
    }
  },
  "nc": {
    "jurisdiction_id": "ocd-jurisdiction/country:us/state:nc/government",
    "bill_count": 2338,
    "max_bill_updated_at": "2026-08-31T22:03:52.696008+00:00",
    "vote_event_count": 774,
    "version_doc_count": 6192,
    "diff_null": 6138,
    "diff_not_null": 54,
    "spot_check_bill": {
      "id": "ocd-bill/334b9717-b1af-4d26-9e4f-86ef18c0fa78",
      "identifier": "SB 257",
      "updated_at": "2026-08-31T22:02:35.494516+00:00",
      "version_count": 31
    }
  }
}
```

Fields per jurisdiction: `bill_count`, `max_bill_updated_at` (newest bill's `updated_at`),
`vote_event_count`, `version_doc_count`/`diff_null`/`diff_not_null` (the same
`ddp_bill_version_document` split `PLAN-rds-data-quality-backfill.md` §5 already uses), and
`spot_check_bill` (the most-versioned bill per jurisdiction, same selection rule
`infra/rds/README.md`'s own OPEN-191 checklist established -- for a later field-for-field
`diff_from_previous_version` comparison if the aggregate numbers raise a question).

## What I need back

Run the equivalent queries against RDS for the same 9 jurisdictions (same table names --
`opencivicdata_bill`, `opencivicdata_voteevent`, `ddp_bill_version_document`, joined through
`opencivicdata_legislativesession.jurisdiction_id`) and send back the same shape. I'll diff the
two and write up the actual finding to close AC6 -- expected direction and all -- rather than
just assert it.
