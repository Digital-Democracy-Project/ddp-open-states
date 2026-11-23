# REQUEST (not a GO): certificate checks on by default (OPEN-800). (0) two read-only questions, (1) core `58205e01` on both api-v3 copies and EC2 ddp-sync, (2) image v85 (Ramon builds it), (3) **Utah canary first**, then watch Georgia. 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Steps 1–3 each wait on Ramon's go. Step 0 is read-only and can be answered now.

## Why
* Ramon decided 2026-11-23 (OPEN-800, comment 22886): "Check by default, named exceptions".
* Before, the archive's text fetch (`text_extract`) used `verify=False`, and a scraper could turn checks off per call.
* openstates-core #143, reviewed and merged by the PM session as **`58205e01`**:
    * **Every** request core makes is checked (scrape, archive text fetch, every redirect hop).
    * A scraper's own `verify=False` no longer turns checks off.
    * The only way to skip a check is an entry for one host in `openstates/utils/tls.py` `TLS_VERIFY_EXCEPTIONS`, which **ships empty**.
    * The global switches `VERIFY_CERTS` / `SCRAPELIB_VERIFY` and `os-update --no-verify` are removed. Nothing on main in ddp-open-states or ddp-sync used them.
    * Core since `9157b6b5` is only #143. **No migration.**
* **Measured from the Mac** (99 hosts the 30 states use, checks on): **92 pass**, 2 name mismatches, 5 no answer.
    * The mismatches are `www.malegislature.gov` and `webserver1.lsb.state.ok.us`. Neither is fetched over HTTPS by a production run today. No exception is proposed; Ramon decides.
    * Georgia's `www.legis.ga.gov` and `webservices.legis.ga.gov` don't answer from the Mac, so they're unverified.
    * Utah's `le.utah.gov` passes from the Mac and the image, but failed on Fargate in October (OPEN-322).

## Step 0: read-only questions (please answer in a `reply-` note)
1. Is `VERIFY_CERTS`, `REQUESTS_CA_BUNDLE` or `CURL_CA_BUNDLE` set in the **Fargate scrapers task definitions** (current revisions), or in the **EC2 ddp-sync** or **api-v3** container environments? Report names and whether set; don't print values unless they're a file path.
2. **From a Fargate scrapers task** (any current run's logs), or from EC2 if Fargate can't be read: does an HTTPS request to `https://www.legis.ga.gov/` and to `https://le.utah.gov/` succeed with normal certificate checks? A plain `curl -sS -o /dev/null -w '%{http_code}'` with no `-k` is enough. Report the codes or the TLS error text.

## Step 1: core `58205e01` (on a GO)
* As for `9157b6b5` (`ce0bf8b` step 1), with `DDP_CORE_SHA=58205e011717c0ff7449104bc157ef2fe61e6fc5`:
    * EC2 api-v3 (rollback tag, build, `up -d --no-deps api`);
    * EC2 ddp-sync at its current commit (`85c8888`);
    * the Mac api-v3 via `refresh-api-v3.sh`.
* **If `ce0bf8b` step 1 (core `9157b6b5`) hasn't run yet, do this one instead.** `58205e01` contains it, so one restart covers both.
* Post the in-flight list before the ddp-sync restart, as in `692a2ba`. Never 02:15–04:45 UTC. api-v3 not 05:00–07:00 UTC.
* Then `check-core-pin-drift.py --image-core 58205e01…` exits 0.
* **What the loader core changes for loads:** api-v3 makes no outbound fetches, and the ddp-sync loader reads Fargate output, so neither should behave differently. Report any TLS error in their logs within an hour.

## Step 2: image v85 (Ramon)
* Build at scrapers main **`6f9a1464` or later** with core main **`58205e01`**.
* The scrapers fork itself still has about 15 request paths that skip checks outside core (OPEN-803, not built). v85 checks everything that goes through core.
* Mac side checks `DDP_CORE_COMMIT` is `58205e01`.

## Step 3: Utah canary, then watch Georgia (on a GO)
1. **Before any other run on v85:**
    * `POST /ddp-sync/v1/trigger/openstates-scrape/ut` once (incremental, as its weekly), on v85's revision.
    * Not while Utah's own run or re-import holds its lock.
    * Report whether collection completes, and any `SSLError` / `CERTIFICATE_VERIFY_FAILED` line with its host.
    * **A certificate error stops the rollout:** report it, and don't let other states run on v85 until we decide.
        * Either an exception for that host, on Ramon's approval;
        * or a CA-bundle fix, if the host's chain is incomplete as seen from AWS.
2. **Then the normal schedule continues on v85.**
3. **Georgia:** its next run (Friday 12:00 UTC) is the first real check of its hosts. Report collection and archive results and any certificate error. A failure there is a stop and report, not a retry.
4. **For the first full day on v85:** report any certificate error from any state's scrape or archive, by host. I check the Mac replica for states whose version or document counts drop.

## If it goes wrong
* **Rollback:**
    * the scrapers image: register the previous revision (rev 86 / v84, or the one live before v85);
    * the core: re-tag the api-v3 and ddp-sync rollback images.
* No data is changed by a failed fetch: a run that can't connect loads nothing.

## Not authorized
* Adding any host to `TLS_VERIFY_EXCEPTIONS` (that needs Ramon and a code change).
* Setting any environment variable that turns checks off.
* Any `-k` / `--insecure` fetch.
* A retry of a failed run.
* Any other state's manual run.

Tickets: OPEN-800 (OPEN-146); follow-up OPEN-803.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
