# Reply: OPEN-475, Massachusetts 11-01 run against the 10-25 run (read-only), 2026-11-01 ~22:20 UTC

Read from CloudWatch `/aws/ecs/ddp-scrapers`: 11-01 stream `a400a49e2c1646e79264fa2047d3c1a6` (31,813 events) and 10-25 stream `737b2599f0fd4f56b777d910ab5e5862` (36,821 events). Nothing launched, stopped or changed; lines redacted. Hours below are UTC. "Not readable" means the log does not hold it.

## 1. How each run started (first 15 lines; identical shape)
Both: `ma (scrape)`, **`bills: {'start': ...}`** (11-01: `2026-10-25T11:14:44`; 10-25: `2026-10-18T09:01:07`), then the line **`MA OPEN-128: ignoring start= and listing every bill`** and `no session provided, using active sessions: {'194th'}`. So **both runs walked the whole 194th session**; the start date was ignored on both.

## 2 to 4. The numbers, 11-01 beside 10-25
| | 11-01 (stopped at 14:00:54) | 10-25 (finished 12:21:55) |
|---|---|---|
| Span of the log | 12.00 h (43,215 s) | 10.35 h (37,275 s) |
| Requests to malegislature.gov (scrapelib lines) | 10,554 | 12,226 |
| of which bill pages (`/Bills/194/...`) / other | 10,427 / 127 | 11,989 / 237 |
| Distinct bill pages requested | **10,425** | **11,987** |
| Repeated requests (same bill id twice) | 2 | 2 |
| `save bill` lines (distinct) | 9,559 (9,558 by 14:00:54) | 11,747 |
| **Elapsed per bill-page request** | **4.14 s** | **3.11 s** |
| Same, leaving out the wait right before each Server Error | 4.02 s | 2.91 s |
| Median gap between log lines, by hour | 0.47 to 1.72 s | 0.42 to 0.63 s |
| Gaps over 60 s / over 30 s | 13 / 20 | 43 / 48 |

- **Bill pages per hour (bill-detail / other).** 11-01: 02h 1,027/1; 03h 875/1; 04h 718/1; 05h 877/0; 06h 861/0; 07h 1,074/25; 08h 874/12; 09h 683/23; 10h 779/1; 11h 801/1; 12h 813/1; 13h 1,026/61; 14h 19/0. 10-25: 02h 1,209/1; 03h 1,234/2; 04h 1,019/0; 05h 1,401/7; 06h 960/31; 07h 1,555/25; 08h 1,150/1; 09h 1,076/2; 10h 936/63; 11h 1,177/102; 12h 272/3. **11-01 made 718 to 1,074 requests an hour; 10-25 made 936 to 1,555** (about 25% fewer on average: 880 an hour against 1,181).
- **Median gap per hour (s).** 11-01: 02h 0.62; 03h 0.76; 04h 1.16; 05h 0.82; 06h 0.00; 07h 0.47; 08h 1.34; 09h 1.71; 10h 1.72; 11h 0.66; 12h 1.00; 13h 0.59; 14h 0.64. 10-25: 0.42 to 0.63 in every hour (02h 0.44; 03h 0.46; 04h 0.48; 05h 0.44; 06h 0.52; 07h 0.42; 08h 0.42; 09h 0.54; 10h 0.55; 11h 0.52; 12h 0.63). **11-01 was slower per request in 04h and from 08h to 10h** (gaps two to three times the 10-25 ones) and about the same in 02h, 03h, 07h and 11h to 14h (0.6 to 0.8 s).
- **Progress at the stop:** 10,425 distinct bill pages requested = **87.0%** of 10-25's 11,987; 1,562 left.
- **The 20 largest gaps, 11-01** (seconds; each is a stall before a `Server Error` warning unless noted): 135.4 (11:13:45), 134.9 (03:06:20), 134.5 (08:49:02), 134.5 (08:22:14), 133.6 (11:29:23), 133.1 (11:57:54), 133.0 (03:23:46), 130.7 (11:32:25), 68.3 (05:24:11, a bill save), 60.1 (13:01:27), 60.1 (13:00:27), 60.1 (12:59:27), 60.0 (07:56:59), 57.7, 54.5, 42.1, 33.6, 32.8, 32.8, 30.8. **10-25:** 431.0 (12:14:44, the end of the run: the final status line after the loading summary), **426.1 (08:26:16 to a `save bill`, no warning)**, **337.8 (02:05:18 to a `save bill`, no warning)**, then 17 gaps of 60.1 s (04h, 06h, 10h; each before a `Server Error`). **Any single request that stalled over 60 s:** 11-01: 8 stalls of 130 to 135 s, 5 of 60 s and 2 more at 54 to 68 s; 10-25: 43 of about 60 s and the two bill-save stalls of 426 s and 338 s.

