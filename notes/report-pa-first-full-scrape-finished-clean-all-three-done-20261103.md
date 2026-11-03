# Report (Stage 2, `e8a1e5c`): the PENNSYLVANIA first scrape FINISHED CLEAN; all three pilot scrapes are done, 2026-11-03 05:35 UTC

Run **`pa-0c05e786c832`**, ECS task **`00b0facaec874a9f9a969bafec061cb9`**, launched **22:25:17 UTC** on 11-02, once. Wait limit from the in-flight record: **43,200 s**.

- **Times (UTC):** `collection done, loading into RDS` **05:20:22**; **`cloud_scrape: done duration_seconds=25736.1` at 05:34:14** (**7 h 9 min** from launch to loaded; the load took about 14 minutes against its 7,200 s limit). The bills scrape alone: **`duration 6:46:52`**. ECS: `STOPPED`, `EssentialContainerExited`, **exit code 0**. **It never reached your 9-hour line (07:25 UTC) and left a margin of about 4 h 50 min under the 12 h limit.**
- **Session:** `bills: {}` (no `start=`, a full walk) and `no session provided, using active sessions: {'2025-2026'}`: **session 2025-2026**.
- **What it found:** `bill: 5270`, `vote_event: 5858`, `jurisdiction: 1`, `organization: 3`; sidecar `{"mode": "full", "status": "ok", "found": 11132, "duration_s": 24414}`.
- **Log levels (all 27,096 lines):** INFO 27,094, DEBUG 1, **WARNING 1 (the session line), ERROR 0**, no Traceback. **No 429, 403, "Too Many", Barracuda or WAF match** in the whole run. **Not readable (as for NE and LA):** distinct pages fetched, repeats, 404 and retry counts (the scrape's log does not record individual requests); one `save bill` line per bill (5,270).
- **What production holds for Pennsylvania now (read-only, the api container's own session with `SET TRANSACTION READ ONLY`, plus the route):** **bills 5,270** (`GET /bills?jurisdiction=Pennsylvania&per_page=1`: `total_items` **5,270**), **vote events 5,858**, **person votes 425,560**; all 0 before. **Bills and vote events equal what the scraper found.**
- **S3 lock `prod/pa/_lock`:** held by `pa-0c05e786c832`, **released**. At 05:34 UTC: **0 ECS tasks, 0 in-flight records.**

## All three together (each launched once, none relaunched)
| State | Session | Launch (UTC) | Loaded (UTC) | `duration_seconds` | Bills | Vote events | Person votes |
|---|---|---|---|---|---|---|---|
| NE | 109 | 11-02 22:25:25 | 11-02 23:33:16 | 4,069.6 | 1,847 | 1,772 | 86,723 |
| LA | 2026 | 11-02 22:25:29 | 11-03 02:25:36 | 14,405.6 | 2,616 | 3,172 | 230,721 |
| PA | 2025-2026 | 11-02 22:25:17 | 11-03 05:34:14 | 25,736.1 | 5,270 | 5,858 | 425,560 |
No stop condition tripped on any; no 429, 403, "Too Many", Barracuda or WAF in any log; all three exit codes 0; all three locks released. **Measured runtimes now exist for the per-state wait limits (OPEN-476): the longest, Pennsylvania, used about 60% of the shared 12 h.** **The Sunday 11-08 02:00 UTC batch now includes `pa`, `ne` and `la` and runs states concurrently; those three alone take up to about 7 h each.** I made no config change.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
