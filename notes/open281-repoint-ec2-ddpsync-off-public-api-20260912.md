# New ticket for you: OPEN-281 -- repoint the EC2 ddp-sync instance off the public OpenStates API

Ramon's ask, same spirit as the `ddp-broker` proxy fix from earlier today: the EC2 host at
`10.0.0.1` (WireGuard + `ddp-api`) already runs a `ddp-sync` instance -- confirmed by Ramon
directly, it handles webflow CMS updates and votebot's Pinecone sync, and **it's currently
pointed at the public OpenStates API (`v3.openstates.org`)**, not DDP's own internal
production `api-v3` (`http://10.0.0.11:8002`, the real RDS-connected instance on the
`ddp-broker` host, per INFRA-1).

Two real problems with staying on the public API, not just one:
1. Reading whatever public OpenStates has, not DDP's own RDS-backed data -- potentially
   different/staler for DDP-tracked jurisdictions.
2. The public API is rate-limited to a hard 2 requests/second (confirmed earlier this
   project) -- the internal `api-v3` has no such ceiling.

**Likely shared root cause worth checking first**: `ddp-sync`'s own `OpenStates` client
class (`fetch/interfaces/OpenStates/openstates_client.py`) hardcodes
`self.api_root = "https://v3.openstates.org"` by default. This is almost certainly the
same client class `ddp-broker-py` used before today's fix (which switched it to
`DDP_OPENSTATES_API_ROOT=http://10.0.0.11:8002` + an API key, flipping from Bearer/proxy
mode to direct `x-api-key` mode -- see BROKER-41 and today's
`notes/ddp-broker-repointed-to-ec2-apiv3-20260912.md`). If this EC2 `ddp-sync` instance's
webflow/votebot code paths go through the same class, the fix pattern should look
identical: whatever env var this instance reads (or the class's own default, if nothing
overrides it there) needs to point at the internal api-v3 instead, plus a real API key
(via `profiles_profile` on that instance, same as `ddp-broker`'s fix).

**Please, on the real `10.0.0.1` host**:
1. Find the real, currently-running `ddp-sync` process/config there (same discipline as
   the `ddp-broker` fix -- check the actual systemd/launch config and running process, not
   a checked-out repo copy).
2. Confirm exactly what's pointing it at the public API today (an env var override, a
   hardcoded default with nothing overriding it, something else).
3. Repoint it at the internal production `api-v3` (`http://10.0.0.11:8002`), with whatever
   auth it needs.
4. Verify for real: an actual webflow CMS update or votebot Pinecone sync run succeeding
   against the new target, not just a health check.

Full ticket: OPEN-281 (parented under the OPEN-269 epic). One loose end: I initially
linked it as "blocked by OPEN-193" (a wrong assumption, corrected in the ticket's own
description) -- I don't have a way to delete that stale issue link from here; not urgent,
just flagging it's there and inaccurate.
