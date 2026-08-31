# OPEN-191 — AZ/MA/MI/US comparison: 3/4 exact, MA S 3181 is genuinely stale on RDS

*Replies to `notes/open191-az-ma-mi-us-comparison-apikey-typo-20260831.md`.*

Corrected key worked — `apikey=00000000-0000-0000-0000-000000000001` (the version with the
missing `-0000-` group 401'd, the full 5-group UUID authenticates fine). All four requests run
against this host's RDS-backed api-v3 (`localhost:8002`), same shape as the frozen baseline in
`infra/rds/README.md` on `docs/open191-phase2-closure-evidence` (PR #213).

## AZ HB 2999, MI HB 4420, US HR 6644 — exact match

Compared field-for-field against the quoted baseline (`updated_at`, version/document/action
counts):

| Bill | `updated_at` | Versions | Documents | Actions |
|---|---|---|---|---|
| AZ HB 2999 | `2026-06-16T22:04:19.528671+00:00` | 10 | 11 | 18 |
| MI HB 4420 | `2026-06-14T01:52:56.034029+00:00` | 21 | 5 | 51 |
| US HR 6644 | `2026-08-13T23:00:57.935370+00:00` | 9 | 106 | 59 |

All three identical to the Mac-side baseline on every one of those fields. No discrepancies.

## MA S 3181 — real mismatch, RDS is stale, not a version-ordering bug

RDS-side response:
```json
{
  "id": "ocd-bill/db94bbcd-c21b-4a1d-9302-f7bbeb327fea",
  "session": "194th",
  "identifier": "S 3181",
  "created_at": "2026-08-09T10:59:45.242049+00:00",
  "updated_at": "2026-08-24T23:34:27.918254+00:00",
  "first_action_date": "2026-07-16",
  "latest_action_date": "2026-08-24",
  "latest_action_description": "Enacted and laid before the Governor",
  "latest_passage_date": "2026-08-24"
}
```
1 version (`Bill Text`, 1 link), 0 documents, 12 actions — last 3: `Senate concurred in the House
amendment` → `Enacted` → `Enacted and laid before the Governor`, all dated 2026-08-24.

Baseline (Mac, `updated_at` `2026-08-30T07:25:00.284176+00:00`): 2 versions (`Bill Text`,
`Chapter Law Text (Enacted)`), 0 documents, 13 actions, `latest_action_description` `"Signed by
the Governor, Chapter 193 of the Acts of 2026"`.

RDS's copy of this bill is missing exactly its final stage — the governor's signature action and
the resulting `Chapter Law Text (Enacted)` version. Everything up through `"Enacted and laid
before the Governor"` is present and correct; nothing downstream of that point made it into RDS.
This reads as the RDS snapshot for this one bill predating its gubernatorial signature (2026-08-25
per the baseline's `latest_action_date`), not a version-ordering or field-mapping bug — the data
that *is* there matches the baseline exactly, field for field.

## Where this leaves OPEN-191

Jurisdiction coverage (checklist item 2) is now **closed** for FL/VA/WA (PR #208) plus AZ/MI/US
here — 6 of 7 clean matches. MA is the one open item, and it's a data-freshness gap on RDS for
this specific bill rather than evidence against the routing/serialization path itself (AZ/MI/US
all being byte-for-byte correct on the same instance argues against a systemic issue). Worth a
call on whether that's just "RDS needs a re-sync/re-collection pass to pick up recent MA
enactments" or something worth tracking as its own ticket.
