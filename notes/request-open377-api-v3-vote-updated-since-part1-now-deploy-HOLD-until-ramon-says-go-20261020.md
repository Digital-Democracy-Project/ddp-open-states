# REQUEST: OPEN-377, put api-v3 `a2f5db8` (`GET /bills?vote_updated_since=`) on the EC2-broker host. **Part 1 (read-only) now; Part 2 (the deploy) HOLD until Ramon says GO.** (Mac side, 2026-10-20 EDT)

**STATUS:** Ramon asked (Mac session, 2026-10-20) for this request. **Do only Part 1 now.** It is read-only: nothing is pulled, built, recreated or restarted. Part 2 starts only when a note from Ramon on this branch says GO for it. A failed gate is not permission to improvise: stop and report. A HOLD note from Ramon overrides this one.

Jira: **OPEN-377** (the parameter), **BROKER-241** (the vote alerts that need it, blocked on this). Code: api-v3 fork `main` **`a2f5db8`** (PR #32, merged 2026-10-16). The Mac's api-v3 is being refreshed by Ramon separately (`refresh-api-v3.sh`); this note is only the EC2 instance.

## 0. What this is, and why it matters

`GET /bills` gets a new filter, `vote_updated_since`: only bills with at least one vote event whose own `updated_at` is at or after the datetime. The alert engine (`bill.vote_occurred`) needs it because vote events are imported separately and do not move `Bill.updated_at`: on the 2026-10-16 replica 117 bills had a vote change in 30 days and `updated_since` alone found 97 (20 missed, 17%). It is an additive `in_(subquery)` copying `document_updated_since`'s shape: existing parameters, responses and pagination are untouched. **Until this is deployed the parameter is silently ignored** (an unknown query parameter is not an error): on the Mac today `vote_updated_since=2099-01-01` returns all 1,021 Utah bills, where `document_updated_since=2099-01-01` correctly returns 0. So a caller would get every bill back and no error.

The broker reaches api-v3 either through the ddp-api proxy (`openstates_proxy.py`, which forwards every query parameter except `apikey`) or directly over WireGuard; which instance sits behind it is `OPENSTATES_SERVICE_URL` on the ddp-api host. So **both** instances need the parameter.

**Timestamp rules (for BROKER-241, repeated here because they bite):** send an explicit offset, `2026-03-01T00:00:00+00:00` with the `+` percent-encoded as `%2B`; no offset is read as UTC; **a trailing `Z` is rejected with a 400**, the same as `updated_since` and `document_updated_since` today. I did not change the parser.

## 1. Part 1: read-only (do now)

1. **G1 (starting state).** In `/opt/ddp-open-states/api-v3`: branch, `git rev-parse --short HEAD` (expect `ba0b6468`, your OPEN-381 Part 2), `git status --short`. Uncommitted changes, another branch or commit: **stop and report**; do not stash or reset. Then `git fetch` and list `git log --first-parent HEAD..origin/main`: it must be **exactly PR #32** (merge `a2f5db8`; commits `92dd0e7`, `d4a1a6c`). If anything else is in the range, report it and stop.
2. **G2 (quiet, rollback point).** Record the running image id (the one to roll back to) and that api-v3 has been quiet for 5 minutes (the OPEN-361 check: only `/healthz`). Say when the next ddp-sync job that reads api-v3 starts, so Part 2 can avoid it (the container recreate takes ~17 s, as on 2026-10-14).
3. **G3 (baseline behaviour, before).** From inside the ddp-sync container with its `X-API-Key` (as in your OPEN-361 checks), report `pagination.total_items` for:
   * `GET /bills?jurisdiction=Utah&per_page=1` (all Utah bills),
   * `GET /bills?jurisdiction=Utah&per_page=1&vote_updated_since=2099-01-01T00:00:00%2B00:00` (expected today: **the same number**, i.e. the parameter is ignored),
   * `GET /bills?jurisdiction=Utah&per_page=1&document_updated_since=2099-01-01T00:00:00%2B00:00` (expected **0**: the working control),
   * `GET /bills?jurisdiction=Utah&per_page=1&vote_updated_since=2026-10-01T00:00:00Z` (expected today: 200, ignored; after the deploy it must be **400**).
4. **G4 (RDS, read-only): the number the API must match after the deploy.** For a fixed cutoff, how many distinct bills have a vote updated since it:
```sql
SELECT j.name, count(DISTINCT v.bill_id) AS bills_with_vote_updated_since, count(*) AS votes, max(v.updated_at)::date AS newest_vote_update
FROM opencivicdata_voteevent v
JOIN opencivicdata_legislativesession s ON s.id = v.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id = s.jurisdiction_id
WHERE j.name IN ('Utah', 'Virginia') AND v.bill_id IS NOT NULL AND v.updated_at >= '2026-06-01T00:00:00+00:00'
GROUP BY j.name;
```
   (On the Mac's replica this reads Utah **739**, Virginia **2,201**; production should be higher or equal, since the replica's newest vote update is old.) Also run it for a recent cutoff, 7 days back, so the post-deploy comparison also covers fresh data.
5. **G5 (which instance the broker uses).** If you can see it from this host, report what `OPENSTATES_SERVICE_URL` is on the ddp-api host (Mac `10.0.0.8:8002`, or this instance), and whether the broker's `DDP_OPENSTATES_API_ROOT` points at the ddp-api proxy or directly at an api-v3. Do not change anything. If you cannot see it, say so.
6. **Report Part 1** in a `reply-open377-api-v3-preflight-...` note. Then wait for GO.

## 2. Part 2: the deploy (needs GO for Part 2)

The OPEN-361 method, unchanged: tag the running image `ddp-openstates-api:pre-open377` (the rollback); `git pull --ff-only` in `/opt/ddp-open-states/api-v3` to `a2f5db8`; rebuild with `docker compose -p ddp-openstates-rds -f docker-compose.rds.yml build api` and recreate **only** `api` (`up -d --no-deps api`) from `/opt/ddp-open-states/deploy`. Do not touch any other container or the database. Then:
* `/healthz` 200, restarts 0, ddp-sync healthy, **0** `apikey=` lines in api-v3's log.
* The G3 queries again: the 2099 `vote_updated_since` query returns **0**; the `Z` query returns **400**; the `document_updated_since` control and the unfiltered total are **unchanged** from G3.
* **The equality check:** for the G4 cutoffs, `total_items` from `GET /bills?jurisdiction=<J>&per_page=1&vote_updated_since=<cutoff>%2B00:00` **equals** G4's `bills_with_vote_updated_since` for Utah and Virginia, both cutoffs.
* One existing bill read unchanged: `GET /bills/ocd-bill/<an id you used for OPEN-361>?include=versions` returns the same `versions[].note` order as in your OPEN-361 reply.
Stop conditions: any gate or number that does not match, a restart count above 0, a 5xx. Stop, report; the rollback is `docker tag ddp-openstates-api:pre-open377 ddp-openstates-api:local`, `up -d --no-deps api`, and `git checkout ba0b6468` in the checkout.

## 3. Not authorized

Anything in Part 2 before a GO note; any other container, the database, ddp-sync, ddp-api or the broker; any flag, schedule, scrape, archive, embedding or LegBot run; changing `OPENSTATES_SERVICE_URL` or any environment setting; rolling back without authorization. The broker work (BROKER-241) is not part of this.

## 4. Reply

`reply-open377-api-v3-preflight-...` for Part 1, then (after a GO) `reply-open377-api-v3-deployed-...` with the commit before and after, the times, the image tag, every number above and anything unexpected.
