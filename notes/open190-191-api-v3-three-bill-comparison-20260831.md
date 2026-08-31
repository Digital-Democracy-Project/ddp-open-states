# OPEN-190/191: api-v3 response comparison, now three bills (consolidated)

*Written 2026-08-31. Supersedes/extends the single-bill ask in
`notes/open190-api-v3-response-comparison-20260831.md` — no reply on that one yet, and two more
bills' local-side data has been gathered since, so this covers all three in one round trip
rather than three separate ones.*

## What I need

Three `curl`s from this host, against the api-v3 instance from INFRA-1 (`localhost:8002`,
pointed at the real `ddp-openstates` RDS instance):

```
curl -s "http://localhost:8002/bills/ocd-bill/03418e03-cd16-4614-829f-215e5afa5fec?apikey=00000000-0000-0000-0000-000000000001"
curl -s "http://localhost:8002/bills/ocd-bill/ae6f0d7a-6a70-430e-a85b-557412caaedf?apikey=00000000-0000-0000-0000-000000000001&include=versions"
curl -s "http://localhost:8002/bills/ocd-bill/271de7b7-47b6-4992-bb36-40c54862e135?apikey=00000000-0000-0000-0000-000000000001"
```

(FL HB 1325, VA SB 192 — with `include=versions` since this one's specifically checking
OPEN-90/92's stage-aware version ordering — and WA SB 6099.)

## Why

Both OPEN-190 and OPEN-191 have PRs open (`ddp-open-states` #207, #208) with real database-level
comparisons already done for these three bills — row counts, action/version counts, and
document links are identical between local production Postgres and RDS on all three. The one
piece still missing from both PRs is the api-v3 *application*-layer comparison specifically:
does api-v3 pointed at RDS return the same thing as the Mac's own existing instance for the same
bill. Please paste the three responses in a reply note (plus whether any of them differ from
what's already in those two PRs, not just "matches"), and I'll fold the result into both.

No urgency beyond that — nothing is blocked waiting on this except closing out those two
specific checklist lines; everything else in both tickets already has real evidence.
