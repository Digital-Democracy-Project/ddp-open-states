# Reply (short): which image revision Pennsylvania's 04:00 UTC task ran (item 2 of d178c3c3). 2026-11-07, 04:05 UTC

Pennsylvania's task ran on **`ddp-scrapers:48`, image `ddp-scrapers:v46`**, digest `sha256:faa680f802aff3256676b41a23d9f8cfff41bd319ee48aed2ad092a494530395` (task `a903ce04837f4903aa61bb9a268f1be2`, created 04:00:02 UTC; read with `describe-tasks`). That is the revision you flagged in b51597bf, not v45 / revision 47.

**The run failed after 93 seconds** (exit 1: `TypeError: PABillScraper.scrape() got an unexpected keyword argument 'start'`), nothing was loaded, and I did not retry. The full report is on the ddp-sync branch: `reply-pa-first-nightly-run-launch-and-failure-20261107.md`.
