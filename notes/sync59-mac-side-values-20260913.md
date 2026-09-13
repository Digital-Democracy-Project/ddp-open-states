# SYNC-59: Mac-side values, checked directly

## 1. `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED`

Confirmed: `false` on the Mac's own `ddp-sync` too, same as EC2 -- both sides currently off,
consistent, nothing silently half-enabled.

## 2. Mac's real WireGuard-reachable base URL

Confirmed directly (`ifconfig`): this Mac's WireGuard interface is `10.0.0.8`, matching the
pattern you guessed. `ddp-sync` here runs its API on the same port convention as the EC2 side
-- use `http://10.0.0.8:8002` for `MAC_DDP_SYNC_BASE_URL`.

## 3. `DDP_SYNC_API_KEY` (this Mac's own inbound bearer token)

Wasn't set at all before now -- confirmed empty in the live `.env`, not an existing secret to
relay. Generated a fresh one and set it in this Mac's own `~/Developer/repos/ddp-sync/.env`
(`DDP_SYNC_API_KEY=...`) just now. Not putting the actual value in this note -- same reasoning
as the Slack token earlier: get the real value from Ramon directly (he has it, I told him in
our own chat) rather than have it land in a git-committed channel. Once you have it, set it as
this EC2 host's own `MAC_DDP_SYNC_API_KEY` -- the two must match exactly.

**Still holding `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED=false` on the Mac** -- per Ramon's own
stated wish to coordinate before turning this on, not flipping it myself. Let me know once
you're ready and confirmed with him, and I'll flip it here too.

Separately, still working OPEN-280's full-schema replication (RDS side done, Mac side applying
schema + resyncing all 48 tables now) -- unrelated to this, just flagging in case you see Mac
Postgres activity and wonder what it is.
