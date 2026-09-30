# Report: api-v3 search, section 7 checks through ddp-api, and the NC people gap confirmed on RDS (2026-09-30)

From the prod agent on the EC2 host. Follows `report-api-v3-search-deploy-on-rds-instance-20260930.md` (same branch, `585a698`) and replies to the
Mac session's `45ee7e4` / `a0b3f21` (NC people gap, OPEN-312). Times are UTC. Everything here was read-only except one deliberate rejection test, noted below.

## Decision recorded: `suggest` latency is over the bar and the user has accepted it

The user (not Ramon) told me on 2026-09-30 to accept the slowness and move on to section 8. **The checklist's stop condition ("if over the bar: stop and
revisit plan 4.5.2") is therefore overridden, not satisfied.** I have not revisited plan 4.5.2, and Ramon has not confirmed. If he wants it revisited, say so here.

## Section 7 results

**Latency, `GET /openstates/ddp/search/suggest`, all 65 judged-set queries, two passes, from this host over the public endpoint, bar is p95 at or under 150 ms: FAIL**

| Route | Pass | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| through ddp-api | 1 (cold-ish) | 214 ms | 764 ms | 1,052 ms | 1,866 ms |
| through ddp-api | 2 (warm) | 193 ms | **348 ms** | 981 ms | 1,061 ms |
| direct to api-v3 (`localhost:8002`, earlier today) | 1 | 84 ms | 345 ms | 849 ms | 1,022 ms |
| direct to api-v3 | 2 (warm) | 75 ms | **197 ms** | 853 ms | 885 ms |

- Zero errors. The ddp-api hop adds about 120 ms at the median. Slowest warm queries: `S 1` (1,061 ms through ddp-api, 853 ms direct) and `school lun` (981 / 885 ms),
  the known slow shapes.
- **Caveats:** the judged set has no jurisdiction field, so every query used all 8 jurisdictions (worst case). One sequential client. The local reference numbers
  (suggest p95 about 83 ms) were measured against a local database; these include the network to RDS. An earlier 60-request mix of my own gave p95 602 ms direct
  (single-jurisdiction median 99 ms, 8-jurisdiction median 234 ms).

**Authorization through ddp-api (read token, `DDP_OPENSTATES_BEARER_TOKEN` from the broker `.env`, never printed): PASS**

- `POST /openstates/ddp/search/refresh?jurisdiction=UT&limit=1`, no token: **401** `Not authenticated`.
- Same `POST` with the read token: **403** `Write access required`. api-v3's own log shows **no** `POST /ddp/search/refresh` reached it.
  (I used `limit=1` so an unexpected acceptance would have been one small no-op refresh.)
- `GET` search with the read token: 200. With a bad token: **403** `Invalid Bearer token` (the checklist expected 401; it is rejected either way). `limit=101`: 422.
- Network reachability of api-v3 itself: none of this instance's five security groups opens port 8002 (only 80, 443, 4443, 8080; SSH restricted to six addresses). In the last 24 hours
  the only callers were `GET`s from localhost, the Docker gateway and the Mac over WireGuard (`10.0.0.1`); no `POST /ddp/search/refresh` has ever appeared in the retained logs.
  Not checked: host firewall, NACLs, other WireGuard peers. api-v3 keys have no scopes, so any peer with a valid key could call its refresh directly.

**Serving instance (recorded by inference):** `coverage` through ddp-api returns exactly what the RDS-backed instance returns (FL: 7,685 bills, 7,685 projected, 539 people). `ddp_bill_search`
exists only on that instance, so ddp-api is reaching it. I did not read ddp-api's `OPENSTATES_SERVICE_URL`. Broker `DDP_OPENSTATES_API_ROOT` and ddp-sync `RDS_OPENSTATES_API_BASE` (on this host) both name
`http://10.0.0.11:8002`, the same instance. The Mac's ddp-sync `local_openstates_api_base` points at the Mac's own api-v3 and is unrelated to this host's path; which base the future SYNC-87 hook will use
is still undecided, and the Mac's instance has no `ddp_bill_search` table.

**Not done:** the importer freshness test (needs a non-production database).

## NC people: confirmed on RDS with the Mac session's own query

`SELECT count(*) FROM opencivicdata_person WHERE current_jurisdiction_id = 'ocd-jurisdiction/country:us/state:nc/government'` returns **0 on RDS**, matching the Mac replica. RDS has 4,088 people in total, the same
as the replica; state jurisdictions present: FL 539, MI 450, MA 415, VA 356, WA 347, AZ 341, AL 286, UT 271 (plus a few municipal ones). NC is absent. My earlier membership-based query also found 0 NC memberships,
and all 2,338 NC bills have sponsorships (26,099). So the gap is that the Mac's 508 NC people were never loaded to RDS, and the replica simply mirrors RDS. Loading them into RDS is what would fix NC name search;
I have not done it and it is not part of this deploy.

## Next step

1. Ramon: confirm or reverse the latency decision, and decide on loading the NC people into RDS (OPEN-312).
2. Section 8 follows on the user's instruction: a `start-os-api.sh` PR (not merged until the Mac `api` image is rebuilt and its import check passes), no SYNC-87 (not built), and OPEN-310 / api-v3 PR #14, which are Ramon's.
3. Reply on this same branch either way.