## 5. Block or throttle signs, both streams
- **No `429`, `403`, `Too Many`, `Barracuda` or `timed out` line in either stream.** The only warning type in volume is **`Server Error on https://malegislature.gov/Bills/194/<id>`** (the retry wait that precedes it is 60 s or about 130 s). 11-01: **873 Server Error warnings** (873 distinct bill pages: H 446, HD 396, SD 18, S 5, and 3 `BillHistory`), by hour 02h 43, 03h 33, 04h 26, 05h 33, **06h 448, 07h 253**, 08h 4, 09h 6, 10h 6, 11h 8, 12h 7, 13h 6. 10-25: **252** (240 distinct pages: HD 195, SD 25, H 17, 12 `RollCall/.../SenateRollCall`, S 3), by hour 02h 50, 03h 46, 04h 40, 05h 59, 06h 17, 07h 10, 08h 10, 09h 6, 10h 13, 11h 1.
- Other warnings: `MA House roll call unreadable ... supplement` 27 on 11-01 and 40 on 10-25 (27 + 13), and `no session provided`. No other `ERROR`, `retry` or empty-response lines.

## What the numbers say (observed facts first, then my reading)
- **Observed:** the 11-01 run made **fewer** requests an hour and took **4.14 s per bill page against 3.11 s** (33% longer); it had **more Server Errors** (873 against 252) but the **waiting time right before them was smaller** (1,311 s, 3.0% of the run, against 2,404 s, 6.5%). Leaving that wait out, 11-01 still took 4.02 s a request against 2.91 s (38% longer). So the extra time is **not** the Server Error retries and **not** a few long stalls (10-25 had more of those, and two unexplained 6 to 7 minute stalls); it is a slower pace for ordinary requests, most clearly in 04h and 08h to 10h.
- **Observed:** a burst of 448 + 253 Server Errors in 06h and 07h on 11-01 (mostly H and HD pages) had little effect on the clock: the gaps before most of them are under one second.
- **My reading (not proven):** the log shows only the time between lines, not each request's own time, so I cannot say whether the slowness is Massachusetts' site responding more slowly, the Fargate task, or the network; there is no sign of throttling or blocking. The cause I would write on OPEN-475 is "malegislature.gov answered about a third slower on 11-01, with no throttle signs".
- **Projection (an estimate):** the 11-01 run had asked for 87.0% of 10-25's bill pages when it was stopped; at its own pace (4.15 s a page) the 1,562 remaining pages would need about 1.8 more hours, so **a finish at about 13.8 hours, 1.8 hours over the 12-hour wait limit.** The 10-25 run was 10.35 hours, so a run 16% slower than 10-25 misses the limit, as you calculated.
- Both runs ignore `start=` (OPEN-128), so each is a full walk of 11,987 bill pages; a faster cure would be fewer pages, but that is Ramon's call.

## Item 6, the task definition revision
**Not readable**: my role cannot read ECS. The task id is `a400a49e2c1646e79264fa2047d3c1a6`.

The analysis files are kept in `/home/bitnami/ops/open475-ma-20261101/` (raw redacted events as `.jsonl`, `analysis.txt`). Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
