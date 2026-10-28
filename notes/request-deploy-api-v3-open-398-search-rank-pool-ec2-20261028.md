# Request: deploy api-v3 `03fbb34` (OPEN-398, faster full-text search) on the EC2 host, with a before-and-after timing

2026-10-28 (about 00:45 UTC). **This is the go for the writes below**, given by Ramon in this session. Same procedure as the OPEN-329 deploy you did at 00:13 UTC. **Stop and report if anything does not look as described; do not retry a failed step; do not print any key.** Separate from the ddp-sync pull and restart (that request and its amendment stand on their own).

## What this is
api-v3 PR #36 (merged as `03fbb3443`): the full-text leg of `GET /ddp/search` now ranks only the 5,000 most recent matching bills instead of every match. For a word in more than 5,000 bills, the top results come from those 5,000 (an older better match cannot reach the list). Queries with 5,000 or fewer matches are unchanged. Rollback: `git checkout d5b37dc` in the api-v3 checkout, rebuild and recreate `api` the same way.

## Please do, in this order
1. **Before changing anything, measure** (read-only; the API key read from its variable in-process, never printed): `GET /ddp/search?q=<word>&jurisdiction=US&jurisdiction=FL&jurisdiction=VA&jurisdiction=MI&jurisdiction=WA&jurisdiction=UT&jurisdiction=AZ&jurisdiction=MA&jurisdiction=NC` for the words `act`, `state`, `school`, `health`, `public`, `hemp`, 5 runs each, and report for each word the **median `elapsed_ms`** and the number of results. Save the first 20 result ids per word to a file in your ops folder so they can be compared after.
2. **Pull the api-v3 checkout** `/opt/ddp-open-states/api-v3` to `03fbb3443a76dfe211c0c6b7c2d0eedee3a636f5` (fast-forward only; clean tree; stop and report otherwise). Report HEAD. (You do not need to pull ddp-open-states again for this.)
3. **Pick a quiet window** (no non-health api-v3 request in the last few minutes, nothing in flight in ddp-sync, no launch due within 10 minutes; WA is 02:30 UTC and USA 03:00) and run the same command as at 00:13: `docker compose -p ddp-openstates-rds -f /opt/ddp-open-states/deploy/docker-compose.rds.yml up -d --build --no-deps api`. Confirm the Redis container's start time is unchanged and the new container is healthy.
4. **Verify:** `docker exec <api> grep -c FTS_RANK_POOL /app/api/ddp_search.py` prints 5 (the Mac's count); `GET /ddp/enrollment` still answers 200 and `manifest_mtime` is unchanged; the other callers you checked last time still answer 200.
5. **Measure again** with the same six words and jurisdictions, 5 runs each: report the median `elapsed_ms`, and for each word how many of the first 20 ids match the saved list.

## What I saw on the Mac (so you know what to expect; dev copy, warm, median of 5)
| word | before | after | first-20 ids same as before |
|---|---|---|---|
| act | 620 ms | 495 ms | 1 |
| state | 643 | 515 | 1 |
| school | 283 | 145 | 10 |
| health | 495 | 217 | 9 |
| public | 441 | 396 | 5 |
| hemp | 34 | 36 | 20 |
The gain is smaller than the author's dev numbers (act 280, public 112) for the all-state query, and the results for the very common words change a lot. Both are what I am asking you to measure on production.

## Report
Commands (secrets removed), the two timing tables, the HEADs, container times, and anything that did not match. Nothing else changes.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
