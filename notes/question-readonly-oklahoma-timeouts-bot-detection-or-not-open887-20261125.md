# QUESTION (read-only, not a GO): **do the Oklahoma timeouts look like bot detection on the legislature's side? Compare the failing runs with the runs that worked, in counts and plain words.** For Ramon, via the PM. 2026-11-25 ~21:35 UTC (Mac side, Onboard New States)

**This note is on a PUBLIC branch.** Say "the legislature host"; **no host names, addresses, ARNs, task ids or group ids in the note or its reply, counts only.** Run ids (`ok-…`) are fine.

## What Ramon wants to know
Whether the Oklahoma collection timeouts (OPEN-887) **look like aggressive bot detection or throttling by the legislature's side**, or something else (a slow window, a network path problem, our own request pattern).

## The runs to compare (all Fargate collection tasks, one scraper, one source)
* **Failed with the connect timeout about 9 minutes in:** `ok-1d84ac39c6ba` (2025, 11-24 22:49 UTC), `ok-7c12e3178e25` (2026, 11-25 06:59), `ok-5af769a2a5ea` (2026 retry, 11-25 18:03).
* **Worked:** `ok-1dc8b007733e` (the 2025 retry, started 11-25 01:29, took about 8,900 s), the 11-24 2026 run `ok-3f164c3f15c1` (collected, then loaded 11-25 01:19 UTC), and the earlier Oklahoma runs on 11-23 (2025 and 2026).

## What to report, in plain words and counts
1. **Where exactly does a failing run stall?** The error class we saw is a **connect timeout** (in the HTTP library that means the TCP connection did not complete; a DNS failure, a TLS handshake failure and a read timeout show up as different errors). Please confirm the error class for each failing run, and whether the stall is **the very first request** or a later one (count the requests made before the stall, and the request rate, from the task's own log lines).
2. **Time of day** of each run and of its failure (UTC), for failing and working runs.
3. **Parallelism:** how many Oklahoma tasks (and how many tasks of any state) were running at the same time as each failing and each working run; were the 2025 and 2026 sessions ever collecting at once?
4. **Any block signature in any response, ever** (counts): 403, 429, 503, a challenge or captcha page, a connection reset, a tarpit-style hang (connected but no bytes), or provider headers that name a CDN or a web application firewall. If no response is ever received (pure connect timeout), say so: that itself is the finding.
5. **Clustering (counts only):** do failures cluster by the task's **outbound address** (how many distinct addresses among failing runs versus working runs, and whether any address appears in both), by hour, or by session? Do **not** write the addresses.
6. **How do the working runs differ?** Request pattern, volume, duration, the number of the scraper's own retries used before success, anything else you can see.
7. **Your verdict, plainly:** consistent with bot detection or throttling, consistent with a network path or availability problem on one side, or not distinguishable from the logs. Say what would settle it.

## Rules
* **Read-only.** No new attempt, no retry, no test request to the host from anywhere.
* **Do NOT change our user agent, rotate outbound addresses, slow down or speed up the scraper, or work around anything.** Ramon's earlier rule stands: no workaround of a possible block.
* No secrets, no connection strings; counts, not addresses.

Ticket: OPEN-887. The answer's verdict goes on the ticket (by whoever owns Oklahoma now).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
