# Report: NM's first scrape FAILED on revision 68: the votes scraper needs pandas and the image has none. Not retried.

Written 05:45 UTC 11-18 (date -u at write time). From the production EC2 host. Follows 660b5263e. Per your GO, a failed run is not retried; nothing else was done.

## What happened (run nm-88f44afc3e2b, ddp-scrapers:68, launched 05:24:35 UTC)
- The bills scraper read NM's pages and the run reached the **votes scraper** (OPEN-592 reads it for NM). At 05:25:31 it fetched its first vote PDF (votes/HB0001SVOTE.PDF) and crashed:
  - `scrapers/nm/votes.py` line 111 in parse_vote: `pdf_table_df = pdf_tables.tables[0].to_pandas()`
  - `/opt/venv/lib/python3.13/site-packages/pymupdf/table.py` line 1557 in to_pandas: `import pandas as pd`
  - **`ModuleNotFoundError: No module named 'pandas'`**
- The scraper logged "nm scrape failed, exit 1" (summary line: mode full, status failed, duration 20 s, run nm-88f44afc3e2b). The Fargate task exited 1; ddp-sync logged "cloud_scrape: collection failed ... Essential container in task exited", and **`openstates_pipeline: done archived=None duration_seconds=91.8 failed=1 status=failed`** at 05:26:07. (Observed fact: the image's Python 3.13 venv does not have pandas. I did not look at the Dockerfile or the requirements to say why.)
- The scraper's active-sessions line was reached (the log shows session 26 Regular pages being fetched); I did not capture the session set it printed before the crash.

## State now
- **Nothing was loaded:** NM has **0 bills and 0 vote events** in RDS, no archive step ran (archived=None), no LegBot.
- **The S3 lock is released:** _lock holder nm-88f44afc3e2b has expires_at one second before acquired_at (a released lock), so it will not block a later run.
- **NM is at `scraping` on EC2 since the 05:24 rollout, so it is in the Sunday 11-22 02:00 weekly batch.** Unless the image gets pandas (a v66 build) or a PR sets NM back to probing before then, **that run will fail the same way** (and hold a Fargate task for a minute or two). I will not edit the manifest by hand.

## What I need from you
Which way: a new image with pandas (then a revision GO), or a PR returning NM to probing (then a rollout). I will not run NM again, change the manifest or touch the image without a GO note and the user's word.
