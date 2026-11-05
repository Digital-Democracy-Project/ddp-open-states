# Reply: count of page sizes asked of api-v3, and of the refusals (OPEN-493, BROKER-431). Read-only; nothing changed. Run 2026-11-05 00:32 UTC at the user's go ("yes, read it and run it if it's read-only").

**Result: no request for more than 20 bills a page on `/bills` appears in anything I still hold (about 196,000 access-log requests). So nothing on `/bills` can be relying on the refusal, as far as these logs show.** Counts only; no query string, key or address is printed here. I wrote my own counter (Python, not the suggested awk) because the log format has a space before the status and no `apikey=` in the lines I looked at; the key is not in the log lines I saw (my probes send it in a header), and my counter never printed any URL.

## What I read, and the time span of each
The log format is uvicorn's: `<peer> - "GET <path>?<query> HTTP/1.1" <status>`. **The archived files carry no timestamps**, so I cannot give dates inside them; only the time each was saved (when the container was replaced) is known from its name. Only the current container's log (read with `docker logs --timestamps`) has timestamps.
| file | saved at (UTC) | access-log requests |
|---|---|---|
| `ddp-openstates-api-1-20261028T001334Z.log.gz` | 10-28 00:13 | 96,514 |
| `ddp-openstates-api-1-20261028T004605Z.log.gz` | 10-28 00:46 | 173 |
| `ddp-openstates-api-1-20261028T020434Z.log.gz` | 10-28 02:04 | 549 |
| `ddp-openstates-api-1-20261030T183605Z.log.gz` | 10-30 18:36 | 21,698 |
| `api-v3-pre-manifest-refresh-20261102T0210Z.gz` | 11-02 02:10 | 52,188 |
| `api-v3-pre-pilot2-manifest-20261102T2011Z.gz` | 11-02 20:11 | 6,545 |
| `api-v3-pre-open481-20261102T2039Z.gz` | 11-02 20:39 | 119 |
| `api-v3-pre-pa-ne-la-20261102T2222Z.gz` | 11-02 22:22 | 531 |
| `api-v3-pre-open482-20261103T1824Z.gz` | 11-03 18:24 | 6,888 |
| `api-v3-pre-archive-flags-20261103T2056Z.gz` | 11-03 20:56 | 656 |
| `ddp-openstates-api-pre-recreate-20261104T1924Z.log.gz` | 11-04 19:24 | 8,305 |
| `ddp-openstates-api-pre-open422-20261105T0025Z.log.gz` | 11-05 00:25 | 1,889 |
| the current container (started 00:25 UTC) | `docker logs --timestamps`, 00:25:30 to 00:31:13 | 65 |
**Coverage gaps I know of (retention):** these are the logs of the containers I saved before a recreate. I did **not** save one before the api-v3 releases of **10-31** (OPEN-467 at 20:43 and OPEN-469 at 23:31 UTC), so the container that ran from **10-30 18:36 to about 10-31 20:43, and the short one after it, are not here**. The earliest file starts at whatever the container held at 10-28 00:13 (the start is not known; its 96,514 requests are the largest file). So: **everything from about 10-27 to 10-30 18:36, and from 11-02 02:10 to now, but with a hole of about two days around 10-31.** Docker's own log of a replaced container is gone.

## 1. Table: `/bills`, by `per_page` and status (all files together; "none" = no `per_page`)
| `per_page` | status | requests |
|---|---|---|
| none | 200 | 11,866 |
| 20 | 200 | 7,254 |
| 1 | 200 | 53 |
| 5 | 200 | 4 |
| 3 | 200 | 2 |
| none | 400 | 4 |
| 1 | 400 | 2 |
| 1 | 403 | 2 |
The `none` rows with 200 are mostly the many calls that read bills by their own id and calls that list without a page size. **Every other endpoint that carries a `per_page`, by value:**
- `/bills`: 1 (57), 3 (2), 5 (4), **20 (7,254)**
- `/people`: 1 (19), 3 (65), 10 (28), **50 (1,370)**
- `/jurisdictions`: 1 (77), **52 (9)**
- `/people/{id}/votes`: 1 (1), 3 (1), 20 (3), **50 (5)**
Status codes over all 196,000 requests: **200 196,048; 400 44; 404 23; 403 6; 307 1.**

## 2. Requests with `per_page` above 20 on `/bills`
**None in any file I hold.** The only requests with a `per_page` above 20 anywhere are on other endpoints and all answered 200: `/people` with 50 (1,370, which is that endpoint's own cap: VoteBot's roster reads), `/people/{id}/votes` with 50 (5) and `/jurisdictions` with 52 (9). So the cap on `/bills` has **never been tested by a caller in these logs** and no refusal of that kind exists (the request expected 400s; there are none).
**Caller classes:** the log's peer is **not informative here**: 12,816 of the `/bills` requests show the docker bridge's gateway address (traffic arriving through the published port is NAT'ed to it) and 6,371 show another private docker address (calls from containers on the same host); **I cannot tell the broker, the Mac Studio, the civic host or ddp-sync apart from this log.** This is a limit of the log, not an answer.

## 3. 400s that are not a `per_page` one
**On `/bills`: 6 in all, and none has a `per_page` above 20** (4 with no `per_page`, 2 with `per_page=1`); I cannot say what made them 400 (the log keeps only the status). On other endpoints: **`/ddp/search` 38**. Those 38 are **mine**: I sent a wrong `types=` value while timing search earlier on 11-04 (12 + 12 + 12 + 2 calls; the note `1f82173` describes the error). So a "normal" 400 on `/bills` is rare: 6 in about 19,000 `/bills` requests.

## 4. Odd things in the log format or retention
- The archives have **no timestamps**, so "on which dates" cannot be answered from them.
- The two-day hole around 10-31 (above).
- Nothing else odd in the format. Access-log lines for the key-checked routes show 403 (6 in all) as expected.

## Not done
No change of any kind. The OPEN-493 build and its recreate were not asked and not done. If Ramon wants the 10-31 hole closed, the only source would be any copy of those logs I do not hold.
