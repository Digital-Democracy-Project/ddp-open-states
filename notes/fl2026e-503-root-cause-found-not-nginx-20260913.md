# FL 2026E test: 503 root cause found -- not nginx, a missing production broker config

Confirmed there's no nginx anywhere in front of `ddp-sync` on the Mac at all (`ps aux`, no
process; no config found; not a brew service) -- Ramon's nginx suspicion was reasonable
but not it.

**Real cause, confirmed directly in code and the Mac's own logs.** Found all 8 real 503
responses in `ddp-sync`'s log (`10.0.0.1` -- the WireGuard gateway -- hitting
`POST /ddp-sync/v1/trigger/scraper-session-legbot`, four session codes x two attempts
each, all `503 Service Unavailable`, returned directly by the FastAPI app itself, not an
infra layer). Traced why: `trigger_scraper_session_legbot`'s handler calls
`_resolve_batch_broker_target(x_ddp_environment)` first thing, and that function raises
exactly:

```
HTTPException(status_code=503, detail="ONDEMAND_BROKER_API_BASE_PROD is not configured "
"-- production ddp-broker-py routing isn't set up on this instance yet.")
```

whenever `X-DDP-Environment: prod` is set (which your caller does, per this route's own
docstring: "SYNC-59's own caller sends `X-DDP-Environment: prod`") and
`settings.ondemand_broker_api_base_prod` is empty. Checked the Mac's `ddp-sync/.env`
directly: both `ONDEMAND_BROKER_API_BASE_PROD` and `ONDEMAND_BROKER_API_TOKEN_PROD` are
present but commented out, with what look like correct, real values already sitting right
there:

```
#ONDEMAND_BROKER_API_BASE_PROD=https://api.digitaldemocracyproject.org/broker
#ONDEMAND_BROKER_API_TOKEN_PROD=ddp-rw-XDH6CW-KCBWw_LtPlmMiXxfmwUrHEITz3NXAvVCaU6Q
```

This on-demand `X-DDP-Environment: prod` path for this specific route had apparently
never been exercised before this test, so nothing surfaced this gap until now.

**Ready to uncomment both lines and restart** -- want me to go ahead, or would you rather
confirm those are the actual current, correct production broker base/token first (they
look right, matching the already-active `DDP_BROKER_API_BASE`/`DDP_BROKER_API_TOKEN`
values two lines above, also currently commented, which is a separate, pre-existing
question of whether those should be live too)?

Also noting your separate flag about the 60-day lookback resolving 4 sessions (2026F/E/D/
plain-2026) instead of just 2026E -- that's a real, separate thing to narrow before
retrying, once this config gap is fixed.
