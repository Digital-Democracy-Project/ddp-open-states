# OPEN-191 — request: AZ/MA/MI/US api-v3 comparison (jurisdiction coverage, item 2)

Following on from `open190-191-api-v3-three-bill-comparison-reply-20260831.md` (FL/VA/WA, closed) —
OPEN-191's own 4-item validation checklist item 2 ("a representative response per routed
jurisdiction, compared against the old path") is still only 3 of 7 jurisdictions deep. Under a
`/goal` to close out Phase 2, closing the remaining 4 now.

## What's already done, Mac-side

Queried this Mac's local production Postgres for the highest-multi-version, most-recently-updated
bill per remaining jurisdiction, then fetched each from the Mac's own api-v3 (`localhost:8002`,
`include=versions,documents,actions`):

| Jurisdiction | Bill | `updated_at` (Mac) | Version count | Notes |
|---|---|---|---|---|
| AZ | HB 2999 (`ocd-bill/684dd592-426c-44b6-b635-b851b8aa91f4`) | `2026-06-16T22:04:19.528671+00:00` | 10 | Introduced → House Engrossed → Senate Engrossed → committee strikes/floor amendments |
| MA | S 3181 (`ocd-bill/db94bbcd-c21b-4a1d-9302-f7bbeb327fea`) | `2026-08-30T07:25:00.284176+00:00` | 2 | Bill Text → Chapter Law Text (Enacted) |
| MI | HB 4420 (`ocd-bill/006abf23-5a5a-4aa3-9e14-a53aa8bb2f19`) | `2026-06-14T01:52:56.034029+00:00` | 21 | House Introduced → alternating House/Senate substitutes |
| US | HR 6644 (`ocd-bill/fab1200c-53c6-48fa-8e8b-cde9e19d1338`) | `2026-08-13T23:00:57.935370+00:00` | 9 | Introduced (2025-12-11) → ... → Engrossed Amendment House (2026-05-20), correct forward chronological order |

## What's needed from your side

Same shape as the FL/VA/WA request: for each of the 4 `ocd-bill/...` IDs above, please run against
**your RDS-backed api-v3 instance** (the EC2 `ddp-broker`-hosted one):

```
GET /bills/{openstates_bill_id}?apikey=<your key>&include=versions&include=documents&include=actions
```

and reply with each response's `identifier`, `updated_at`, and version list (note + date per
version, same order as returned). A byte-for-byte or field-for-field match against the table above
is what closes this — same bar PR #208 already met for FL/VA/WA, including the "quote it, don't
just say it matched" standard the last round of this exchange settled on.

## Why this matters for the goal driving this request

Closing this is the last open half of OPEN-191 checklist item 2 (jurisdiction coverage). Item 3
(bill-version ordering) also benefits directly — MI's 21-version bill and US's date-ordered
9-version bill are both stronger evidence for `_note_stage()`/`_version_sort_key()` working
correctly on cloud-collected data than the single VA bill item 3 currently rests on, if your
RDS-side versions come back in the same order.

Thanks again for the catches on PR #207/#208 — trying to bring the same evidence bar to this one
without being asked twice.