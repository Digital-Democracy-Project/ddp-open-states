# Real credential leak: RDS_OPENSTATES_API_KEY is being logged in plaintext on every api-v3 call, systemically

Found while digging into tonight's LegBot-trigger bug (see
`legbot-trigger-false-negative-on-transient-network-blip-20260916.md`) -- a separate, real issue,
not the same one.

## What's happening

`local_openstates_client.py`'s api-v3 calls authenticate by putting the key in the URL's own
query string: `params["apikey"] = settings.rds_openstates_api_key` (or
`local_openstates_api_key`), then `httpx.AsyncClient().get(url, params=params)`. httpx's own
default logger emits an INFO-level line for every request in the form
`"HTTP Request: {method} {url} \"{http_version} {status_code}\""` -- and that `{url}` includes
the full query string, `apikey` included.

`ddp-sync`'s own logging setup (`app.py`, `logging.basicConfig(...)`) configures the root logger
generically, so httpx's own logger propagates straight through with no filtering. Confirmed live
tonight -- a real WA archive-trigger check produced this exact line in this container's own logs
(and, if these ship to CloudWatch the way the scraper Fargate logs do, there too):

```
httpx INFO HTTP Request: GET http://10.0.0.11:8002/bills?jurisdiction=WA&document_updated_since=...&apikey=<the real key>&per_page=20&page=1 "HTTP/1.1 200 OK"
```

I did not re-print or forward the actual value anywhere past my own terminal session on this
host, but the key is now sitting in this container's log history regardless of anything I did --
this is a pre-existing, systemic pattern, not something introduced tonight. Every one of
`local_openstates_client.py`'s ~7 functions that authenticates this way (`get_bill_detail`,
`get_archived_bill_text`, `get_current_version_identity`, the changelog-inputs refetch,
`list_current_session_bill_candidates`, `resolve_touched_sessions`, at minimum) leaks the same
way, every time it runs, on both `local_openstates_api_key` and `rds_openstates_api_key`.

## Ask

1. **Rotate `RDS_OPENSTATES_API_KEY`** (and `LOCAL_OPENSTATES_API_KEY` if it's had the same
   exposure on the Mac) -- treat both as already-exposed, not hypothetically at risk.
2. **Stop the leak at the source**, a few options, roughly in order of how much they cover:
   - Silence or downgrade httpx's own request logger specifically
     (`logging.getLogger("httpx").setLevel(logging.WARNING)`), the smallest fix but leaves any
     other httpx caller with the same pattern exposed if one gets added later.
   - Send the key as a header (`X-API-KEY`) instead of a query param everywhere it currently
     rides in the URL -- api-v3's own `apikey_auth` already accepts either
     (`x_api_key or apikey`, confirmed by reading its source), so this needs no api-v3-side
     change, just switching the client calls. Closes the leak at the root cause rather than
     just suppressing the one logger.
   - If URL-based auth needs to stay for some reason, a logging filter that redacts known
     query-param names (`apikey`) before formatting would catch it regardless of which client
     library is used in the future.

Not fixing this myself -- it's a real code change across a shared client module, and I don't
want to guess at which approach fits this codebase's own conventions. Flagging with full detail
so whoever picks it up doesn't have to re-derive the mechanism.
