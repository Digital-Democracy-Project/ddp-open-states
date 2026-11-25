# REPLY to 2e6f689 (read-only; Ramon's question): Oklahoma timeouts, counts only. **No block signature in any log; every failure is a pure connect timeout on the very first request; not distinguishable from a network-path problem on one side.**

Method: I read the CloudWatch log of every Oklahoma collection task since 11-23 (11 tasks: 3 failed, 8 worked) from the host, read only. **No request was made to the legislature host from here, no retry, nothing changed.** No hostnames, addresses, ARNs or task ids below; the "legislature host" only.

## 1. Where a failing run stalls (3 of 3 the same)
- **Error class, all three:** `requests.exceptions.ConnectTimeout` (the underlying error is `TimeoutError [Errno 110] Connection timed out`, i.e. the TCP connection never completed; not a DNS failure, TLS failure or read timeout). Runs: ok-1d84ac39c6ba (2025), ok-7c12e3178e25 (2026), ok-5af769a2a5ea (2026 retry).
- **It is the very first request, and the only one:** each failing task logged **exactly 1 request** (the session page) and **0 responses**. The HTTP library retried it **3 more times** (retry totals 2, 1, 0), each connect attempt about **131 s** later (131.5, 130.9, 131.1 s measured as the gap after the first request), then gave up at **541 s** in all three (task duration 541, 541, 541 s; the scraper's JSON says 542, 541, 543). Request rate before the stall: none.

## 2. Time of day (UTC)
- Failing: 11-24 22:50, 11-25 07:00, 11-25 18:03. Working: 11-23 18:22 and 20:52; 11-24 17:47, 20:16, 23:01; 11-25 01:30 and 04:30 (plus one 11-22 20:12 run). Failures are not bunched in an hour or a window; working runs started at 17:47, 18:22, 20:16, 20:52 and 23:01, close to the failing hours.
- **A failure and a success 90 seconds apart:** the 11-24 2025 attempt failed at 22:59:36 and the 2026 session of the same request started 23:01:12 and **worked** (7,857 s, 7,638 requests).

## 3. Parallelism (other collection or database tasks, any state, alive at each task's start; from the stream times)
- Failing runs: 4, 1 and 1 other tasks. Working runs: 0, 10, 8, 1, 4, 4, 2, 2. No relation to load. The 2025 and 2026 sessions never ran together (a request runs its sessions one after the other).

## 4. Block signature in any response
- **HTTP 403, 429, 502 or 503 status lines: 0 in all 11 tasks** (strict match on status wording; my first, looser count included bill numbers like "HB 403" and means nothing). **Connection resets or tarpit-style hangs: 0.** Challenge or captcha page, CDN or WAF header names: **0, but the scraper's log carries no response status or headers for successful requests** (only the request line), so a 403 or a header would not be visible in a *working* run; in a *failing* run there is **no response at all**, which is the finding. The working runs' first request answered within **0.1 to 0.3 s** (the next log line follows the request line by that gap).

## 5. Clustering by outbound address
- **Not knowable from the logs:** the tasks do not log their egress address, and the ECS records that carry it have aged out (one hour). So I cannot count distinct addresses or say whether one appears in both groups. Clustering by session: failing = 2025 once, 2026 twice; working = 2025 four times, 2026 three times. By hour: see 2.

## 6. How the working runs differ
- 7,592 to 8,133 requests per session (16,000 for the 11-22 run, both sessions), **0 connection retries**, durations 7,815 to 8,413 s (2025: 8,102 to 8,133 requests; 2026: 7,592 to 7,638). A run that gets its first answer simply goes on; the request rate is about 1 per second. 4 warning lines per failing task against 22 to 27 per working task (one with 168); I did not read what the working runs' warnings are.

## 7. Verdict
- **Not distinguishable from the logs, with a lean:** a silently dropped connection (no answer to the connection attempt, repeated for about 9 minutes) is **consistent with a network-path or availability problem on one side, or with a source-address filter that drops packets without a reply**. It is **not** the usual signature of throttling or bot detection by a server (a 429, a 403, a challenge page, or a reset after connecting), and **none of those appears**. Failures are 3 of 11 tasks and are independent of the hour and of parallel load; a failure and a success 90 seconds apart suggests the cause is per-attempt (per address or per path), not a standing block on us.
- **What would settle it (cheap, read-only for the host):** (a) make each scraper task **print its egress address at start** (counts per run, never published), so failing and working runs can be compared for repeated addresses; (b) **time the first connect** in the log (it is already timed implicitly: 0.1-0.3 s versus never); (c) if tasks leave through a shared NAT address, ask the network owner whether the legislature side drops that address at times. **I changed nothing and will not work around anything**, as Ramon said.
