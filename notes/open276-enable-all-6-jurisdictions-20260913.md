# OPEN-276/OPEN-265: Ramon's decision -- enable all 6 jurisdictions now, skip single-pilot staging

Ramon's direct decision (2026-09-13, recorded on OPEN-276): skip the single-pilot rollout
and enable all 6 already-clean jurisdictions on LegBot's RDS-replica allowlist at once,
rather than picking one and widening later. Reasoning: api-v3 already has working
stage-aware version-ordering logic (OPEN-90/92) that handles same-date version
disambiguation downstream, so the one known gap in this mechanism's own SQL (~24,283
bills with tied version dates, no tie-breaker) doesn't carry the risk it would if
nothing downstream handled ordering at all. All 6 candidate jurisdictions are
independently confirmed data-quality-clean already (not staggered), so there's no one
being "waited on" by going all-in.

**Requesting the following production config change on ddp-sync (EC2), both env vars
mentioned in OPEN-275/OPEN-276's own PRs (ddp-sync #136, #138):**

- `REPLICA_FRESHNESS_CHECK_ENABLED=true` (currently off by default)
- `LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST=mi,ut,fl,va,wa,us` (currently empty)

After setting these and restarting ddp-sync, please verify for real (not just that the
env vars are set) -- e.g. trigger or observe a real LegBot dispatch for one of the 6
jurisdictions and confirm the freshness check actually runs and passes against real
data, the way you verified the archive-completion hook end-to-end for SYNC-65 earlier
today. Once confirmed, this should close out OPEN-275, OPEN-276, and OPEN-277 (widening
is now moot -- all 6 go in at once), which in turn closes epic OPEN-269 and OPEN-265
itself.
