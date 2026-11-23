# REQUEST (not a GO): Pennsylvania go-live. Roll out ddp-open-states main with #458 (PA `status: live`; search refresh, embedding, API smoke test and QA sweep on), then check each switch took. 2026-11-23 (Mac side, Onboard New States)

**This waits for Ramon's go in your session or through the PM session.** Ramon decided "Go now" for Pennsylvania (2026-11-23, via the PM session's /ask-me; recorded on OPEN-447 and OPEN-478). This note isn't that go: start only on it.

## Why
* #458 (merged by the PM session as **`e5fe4140`**) is the last manifest step for Pennsylvania.
* Routing and LegBot have been on since 11-08. The spot check (OPEN-447 comment 22530) found every one of 18 PA roll calls matching palegis.us, and every PA vote linked to a person.
* **BROKER-579 (veto overrides count as passage), which held PA, is in image v79** (ddp-scrapers:81, scrapers `0292506c`; checked by the PM session).
* For **pa** only, #458 changes:
    * `status: scraping → live`;
    * `enrollment.search_refresh`, `embedding`, `api_smoke_test` and `qa_sweep`: false → true, like every live state.
* Nothing else for PA changes: the scrape schedule, `replica_routing`, `legbot_replica` and `archive.enabled` stay as they are.

## What the rollout brings in
* The rollout pulls `/opt/ddp-open-states` to `origin/main`, which is **`e5fe4140`** or later. Since your last rollout (`5a0eb41b2`, `bce6eef`), main gained three merges:

| Merge | What |
|---|---|
| #464 `b255d694` | docs only (OPEN-767) |
| #461 `6b40bc22` | **Idaho to `scraping`** (Ramon: "Go: merge and scrape"; its first-scrape request is ddp-sync notes `46ab1e0`) |
| #458 `e5fe4140` | **PA live** (this request) |

* **So this rollout also moves Idaho to `scraping`, and Idaho's request (`46ab1e0`) needs the same rollout.** Whichever request runs first does the rollout for both, and the other skips its rollout step and reports the commit already in place.
* No validator change since `5a0eb41b2`, so pull first isn't needed. It's harmless if you do.

## What I need from you (on Ramon's go)
### 1. Gates
* `origin/main` at `e5fe4140` or later. `origin/main:jurisdictions.yaml` shows `pa` with `status: live` and the four switches true.
* **Nothing for `pa` is running.** PA's nightly starts 04:00 UTC: its scrape, archive and LegBot steps must have finished. `--skip-ecs-check` is fine only for the usual reason (another state's task is running, and nothing for pa).

### 2. Roll out
* `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`.
* Report the commit, "OK: N jurisdiction(s) valid", "every list compared agrees", and the api-v3 copy's md5.
* No restart, no other change.

### 3. Checks right after (read-only; report each)
* `/ddp/enrollment` (from the broker's web container) lists **pa as `live`**, with search_refresh, embedding, api_smoke_test and qa_sweep true. **id is `scraping`.**
* Both drift checks exit 0.
* ddp-sync `GET /schedule` shows the same jobs as before; pa's nightly is unchanged.

### 4. Read-only, in your next reports
* **Search refresh and embedding:** the next run after PA's nightly includes pa. The first embedding run covers every PA bill the version cache doesn't know yet (SYNC-95), so it is longer than usual. Report its count and runtime, and any error.
* **API smoke test and QA sweep:** their next runs include pa. Report pass or fail.
* **Veto overrides:** the first PA nightly on rev 81 or later. Report the revision it ran.

## If it goes wrong
* **A failed check:** stop and report.
* **The way back:** a PR setting pa back to `scraping` with those four switches false (I'll write it), then a rollout. Don't hand-edit the manifest.

## Not authorized
* Any other state's switch beyond what main already carries (Idaho's `scraping`, per its own go).
* A scrape, recompute or relabel.
* Any change to routing, LegBot or the schedule.
* Nebraska or Louisiana: their requests come separately.

Tickets: OPEN-478, OPEN-447 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
