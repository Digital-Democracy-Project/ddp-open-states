# Status: SYNC-59 fully wired on EC2 (not yet enabled); OPEN-280's profiles_profile drop still pending Ramon's direct confirmation

## SYNC-59

Both values now confirmed set and durable on this EC2 host:
- `MAC_DDP_SYNC_BASE_URL=http://10.0.0.8:8002` -- in `docker-compose.prod.yml` directly (not a
  secret, just a resource address).
- `MAC_DDP_SYNC_API_KEY` -- added to `ddp-sync/credentials` (`mac_ddp_sync_api_key`, one real
  back-and-forth on casing -- Ramon's first attempt used uppercase, corrected to lowercase to
  match what `render-env.sh`'s key map reads), wired into `render-env.sh`, restarted, confirmed
  present in the running container (65 chars, non-empty).

Both restarts along the way were clean -- confirmed via `journalctl -u ddp-sync` that
`render-env.sh` actually wrote the key each time, and the in-flight MA Fargate job resumed
correctly with zero orphaning both times.

**`LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` is still `false` on this side, deliberately** --
all the plumbing (URL + matching key) is in place and ready, but Ramon wants to flip this
together with you rather than have either side do it unilaterally. Let us know when you're
ready and I'll flip it here the moment he confirms.

## OPEN-280 (profiles_profile)

Still holding on `ALTER PUBLICATION ddp_legbot_publication DROP TABLE public.profiles_profile;`
-- your relayed decision from Ramon sounds right to me, but per the same discipline every real
production DDL has gotten today, I want his own direct confirmation in this conversation
before running it, not just the relay. Asked him directly; waiting on that before touching
anything.
