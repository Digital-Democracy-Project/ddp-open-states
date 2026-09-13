# FL 2026E test: real trigger fired, got 503 from every attempt -- Ramon suspects nginx, please investigate

Fired the real archive-completion-hook path for real (in-memory-only settings override, no
persistent config change -- confirmed the standing `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED`
config on this host is untouched). `_maybe_trigger_legbot_for_archive('fl', ...)` ran the real
code path end to end: `_mac_capable()` correctly `False`, `resolve_touched_sessions` correctly
resolved real touched FL sessions, then attempted the real WireGuard POST to
`http://10.0.0.8:8001/ddp-sync/v1/trigger/scraper-session-legbot` for each.

**Every attempt came back `503 Service Unavailable`** -- not a connection failure. Confirmed
separately that `http://10.0.0.8:8001/ddp-sync/v1/health` responds normally (`200`, `healthy`,
scheduler running, redis connected) at the same time, so this isn't a total outage of the
Mac's `ddp-sync` process -- something specific to this trigger route (or a layer in front of
it) is failing.

**Ramon's suspicion: this looks like an nginx-level 503**, not the application itself. Could
you check the Mac's nginx config/logs (if `ddp-sync` sits behind nginx there) alongside
`ddp-sync`'s own logs around this timestamp for the real cause? Real request time:
2026-09-13 ~20:16:14-15 UTC, four requests about a second apart, all for jurisdiction FL,
session_codes 2026F/2026E/2026D/2026.

**Separately, worth flagging**: my lookback window (60 days, chosen to safely cover 2026E's
last known document update on 2026-07-26) resolved FOUR touched FL sessions -- 2026F, 2026E,
2026D, and a bare 2026 -- not just the intended 2026E. All four failed the same way, so nothing
actually generated anywhere (clean failure, not partial), but before retrying I want a tighter
window that only picks up 2026E, to keep this test to the agreed 22-bill scope. Will work that
out once we understand the 503 first.

Not retrying yet -- want the root cause first, and a narrower window before firing again.
