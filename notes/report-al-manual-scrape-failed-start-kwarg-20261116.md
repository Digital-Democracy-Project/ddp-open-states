# Report: Alabama's manual scrape FAILED after 2 s on revision 63: `ALBillScraper.scrape() got an unexpected keyword argument 'start'`. Not relaunched; section B is blocked. 2026-11-16 07:37 UTC (prod agent)

For the dev agent. Follows `07a9d850` (al and la launched). **No relaunch of al** (your rule: a failure is a report, not a relaunch; and nothing authorizes one). **la is still running normally.** The user was alerted by the CAMS message.

## What happened (observed)
- **Run `al-2086d764108a`**, task `9175a3b3a5564709a86dd0fbe7ca83b4` on **`ddp-scrapers:63`** (read from ECS), launched 07:34:55 UTC. ddp-sync 07:36:28: `cloud_scrape: collection failed detail='Essential container in task exited' exit_code=1`, `openstates_pipeline: done archived=None duration_seconds=91.8 failed=1 ... status=failed`; `operator_alert_sent_via_cams http_status=202`. Nothing was scraped, loaded or archived; vote events and bills unchanged (2,550 and 1,507).
- **The task's own log (CloudWatch, 07:35:37 to 07:35:38):** `al (scrape)`, **`bills: {'start': '2026-11-15T02:08:44'}`**, the jurisdiction and three organizations saved, `no session provided, using active sessions: {'2026rs'}`, then `os-update ... do_scrape ... TypeError: ALBillScraper.scrape() got an unexpected keyword argument 'start'`, `ERROR: al scrape failed, exit 1`, and `{"source": "al", "run_id": "al-2086d764108a", "mode": "incremental", "status": "failed", "duration_s": 2}`. Exit code **1** (not 90), so it is a crash, not the lock refusal PA had.

## Why (read from the code; I have not run anything to prove it)
- `cloud_collector.py`: `mode = "incremental" if found_watermark else "full"`, and the hydrated `.ts` watermark becomes `--start` for the scraper **whenever a watermark exists**. **Sunday's Alabama run (`al-5e2e5c22bba3`) was `mode: "full"`**: the first Alabama run had no watermark, so it passed no `start` and worked, and it then wrote the watermark (the `02:08:44` above is in that run's window). **Today's was Alabama's first incremental run, so it passed `start` to a scraper that does not accept it.**
- **The manifest already says so, and nothing reads it for this:** `jurisdictions.yaml` (line 535) has Alabama's `scrape.start_filter: false` with the comment that `scrapers/al/bills.py`'s `scrape(self, session)` takes no `start=`. **A search of the ddp-sync source finds no read of `start_filter`**, and `cloud_collector.py` does not consult it. So `start_filter: false` does not stop `start` being passed on the cloud path.
- **This is the same class as Pennsylvania's first nightly on 11-07** (`TypeError`, `start` kwarg; my note from that day). **I expect every future Alabama run to fail the same way** while the watermark exists (a failed run publishes no new watermark), including next Sunday's 02:00 batch, **and any other state whose scraper takes no `start`** and has a watermark. NC, NE and LA ran incremental today without this error, so their scrapers accept it (I did not check why NC's manifest comment says otherwise).

## What this blocks
**Alabama's section B** (needs an Alabama run that has finished its import and archive): **blocked.** Alabama's search rebuild and the 11-22 batch are affected the same way.

## Options for you (not mine to choose; nothing here is authorized)
1. Make the Alabama scraper accept and ignore `start`, or make the collector skip `--start` when the manifest says `start_filter: false` (it needs the flag in the task environment; ddp-sync does not send it today). A new image is Ramon's step.
2. A one-off full Alabama run by clearing Alabama's watermark in S3 (`prod/al/`, the `.ts` marker): that is a change to the scraper's memory store, **not authorized**, and I have not touched it.

I changed nothing for Alabama and did not touch its locks (the failed run released its lock normally: the collector's `finally`).
