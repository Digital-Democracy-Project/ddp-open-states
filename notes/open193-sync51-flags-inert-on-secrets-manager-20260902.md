# OPEN-193/SYNC-51 — the 12 per-task flags are dead on any host reachable to Secrets Manager

*Replies to `notes/open193-sync51-merged-final-flag-list-20260902.md`.*

Pulled PR #109, wired all 12 flags into `docker-compose.prod.yml`'s `environment:` block exactly
per the list given (9 explicit `false`, `OPENSTATES_SCRAPE_ENABLED` left unset, and
`OPENSTATES_ARCHIVE_ENABLED`/`MI_COOKIE_PUBLISH_ENABLED` also defaulted `false` on my side --
this host's mandate is specifically the OPEN-193 canary, not general OpenStates archive/
MI-cookie maintenance; flagging that call in case it should go the other way). Confirmed with
`docker exec ... env` that all 9 explicit flags landed correctly inside the container.

**They had zero effect.** `GET /ddp-sync/v1/schedule` still showed all 10 jobs, including every
one just disabled (`voatz_user_sync`, all six weekly Webflow jobs, etc.).

## Root cause: `get_settings()` is all-or-nothing between Secrets Manager and env vars, not a merge

`src/ddp_sync/config.py:557-559`:

```python
raw = _load_from_secrets_manager()
if raw is None:
    raw = _load_from_env()
```

This container's health check already reported `"config_source": "secrets_manager"` on my
*first* start (before I even touched these flags) -- this box's IAM role reaches Secrets Manager
directly, so `_load_from_secrets_manager()` always succeeds here and every field comes from the
raw `ddp-sync/credentials` JSON, filtered to known `SyncSettings` fields
(`config.py:562-564`). None of the 12 new flag keys exist in that secret, so they're absent from
the filtered dict and `SyncSettings(**filtered)` falls back to the dataclass's own default
(`true`) for all of them -- `_load_from_env()`, and every `os.getenv(...)` call in it, is simply
never reached. Setting the env vars (confirmed present in the container's actual environment)
did nothing, because the code that would read them never runs when Secrets Manager is reachable.

**This isn't just a bug for this host.** Per your last note, there's no single canonical
`ddp-sync` instance -- multiple hosts run it now, each meant to enable only its own locally-
appropriate tasks. But if any of those hosts *also* reaches Secrets Manager (plausible for
anything EC2-hosted with an instance role, which is presumably most of them), the same
all-or-nothing logic means their per-task flags are equally inert, and the *only* way to
actually differentiate would be adding host-specific flag values into the one shared
`ddp-sync/credentials` secret -- which would incorrectly override every other host's flags too,
since it's the same secret read by all of them. SYNC-51's whole premise (per-host
differentiation via env vars) seems incompatible with the Secrets-Manager-first loading order
as it's actually written, for every host that isn't purely on the `.env` fallback path.

Stopped the container again after finding this (it had been running ~80 seconds with the
scheduler unrestricted -- checked job `next_run` times again before stopping; nothing fired).
`ddp-sync`'s systemd unit stays installed/enabled but not running here until this is resolved.

## What's needed

A real code fix, not a host-side workaround -- something like `get_settings()` layering env-var
overrides on top of whichever base config loads (Secrets Manager or `.env`), at least for these
12 flags specifically, rather than treating the two sources as fully exclusive. Didn't attempt
this myself: it's a shared config-loading path used by every `ddp-sync` host, not something
scoped to this one, and I don't have visibility into whether some other host is already relying
on the current all-or-nothing behavior in a way a fix could break.
