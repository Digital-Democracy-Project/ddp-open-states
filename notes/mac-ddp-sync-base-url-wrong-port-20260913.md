# Urgent: MAC_DDP_SYNC_BASE_URL points at the wrong port -- api-v3, not ddp-sync

Ramon asked me to double-check what's actually running on port 8002 on this Mac, and it's not
what `MAC_DDP_SYNC_BASE_URL` assumes.

**Checked directly, just now:**

- `docker ps` -- port **8002** is `ddp-openstates-api-1` (`0.0.0.0:8002->80/tcp`), i.e. **api-v3**.
  No `/ddp-sync/v1/...` routes exist there at all.
- `ps aux` -- ddp-sync's own API is a native (non-Docker) `uvicorn ddp_sync.app:app --host
  0.0.0.0 --port 8001` process. **Port 8001**, not 8002.

This matches SYNC-59's own ticket description exactly ("Mac Studio's `ddp-sync` already listens
on `0.0.0.0:8001`... confirmed live today by a real dispatch of FL's 2026 session against it").

But your own status note (`4c85d30`, `notes/sync59-and-open280-status-20260913.md`) set:

```
MAC_DDP_SYNC_BASE_URL=http://10.0.0.8:8002
```

That's api-v3's port, not ddp-sync's. If the EC2 host actually POSTs to
`http://10.0.0.8:8002/ddp-sync/v1/trigger/scraper-session-legbot` right now, it hits api-v3's
container instead -- which has no matching route, so this would fail, not silently work. The
WireGuard trigger path (both SYNC-59's original design and SYNC-65/#148's archive-completion
fallback, which now depends on this same URL) has not actually been exercised end-to-end through
the real configured value, despite being reported as verified.

**Please correct `MAC_DDP_SYNC_BASE_URL` to `http://10.0.0.8:8001`** in `docker-compose.prod.yml`,
redeploy, and re-verify with a real request before relying on this path for anything --
especially before flipping `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED`. Happy to help confirm from
this side once it's corrected.
