# Request: reload api-v3 on the EC2 host from the reverted `main` (OPEN-398: #36 and #37 are reverted)

2026-10-28 (about 01:55 UTC). **This is the go for the writes below**, given by Ramon in this session. It **replaces and cancels** both earlier api-v3 OPEN-398 notes (the deploy request `0dbe72a` and the hold `c98a537`) and the index pre-build idea in the ticket: nothing from them is still to do. **Stop and report if anything does not look as described; do not retry a failed step; do not print any key.**

## What happened (short)
api-v3 #36 (rank only the 5,000 most recent full-text matches) is what you deployed at 00:46 UTC. On production it gave no speedup for act, state or public (your numbers) and changed their top results. A follow-up #37 added an index; on the Mac it made some words much faster and others (health, education) 37 to 52% slower, so it was dropped and never built on production. Ramon decided to **revert both**. Revert PR: api-v3 #38, merged as **`f9dde9192784f6ac78d599161e8d9d318968caa5`**; the tree is identical to `d5b37dc` (the commit you deployed at 00:13, which includes the enrollment endpoint, #33). The Mac has already been reloaded from it (healthy, the pool limit and the index code are gone).

## Please do, in this order
1. **Before changing anything, report:** the api-v3 checkout's HEAD (`/opt/ddp-open-states/api-v3`, expected `03fbb3443a76dfe211c0c6b7c2d0eedee3a636f5`), the api container's start time, and that `ddp_bill_search_recency_idx` does **not** exist in the production database (`SELECT count(*) FROM pg_indexes WHERE indexname='ddp_bill_search_recency_idx'` should be 0; it was never built there). If it exists, stop and tell me.
2. **Pull the api-v3 checkout to `f9dde9192784f6ac78d599161e8d9d318968caa5`** (fast-forward only; clean tree; stop and report otherwise). Report HEAD.
3. **Pick a quiet window** (no non-health api-v3 request in the last few minutes, nothing in flight in ddp-sync, no launch due within 10 minutes; WA is 02:30 UTC, USA 03:00) and run the same command as before: `docker compose -p ddp-openstates-rds -f /opt/ddp-open-states/deploy/docker-compose.rds.yml up -d --build --no-deps api`. Confirm the Redis container's start time is unchanged and the new container is healthy.
4. **Verify:** `docker exec <api> grep -c FTS_RANK_POOL /app/api/ddp_search.py` prints **0** and `grep -c recency /app/api/search_projection.py` prints **0**; `GET /ddp/enrollment` still answers 200 with the same `manifest_mtime` (the manifest mount must still be there); the other callers you checked last time still answer 200; no error in the new container's log.
5. **Measure** the same six words as at 00:46 (act, state, school, health, public, hemp; all nine jurisdictions; 5 runs, median of `elapsed_ms`) and report them next to your earlier before (pre-#36) numbers. Expect them back near your first set (act about 1023 ms, health about 510). Compare the first 20 ids against your saved `open398-ids-before` file and report how many match per word (expect all 20).

## Report
Commands (secrets removed), HEADs, container times, the timing table, and anything that did not match. Nothing else changes.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
