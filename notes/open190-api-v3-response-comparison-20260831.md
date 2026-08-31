# OPEN-190/OPEN-191: api-v3 response comparison request

*Written 2026-08-31 for the prod agent. Quick, read-only ask — not a deploy, doesn't touch
anything running on the host.*

## What I need

A single `curl` from this host, against the api-v3 instance you stood up for INFRA-1
(`localhost:8002`, pointed at the real `ddp-openstates` RDS instance):

```
curl -s "http://localhost:8002/bills/ocd-bill/03418e03-cd16-4614-829f-215e5afa5fec?apikey=00000000-0000-0000-0000-000000000001"
```

## Why

OPEN-190's own acceptance criteria want one jurisdiction's cloud-collected data compared
against a local run "on row counts, document references, and api-v3 responses." The row-count
and document-link comparisons are already done directly against Postgres (identical on both
sides — same bill, same title/actions/versions/sponsors/document URLs). This is the last piece:
comparing what api-v3-the-application returns for the same bill on both instances, which also
directly feeds OPEN-191's own validation checklist ("a representative response per routed
jurisdiction, compared against the old path").

The Mac's own api-v3 (pointed at local production Postgres) returns this for the same bill:

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

Please paste the actual response from your instance in a reply note, plus a note of any
difference (even a cosmetic one, e.g. field ordering) — not just "matches"/"doesn't match".
