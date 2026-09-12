# Urgent, time-boxed: switch production ddp-broker over to the EC2 api-v3 before tonight's nightly run

Ramon asked me to relay this directly to you. Time-sensitive: **~9 hours until tonight's
nightly production run** (Ramon's estimate, as of ~14:30 ET 2026-09-12) -- that run is when
`ddp-broker`'s representative/person-roster sync (`get_people`, via
`update_representatives_for_jurisdiction`) actually gets exercised for real, so this needs
to land before then.

## What's happening on the dev side (OPEN-272)

The dev session is repointing the Mac Studio's own local `api-v3` (`ddp-openstates-api-1`)
at a new local database rebuilt from an RDS schema-only dump -- but that new database only
carries the 7 tables `PLAN-rds-local-postgres-replication.md`'s publication scopes (bill/
version/jurisdiction data for LegBot), not the ~38 other tables real api-v3 endpoints need
(`profiles_profile` for auth -- already fixed via a one-time local copy -- plus all of
`opencivicdata_person`/`membership`/`vote`/`event`/etc., which it does NOT have and never
will under this plan's current scope).

**Confirmed via real code inspection**: production `ddp-broker` (this EC2 host, `10.0.0.11`)
is currently configured to reach OpenStates data for **all 8 DDP jurisdictions**
(`DDP_OPENSTATES_JURISDICTIONS=US,FL,MI,AZ,VA,WA,UT,NC`) via
`DDP_OPENSTATES_API_ROOT=http://host.docker.internal:8002` -- i.e. straight at the **Mac
Studio's** `api-v3`, not at anything on this EC2 host. Once the Mac's `api-v3` is repointed
at the new 7-table database (imminent, later today), `ddp-broker`'s
`update_representatives_for_jurisdiction` (`openstates_service.py`, calls
`client.get_people(...)`) will start failing for all 8 jurisdictions the moment it's next
exercised, since `/people` needs tables the Mac's new database doesn't have.

## What needs to happen here

Per **INFRA-1** (already proven live, your own comment from 2026-08-30): a real,
self-contained `api-v3` instance is already up and healthy on this exact host, pointed
directly at the real `ddp-openstates` RDS instance (the *full* schema, not a 7-table
subset) -- security-group ingress already added for this host to reach RDS on 5432.

Please:
1. Confirm the real, currently-deployed production `ddp-broker` config on this host (not
   just the dev checkout's `.env` I can see from the Mac side, which may not reflect what's
   actually live here) -- specifically `DDP_OPENSTATES_API_ROOT` and
   `DDP_OPENSTATES_JURISDICTIONS`.
2. Switch `DDP_OPENSTATES_API_ROOT` to point at the api-v3 instance already running on this
   host (per INFRA-1) instead of the Mac's `http://host.docker.internal:8002`.
3. Restart/redeploy `ddp-broker` so the change takes effect.
4. Verify for real: a `get_people`/representative-roster call for at least one of the 8
   configured jurisdictions succeeds against this host's own api-v3 (not the Mac's).
5. Comment back here (or update INFRA-1/OPEN-272) with what you found and confirmed --
   especially if the real production config turns out to already differ from what the dev
   checkout's `.env` shows, since that would change what "switch it over" actually means in
   practice.

If anything about this host's real config, IAM scope, or reachability blocks you, report
back rather than improvising a workaround -- same standing discipline as everything else on
this handoff branch.

## Why the Mac's api-v3 can't just carry both roles

Two options were on the table for the Mac-side gap (run api-v3 as two instances locally, or
broaden what's replicated to the Mac) -- Ramon's call was neither: production `ddp-broker`
should simply stop depending on the Mac's `api-v3` at all and use the real, RDS-connected,
already-proven EC2 instance instead. This also happens to be more correct long-term per
INFRA-1/PLAN-production-website-rollout.md's own direction (api-v3 belongs on EC2 next to
`ddp-broker`, not on the Mac) -- this just makes it load-bearing sooner than that plan's own
timeline otherwise would have.
