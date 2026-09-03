# usa failed both attempts (lower, then upper) — full evidence, one detail worth double-checking against OPEN-216/220

*Replies to `notes/open193-mi-cookie-correction-sync53-20260902.md`.*

As part of the 9-jurisdiction canary: `usa` failed both times it ran (lower chamber, then
upper chamber -- ddp-sync's own `run_usa_scrapes_job` runs them sequentially). Identical
traceback both times:

```
Traceback (most recent call last):
  ...
  File ".../openstates/scrape/base.py", line 365, in do_scrape
    raise ScrapeError(
openstates.exceptions.ScrapeError: no objects returned from USBillScraper scrape
ERROR: usa scrape failed, exit 1
{"source": "usa", "run_id": "usa-13d0565e8c76", "status": "failed", "mode": "full", "session": "119 chamber=lower", "duration_s": 1}
{"source": "usa", "run_id": "usa-e7d3ed5ca3b0", "status": "failed", "mode": "full", "session": "119 chamber=upper", "duration_s": 1}
```

Both hit the sitemap fetch (`GET https://www.govinfo.gov/sitemap/bulkdata/BILLSTATUS/
sitemapindex.xml`) then immediately raised, 1 second in.

**One thing worth double-checking against what OPEN-216/220 actually track:** both runs show
`"mode": "full"`, not incremental -- this is the first-ever cloud-path attempt for `usa` on this
host, so there's no watermark to have made it incremental yet. If OPEN-216/220 specifically
describes an *incremental*-window crash, this might be either the same underlying
`USBillScraper`/govinfo.gov issue manifesting on a full crawl too, or a related-but-distinct
symptom worth its own look. Flagging the exact shape rather than assuming it's a 1:1 match,
per your own "report it, don't spend time re-investigating" instruction -- just making sure
what gets filed under that ticket actually matches what happened.

Not investigating further myself. Moving on to the remaining jurisdictions (`wa`/`ma`/`ut`/`az`
still running as of this note).
