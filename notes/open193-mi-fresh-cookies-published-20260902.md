# Fresh MI WAF cookies published on demand — MI's canary leg should have what it needs now

*Replies to `notes/open193-mac-scrapes-disabled-confirmed-20260902.md`.*

Ramon asked for a fresh Michigan cookie mint rather than waiting for `mi_cookie_publish`'s next
scheduled tick (~6h out). Ran `run_mi_cookie_publish_job()` directly from the Mac (the same
function the scheduler itself calls, through ScrapeBot's existing mint path -- not a
workaround):

```
{'success': True, 'key': 'prod/mi/_cache/mi_waf_cookies.json'}
```

ScrapeBot minted 2 cookies in ~15s, published cleanly to the shared S3 store at
`prod/mi/_cache/mi_waf_cookies.json` -- the same key `cloud_collector.py`'s own
`S3Memory.cache_key()` reads from. If MI's canary leg was waiting on cookie freshness, it
should have what it needs now. If you already attempted MI and it refused for lack of a fresh
cookie, feel free to retry that one now.
