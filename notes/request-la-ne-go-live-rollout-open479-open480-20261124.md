# REQUEST (not a GO): **Louisiana and Nebraska go-live.** Roll out ddp-open-states main with #466 (LA) and #465 (NE), then check each switch took. 2026-11-24 ~14:10 UTC (Mac side, Onboard New States)

**This waits for Ramon's go in your session.** Ramon approved both scorecard lists and the go-live for LA and NE (2026-11-24 ~05:15 UTC, via the PM session's /ask-me; recorded on OPEN-480 and OPEN-479), and the PM session merged both PRs. This note isn't the go. Confirm with him, as for every relayed answer.

## Why
* **LA (OPEN-480):** your 11-23 re-import (`d32c574`) verified on the Mac: 0 of 230,721 votes unmatched; links 44 + 44; Stage 3 passes.
* **NE (OPEN-479):** your 11-23 re-import (`da4f695`) verified: 7 of 86,723 votes unmatched (the bare "Meyer" of 01-14, none counted on a scorecard; OPEN-838's fix is optional per Ramon); links 292 + 292; Stage 3 passes.
* Both were already scraping with `replica_routing` and `legbot_replica` on. For **la** and **ne** the merges change only:
    * `status: scraping → live`;
    * `enrollment.search_refresh`, `embedding`, `api_smoke_test`, `qa_sweep`: false → true, like PA (`request-pa-go-live-rollout-open478-20261123.md`).

## What the rollout brings in
`origin/main` = **`c9274b3`** or later. Since your last rollout (main `f721770`), main gained:

| Merge | What |
|---|---|
| #479 `1109edf` | Maryland's presiding officers in the manifest (OPEN-815). **Already in v86** via the image; this rollout brings the hosts' copy level |
| #466 `aed0519` | **LA live** |
| #465 `c9274b3` | **NE live** |

* Files: `jurisdictions.yaml` and `test_validate_jurisdictions.py` only. **No validator change**, so pull first isn't needed (it's harmless).

## What I need from you (on Ramon's go)
### 1. Gates
* `origin/main` is at `c9274b3` or later; its `jurisdictions.yaml` shows `la` and `ne` with `status: live` and the four switches true.
* **Nothing for `la` or `ne` is running:** no task, no load, no archive, no LegBot step. `--skip-ecs-check` only for the usual reason (another state's task is running).

### 2. Roll out
* `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`.
* Report the commit, "OK: N jurisdiction(s) valid", "every list compared agrees", and the api-v3 copy's md5.
* No restart, no other change.

### 3. Checks right after (read-only; report each)
* `/ddp/enrollment` lists **la and ne as `live`**, with search_refresh, embedding, api_smoke_test and qa_sweep true. **md, nm and the others stay `scraping`.**
* Both drift checks exit 0.
* ddp-sync `GET /schedule` shows the same jobs as before.

### 4. Read-only, in your next reports
* The next search refresh and embedding runs include la and ne. The first embedding run for each is longer (the first pass, as SYNC-95 for PA): report the counts, runtimes and any error.
* The next API smoke test and QA sweep include them: pass or fail.
* After the next scorecard chain: `validate_scorecards --jurisdiction LA --all`, `reconcile_scorecards --jurisdiction LA`, and the same for NE. Expect no discrepancies.

## If it goes wrong
* **A failed check:** stop and report.
* **The way back:** a PR setting the state back to `scraping` with those four switches false (I'll write it), then a rollout. No hand edits.

## Not authorized
* New Mexico's go-live (#480 stays held until its v86 re-import shows 0 unmatched).
* Any other state's switch.
* A scrape, re-import, recompute or relabel.
* Any routing, LegBot or schedule change.

Tickets: OPEN-480 (LA), OPEN-479 (NE), OPEN-447 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
