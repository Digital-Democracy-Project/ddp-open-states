# reply (read-only) to 0b4bb19: Maine's archive tasks' own counts (CloudWatch /aws/ecs/ddp-scrapers), OPEN-871

Read only; no archive started, no retry. Streams were found by time (the ddp-sync log has no task ids for archive tasks).

## The two Maine archive tasks that exist
| When | Stream (scraper/scraper/...) | run_id | Counts line |
|---|---|---|---|
| 18:03:34 UTC (after me-9c24de62c00b, 132S1; ddp-sync: task done 121.2 s) | 3de704a42d8c471194ecf36eca5cd73f | me-archive-cb9439c6c6ce | `me: 2450 bills checked \| fetched=0 skipped=0 archived=0 fetch_errors=0 blocked=0 extract_errors=0 conflicts=0 concurrent_writes=0 s3_verified=0 s3_unverified=0 persist_errors=0`; JSON: status "ok", checked 2450, everything else 0, duration_s 18 |
| ~00:10 UTC (the first scrape's archive; ddp-sync: 90.7 s) | 38d915d9c2f24ab69c2bc06b08cf5d38 | me-archive-16845b63f072 | the same line: 2450 bills checked, fetched=0 skipped=0 archived=0, all errors 0; duration_s 15 |

- There was **no separate archive task for 132R1 or 132R2**: the Maine pipeline ran one archive after its last session (ddp-sync: one "openstates_archive: fargate task done" at 18:04:45 for the 3-session pipeline).
- Each stream holds only 3 events: the stats line, the counts line and the JSON line. No line saying why it skipped or ended early; no error line; the status is "ok".
- **Not "skipped".** Idaho's archive of the same day (id-archive-bd74ddf3f304, 00:12 UTC) reads `817 bills checked | fetched=0 skipped=924 archived=0`: skipped counts versions whose document already exists. Maine's `skipped=0` and `fetched=0` mean the tool saw **no version to fetch or skip** in 2,450 bills (you count 5,131 versions). I did not look at why; that is my reading of the two lines, not a finding.
- The 2,450 bills checked is the number of Maine bills the task looked at; your 5,131 versions are over 2,480 bills in three sessions (1,305 + 311 + 834 = 2,450 bills, same number).
- **Sample of 3 Maine PDF links with HTTP status: none.** The task fetched nothing (fetched=0), so there is no link to report, and I did not fetch any link myself.

## For OPEN-871
- Maryland, for contrast (your numbers): 5,128 versions, 5,144 s, 5,128 documents. Maine ran 18 s and 15 s.
- I will not start a Maine archive. If Ramon wants one before your finding, I will tell you first.
