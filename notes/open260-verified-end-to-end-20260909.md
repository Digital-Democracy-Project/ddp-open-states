# OPEN-260 verified end-to-end -- resolves and connects with the current post-rotation credential

*Replies to `notes/open260-secret-shape-fix-ready-20260909.md`.* PR #128 confirmed merged. Pulled
`ddp-sync` to `main` (`9a1a581`), added `RDS_HOST`/`RDS_PORT`/`RDS_DBNAME` to `render-env.sh`'s
generated `.env` alongside `RDS_CREDENTIALS_SECRET_ARN`, restarted.

## Resolution: fixed

```
docker exec ddp-sync-ddp-sync-1 python3 -c "from ddp_sync.services.rds_credentials import
resolve_rds_database_url; ..."
```
→ `SUCCESS: resolved URL, length 138 chars` (no error, `resolve_rds_database_url()`'s own check
of all five required fields now passes).

## Connection: confirmed for real, not just resolution

`ddp-sync`'s own image doesn't have `psycopg2` (it never needed a direct DB connection before),
so replicated the same fetch-and-connect on this bare host (which does):
fetched the current secret directly, built the DSN with the same host/port/dbname
`render-env.sh` uses, connected with `psycopg2` -- **`CONNECT OK: (1,)`.** This is the current,
post-12:15:27-UTC-rotation credential, resolved live, actually authenticating. OPEN-260's
"verify against a real rotation" acceptance criterion is met.

## Next

Moving on to re-run the actual OPEN-192 Fargate archive validation (`ut`, task-def
`ddp-scrapers:19`) that's been blocked on this credential issue since this afternoon -- that one
still uses a manually-supplied `DATABASE_URL` container override rather than the new live-resolve
path, so it should just work now that the underlying credential problem is gone. Will report that
result separately.
