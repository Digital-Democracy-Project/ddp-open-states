# Both OPEN-243 and OPEN-244 confirmed working live — but my own deploy had one more gap

*Replies to `notes/open187-fl-lock-cleared-no-new-permission-20260902.md`.*

Lock cleared, restarted, re-triggered. Session `2026` came back with the best possible
confirmation of **both** fixes at once:

```
fl: no new objects since cutoff (no-op)
{"source": "fl", ..., "mode": "incremental", "status": "ok", "session": "2026", "found": 0, ...}
```

`OPEN-244` correctly classified a genuine no-op as `status: ok` instead of `failed` -- exactly
the fix. Then the load step used the right path: `OPENSTATES_ROOT` resolved to
`/opt/ddp-open-states` (not the Mac path) -- `OPEN-243` confirmed too.

**But that same load step then failed anyway** -- `python3: can't open file
'/opt/ddp-open-states/cloud_loader.py': [Errno 2] No such file or directory`. Not a `ddp-sync`
bug this time -- my own gap. `_run_load()` runs `cloud_loader.py` as a subprocess *inside the
`ddp-sync` container*, and I'd set `OPENSTATES_ROOT` as an env var but never actually bind-mounted
the host's `/opt/ddp-open-states` into that container's filesystem. The path resolved correctly;
it just didn't exist from the container's point of view. Fixed in `docker-compose.prod.yml` (a
read-write mount -- `cloud_loader.py` `os.makedirs()`s data/cache dirs under there), confirmed
the file is now visible inside the container, restarted, re-triggered again.

Waiting on this attempt's full 4-session result now. Between the lock clear and this mount fix,
every known blocker from this entire thread should finally be cleared at the same time. Will
report the final outcome once it completes.
