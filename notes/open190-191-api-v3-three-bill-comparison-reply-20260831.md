# OPEN-190/191: api-v3 response comparison — RDS-side results (reply)

*Written 2026-08-31, from the INFRA-1 host (`/opt/ddp-open-states`, api-v3 on `localhost:8002`,
pointed at the real `ddp-openstates` RDS instance). Replies to
`notes/open190-191-api-v3-three-bill-comparison-20260831.md`.*

All three requests returned 200s from the RDS-backed instance. Raw responses and per-bill notes
below; I don't have the Mac-side (local Postgres-backed) api-v3 captures on hand to diff against
myself for VA/WA — only FL's Mac-side response was already captured in
`notes/open190-phase1-closure-validation-20260831.md` (PR #207). Please fold in against whatever
local-side captures you're holding.

## FL HB 1325 — matches the Mac-side capture in PR #207, field for field

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

Checked every field against the JSON pasted in PR #207's note — identical, including
`updated_at` to the microsecond. This closes OPEN-190's third named sub-part (api-v3 responses)
for the bill it was captured against.

## VA SB 192 (`include=versions`) — correct stage-aware ordering, 2 versions

Metadata (row-count fields, not the full versions array):

```json
{
  "id": "ocd-bill/ae6f0d7a-6a70-430e-a85b-557412caaedf",
  "session": "2027",
  "jurisdiction": {"id": "ocd-jurisdiction/country:us/state:va/government", "name": "Virginia", "classification": "state"},
  "from_organization": {"id": "ocd-organization/9f1a0a17-d2fb-4d0c-90fb-119004411b83", "name": "Senate", "classification": "upper"},
  "identifier": "SB 192",
  "title": "State-owned bottomlands; localities, property interest.",
  "classification": ["bill"],
  "subject": [],
  "extras": {"VA_LEG_ID": 99056},
  "created_at": "2026-08-25T00:31:20.933573+00:00",
  "updated_at": "2026-08-25T00:31:20.943513+00:00",
  "openstates_url": "https://openstates.org/va/bills/2027/SB192/",
  "first_action_date": "2026-01-09",
  "latest_action_date": "2026-07-21",
  "latest_action_description": "Continued from last session",
  "latest_passage_date": ""
}
```

`versions` array — 2 entries, in stage order (not insertion/date order, both bear `date: ""`):

1. `note: "Introduced"` — PDF (with `raw_text`) + HTML links
2. `note: "Agriculture, Conservation and Natural Resources Substitute"` — PDF (with `raw_text`
   and a real `diff_from_previous_version` against version 1) + HTML links

This is the same "Introduced before the later committee substitute" ordering PR #208's README
already claims for OPEN-90/92 — confirms the claim holds through this second, independently
stood-up api-v3 instance too, not just the Mac's. I have full raw `raw_text`/
`diff_from_previous_version` content if you want it pasted here too; left it out of this note as
it's the full bill text and a full unified diff (verified both fields are non-empty and the diff
is a real single-line-of-substance textual diff between the two versions' text, not boilerplate
or empty).

## WA SB 6099 — no versions requested, metadata only

```json
{
  "id": "ocd-bill/271de7b7-47b6-4992-bb36-40c54862e135",
  "session": "2025-2026",
  "jurisdiction": {"id": "ocd-jurisdiction/country:us/state:wa/government", "name": "Washington", "classification": "state"},
  "from_organization": {"id": "ocd-organization/ddae63d3-9f3e-4c46-a00f-703fe21b54d1", "name": "Senate", "classification": "upper"},
  "identifier": "SB 6099",
  "title": "Providing basic taxpayer fairness by delaying department of revenue action with regard to tax changes until rule making is finalized.",
  "classification": ["bill"],
  "subject": [],
  "extras": {},
  "created_at": "2026-06-15T23:09:25.014748+00:00",
  "updated_at": "2026-06-15T23:09:25.032880+00:00",
  "openstates_url": "https://openstates.org/wa/bills/2025-2026/SB6099/",
  "first_action_date": "2026-01-13",
  "latest_action_date": "2026-01-13",
  "latest_action_description": "First reading, referred to Ways & Means.",
  "latest_passage_date": ""
}
```

Nothing unusual — matches the ~2.5-month staleness already noted in PR #208's README (this
bill's own `updated_at`/`latest_action_date` are consistent with that, not a new discrepancy).

## Net

FL: closed, confirmed identical to the Mac-side capture already in PR #207. VA: stage-ordering
criterion confirmed on this instance too. WA: nothing anomalous, but I don't have a Mac-side
api-v3 capture for either VA or WA to diff byte-for-byte myself — over to whoever's holding
those to fold in and mark PR #207/#208's outstanding checklist lines however they land.
